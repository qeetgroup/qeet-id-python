import base64
import functools
import json
import time
from collections.abc import Callable
from typing import Any

import anyio
import httpx2
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from qeet_id import APIError, NetworkError, TokenVerificationError
from qeet_id._async import _token_verifier as async_module
from qeet_id._sync import _token_verifier as sync_module
from qeet_id.tokens import AsyncTokenVerifier, TokenVerifier

from .conftest import Kind, run

pytestmark = pytest.mark.anyio

ISSUER = "https://api.id.qeet.in"
AUDIENCE = "https://api.brightleaffoods.in"
KEY_A = ec.generate_private_key(ec.SECP256R1())
KEY_B = ec.generate_private_key(ec.SECP256R1())


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def jwk(key: ec.EllipticCurvePrivateKey, kid: str, **extra: Any) -> dict[str, Any]:
    numbers = key.public_key().public_numbers()
    return {
        "kty": "EC",
        "crv": "P-256",
        "x": b64(numbers.x.to_bytes(32, "big")),
        "y": b64(numbers.y.to_bytes(32, "big")),
        "use": "sig",
        "alg": "ES256",
        "kid": kid,
        **extra,
    }


def claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    base = {"iss": ISSUER, "sub": "u1", "aud": AUDIENCE, "exp": now + 600, "iat": now, "tenant_id": "t1"}
    return {k: v for k, v in {**base, **overrides}.items() if v is not None}


def token(
    payload: dict[str, Any] | None = None,
    *,
    key: ec.EllipticCurvePrivateKey = KEY_A,
    kid: str | None = "k1",
    **header: Any,
) -> str:
    head = {"alg": "ES256", "typ": "at+jwt", **({"kid": kid} if kid is not None else {}), **header}
    signing_input = f"{b64(json.dumps(head).encode())}.{b64(json.dumps(payload or claims()).encode())}"
    r, s = decode_dss_signature(key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256())))
    return f"{signing_input}.{b64(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"


class JWKS:
    """A JWKS endpoint whose answer the test controls, counting fetches."""

    def __init__(self, *keys: object) -> None:
        self.keys = list(keys)
        self.fetches = 0
        self.failing: Exception | int | None = None
        self.raw: bytes | None = None

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        self.fetches += 1
        if isinstance(self.failing, Exception):
            raise self.failing
        if isinstance(self.failing, int):
            return httpx2.Response(self.failing, json={"error": {"code": "x", "message": "down"}})
        if self.raw is not None:
            return httpx2.Response(200, content=self.raw)
        return httpx2.Response(200, json={"keys": self.keys})


class Clock:
    def __init__(self) -> None:
        self.now = 50_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr(sync_module, "monotonic", fake)
    monkeypatch.setattr(async_module, "monotonic", fake)
    return fake


def verifier(kind: Kind, jwks: JWKS, **options: Any) -> TokenVerifier | AsyncTokenVerifier:
    options.setdefault("issuer", ISSUER)
    options.setdefault("audience", AUDIENCE)
    transport = httpx2.MockTransport(jwks.handler)
    if kind == "sync":
        return TokenVerifier(http_client=httpx2.Client(transport=transport), **options)
    return AsyncTokenVerifier(http_client=httpx2.AsyncClient(transport=transport), **options)


async def code_of(call: Callable[[], Any]) -> str:
    with pytest.raises(TokenVerificationError) as caught:
        await run(call())
    return caught.value.code


async def test_a_valid_token_returns_its_claims(kind: Kind, clock: Clock) -> None:
    jwks = JWKS(jwk(KEY_A, "k1"))
    v = verifier(kind, jwks)
    payload = claims(scope="files:read", act={"sub": "agent_1"})
    assert await run(v.verify(token(payload))) == payload
    assert jwks.fetches == 1
    assert v.jwks_url == "https://api.id.qeet.in/.well-known/jwks.json"


