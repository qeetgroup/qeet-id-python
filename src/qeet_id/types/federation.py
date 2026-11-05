"""Federation: OAuth, applications, service principals, SAML, LDAP, SCIM, social sign-in, admin portal."""

from typing import Any, Literal, NotRequired, Required, TypedDict

__all__ = [
    "AdminPortalCapability",
    "AdminPortalLink",
    "AdminPortalLinkCreated",
    "Application",
    "ApplicationAuthFailure",
    "ApplicationAuthFailures",
    "ApplicationCreateParams",
    "ApplicationCreated",
    "ApplicationSecret",
    "ApplicationUpdateParams",
    "BackchannelAuthentication",
    "ClientCredentialsToken",
    "ConnectionCheck",
    "ConnectionStatus",
    "ConnectionTestResult",
    "DeviceAuthorization",
    "DiscoveryDocument",
    "Introspection",
    "LDAPAuthenticationResult",
    "LDAPConnection",
    "LDAPConnectionCreateParams",
    "LDAPConnectionUpdateParams",
    "LDAPMfaChallengeResult",
    "LDAPTestResult",
    "LDAPTokensResult",
    "MfaChallenge",
    "MfaFactor",
    "OAuthDeviceAuthorization",
    "OAuthGrant",
    "OAuthGrantListParams",
    "OAuthGrantsRevoked",
    "OAuthResource",
    "OAuthResourceCreateParams",
    "SAMLAttributeMapping",
    "SAMLCertificate",
    "SAMLCertificateDetails",
    "SAMLConnection",
    "SAMLConnectionCreateParams",
    "SAMLConnectionImportParams",
    "SAMLConnectionUpdateParams",
    "SAMLServiceProvider",
    "SAMLServiceProviderAssignments",
    "SAMLServiceProviderCreateParams",
    "SAMLServiceProviderGroupAssignment",
    "SAMLServiceProviderUpdateParams",
    "SAMLServiceProviderUserAssignment",
    "SCIMConfig",
    "SCIMGroup",
    "SCIMLastRequest",
    "SCIMToken",
    "SCIMTokenCreated",
    "SCIMTokenRotated",
    "SCIMUser",
    "SSOGroupMapping",
    "ServicePrincipal",
    "ServicePrincipalCreateParams",
    "ServicePrincipalCreated",
    "ServicePrincipalSecret",
    "ShadowAIApplication",
    "SigningKey",
    "SocialProvider",
    "SocialProviderUpdateParams",
    "SocialProviderUpsertParams",
    "TokenPair",
    "TokenResponse",
]

# ---------------------------------------------------------------------------
# OAuth


class TokenResponse(TypedDict):
    """A token endpoint's answer."""

    access_token: str
    token_type: str
    expires_in: int
    """The access token's lifetime in seconds."""
    scope: NotRequired[str]
    id_token: NotRequired[str]
    """Present when ``openid`` was granted."""
    refresh_token: NotRequired[str]
    """Present when the application is registered for ``refresh_token``."""
    issued_token_type: NotRequired[str]
    """RFC 8693: the type of the token a token exchange issued."""


class ClientCredentialsToken(TypedDict):
    """The client-credentials grant's answer: a token with its lifetime and expiry."""

    access_token: str
    token_type: str
    expires_in: int
    """The access token's lifetime in seconds."""
    expires_at: str
    """When the access token expires (RFC 3339)."""
    scope: str
    """The service principal's scopes, space-separated."""


class DeviceAuthorization(TypedDict):
    """RFC 8628 §3.2: what the device shows the person, and how it polls."""

    device_code: str
    user_code: str
    """The code the person types, ``XXXX-XXXX``."""
    verification_uri: str
    verification_uri_complete: NotRequired[str]
    expires_in: int
    interval: NotRequired[int]
    """The minimum seconds between polls."""


class BackchannelAuthentication(TypedDict):
    """OpenID CIBA: the request to poll with."""

    auth_req_id: str
    expires_in: int
    interval: int


class Introspection(TypedDict, total=False):
    """RFC 7662 introspection. Only ``active`` is always present; the claims come with an active token.

    An application learns only about its own tokens and tokens for resources it
    serves; any other answers ``{"active": False}``.
    """

    active: Required[bool]
    sub: str
    scope: str
    aud: str | list[str]
    client_id: str
    iss: str
    token_type: str
    resource: str | list[str]
    exp: int
    iat: int
    tenant_id: str
    sid: str
    actor_type: Literal["user", "service", "agent"] | str
    agent_id: str
    act: dict[str, Any]
    """RFC 8693: the party acting for the subject, ``{"sub": …}``."""


