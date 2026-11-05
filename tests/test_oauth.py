"""The OAuth flows: client authentication, retries, RFC 6749 errors, expires_in, and the token guard."""

import base64
from typing import Any

import pytest

from qeet_id import (
    AsyncQeetID,
    AuthenticationError,
    OAuthError,
    PermissionDeniedError,
    QeetID,
    ServiceUnavailableError,
)

from .conftest import Kind, MockAPI, envelope, run

pytestmark = pytest.mark.anyio

TOKEN = {"access_token": "at", "token_type": "Bearer", "expires_in": 900, "scope": "openid", "refresh_token": "rt"}


def basic(client_id: str, secret: str) -> str:
    return "Basic " + base64.b64encode(f"{client_id}:{secret}".encode()).decode()


async def test_grants_expose_expires_in(api: MockAPI, kind: Kind) -> None:
    api.answer({"json": TOKEN})
    token = await run(
        api.client(kind).oauth.authorization_code_grant(
            client_id="app", client_secret="s", code="c", redirect_uri="https://app.example/cb"
        )
    )
    assert token["expires_in"] == 900
    assert token["refresh_token"] == "rt"


async def test_client_credentials_expose_expires_in_and_expires_at(api: MockAPI, kind: Kind) -> None:
    answer = {**TOKEN, "expires_at": "2026-11-05T10:00:00Z", "scope": "user:read"}
    api.answer({"json": answer})
    token = await run(api.client(kind, api_key=None).oauth.client_credentials_grant(client_id="sp1", client_secret="s"))
    assert (token["expires_in"], token["expires_at"]) == (900, "2026-11-05T10:00:00Z")
    assert api.last.headers["authorization"] == basic("sp1", "s")


async def test_confidential_clients_use_basic_and_public_ones_the_form(api: MockAPI, kind: Kind) -> None:
    client = api.answer({"json": TOKEN}).client(kind)
    await run(client.oauth.refresh_token_grant(client_id="app", client_secret="s3cr3t", refresh_token="rt"))
    assert api.last.headers["authorization"] == basic("app", "s3cr3t")
    assert "client_id" not in api.last.form
    assert "client_secret" not in api.last.form
    await run(client.oauth.refresh_token_grant(client_id="spa", refresh_token="rt"))
    assert "authorization" not in api.last.headers
    assert api.last.form["client_id"] == "spa"


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.oauth.client_credentials_grant(client_id="sp1", client_secret=""),
        lambda c: c.oauth.ciba_grant(client_id="app", client_secret="", auth_req_id="ar"),
        lambda c: c.oauth.backchannel_authentication(client_id="app", client_secret="", login_hint="a@b.in"),
        lambda c: c.oauth.introspect("t", client_id="app", client_secret=""),
    ],
    ids=["client_credentials", "ciba", "bc_authorize", "introspect"],
)
async def test_confidential_only_endpoints_refuse_a_public_client(api: MockAPI, kind: Kind, call: Any) -> None:
    with pytest.raises(ValueError, match="client_secret is required"):
        await run(call(api.client(kind)))
    assert api.requests == []


async def test_a_client_id_is_required(api: MockAPI, kind: Kind) -> None:
    with pytest.raises(ValueError, match="client_id"):
        await run(api.client(kind).oauth.device_authorization(client_id=""))


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (400, "invalid_grant"),
        (401, "invalid_client"),
        (400, "unauthorized_client"),
        (400, "unsupported_grant_type"),
        (400, "invalid_scope"),
        (400, "invalid_target"),
        (400, "authorization_pending"),
        (400, "slow_down"),
        (400, "access_denied"),
        (400, "expired_token"),
    ],
)
async def test_token_errors_are_oauth_errors(api: MockAPI, kind: Kind, status: int, error: str) -> None:
    api.answer({"status": status, "json": {"error": error, "error_description": "No."}})
    with pytest.raises(OAuthError) as caught:
        await run(api.client(kind).oauth.device_code_grant(client_id="tv", device_code="dc"))
    assert (caught.value.status, caught.value.code, caught.value.error, caught.value.message) == (
        status,
        error,
        error,
        "No.",
    )


