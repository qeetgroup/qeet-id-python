"""Verifies access tokens locally against the issuer's published signing keys (JWKS)."""

import time
from collections.abc import Sequence
from math import inf
from time import monotonic
from typing import Any, Self

import httpx2
from cryptography.hazmat.primitives.asymmetric import ec

from qeet_id._async._compat import Lock
from qeet_id._claims import AccessTokenClaims
from qeet_id._config import normalize_base_url
from qeet_id._constants import DEFAULT_BASE_URL
from qeet_id._errors import APIError, NetworkError, RequestTimeoutError, TokenVerificationError
from qeet_id._jwt import (
    DEFAULT_LEEWAY,
    JWKS_CACHE_TTL,
    JWKS_REFRESH_COOLDOWN,
    JWKS_TIMEOUT,
    check_audiences,
    check_claims,
    parse_jwks,
    parse_token,
    verify_signature,
)

__all__ = ["AsyncTokenVerifier"]


class AsyncTokenVerifier:
    """Verifies Qeet ID access tokens locally, with no network call per token once the keys are cached.

    Checks the ES256 signature against the issuer's keys, and ``iss``, ``aud``,
    ``exp``, ``nbf`` and ``iat`` with ``leeway`` seconds of clock tolerance.
    The keys are cached for five minutes; a token naming an unknown ``kid`` (a
    rotated-in key) refetches them at most every 30 seconds; if the issuer
    can't be reached, the keys in hand keep verifying. Create one per process
    and share it::

        verifier = await AsyncTokenVerifier.from_discovery(audience="https://api.brightleaffoods.in")
        claims = await verifier.verify(bearer_token)

    Args:
        issuer: The issuer tokens must carry in ``iss``: the ``issuer`` of the discovery document.
        audience: The audience ``aud`` must include: the platform audience, or your service's
            RFC 8707 resource identifier. Any one of a list will do. Required.
        jwks_url: The JWKS document. Default ``{base_url}/.well-known/jwks.json``.
        base_url: The API, used when ``jwks_url`` isn't given. Default ``https://api.id.qeet.in``.
        leeway: Seconds of clock difference allowed when checking ``exp``, ``nbf`` and ``iat``. Default 30.
        http_client: An ``httpx2.AsyncClient`` for the JWKS requests; one is opened per fetch otherwise.

    Raises:
        ValueError: without an issuer or audience, or with a URL that isn't https.
    """

    __slots__ = ("_http", "_keys", "_last_attempt", "_lock", "_refresh_at", "audiences", "issuer", "jwks_url", "leeway")

    def __init__(
        self,
        *,
        issuer: str,
        audience: str | Sequence[str],
        jwks_url: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        leeway: float = DEFAULT_LEEWAY,
        http_client: httpx2.AsyncClient | None = None,
    ) -> None:
        if not isinstance(issuer, str) or not issuer:
            raise ValueError("issuer is required: the issuer the tokens carry in iss.")
        if isinstance(leeway, bool) or not isinstance(leeway, int | float) or leeway < 0:
            raise ValueError("leeway must be a number of seconds, 0 or more.")
        self.issuer = issuer
        self.audiences = check_audiences(audience)
        self.leeway = float(leeway)
        self.jwks_url = (
            normalize_base_url(jwks_url, name="jwks_url")
            if jwks_url is not None
            else normalize_base_url(base_url) + "/.well-known/jwks.json"
        )
        self._http = http_client
        self._keys: dict[str, ec.EllipticCurvePublicKey] | None = None
        self._refresh_at = -inf
        self._last_attempt = -inf
        self._lock = Lock()

    @classmethod
    async def from_discovery(
        cls,
        *,
        audience: str | Sequence[str],
        base_url: str = DEFAULT_BASE_URL,
        leeway: float = DEFAULT_LEEWAY,
        http_client: httpx2.AsyncClient | None = None,
    ) -> Self:
        """Build a verifier from ``{base_url}/.well-known/openid-configuration``: its ``issuer`` and ``jwks_uri``.

        One network call; reuse the verifier.

        Raises:
            NetworkError: when the discovery document can't be fetched.
            APIError: when the answer isn't a discovery document.
            ValueError: when ``audience`` is missing or ``jwks_uri`` isn't https.
        """
        url = normalize_base_url(base_url) + "/.well-known/openid-configuration"
        response = await _get(url, http_client)
        document = _json(response)
        issuer = document.get("issuer") if isinstance(document, dict) else None
        jwks_uri = document.get("jwks_uri") if isinstance(document, dict) else None
        if response.status_code != 200 or not isinstance(issuer, str) or not isinstance(jwks_uri, str):
            raise APIError(
                "The discovery document could not be read.",
                status=response.status_code,
                code="invalid_response" if response.status_code == 200 else f"http_{response.status_code}",
                headers=response.headers,
            )
        return cls(issuer=issuer, audience=audience, jwks_url=jwks_uri, leeway=leeway, http_client=http_client)

    async def verify(self, token: str) -> AccessTokenClaims:
        """Verify ``token`` and return its claims.

        Raises:
            TokenVerificationError: when the token isn't one this verifier accepts. Treat the caller as
                unauthenticated. ``code`` says why: ``malformed_token``, ``unsupported_algorithm``,
                ``unknown_key``, ``invalid_signature``, ``token_expired``, ``token_not_yet_valid``,
                ``invalid_issuer``, ``invalid_audience`` or ``jwks_unavailable``.
        """
        parsed = parse_token(token)
        key = await self._key(parsed.kid)
        verify_signature(key, parsed)
        return check_claims(
            parsed.payload, issuer=self.issuer, audiences=self.audiences, leeway=self.leeway, now=time.time()
        )

    async def _key(self, kid: str) -> ec.EllipticCurvePublicKey:
        if monotonic() >= self._refresh_at:
            await self._refresh(unknown_kid=False)
        if self._keys is not None and kid in self._keys:
            return self._keys[kid]
        if monotonic() - self._last_attempt >= JWKS_REFRESH_COOLDOWN:
            await self._refresh(unknown_kid=True)  # a rotated-in key
        if self._keys is None:
            raise TokenVerificationError("jwks_unavailable", "The issuer's signing keys could not be fetched.")
        if kid not in self._keys:
            raise TokenVerificationError("unknown_key", "The token's signing key is not among the issuer's keys.")
        return self._keys[kid]

    async def _refresh(self, *, unknown_kid: bool) -> None:
        async with self._lock:
            now = monotonic()
            # Another caller may have refreshed while this one waited for the lock.
            if not unknown_kid and now < self._refresh_at:
                return
            if unknown_kid and now - self._last_attempt < JWKS_REFRESH_COOLDOWN:
                return
            self._last_attempt = now
            try:
                keys = await self._fetch()
            except TokenVerificationError:
                # Try again after the cooldown rather than on every token. Keys
                # already in hand keep verifying through the outage.
                self._refresh_at = now + JWKS_REFRESH_COOLDOWN
                if self._keys is None or unknown_kid:
                    raise
                return
            self._keys = keys
            self._refresh_at = now + JWKS_CACHE_TTL

    async def _fetch(self) -> dict[str, ec.EllipticCurvePublicKey]:
        try:
            response = await _get(self.jwks_url, self._http)
        except NetworkError as exc:
            raise TokenVerificationError("jwks_unavailable", "The issuer's signing keys could not be fetched.") from exc
        document = _json(response)
        if response.status_code != 200 or not isinstance(document, dict):
            raise TokenVerificationError(
                "jwks_unavailable", f"The issuer's signing keys could not be read (HTTP {response.status_code})."
            )
        return parse_jwks(document)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(issuer={self.issuer!r}, audiences={self.audiences!r})"


async def _get(url: str, http_client: httpx2.AsyncClient | None) -> httpx2.Response:
    headers = {"Accept": "application/json"}
    try:
        if http_client is not None:
            return await http_client.get(url, headers=headers, timeout=JWKS_TIMEOUT)
        async with httpx2.AsyncClient(follow_redirects=False, timeout=JWKS_TIMEOUT) as client:
            return await client.get(url, headers=headers)
    except httpx2.TimeoutException as exc:
        raise RequestTimeoutError(f"GET {url} got no response in time.") from exc
    except httpx2.HTTPError as exc:
        raise NetworkError(f"GET {url} failed: {type(exc).__name__}: {exc}") from exc


def _json(response: httpx2.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