class OAuthGrant(TypedDict):
    """A person's consent to an application."""

    id: str
    client_id: str
    client_name: str
    user_id: str
    user_email: str
    user_name: str | None
    scopes: list[str]
    authorized_at: str
    consented_at: str | None
    last_used_at: str
    issued_at: str
    expires_at: str


class OAuthGrantListParams(TypedDict, total=False):
    limit: int
    cursor: str
    client_id: str
    """Only grants to this application."""


class OAuthGrantsRevoked(TypedDict):
    revoked: int


class OAuthDeviceAuthorization(TypedDict):
    """A device-flow authorization, for review. Never includes the device code."""

    id: str
    client_id: str
    client_name: NotRequired[str]
    user_code: str
    status: Literal["pending", "authorized", "denied"] | str
    user_id: NotRequired[str | None]
    user_email: NotRequired[str]
    scopes: NotRequired[list[str]]
    created_at: str
    expires_at: str
    last_polled_at: NotRequired[str | None]
    consumed_at: NotRequired[str | None]


class SigningKey(TypedDict):
    """Non-secret metadata of one of the issuer's signing keys."""

    kid: str
    alg: str
    use: str
    status: Literal["candidate", "active", "retired"] | str
    retire_at: NotRequired[str | None]
    created_at: NotRequired[str | None]
    activated_at: NotRequired[str | None]


class DiscoveryDocument(TypedDict, total=False):
    """The authorization server's metadata (OpenID Connect Discovery 1.0, RFC 8414)."""

    issuer: Required[str]
    authorization_endpoint: Required[str]
    token_endpoint: Required[str]
    jwks_uri: Required[str]
    userinfo_endpoint: str
    revocation_endpoint: str
    introspection_endpoint: str
    end_session_endpoint: str
    device_authorization_endpoint: str
    backchannel_authentication_endpoint: str
    grant_types_supported: list[str]
    scopes_supported: list[str]
    code_challenge_methods_supported: list[str]
    id_token_signing_alg_values_supported: list[str]
    token_endpoint_auth_methods_supported: list[str]
    resource_indicators_supported: bool
    actor_types_supported: list[str]


# ---------------------------------------------------------------------------
# Applications and RFC 8707 resources


class Application(TypedDict):
    """An OAuth 2.0 / OpenID Connect client that signs people in with Qeet ID."""

    id: str
    tenant_id: str
    client_id: str
    """The OAuth ``client_id``."""
    type: Literal["confidential", "public"] | str
    name: str
    redirect_uris: list[str]
    post_logout_uris: list[str]
    grant_types: list[str]
    scopes: list[str]
    created_at: str
    pkce_exempt_until: str | None
    """When a confidential application's exemption from PKCE ends; ``None`` for none."""
    backchannel_logout_uri: str
    frontchannel_logout_uri: str
    logo_uri: str
    client_uri: str
    web_origins: list[str]
    """Browser origins allowed to call the token endpoints."""


class ApplicationCreateParams(TypedDict, total=False):
    name: Required[str]
    type: Required[Literal["confidential", "public"]]
    redirect_uris: list[str]
    post_logout_uris: list[str]
    grant_types: list[str]
    scopes: list[str]
    backchannel_logout_uri: str
    frontchannel_logout_uri: str
    logo_uri: str
    client_uri: str
    web_origins: list[str] | None
    """Omit or ``None`` for the redirect URIs' origins."""


class ApplicationUpdateParams(TypedDict, total=False):
    name: str
    redirect_uris: list[str]
    post_logout_uris: list[str]
    grant_types: list[str]
    scopes: list[str]
    pkce_exempt_until: str | None
    """Sets (a time within 90 days) or clears (``None``) a confidential application's PKCE exemption."""
    backchannel_logout_uri: str
    frontchannel_logout_uri: str
    logo_uri: str
    client_uri: str
    web_origins: list[str] | None


class ApplicationCreated(TypedDict):
    """A registered application and, for a confidential one, its secret: shown once, never again."""

    client: Application
    client_secret: NotRequired[str]
    warning: NotRequired[str]


class ApplicationSecret(TypedDict):
    """A new secret, shown once. The old one stops working at once."""

    client_secret: str
    warning: NotRequired[str]


class ApplicationAuthFailure(TypedDict):
    at: str
    ip: str
    reason: str


