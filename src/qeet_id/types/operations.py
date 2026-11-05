"""Operations: audit log, analytics, billing, GDPR, email templates, retention, log sinks, rate limits."""

from typing import Any, Literal, NotRequired, Required, TypedDict

__all__ = [
    "AnalyticsActivityPoint",
    "AnalyticsHourlyFailures",
    "AnalyticsKPIs",
    "AnalyticsMethodShare",
    "AnalyticsMetric",
    "AnalyticsMfaAdoption",
    "AnalyticsOverview",
    "AnalyticsOverviewParams",
    "AnalyticsRange",
    "AnalyticsRangeDay",
    "AnalyticsTrendPoint",
    "AnalyticsWeek",
    "AuditAnomaly",
    "AuditAnomalySettings",
    "AuditAnomalySummary",
    "AuditChainVerification",
    "AuditLogEntry",
    "AuditLogListParams",
    "AuditVerificationStatus",
    "BillingProfile",
    "BuiltInRateLimit",
    "CheckoutParams",
    "CheckoutResult",
    "EmailLocalizedContent",
    "EmailTemplate",
    "EmailTemplateContent",
    "EmailTemplateOptions",
    "EmailTemplatePreview",
    "Entitlements",
    "ErasureRequest",
    "ExportRequest",
    "Invoice",
    "LogSink",
    "LogSinkCreateParams",
    "LogSinkTestResult",
    "LogSinkType",
    "PaymentMethod",
    "RateLimitBucket",
    "RateLimitBuckets",
    "RateLimitsUpdateParams",
    "RetentionPolicy",
    "RetentionPreview",
    "RetentionRun",
    "Subscription",
    "SubscriptionCancellation",
    "TenantRateLimits",
]

# ---------------------------------------------------------------------------
# Audit log


class AuditLogEntry(TypedDict):
    """One entry of the hash-chained audit log."""

    id: str
    tenant_id: str | None
    action: str
    actor_type: str
    actor_user_id: str | None
    resource_type: str
    resource_id: str | None
    ip: str | None
    user_agent: str | None
    request_id: str | None
    metadata: NotRequired[dict[str, Any]]
    created_at: str


class AuditLogListParams(TypedDict, total=False):
    """Filters for ``audit_logs.list``. They combine."""

    limit: int
    cursor: str
    q: str
    """Free text over action, resource type, actor type, user agent and metadata; "quoted phrases",
    -exclusions and OR."""
    action: str
    resource_type: str
    resource_id: str
    actor_user_id: str
    ip: str
    from_: str
    """An RFC 3339 time: entries created at or after it. Sent as ``from``."""
    to: str
    """An RFC 3339 time: entries created before it."""


class AuditChainVerification(TypedDict):
    """The result of walking the hash chain now. A broken chain names the first bad row."""

    ok: bool
    rows_checked: int
    last_verified_id: NotRequired[str]
    broken_at_id: NotRequired[str]
    broken_reason: NotRequired[str]
    reason_code: NotRequired[Literal["audit.chain_prev_hash_mismatch", "audit.chain_row_hash_mismatch"] | str]


class AuditVerificationStatus(TypedDict):
    """The latest scheduled verification of the chain."""

    verified: bool
    intact: bool
    last_verified_at: str | None
    broken_at: str | None
    last_verified_event_id: str | None
    last_run_at: str | None
    last_run_scope: str


class AuditAnomaly(TypedDict):
    """An audit event that departs from the actor's usual behaviour."""

    id: str
    tenant_id: str
    event_id: str
    actor_user_id: str | None
    actor_email: NotRequired[str | None]
    score: float
    reasons: list[Literal["new_action_type", "unusual_hour", "new_ip"] | str]
    status: Literal["open", "resolved"] | str
    resolved_at: str | None
    resolved_by: str | None
    action: NotRequired[str]
    resource_type: NotRequired[str]
    ip: NotRequired[str | None]
    event_at: NotRequired[str]
    created_at: str


class AuditAnomalySummary(TypedDict):
    open: int
    high_score_open: int
    resolved_7d: int


class AuditAnomalySettings(TypedDict):
    enabled: bool
    score_threshold: float
    """Events scoring at least this are flagged."""
    min_baseline_events: int
    """Events an actor needs before their behaviour is judged."""


# ---------------------------------------------------------------------------
# Analytics


class AnalyticsMetric(TypedDict):
    value: float
    delta_pct: float


class AnalyticsTrendPoint(TypedDict):
    date: str
    value: float


class AnalyticsActivityPoint(TypedDict):
    """One day's sign-ins by method. A method with none is 0, not missing."""

    date: str
    password: int
    passkey: int
    social: int
    saml: int
    oidc: int
    ldap: int
    magic_link: int