def test_issuer_and_audience_are_required() -> None:
    with pytest.raises(ValueError, match="issuer"):
        TokenVerifier(issuer="", audience=AUDIENCE)
    for audience in ("", [], ["", AUDIENCE]):
        with pytest.raises(ValueError, match="audience"):
            AsyncTokenVerifier(issuer=ISSUER, audience=audience)
    with pytest.raises(ValueError, match="leeway"):
        TokenVerifier(issuer=ISSUER, audience=AUDIENCE, leeway=-1)
    with pytest.raises(ValueError, match="https"):
        TokenVerifier(issuer=ISSUER, audience=AUDIENCE, jwks_url="http://keys.example/jwks.json")


@pytest.mark.parametrize(
    ("make", "code"),
    [
        (lambda: token(alg="HS256"), "unsupported_algorithm"),
        (lambda: token(alg="none"), "unsupported_algorithm"),
        (lambda: token(kid=None), "unknown_key"),
        (lambda: token(kid=""), "unknown_key"),
        (lambda: token(kid="k-unknown"), "unknown_key"),
        (lambda: token(crit=["exp"]), "malformed_token"),
        (lambda: token(key=KEY_B), "invalid_signature"),
        (lambda: token().rsplit(".", 1)[0] + "." + b64(b"\x01" * 64), "invalid_signature"),
        (lambda: token().rsplit(".", 1)[0] + "." + b64(b"\x01" * 70), "invalid_signature"),
        (lambda: token(claims(exp=int(time.time()) - 31)), "token_expired"),
        (lambda: token(claims(exp=None)), "malformed_token"),
        (lambda: token(claims(exp="soon")), "malformed_token"),
        (lambda: token(claims(nbf=int(time.time()) + 60)), "token_not_yet_valid"),
        (lambda: token(claims(iat=int(time.time()) + 60)), "token_not_yet_valid"),
        (lambda: token(claims(iss="https://evil.example")), "invalid_issuer"),
        (lambda: token(claims(iss=None)), "invalid_issuer"),
        (lambda: token(claims(aud="https://other.example")), "invalid_audience"),
        (lambda: token(claims(aud=["https://a.example", 7])), "invalid_audience"),
        (lambda: token(claims(aud=None)), "invalid_audience"),
        (lambda: token(claims(sub=None)), "malformed_token"),
        (lambda: "not-a-jwt", "malformed_token"),
        (lambda: "a.b.c.d", "malformed_token"),
        (lambda: "@@@." + token().split(".", 1)[1], "malformed_token"),
        (lambda: b64(b"[1]") + "." + token().split(".", 1)[1], "malformed_token"),
        (lambda: b64(b"{") + "." + token().split(".", 1)[1], "malformed_token"),
        (lambda: "x" * (16 * 1024 + 1), "malformed_token"),
        (lambda: "", "malformed_token"),
        (lambda: 42, "malformed_token"),
    ],
)
async def test_tokens_are_refused_with_the_reason(kind: Kind, clock: Clock, make: Callable[[], Any], code: str) -> None:
    v = verifier(kind, JWKS(jwk(KEY_A, "k1")))
    assert await code_of(lambda: v.verify(make())) == code


async def test_a_tampered_payload_is_refused(kind: Kind, clock: Clock) -> None:
    head, _, signature = token().split(".")
    forged = f"{head}.{b64(json.dumps(claims(sub='admin')).encode())}.{signature}"
    assert await code_of(lambda: verifier(kind, JWKS(jwk(KEY_A, "k1"))).verify(forged)) == "invalid_signature"


async def test_clock_leeway(kind: Kind, clock: Clock) -> None:
    now = int(time.time())
    v = verifier(kind, JWKS(jwk(KEY_A, "k1")))
    await run(v.verify(token(claims(exp=now - 20, nbf=now + 20, iat=now + 20))))
    strict = verifier(kind, JWKS(jwk(KEY_A, "k1")), leeway=0)
    assert await code_of(lambda: strict.verify(token(claims(exp=now - 1)))) == "token_expired"