class ApplicationAuthFailures(TypedDict):
    """An application's wrong-secret lockout and its last failed authentications."""

    locked_until: str | None
    items: list[ApplicationAuthFailure]


class ShadowAIApplication(TypedDict):
    """An application holding a machine grant nobody has reviewed: possibly unmanaged AI or automation."""

    id: str
    client_id: str
    name: str
    grant_types: list[str]
    live_grants: int
    """Live refresh grants: the higher, the more it is in use."""
    created_at: str


class OAuthResource(TypedDict):
    """An RFC 8707 resource. A token issued for it names it alone as audience."""

    id: str
    tenant_id: str
    identifier: str
    """An absolute URI without a fragment, unique on the platform."""
    name: NotRequired[str]
    server_client_id: NotRequired[str]
    """The application that serves the resource, which may then introspect its tokens."""
    created_at: str


class OAuthResourceCreateParams(TypedDict, total=False):
    identifier: Required[str]
    name: str
    server_client_id: str


# ---------------------------------------------------------------------------
# Service principals


class ServicePrincipal(TypedDict):
    """A machine identity that gets tokens with the ``client_credentials`` grant."""

    id: str
    tenant_id: str
    name: str
    description: str
    scopes: list[str]
    disabled_at: str | None
    last_used_at: str | None
    previous_secret_expires_at: NotRequired[str]
    """While a rotated-out secret still gets tokens."""
    created_at: str


class ServicePrincipalCreateParams(TypedDict, total=False):
    tenant_id: Required[str]
    name: Required[str]
    description: str
    scopes: list[str]


class ServicePrincipalCreated(TypedDict):
    """A new principal and its credentials. The secret is shown once and can't be read again."""

    service_principal: ServicePrincipal
    client_id: str
    client_secret: str
    warning: str


class ServicePrincipalSecret(TypedDict):
    """A new secret, shown once, and when the old one stops working."""

    client_id: str
    client_secret: str
    previous_secret_expires_at: str
    warning: str


# ---------------------------------------------------------------------------
# SAML

ConnectionStatus = Literal["draft", "active", "disabled"]
"""A connection's lifecycle state: a ``draft`` lacks the identity provider's details."""


class SAMLCertificate(TypedDict):
    """One of an identity provider's signing certificates."""

    id: str
    certificate: str
    subject: str
    fingerprint_sha256: str
    not_before: str | None
    not_after: str | None
    source: Literal["manual", "metadata"] | str
    created_at: str


class SAMLConnection(TypedDict):
    """An inbound SAML connection: Qeet ID is the service provider for an external identity provider."""

    id: str
    tenant_id: str
    name: str
    sp_entity_id: str
    """Give these to the identity provider: ``sp_entity_id``, ``acs_url``, ``sp_metadata_url``."""
    acs_url: str
    sp_metadata_url: str
    idp_entity_id: NotRequired[str]
    idp_sso_url: NotRequired[str]
    idp_certificate: NotRequired[str]
    certificates: NotRequired[list[SAMLCertificate]]
    metadata_url: NotRequired[str | None]
    metadata_refreshed_at: NotRequired[str | None]
    metadata_error: NotRequired[str | None]
    email_attribute: NotRequired[str]
    name_attribute: NotRequired[str]
    groups_attribute: NotRequired[str]
    status: ConnectionStatus | str
    allow_idp_initiated: NotRequired[bool]
    created_at: str
    updated_at: str
    last_login_at: NotRequired[str | None]


class _SAMLConnectionFields(TypedDict, total=False):
    idp_entity_id: str
    idp_sso_url: str
    idp_certificate: str
    email_attribute: str
    name_attribute: str
    groups_attribute: str
    status: ConnectionStatus


class SAMLConnectionCreateParams(_SAMLConnectionFields, total=False):
    """A name alone creates a draft; the identity provider's details come together or not at all."""

    name: Required[str]


class SAMLConnectionUpdateParams(_SAMLConnectionFields, total=False):
    name: str


class SAMLConnectionImportParams(TypedDict, total=False):
    """Creates a connection from the identity provider's metadata: a URL or the XML."""

    name: Required[str]
    metadata_url: str
    metadata_xml: str
    idp_entity_id: str
    email_attribute: str
    name_attribute: str
    groups_attribute: str
    status: ConnectionStatus


class ConnectionCheck(TypedDict):
    name: str
    ok: bool
    detail: NotRequired[str]


class ConnectionTestResult(TypedDict):
    """A connection test: each check and the overall result."""

    ok: bool
    checks: list[ConnectionCheck]