class AnalyticsKPIs(TypedDict):
    mau: AnalyticsMetric
    dau: AnalyticsMetric
    logins_today: AnalyticsMetric
    failed_logins_24h: AnalyticsMetric
    mfa_adoption_pct: AnalyticsMetric
    total_users: AnalyticsMetric
    avg_sessions_per_user: AnalyticsMetric
    stickiness_pct: AnalyticsMetric


class AnalyticsWeek(TypedDict):
    week: str
    wau: int
    dau: int


class AnalyticsMethodShare(TypedDict):
    method: str
    value: float


class AnalyticsMfaAdoption(TypedDict):
    method: str
    users: int


class AnalyticsHourlyFailures(TypedDict):
    hour: str
    attempts: int


class AnalyticsRangeDay(TypedDict):
    date: str
    sign_ins: int
    people: int
    failed: int


# ``from`` is a Python keyword, so the range is declared functionally.
AnalyticsRange = TypedDict(
    "AnalyticsRange", {"from": str, "to": str, "method": str, "days": list[AnalyticsRangeDay]}, total=False
)


class AnalyticsOverview(TypedDict):
    """The sign-in dashboard: key figures and trends."""

    generated_at: str
    kpis: AnalyticsKPIs
    weekly_activity_8w: list[AnalyticsWeek]
    user_trend_14d: list[AnalyticsTrendPoint]
    login_trend_14d: list[AnalyticsTrendPoint]
    mfa_trend_14d: list[AnalyticsTrendPoint]
    failed_trend_14d: list[AnalyticsTrendPoint]
    login_activity_14d: list[AnalyticsActivityPoint]
    login_methods_mix: list[AnalyticsMethodShare]
    mfa_methods_adoption: list[AnalyticsMfaAdoption]
    failed_logins_hourly_24h: list[AnalyticsHourlyFailures]
    range: NotRequired[AnalyticsRange]
    """Present when a range was asked for."""


class AnalyticsOverviewParams(TypedDict, total=False):
    from_: str
    """An RFC 3339 time starting the range. Sent as ``from``."""
    to: str
    days: int
    """A range of this many days back."""
    method: str
    """Only this sign-in method."""


# ---------------------------------------------------------------------------
# Billing


class Subscription(TypedDict):
    """The organisation's Qeet ID subscription. Status ``none`` means it has none."""

    status: Literal["none", "trialing", "active", "past_due", "canceled"] | str
    plan_code: str
    plan_name: str
    currency: str
    amount_minor: int
    """In minor units (paise, cents)."""
    interval: str
    current_period_start: str | None
    current_period_end: str | None
    trial_end: str | None
    cancel_at_period_end: bool
    ended_at: NotRequired[str | None]


class SubscriptionCancellation(TypedDict):
    cancel_at_period_end: bool


class BillingProfile(TypedDict, total=False):
    """Who invoices are addressed to."""

    legal_name: str
    billing_email: str
    address_line1: str
    address_line2: str
    city: str
    state: str
    postal_code: str
    country: str
    tax_id: str
    tax_id_type: str


class Invoice(TypedDict):
    """A tax invoice. Amounts are in minor units."""

    id: str
    invoice_number: str | None
    plan_code: str
    kind: NotRequired[Literal["purchase", "renewal"] | str]
    status: Literal["paid", "open", "void"] | str
    currency: str
    amount_minor: int
    taxable_amount_minor: int
    tax_amount_minor: int
    tax_rate_bps: int
    tax_type: str
    place_of_supply: str
    supplier_gstin: NotRequired[str]
    sac: NotRequired[str]
    billed_to: NotRequired[BillingProfile | None]
    period_start: str
    period_end: str
    issued_at: str
    due_at: NotRequired[str | None]
    paid_at: NotRequired[str | None]
    emailed_at: NotRequired[str | None]


class PaymentMethod(TypedDict):
    """The card or mandate on file."""

    provider: str
    type: str
    brand: NotRequired[str]
    last4: NotRequired[str]
    exp_month: NotRequired[int]
    exp_year: NotRequired[int]
    last_used_at: str


class CheckoutParams(TypedDict, total=False):
    plan_code: Required[str]
    currency: Required[str]
    country: str
    """ISO 3166-1 alpha-2, for tax."""
    success_url: Required[str]
    cancel_url: Required[str]


class CheckoutResult(TypedDict):
    """``active`` for an immediate activation (a free plan); ``checkout`` with the URL to send the person to."""

    status: Literal["active", "checkout"] | str
    checkout_url: NotRequired[str]
    provider: NotRequired[str]


