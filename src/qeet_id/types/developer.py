"""Developer: API keys, agents, credentials, auth hooks, webhook subscriptions, secrets, the token vault."""

from typing import Any, Literal, NotRequired, Required, TypedDict

__all__ = [
    "APIKey",
    "APIKeyCreateParams",
    "APIKeyCreated",
    "Agent",
    "AgentCreateParams",
    "AgentLifecycle",
    "AgentSecret",
    "AgentStatus",
    "AgentToken",
    "AgentsResumed",
    "AgentsSuspended",
    "AuthHook",
    "AuthHookCreateParams",
    "AuthHookState",
    "AuthHookTestResult",
    "AuthHookUpdateParams",
    "CredentialUser",
    "CredentialVerification",
    "IssuedCredential",
    "Secret",
    "SecretCreateParams",
    "SecretRevealedBy",
    "SecretUpdateParams",
    "SecretValue",
    "SponsorshipTransfer",
    "TokenVaultAccessToken",
    "TokenVaultProvider",
    "TokenVaultProviderCreateParams",
    "VerifiableCredential",
    "VerifiableCredentialIssueParams",
    "WebhookCreateParams",
    "WebhookDeliveriesRequeued",
    "WebhookDelivery",
    "WebhookDeliveryAttempt",
    "WebhookDeliveryCounts",
    "WebhookDeliveryListParams",
    "WebhookEventTypeInfo",
    "WebhookSecret",
    "WebhookSubscription",
    "WebhookTestQueued",
    "WebhookUpdateParams",
]

# ---------------------------------------------------------------------------
# API keys


class APIKey(TypedDict):
    """An API key's record. The key itself is shown only when it is created or rotated."""

    id: str
    tenant_id: str
    user_id: str | None
    """The user a personal key acts for; ``None`` for an organisation key."""
    name: str
    prefix: str
    """The key's first characters, to recognise it by."""
    scopes: list[str]
    expires_at: str | None
    last_used_at: str | None
    revoked_at: str | None
    created_at: str
    created_by: NotRequired[str | None]
    rotated_from: NotRequired[str | None]
    """The key this one replaced in a rotation."""


class APIKeyCreateParams(TypedDict, total=False):
    tenant_id: Required[str]
    name: Required[str]
    user_id: str | None
    """Makes a personal key that acts for this user."""
    scopes: list[str]
    expires_at: str | None
    """An RFC 3339 time; ``None`` or omitted for a key that doesn't expire."""


class APIKeyCreated(TypedDict):
    """A new key. ``secret`` is shown only here: store it in a secrets manager."""

    api_key: APIKey
    secret: str
    warning: NotRequired[str]


# ---------------------------------------------------------------------------
# Agents

AgentLifecycle = Literal["active", "suspended", "decommissioned"]
"""An AI agent's lifecycle state. ``decommissioned`` is final."""


class Agent(TypedDict):
    """An AI agent identity, accountable to a human sponsor."""

    id: str
    name: str
    scopes: list[str]
    token_ttl_seconds: int
    """The lifetime of the tokens it gets."""
    status: AgentLifecycle | str
    disabled: bool
    """True whenever ``status`` isn't ``active``."""
    sponsor_user_id: NotRequired[str]
    """The person accountable for the agent."""
    last_used_at: NotRequired[str | None]
    previous_secret_expires_at: NotRequired[str]
    created_at: str
    secret: NotRequired[str]
    """The agent's secret: only in ``create``'s answer, once."""


class AgentCreateParams(TypedDict, total=False):
    name: Required[str]
    sponsor_user_id: Required[str]
    """The person accountable for the agent."""
    scopes: list[str]
    token_ttl_seconds: int


class AgentStatus(TypedDict):
    status: AgentLifecycle | str


class AgentsSuspended(TypedDict):
    suspended: int


class AgentsResumed(TypedDict):
    resumed: int


class SponsorshipTransfer(TypedDict):
    transferred: int


class AgentToken(TypedDict):
    """A token for an agent, from its id and secret."""

    access_token: str
    token_type: str
    expires_in: int
    scope: NotRequired[str]


class AgentSecret(TypedDict):
    """A new agent secret, shown once, and when the old one stops working."""

    id: str
    secret: str
    previous_secret_expires_at: str


# ---------------------------------------------------------------------------
# Verifiable credentials


class CredentialUser(TypedDict):
    id: str
    email: str
    display_name: str


class VerifiableCredential(TypedDict):
    """An issued W3C verifiable credential's record."""

    id: str
    subject: str
    type: str
    issued_at: str
    expires_at: NotRequired[str]
    revoked: bool
    user: CredentialUser | None
    """The user it was issued for, when it names one."""


class VerifiableCredentialIssueParams(TypedDict, total=False):
    subject: Required[str]
    type: Required[str]
    claims: dict[str, Any]
    ttl_seconds: int
    user_id: str | None
    """One of the organisation's users the credential is about."""


class IssuedCredential(TypedDict):
    """An issued credential: a signed JWT-VC."""

    credential_id: str
    jwt: str
    expires_at: NotRequired[str]


class CredentialVerification(TypedDict):
    """Whether a presented JWT-VC is authentic and not revoked."""

    valid: bool
    reason: NotRequired[str]
    reason_code: NotRequired[Literal["vc.not_credential", "vc.signature_invalid", "vc.unknown", "vc.revoked"] | str]
    subject: NotRequired[str]
    issuer: NotRequired[str]
    vc: NotRequired[dict[str, Any]]