async def test_single_use_grants_are_never_retried(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 503, "json": envelope("server.overloaded")})
    client = api.client(kind)
    grants: list[Any] = [
        lambda: client.oauth.authorization_code_grant(client_id="a", code="c", redirect_uri="https://a.example/cb"),
        lambda: client.oauth.refresh_token_grant(client_id="a", refresh_token="rt"),
        lambda: client.oauth.token_exchange_grant(client_id="a", subject_token="st"),
        lambda: client.oauth.device_code_grant(client_id="a", device_code="dc"),
        lambda: client.oauth.ciba_grant(client_id="a", client_secret="s", auth_req_id="ar"),
    ]
    for grant in grants:
        with pytest.raises(ServiceUnavailableError):
            await run(grant())
    assert len(api.requests) == 5


async def test_client_credentials_introspection_and_revocation_are_retried(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 503}, {"json": TOKEN})
    client = api.client(kind)
    await run(client.oauth.client_credentials_grant(client_id="sp1", client_secret="s"))
    api.answer({"status": 503}, {"json": {"active": False}})
    await run(client.oauth.introspect("t", client_id="app", client_secret="s"))
    api.answer({"status": 503}, {"status": 200})
    await run(client.oauth.revoke("rt", client_id="app", client_secret="s"))
    assert len(api.requests) == 6


async def test_token_exchange_defaults_the_token_types(api: MockAPI, kind: Kind) -> None:
    await run(api.client(kind).oauth.token_exchange_grant(client_id="app", subject_token="st"))
    assert api.last.form["subject_token_type"] == "urn:ietf:params:oauth:token-type:access_token"
    assert "actor_token_type" not in api.last.form


async def test_discovery_sends_no_credential(api: MockAPI, kind: Kind) -> None:
    api.answer({"json": {"issuer": "https://api.id.qeet.in", "jwks_uri": "https://api.id.qeet.in/jwks"}})
    document = await run(api.client(kind).oauth.discover())
    assert document["issuer"] == "https://api.id.qeet.in"
    assert "authorization" not in api.last.headers


def guard(api: MockAPI, kind: Kind, answer: dict[str, Any]) -> Any:
    client = api.answer({"json": answer}).client(kind)
    assert isinstance(client, QeetID | AsyncQeetID)
    return client.oauth.create_token_guard(audience="https://mcp.example", client_id="mcp", client_secret="s")


async def test_the_guard_admits_an_active_token_for_its_audience(api: MockAPI, kind: Kind) -> None:
    answer = {"active": True, "aud": ["https://mcp.example"], "scope": "files:read files:write", "sub": "u1"}
    claims = await run(guard(api, kind, answer).verify("tok", ["files:read"]))
    assert claims["sub"] == "u1"
    assert api.last.form == {"token": "tok", "token_type_hint": "access_token"}
    assert api.last.headers["authorization"] == basic("mcp", "s")
    assert await run(guard(api, kind, {**answer, "aud": "https://mcp.example"}).verify("tok", "files:write"))


@pytest.mark.parametrize(
    "answer",
    [{"active": False}, {"active": True, "aud": "https://other.example"}, {"active": True}],
    ids=["inactive", "another audience", "no audience"],
)
async def test_the_guard_refuses_with_401(api: MockAPI, kind: Kind, answer: dict[str, Any]) -> None:
    with pytest.raises(AuthenticationError) as caught:
        await run(guard(api, kind, answer).verify("tok"))
    assert (caught.value.status, caught.value.code) == (401, "invalid_token")


async def test_the_guard_refuses_a_missing_scope_with_403(api: MockAPI, kind: Kind) -> None:
    answer = {"active": True, "aud": "https://mcp.example", "scope": "files:read"}
    with pytest.raises(PermissionDeniedError) as caught:
        await run(guard(api, kind, answer).verify("tok", ["files:read", "files:write"]))
    assert (caught.value.status, caught.value.code) == (403, "insufficient_scope")


def test_the_guard_needs_an_audience_and_a_confidential_client() -> None:
    oauth = MockAPI().client("sync").oauth
    with pytest.raises(ValueError, match="audience"):
        oauth.create_token_guard(audience=" ", client_id="a", client_secret="s")
    with pytest.raises(ValueError, match="client_secret"):
        oauth.create_token_guard(audience="https://x.example", client_id="a", client_secret="")
    created = oauth.create_token_guard(audience="https://x.example", client_id="a", client_secret="hidden")
    assert "hidden" not in repr(created)