class SSOGroupMapping(TypedDict):
    """Maps an identity provider group to one of the organisation's groups."""

    id: str
    idp_group: str
    group_id: str
    group_name: str
    created_at: str


class SAMLAttributeMapping(TypedDict):
    """A SAML attribute sent to a service provider, and the user field it comes from."""

    name: str
    source: str
    name_format: NotRequired[Literal["basic", "uri", "unspecified"]]


class SAMLCertificateDetails(TypedDict):
    subject: str
    fingerprint_sha256: str
    not_before: str
    not_after: str


class SAMLServiceProvider(TypedDict):
    """A downstream service provider that signs people in with Qeet ID as its SAML identity provider."""

    id: str
    tenant_id: str
    name: str
    entity_id: str
    acs_url: str
    name_id_format: NotRequired[str]
    name_id_attribute: NotRequired[str]
    certificate: NotRequired[str]
    require_signed_requests: NotRequired[bool]
    encrypt_assertions: NotRequired[bool]
    certificate_details: NotRequired[SAMLCertificateDetails]
    status: ConnectionStatus | str
    attributes: NotRequired[list[SAMLAttributeMapping]]
    assignment_required: NotRequired[bool]
    """Only assigned users and groups may sign in to it."""
    created_at: str
    updated_at: str
    last_login_at: NotRequired[str | None]


class _SAMLServiceProviderFields(TypedDict, total=False):
    name_id_format: str
    name_id_attribute: str
    certificate: str
    require_signed_requests: bool
    encrypt_assertions: bool
    attributes: list[SAMLAttributeMapping]
    assignment_required: bool


class SAMLServiceProviderCreateParams(_SAMLServiceProviderFields, total=False):
    name: Required[str]
    entity_id: Required[str]
    acs_url: Required[str]


class SAMLServiceProviderUpdateParams(_SAMLServiceProviderFields, total=False):
    name: str
    entity_id: str
    acs_url: str


class SAMLServiceProviderUserAssignment(TypedDict):
    user_id: str
    email: str
    display_name: str | None
    assigned_at: str
    assigned_by: str | None


class SAMLServiceProviderGroupAssignment(TypedDict):
    group_id: str
    name: str
    assigned_at: str
    assigned_by: str | None


class SAMLServiceProviderAssignments(TypedDict):
    """Who may sign in to a service provider that requires assignment."""

    users: list[SAMLServiceProviderUserAssignment]
    groups: list[SAMLServiceProviderGroupAssignment]


# ---------------------------------------------------------------------------
# Directories (LDAP)


class LDAPConnection(TypedDict):
    """A directory (LDAP or Active Directory) connection. The bind password is never returned."""

    id: str
    tenant_id: str
    name: str
    server_url: str
    start_tls: bool
    skip_tls_verify: bool
    bind_dn: str
    base_dn: str
    user_filter: str
    email_attribute: str
    name_attribute: str
    status: ConnectionStatus | str
    created_at: str
    updated_at: str
    last_login_at: str | None


class _LDAPConnectionFields(TypedDict, total=False):
    start_tls: bool
    skip_tls_verify: bool
    """Sign-in refuses a connection that skips certificate verification."""
    user_filter: str
    email_attribute: str
    name_attribute: str
    status: ConnectionStatus


class LDAPConnectionCreateParams(_LDAPConnectionFields, total=False):
    """Unset optional fields get the server's defaults (``(uid=%s)``, ``mail``, ``cn``, ``draft``)."""

    name: Required[str]
    server_url: Required[str]
    """Starts ``ldap://`` or ``ldaps://``."""
    bind_dn: Required[str]
    bind_password: Required[str]
    base_dn: Required[str]


class LDAPConnectionUpdateParams(_LDAPConnectionFields, total=False):
    name: str
    server_url: str
    bind_dn: str
    bind_password: str
    base_dn: str


class LDAPTestResult(TypedDict):
    ok: bool


class TokenPair(TypedDict):
    """A session's tokens."""

    access_token: str
    token_type: str
    expires_at: str
    refresh_token: str
    session_expires_at: str
    """When the session ends however active it is."""
    idle_expires_at: str
    """When the session ends unless renewed before then."""
    session_id: str
    user_id: str
    tenant_id: NotRequired[str | None]


class MfaFactor(TypedDict):
    """A second factor the person may complete a challenge with."""

    type: Literal["totp", "recovery_code", "email", "sms", "passkey", "push"] | str
    id: NotRequired[str]
    """An email or SMS factor's id."""
    destination: NotRequired[str]
    """An email or SMS factor's masked address or number."""


