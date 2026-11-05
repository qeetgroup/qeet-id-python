# Generated from qeet_id/_async/resources/oauth.py by scripts/unasync.py. Edit that file, not this one.
"""OAuth 2.0 and OpenID Connect with Qeet ID as the authorization server (federation.yaml)."""

from collections.abc import Sequence

from qeet_id._errors import AuthenticationError, PermissionDeniedError
from qeet_id._options import RequestOptions
from qeet_id._pagination import ListResult, Page
from qeet_id._request import path
from qeet_id._sync._resource import APIResource
from qeet_id._sync._transport import Transport
from qeet_id.types.federation import (
    BackchannelAuthentication,
    ClientCredentialsToken,
    DeviceAuthorization,
    DiscoveryDocument,
    Introspection,
    OAuthDeviceAuthorization,
    OAuthGrant,
    OAuthGrantsRevoked,
    SigningKey,
    TokenResponse,
)

__all__ = ["OAuth", "OAuthDevices", "OAuthGrants", "SigningKeys", "TokenGuard"]

GRANT_TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"  # noqa: S105 - a URN, not a secret
GRANT_DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"
GRANT_CIBA = "urn:openid:params:grant-type:ciba"
TOKEN_TYPE_ACCESS_TOKEN = "urn:ietf:params:oauth:token-type:access_token"  # noqa: S105 - a URN, not a secret


def _client(
    form: dict[str, str | None], client_id: str, client_secret: str | None, *, confidential: bool = False
) -> tuple[str, str] | None:
    """How the application authenticates: HTTP Basic with a secret, or ``client_id`` in the form without one."""
    if not isinstance(client_id, str) or not client_id:
        raise ValueError("client_id is required.")
    if client_secret:
        return (client_id, client_secret)
    if confidential:
        raise ValueError("client_secret is required: this endpoint refuses public clients.")
    form["client_id"] = client_id
    return None