# ---------------------------------------------------------------------------
# Authentication hooks


class AuthHook(TypedDict):
    """A signed call to your endpoint during sign-in, which may allow, deny or add claims."""

    id: str
    trigger: str
    url: str
    enabled: bool
    fail_open: bool
    """Whether a failing hook lets sign-in proceed."""
    created_at: str
    last_called_at: NotRequired[str | None]
    last_outcome: NotRequired[Literal["allowed", "denied", "skipped"] | str | None]
    last_status_code: NotRequired[int | None]
    calls: NotRequired[int]
    skips: NotRequired[int]
    denies: NotRequired[int]


class AuthHookCreateParams(TypedDict, total=False):
    url: Required[str]
    secret: str
    """Signs every call; generated when omitted."""
    fail_open: bool
    """Default true: an unreachable hook doesn't block sign-in."""


class AuthHookUpdateParams(TypedDict, total=False):
    url: str
    secret: str
    enabled: bool
    fail_open: bool


class AuthHookState(TypedDict):
    enabled: bool
    fail_open: bool


class AuthHookTestResult(TypedDict, total=False):
    """A test call's outcome."""

    status_code: int
    duration_ms: int
    decision: Literal["allow", "deny", "none"] | str
    message: str
    claims: dict[str, Any]
    error: str


# ---------------------------------------------------------------------------
# Webhook subscriptions


class WebhookDeliveryCounts(TypedDict):
    pending: int
    retrying: int
    gave_up: int


class WebhookSubscription(TypedDict):
    """A webhook subscription: an endpoint and the events it receives."""

    id: str
    tenant_id: str
    url: str
    events: list[str]
    disabled_at: str | None
    disabled_reason: NotRequired[Literal["disabled", "failing"] | str | None]
    """``disabled`` by an administrator, or ``failing`` after three days of failed deliveries."""
    disabled_by: NotRequired[str]
    failing_since: NotRequired[str | None]
    previous_secret_expires_at: NotRequired[str | None]
    """While a rotated-out secret still signs deliveries alongside the new one."""
    last_delivered_at: NotRequired[str | None]
    last_status_code: NotRequired[int | None]
    counts: NotRequired[WebhookDeliveryCounts]
    created_at: str
    secret: NotRequired[str]
    """The signing secret: only in ``create``'s answer, once."""


class WebhookCreateParams(TypedDict, total=False):
    url: Required[str]
    """A public https URL."""
    events: Required[list[str]]
    """At least one event from the catalogue."""
    tenant_id: str


class WebhookUpdateParams(TypedDict, total=False):
    url: str
    events: list[str]


class WebhookDelivery(TypedDict):
    """One attempt-tracked delivery of an event to a subscription."""

    id: str
    event_type: str
    attempt: int
    status_code: NotRequired[int]
    error: NotRequired[str]
    payload: str
    """The delivered body, as JSON text."""
    response_body: NotRequired[str]
    delivered_at: NotRequired[str]
    next_attempt_at: NotRequired[str]
    dead_at: NotRequired[str]
    created_at: str


class WebhookDeliveryListParams(TypedDict, total=False):
    limit: int
    cursor: str
    status: Literal["delivered", "pending", "retrying", "dead"]


class WebhookDeliveryAttempt(TypedDict):
    """One attempt to send a delivery."""

    attempted_at: str
    status_code: int | None
    duration_ms: int
    error: str | None


class WebhookDeliveriesRequeued(TypedDict):
    requeued: int


class WebhookSecret(TypedDict):
    secret: str
    previous_secret_expires_at: str


class WebhookTestQueued(TypedDict):
    queued: bool
    subscription: str


class WebhookEventTypeInfo(TypedDict):
    name: str
    description: str


# ---------------------------------------------------------------------------
# Secrets


class SecretRevealedBy(TypedDict):
    id: str
    email: str
    display_name: str


class Secret(TypedDict):
    """A secret's record. Its value is returned only by ``reveal`` and ``get_value``."""

    id: str
    name: str
    scope: str
    last4: str
    """The value's last four characters."""
    created_at: str
    updated_at: str
    value_changed_at: str
    last_revealed_at: str | None
    last_revealed_by: SecretRevealedBy | None
    last_revealed_credential: NotRequired[str]
    rotation_interval_days: int | None
    rotation_due_at: str | None
    rotation_overdue: bool


class SecretCreateParams(TypedDict, total=False):
    name: Required[str]
    scope: Required[str]
    value: Required[str]
    rotation_interval_days: int | None
    """Flags the secret overdue this many days after its value last changed; ``None`` for never."""


class SecretUpdateParams(TypedDict, total=False):
    scope: str | None
    value: str | None
    rotation_interval_days: int | None


class SecretValue(TypedDict):
    value: str
    name: NotRequired[str]


# ---------------------------------------------------------------------------
# Token vault


class TokenVaultProvider(TypedDict):
    """A third-party OAuth provider people can connect accounts from. Its client secret is never returned."""

    id: str
    provider: str
    client_id: str
    authorize_url: str
    token_url: str
    scopes: str
    """Space-separated scopes to ask for."""
    created_at: str
    updated_at: str


class TokenVaultProviderCreateParams(TypedDict, total=False):
    provider: Required[str]
    client_id: Required[str]
    client_secret: Required[str]
    authorize_url: Required[str]
    token_url: Required[str]
    scopes: str


class TokenVaultAccessToken(TypedDict):
    access_token: str