class MfaChallenge(TypedDict):
    """A sign-in stopped before its session: complete it at ``POST /v1/auth/mfa`` with ``mfa_token``."""

    mfa_required: Literal[True]
    mfa_token: str
    methods: list[str]
    factors: list[MfaFactor]
    enrollment_required: NotRequired[bool]
    """The account must set up a second factor first."""
    enrollment_due_at: NotRequired[str]


class LDAPTokensResult(TypedDict):
    type: Literal["tokens"]
    tokens: TokenPair


class LDAPMfaChallengeResult(TypedDict):
    type: Literal["mfa_challenge"]
    challenge: MfaChallenge


LDAPAuthenticationResult = LDAPTokensResult | LDAPMfaChallengeResult
"""A directory sign-in's outcome: tokens, or a second-factor challenge. Branch on ``type``."""


# ---------------------------------------------------------------------------
# SCIM


class SCIMLastRequest(TypedDict):
    at: str
    operation: Literal["post", "put", "patch", "delete"] | str
    resource: Literal["user", "group"] | str
    http_status: int
    status: Literal["success", "warning", "failed"] | str
    error_code: NotRequired[str]
    reason: NotRequired[str]


class SCIMConfig(TypedDict):
    """The organisation's SCIM provisioning state. Tokens are never returned after they are issued."""

    token_set: bool
    token_count: int
    token_prefix: NotRequired[str]
    created_at: str | None
    last_used_at: str | None
    provisioned_count: int
    last_request: SCIMLastRequest | None
    """The identity provider's latest request, when there was one."""


class SCIMToken(TypedDict):
    """A SCIM bearer token's record."""

    id: str
    name: str
    token_prefix: str
    status: Literal["active", "rotated", "expired", "revoked"] | str
    created_at: str
    expires_at: str | None
    last_used_at: str | None
    revoked_at: str | None
    replaced_by: str | None


class SCIMTokenCreated(TypedDict):
    """A new SCIM token. ``token`` is shown only here: give it to the identity provider."""

    scim_token: SCIMToken
    token: str


class SCIMTokenRotated(SCIMTokenCreated):
    replaced: SCIMToken


class SCIMUser(TypedDict):
    """A user the identity provider provisioned over SCIM."""

    id: str
    email: str
    display_name: str | None
    external_id: str | None
    status: str
    created_at: str


class SCIMGroup(TypedDict):
    """A group the identity provider provisioned over SCIM."""

    id: str
    name: str
    external_id: str | None
    members: int
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Social sign-in


class SocialProvider(TypedDict):
    """A social sign-in provider. Its client secret is never returned."""

    id: str
    tenant_id: str
    provider: str
    """``github``, ``facebook``, ``x``, ``discord``, ``apple``, or any name for an OpenID Connect provider."""
    kind: Literal["oidc", "github", "facebook", "x", "discord", "apple"] | str
    client_id: str
    discovery_url: str | None
    enabled: bool
    apple_team_id: NotRequired[str]
    apple_key_id: NotRequired[str]
    created_at: str


class SocialProviderUpsertParams(TypedDict, total=False):
    """Adds a provider, or replaces one's settings. An empty ``client_secret`` keeps the stored one.

    For Apple, ``client_id`` is the Services ID and ``client_secret`` the ``.p8`` key,
    with ``apple_team_id`` and ``apple_key_id``.
    """

    provider: Required[str]
    client_id: Required[str]
    client_secret: str
    discovery_url: str
    """Required for an OpenID Connect provider."""
    apple_team_id: str
    apple_key_id: str


class SocialProviderUpdateParams(TypedDict, total=False):
    enabled: bool
    client_id: str
    client_secret: str
    discovery_url: str
    apple_team_id: str
    apple_key_id: str


# ---------------------------------------------------------------------------
# Admin portal links

AdminPortalCapability = Literal["saml", "scim", "domain_verification"]
"""What a link's holder may set up."""


class AdminPortalLink(TypedDict):
    """A time-limited link that lets a customer's IT administrator set up SSO, SCIM or domains."""

    id: str
    tenant_id: str
    capabilities: list[AdminPortalCapability | str]
    created_by: str | None
    expires_at: str
    revoked_at: str | None
    last_used_at: str | None
    created_at: str


class AdminPortalLinkCreated(TypedDict):
    """A new link. ``token`` and ``url`` are shown only here."""

    link: AdminPortalLink
    token: str
    url: str