class OAuthGrants(APIResource):
    """Consent grants people gave applications."""

    def list(
        self,
        tenant_id: str,
        /,
        *,
        client_id: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> Page[OAuthGrant]:
        """List the grants, latest used first; only those to ``client_id`` when given."""
        return self._paginate(
            path("/v1/tenants/{}/oauth/grants", tenant_id),
            {"client_id": client_id, "limit": limit, "cursor": cursor},
            request_options=request_options,
        )

    def revoke(self, tenant_id: str, grant_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Revoke one grant; the application must ask for consent again."""
        self._request(
            "DELETE", path("/v1/tenants/{}/oauth/grants/{}", tenant_id, grant_id), request_options=request_options
        )

    def revoke_many(
        self,
        tenant_id: str,
        /,
        *,
        ids: Sequence[str] | None = None,
        client_id: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> OAuthGrantsRevoked:
        """Revoke several grants by id (up to 100), or every grant to one application. Give one.

        Raises:
            ValueError: unless exactly one of ``ids`` and ``client_id`` is given.
        """
        if (ids is None) == (client_id is None):
            raise ValueError("Give exactly one of ids and client_id.")
        body = {"ids": [*ids]} if ids is not None else {"client_id": client_id}
        return self._request(
            "POST", path("/v1/tenants/{}/oauth/grants/revoke", tenant_id), json=body, request_options=request_options
        )


class OAuthDevices(APIResource):
    """Device-flow authorizations, for review."""

    def list(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[OAuthDeviceAuthorization]:
        return self._list(path("/v1/tenants/{}/oauth/devices", tenant_id), request_options=request_options)

    def revoke(
        self, tenant_id: str, device_authorization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """Revoke a device authorization; a grant it already bought ends too."""
        self._request(
            "DELETE",
            path("/v1/tenants/{}/oauth/devices/{}", tenant_id, device_authorization_id),
            request_options=request_options,
        )


class SigningKeys(APIResource):
    """The issuer's signing keys. Rotation is an operator task and isn't part of the API."""

    def list(self, *, request_options: RequestOptions | None = None) -> ListResult[SigningKey]:
        return self._list("/v1/oidc/signing-keys", key="keys", request_options=request_options)


class OAuth(APIResource):
    """The token grants, introspection, revocation, the device and backchannel (CIBA) flows, and discovery.

    Applications authenticate with HTTP Basic (``client_secret_basic``) when they
    have a secret, or by ``client_id`` in the form when they are public. The
    endpoints answer errors in the RFC 6749 shape and raise :class:`~qeet_id.OAuthError`,
    whose ``code`` is the RFC ``error`` (``invalid_grant``, ``invalid_client``, …).
    Single-use grants (a code, a refresh token, a device code) are never retried.
    """

    __slots__ = ("devices", "grants", "signing_keys")

    def __init__(self, transport: Transport) -> None:
        super().__init__(transport)
        self.grants = OAuthGrants(transport)
        """People's consent grants to applications."""
        self.devices = OAuthDevices(transport)
        """Device-flow authorizations."""
        self.signing_keys = SigningKeys(transport)
        """The issuer's signing keys."""

    def client_credentials_grant(
        self, *, client_id: str, client_secret: str, request_options: RequestOptions | None = None
    ) -> ClientCredentialsToken:
        """Get a machine-to-machine token for a service principal (``POST /v1/oauth/token``).

        The token carries the principal's scopes; ``expires_in`` and ``expires_at`` give its
        lifetime. To have the client fetch and renew such tokens for its own calls, create it
        with ``client_id`` and ``client_secret`` instead. Retried like a read: asking again only
        issues another token.
        """
        form: dict[str, str | None] = {"grant_type": "client_credentials"}
        auth = _client(form, client_id, client_secret, confidential=True)
        return self._request(
            "POST",
            "/v1/oauth/token",
            form=form,
            authenticate=False,
            client_auth=auth,
            retry_safe=True,
            request_options=request_options,
        )

    def authorization_code_grant(
        self,
        *,
        client_id: str,
        code: str,
        redirect_uri: str,
        client_secret: str | None = None,
        code_verifier: str | None = None,
        resource: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> TokenResponse:
        """Redeem an authorization code (with its PKCE ``code_verifier``) for tokens.

        ``resource`` (RFC 8707) binds the access token to one resource server.
        """
        form: dict[str, str | None] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "resource": resource,
        }
        return self._grant(form, client_id, client_secret, request_options)

    def refresh_token_grant(
        self,
        *,
        client_id: str,
        refresh_token: str,
        client_secret: str | None = None,
        scope: str | None = None,
        resource: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> TokenResponse:
        """Renew tokens with a refresh token. Use the refresh token in the answer next time: it rotates.

        A refused refresh ends the application's refresh tokens for that person.
        """
        form: dict[str, str | None] = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": scope,
            "resource": resource,
        }
        return self._grant(form, client_id, client_secret, request_options)

    def token_exchange_grant(
        self,
        *,
        client_id: str,
        subject_token: str,
        client_secret: str | None = None,
        subject_token_type: str = TOKEN_TYPE_ACCESS_TOKEN,
        actor_token: str | None = None,
        actor_token_type: str | None = None,
        requested_token_type: str | None = None,
        scope: str | None = None,
        resource: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> TokenResponse:
        """RFC 8693 token exchange: narrow a token, or get one that acts for its subject.

        With ``actor_token`` (an AI agent's token, say) the result carries an ``act`` claim
        for it. ``scope`` must be a subset of the subject token's.
        """
        if actor_token is not None and actor_token_type is None:
            actor_token_type = TOKEN_TYPE_ACCESS_TOKEN
        form: dict[str, str | None] = {
            "grant_type": GRANT_TOKEN_EXCHANGE,
            "subject_token": subject_token,
            "subject_token_type": subject_token_type,
            "actor_token": actor_token,
            "actor_token_type": actor_token_type,
            "requested_token_type": requested_token_type,
            "scope": scope,
            "resource": resource,
        }
        return self._grant(form, client_id, client_secret, request_options)

    def device_code_grant(
        self,
        *,
        client_id: str,
        device_code: str,
        client_secret: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> TokenResponse:
        """Poll once for the device flow's tokens.

        Until the person decides, this raises :class:`~qeet_id.OAuthError` with code
        ``authorization_pending`` (poll again after ``interval``) or ``slow_down`` (add five
        seconds to it); ``access_denied`` and ``expired_token`` end the flow.
        """
        form: dict[str, str | None] = {"grant_type": GRANT_DEVICE_CODE, "device_code": device_code}
        return self._grant(form, client_id, client_secret, request_options)

    def ciba_grant(
        self,
        *,
        client_id: str,
        client_secret: str,
        auth_req_id: str,
        request_options: RequestOptions | None = None,
    ) -> TokenResponse:
        """Poll once for a backchannel (CIBA) request's tokens. Pending and refused requests raise as above."""
        form: dict[str, str | None] = {"grant_type": GRANT_CIBA, "auth_req_id": auth_req_id}
        return self._grant(form, client_id, client_secret, request_options, confidential=True)

    def device_authorization(
        self,
        *,
        client_id: str,
        client_secret: str | None = None,
        scope: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> DeviceAuthorization:
        """Start the RFC 8628 device flow: show the person ``user_code`` and ``verification_uri``, then poll."""
        form: dict[str, str | None] = {"scope": scope}
        auth = _client(form, client_id, client_secret)
        return self._request(
            "POST",
            "/v1/oauth/device_authorization",
            form=form,
            authenticate=False,
            client_auth=auth,
            request_options=request_options,
        )

    def backchannel_authentication(
        self,
        *,
        client_id: str,
        client_secret: str,
        login_hint: str,
        scope: str | None = None,
        binding_message: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> BackchannelAuthentication:
        """Start an OpenID CIBA request (poll mode): the person approves it on their own device.

        ``login_hint`` is the person's email address in the client's organisation;
        ``binding_message`` is shown to them, such as a transaction reference.
        """
        form: dict[str, str | None] = {"login_hint": login_hint, "scope": scope, "binding_message": binding_message}
        auth = _client(form, client_id, client_secret, confidential=True)
        return self._request(
            "POST",
            "/v1/oauth/bc-authorize",
            form=form,
            authenticate=False,
            client_auth=auth,
            request_options=request_options,
        )

    def introspect(
        self,
        token: str,
        *,
        client_id: str,
        client_secret: str,
        token_type_hint: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> Introspection:
        """RFC 7662: whether a token is active, and its claims, as a confidential application sees it.

        Introspection is the authoritative answer on revocation: use it where a revoked
        session must stop working at once, rather than verifying the token offline.
        """
        form: dict[str, str | None] = {"token": token, "token_type_hint": token_type_hint}
        auth = _client(form, client_id, client_secret, confidential=True)
        return self._request(
            "POST",
            "/oauth/introspect",
            form=form,
            authenticate=False,
            client_auth=auth,
            retry_safe=True,
            request_options=request_options,
        )

    def revoke(
        self,
        token: str,
        *,
        client_id: str,
        client_secret: str | None = None,
        token_type_hint: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> None:
        """RFC 7009: revoke a refresh token and its whole grant. Succeeds for an unknown token too.

        An access token can't be revoked (``unsupported_token_type``): it lasts out its short lifetime.
        """
        form: dict[str, str | None] = {"token": token, "token_type_hint": token_type_hint}
        auth = _client(form, client_id, client_secret)
        self._request(
            "POST",
            "/oauth/revoke",
            form=form,
            authenticate=False,
            client_auth=auth,
            retry_safe=True,
            request_options=request_options,
        )

    def discover(self, *, request_options: RequestOptions | None = None) -> DiscoveryDocument:
        """The authorization server's metadata: ``/.well-known/openid-configuration``."""
        return self._request(
            "GET", "/.well-known/openid-configuration", authenticate=False, request_options=request_options
        )

    def create_token_guard(self, *, audience: str, client_id: str, client_secret: str) -> "TokenGuard":
        """A guard that admits a token for one protected service (an API or an MCP server) by introspection."""
        return TokenGuard(self, audience=audience, client_id=client_id, client_secret=client_secret)

    def _grant(
        self,
        form: dict[str, str | None],
        client_id: str,
        client_secret: str | None,
        request_options: RequestOptions | None,
        *,
        confidential: bool = False,
    ) -> TokenResponse:
        auth = _client(form, client_id, client_secret, confidential=confidential)
        # A grant is single-use: a retry after a lost answer would be refused, so none is made.
        return self._request(
            "POST",
            "/v1/oauth/token-code",
            form=form,
            authenticate=False,
            client_auth=auth,
            retries=False,
            request_options=request_options,
        )


class TokenGuard:
    """Admits a token for one protected service, by introspection.

    ``verify`` raises :class:`~qeet_id.AuthenticationError` (401, ``invalid_token``) for an
    inactive token or one issued for another audience, and
    :class:`~qeet_id.PermissionDeniedError` (403, ``insufficient_scope``) for a missing scope.

    Args:
        oauth: The client's ``oauth`` namespace.
        audience: The protected service's identifier, as the tokens issued for it name it in
            ``aud``: its registered RFC 8707 resource. Required.
        client_id: The confidential application the guard introspects as.
        client_secret: Its secret.
    """

    __slots__ = ("_client_id", "_client_secret", "_oauth", "audience")

    def __init__(self, oauth: OAuth, *, audience: str, client_id: str, client_secret: str) -> None:
        if not isinstance(audience, str) or not audience.strip():
            raise ValueError("audience is required: without it a token issued for any other service would pass.")
        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are required: introspection authenticates the application.")
        self.audience = audience
        self._oauth = oauth
        self._client_id = client_id
        self._client_secret = client_secret

    def verify(
        self, token: str, required_scopes: str | Sequence[str] = (), *, request_options: RequestOptions | None = None
    ) -> Introspection:
        """Introspect ``token`` and return its claims when it is active, for this audience, with every scope."""
        claims = self._oauth.introspect(
            token,
            client_id=self._client_id,
            client_secret=self._client_secret,
            token_type_hint="access_token",  # noqa: S106 - a hint, not a secret
            request_options=request_options,
        )
        if claims.get("active") is not True:
            raise AuthenticationError("The token is not active.", status=401, code="invalid_token")
        aud = claims.get("aud")
        audiences = [aud] if isinstance(aud, str) else aud if isinstance(aud, list) else []
        if self.audience not in audiences:
            raise AuthenticationError("The token was not issued for this service.", status=401, code="invalid_token")
        scope = claims.get("scope")
        granted = set(scope.split()) if isinstance(scope, str) else set()
        for wanted in [required_scopes] if isinstance(required_scopes, str) else required_scopes:
            if wanted not in granted:
                raise PermissionDeniedError(
                    f"The token lacks the scope {wanted}.", status=403, code="insufficient_scope"
                )
        return claims

    def __repr__(self) -> str:
        return f"{type(self).__name__}(audience={self.audience!r}, client_id={self._client_id!r})"