async def test_any_of_several_audiences_will_do(kind: Kind, clock: Clock) -> None:
    v = verifier(kind, JWKS(jwk(KEY_A, "k1")), audience=["https://mcp.brightleaffoods.in", AUDIENCE])
    await run(v.verify(token(claims(aud=["https://x.example", AUDIENCE]))))


async def test_keys_are_cached_then_refetched(kind: Kind, clock: Clock) -> None:
    jwks = JWKS(jwk(KEY_A, "k1"))
    v = verifier(kind, jwks)
    for _ in range(5):
        await run(v.verify(token()))
    assert jwks.fetches == 1
    clock.now += 301
    await run(v.verify(token()))
    assert jwks.fetches == 2


async def test_a_rotated_in_key_is_fetched_at_most_every_30_seconds(kind: Kind, clock: Clock) -> None:
    jwks = JWKS(jwk(KEY_A, "k1"))
    v = verifier(kind, jwks)
    await run(v.verify(token()))
    jwks.keys.append(jwk(KEY_B, "k2"))
    rotated = token(key=KEY_B, kid="k2")
    assert await code_of(lambda: v.verify(rotated)) == "unknown_key"  # within the cooldown
    assert jwks.fetches == 1
    clock.now += 31
    await run(v.verify(rotated))
    assert jwks.fetches == 2


async def test_made_up_kids_cant_amplify_into_fetches(kind: Kind, clock: Clock) -> None:
    jwks = JWKS(jwk(KEY_A, "k1"))
    v = verifier(kind, jwks)
    await run(v.verify(token()))
    clock.now += 31
    for n in range(20):
        assert await code_of(functools.partial(v.verify, token(kid=f"made-up-{n}"))) == "unknown_key"
    assert jwks.fetches == 2


@pytest.mark.parametrize("failure", [503, httpx2.ConnectError("down"), httpx2.ReadTimeout("slow")])
async def test_cached_keys_keep_verifying_through_an_outage(kind: Kind, clock: Clock, failure: Exception | int) -> None:
    jwks = JWKS(jwk(KEY_A, "k1"))
    v = verifier(kind, jwks)
    await run(v.verify(token()))
    jwks.failing = failure
    clock.now += 301
    await run(v.verify(token()))  # the refresh fails; the stale key still verifies
    await run(v.verify(token()))  # and isn't refetched on every token
    assert jwks.fetches == 2
    clock.now += 31
    await run(v.verify(token()))
    assert jwks.fetches == 3
    jwks.failing = None
    clock.now += 31
    await run(v.verify(token()))
    assert jwks.fetches == 4


async def test_no_keys_at_all_is_reported(kind: Kind, clock: Clock) -> None:
    jwks = JWKS(jwk(KEY_A, "k1"))
    jwks.failing = 500
    v = verifier(kind, jwks)
    assert await code_of(lambda: v.verify(token())) == "jwks_unavailable"
    assert await code_of(lambda: v.verify(token())) == "jwks_unavailable"
    assert jwks.fetches == 1  # not again within the cooldown


async def test_unusable_keys_are_skipped(kind: Kind, clock: Clock) -> None:
    good = jwk(KEY_A, "k1")
    jwks = JWKS(
        {**good, "kid": "rsa", "kty": "RSA"},
        {**good, "kid": "p384", "crv": "P-384"},
        {**good, "kid": "enc", "use": "enc"},
        {**good, "kid": "rs256", "alg": "RS256"},
        {**good, "kid": "short", "x": b64(b"\x01" * 31)},
        {**good, "kid": "off-curve", "y": b64(b"\x01" * 32)},
        {**good, "kid": "bad-b64", "x": "!!"},
        {**good, "kid": ""},
        "not-a-key",
        good,
    )
    v = verifier(kind, jwks)
    await run(v.verify(token()))
    clock.now += 31
    assert await code_of(lambda: v.verify(token(kid="off-curve"))) == "unknown_key"