class Entitlements(TypedDict):
    """The organisation's plan: its features and limits."""

    plan: Literal["free", "starter", "pro", "enterprise"] | str
    features: dict[str, bool]
    limits: dict[str, int]


# ---------------------------------------------------------------------------
# GDPR


class ErasureRequest(TypedDict):
    """An erasure request. It runs when its grace period ends, unless cancelled first."""

    id: str
    tenant_id: str
    user_id: str
    requested_by: str | None
    reason: str | None
    status: str
    grace_until: str
    grace_period_days: NotRequired[int]
    completed_at: str | None
    created_at: str
    subject_email: NotRequired[str | None]
    subject_name: NotRequired[str | None]
    subject_redacted: NotRequired[bool]
    """The subject's details were erased."""


class ExportRequest(TypedDict):
    """A data export. ``payload`` is filled in once ``status`` is ``ready``."""

    id: str
    tenant_id: str
    user_id: str
    requested_by: str | None
    status: Literal["pending", "ready", "failed"] | str
    payload: NotRequired[dict[str, Any]]
    error: NotRequired[str]
    completed_at: str | None
    created_at: str


# ---------------------------------------------------------------------------
# Email templates


class EmailLocalizedContent(TypedDict, total=False):
    """A template's text in one language."""

    subject: Required[str]
    body: Required[str]
    preheader: str
    body_html: str


class EmailTemplateOptions(TypedDict, total=False):
    preheader: str
    body_html: str
    default_locale: str
    show_logo: bool
    alignment: Literal["left", "center"]
    translations: dict[str, EmailLocalizedContent]


class EmailTemplateContent(TypedDict, total=False):
    """A template's editable content. ``{{name}}`` placeholders are filled in when it is sent."""

    subject: Required[str]
    body: Required[str]
    options: EmailTemplateOptions


class EmailTemplate(TypedDict):
    """A template as it is used: the organisation's override (``custom``), or the platform's default."""

    key: str
    name: str
    description: NotRequired[str]
    variables: NotRequired[list[str]]
    """The placeholders it may use."""
    custom: bool
    delivery_scope: NotRequired[Literal["tenant", "platform"] | str]
    subject: str
    body: str
    options: NotRequired[EmailTemplateOptions]


class EmailTemplatePreview(TypedDict):
    """A rendered template. Placeholders left as ``{{name}}`` were not given."""

    subject: str
    body: str
    html: NotRequired[str]
    locale: NotRequired[str]


# ---------------------------------------------------------------------------
# Retention


class RetentionPolicy(TypedDict):
    """When soft-deleted users are purged for good."""

    deleted_users_enabled: bool
    deleted_users_days: int
    """1 to 3650; clamped."""
    updated_at: NotRequired[str]
    updated_by: NotRequired[str]
    updated_by_email: NotRequired[str]


class RetentionPreview(TypedDict):
    ripe_deleted_users: int
    deleted_users_days: int


class RetentionRun(TypedDict):
    purged: int


# ---------------------------------------------------------------------------
# Log sinks

LogSinkType = Literal["splunk_hec", "datadog", "http"]


class LogSink(TypedDict):
    """A destination the audit log is streamed to (a SIEM). Its token is never returned."""

    id: str
    type: LogSinkType | str
    endpoint: str
    enabled: bool
    last_forwarded_at: NotRequired[str]
    last_error: NotRequired[str]
    created_at: str


class LogSinkCreateParams(TypedDict, total=False):
    type: Required[LogSinkType]
    endpoint: Required[str]
    token: str


class LogSinkTestResult(TypedDict):
    """A test event's delivery."""

    delivered: bool
    status: NotRequired[int]
    error: NotRequired[str]
    duration_ms: int


# ---------------------------------------------------------------------------
# Rate limits


class RateLimitBucket(TypedDict):
    """A token bucket: ``rate`` tokens a second, bursting to ``capacity``."""

    rate: float
    capacity: int


class RateLimitBuckets(TypedDict):
    tenant: RateLimitBucket
    user: RateLimitBucket
    api_key: RateLimitBucket


class BuiltInRateLimit(TypedDict):
    name: str
    per: Literal["ip", "user", "address"] | str
    applies: str
    rate: float
    capacity: int


class RateLimitsUpdateParams(TypedDict, total=False):
    tenant: RateLimitBucket
    user: RateLimitBucket
    api_key: RateLimitBucket


class TenantRateLimits(RateLimitsUpdateParams, total=False):
    """The organisation's rate limits per scope, with the defaults and ceilings they sit within."""

    defaults: RateLimitBuckets
    """Read-only."""
    ceiling: RateLimitBuckets
    min_rate: float
    built_in: list[BuiltInRateLimit]
    """Read-only: the platform's fixed limits, such as sign-in attempts per address."""
