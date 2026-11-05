# Generated from qeet_id/_async/_credentials.py by scripts/unasync.py. Edit that file, not this one.
"""The client's credential: an API key, or client credentials exchanged for a cached token."""

import math
from time import monotonic
from typing import TYPE_CHECKING, Protocol

from qeet_id._errors import APIError
from qeet_id._request import Request
from qeet_id._sync._compat import Lock

if TYPE_CHECKING:
    from qeet_id._sync._transport import Transport

__all__ = ["APIKeyAuth", "ClientCredentialsAuth", "Credential"]

TOKEN_REFRESH_MARGIN = 60.0
"""A cached token is replaced this many seconds before it expires (or halfway through a shorter life)."""


class Credential(Protocol):
    """Produces the ``Authorization`` header of each request."""

    def authorization(self, transport: "Transport") -> str:
        """The ``Authorization`` header value for the next request."""
        ...

    def invalidate(self, authorization: str) -> None:
        """Forget ``authorization`` after the API refused it, so the next request gets a fresh one."""
        ...


class APIKeyAuth:
    """``Authorization: ApiKey <key>``."""

    __slots__ = ("_authorization",)

    def __init__(self, api_key: str) -> None:
        self._authorization = f"ApiKey {api_key}"

    def authorization(self, transport: "Transport") -> str:
        """The API key header; it never changes."""
        return self._authorization

    def invalidate(self, authorization: str) -> None:
        """Nothing to forget: a refused API key stays refused."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}(api_key='***')"


class ClientCredentialsAuth:
    """``Authorization: Bearer <token>``, the token got with the client credentials grant and cached.

    The token is fetched on first use (``POST /v1/oauth/token``), reused until
    shortly before it expires, and fetched again; concurrent callers share one
    fetch. A request the API refuses with 401 drops the cached token.
    """

    __slots__ = ("_client_id", "_client_secret", "_expires_at", "_lock", "_token")

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = Lock()

    def _fresh(self) -> str | None:
        if self._token is not None and monotonic() < self._expires_at:
            return self._token
        return None

    def authorization(self, transport: "Transport") -> str:
        """The cached token, fetching a new one when there is none or it is about to expire."""
        token = self._fresh()
        if token is not None:
            return token
        with self._lock:
            token = self._fresh()  # another caller may have fetched it meanwhile
            if token is not None:
                return token
            received = monotonic()
            body = transport.request(
                Request(
                    method="POST",
                    path="/v1/oauth/token",
                    form={"grant_type": "client_credentials"},
                    authenticate=False,
                    client_auth=(self._client_id, self._client_secret),
                    # Asking again only issues another token: nothing happens twice.
                    retry_safe=True,
                )
            )
            access_token = body.get("access_token") if isinstance(body, dict) else None
            if not isinstance(access_token, str) or not access_token:
                raise APIError(
                    "The token endpoint answered without an access_token.", status=200, code="invalid_response"
                )
            expires_in = body.get("expires_in")
            lifetime = float(expires_in) if isinstance(expires_in, int | float) and expires_in > 0 else 0.0
            self._token = f"Bearer {access_token}"
            # Replace it a minute early, or halfway through a short life; a token without a lifetime isn't reused.
            self._expires_at = received + lifetime - min(TOKEN_REFRESH_MARGIN, math.floor(lifetime / 2))
            return self._token

    def invalidate(self, authorization: str) -> None:
        """Drop the cached token if it is the one the API refused."""
        if self._token == authorization:
            self._token = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(client_id={self._client_id!r}, client_secret='***')"