async def test_a_jwks_that_isnt_json_is_unavailable(kind: Kind, clock: Clock) -> None:
    jwks = JWKS()
    jwks.raw = b"<html>"
    v = verifier(kind, jwks)
    assert await code_of(lambda: v.verify(token())) == "jwks_unavailable"


async def test_concurrent_verifications_share_one_fetch(clock: Clock) -> None:
    jwks = JWKS(jwk(KEY_A, "k1"))
    v = verifier("async", jwks)
    assert isinstance(v, AsyncTokenVerifier)
    async with anyio.create_task_group() as group:
        for _ in range(10):
            group.start_soon(v.verify, token())
    assert jwks.fetches == 1


def discovery_handler(document: Any, status: int = 200) -> Callable[[httpx2.Request], httpx2.Response]:
    keys = {"keys": [jwk(KEY_A, "k1")]}

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/.well-known/openid-configuration":
            return httpx2.Response(status, json=document)
        assert request.url.path == "/keys/jwks.json"
        return httpx2.Response(200, json=keys)

    return handler


async def discover(kind: Kind, transport: httpx2.MockTransport) -> TokenVerifier | AsyncTokenVerifier:
    if kind == "sync":
        return TokenVerifier.from_discovery(audience=AUDIENCE, http_client=httpx2.Client(transport=transport))
    return await AsyncTokenVerifier.from_discovery(
        audience=AUDIENCE, http_client=httpx2.AsyncClient(transport=transport)
    )


async def test_from_discovery(kind: Kind, clock: Clock) -> None:
    handler = discovery_handler({"issuer": ISSUER, "jwks_uri": "https://api.id.qeet.in/keys/jwks.json"})
    v = await discover(kind, httpx2.MockTransport(handler))
    assert (v.issuer, v.jwks_url, v.audiences) == (ISSUER, "https://api.id.qeet.in/keys/jwks.json", (AUDIENCE,))
    await run(v.verify(token()))
    assert repr(v) == f"{type(v).__name__}(issuer={ISSUER!r}, audiences=({AUDIENCE!r},))"


@pytest.mark.parametrize(
    ("document", "status", "error"),
    [
        ({"issuer": ISSUER}, 200, APIError),
        ("nope", 200, APIError),
        ({"error": {"code": "x"}}, 503, APIError),
        ({"issuer": ISSUER, "jwks_uri": "http://keys.example/jwks.json"}, 200, ValueError),
    ],
)
async def test_from_discovery_refuses_a_bad_document(
    kind: Kind, document: Any, status: int, error: type[Exception]
) -> None:
    with pytest.raises(error):
        await discover(kind, httpx2.MockTransport(discovery_handler(document, status)))


async def test_from_discovery_reports_network_failures(kind: Kind) -> None:
    def fail(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("down")

    with pytest.raises(NetworkError):
        await discover(kind, httpx2.MockTransport(fail))


async def test_without_a_client_each_fetch_opens_its_own(monkeypatch: pytest.MonkeyPatch, kind: Kind) -> None:
    jwks = JWKS(jwk(KEY_A, "k1"))
    transport = httpx2.MockTransport(jwks.handler)
    real_sync, real_async = httpx2.Client, httpx2.AsyncClient
    monkeypatch.setattr(httpx2, "Client", lambda **kw: real_sync(transport=transport, **kw))
    monkeypatch.setattr(httpx2, "AsyncClient", lambda **kw: real_async(transport=transport, **kw))
    cls = TokenVerifier if kind == "sync" else AsyncTokenVerifier
    v = cls(issuer=ISSUER, audience=AUDIENCE, base_url="http://localhost:4001")
    assert v.jwks_url == "http://localhost:4001/.well-known/jwks.json"
    await run(v.verify(token()))
    assert jwks.fetches == 1
