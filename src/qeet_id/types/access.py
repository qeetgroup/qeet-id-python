"""Access: roles, permissions, relationships, AuthZEN decisions, policies, address rules and threats."""

from typing import Any, Literal, NotRequired, Required, TypedDict

__all__ = [
    "Anomaly",
    "AnomalySummary",
    "AuthPolicy",
    "AuthPolicyUpdateParams",
    "AuthPolicyUsage",
    "AuthPolicyUsageMethod",
    "AuthPolicyUsageSocial",
    "AuthzenAction",
    "AuthzenEntity",
    "BotActivity",
    "BotActivityStats",
    "BotEvent",
    "BotSettings",
    "DecidedBy",
    "DecisionLogEntry",
    "DecisionSource",
    "EffectivePermissions",
    "Evaluation",
    "EvaluationRequest",
    "Evaluations",
    "EvaluationsOptions",
    "GrantStep",
    "IPRule",
    "IPRuleCheck",
    "IPRuleDecision",
    "IPRuleEnforcement",
    "IPRuleList",
    "IPRuleReasonCode",
    "LockoutLimits",
    "LockoutSettings",
    "Permission",
    "PermissionDecision",
    "RelationDecision",
    "RelationGraph",
    "RelationGraphEdge",
    "RelationGraphNode",
    "RelationObject",
    "RelationObjectType",
    "RelationPathStep",
    "RelationTuple",
    "RiskSettings",
    "RiskSettingsUpdateParams",
    "Role",
    "RoleHolder",
    "RoleHolderCounts",
    "RoleHolderGroup",
    "RoleHolders",
    "SecurityPolicy",
    "SecurityPolicyUpdateParams",
]

# ---------------------------------------------------------------------------
# Roles and permissions


class RoleHolderCounts(TypedDict):
    people_direct: int
    people_through_groups: int
    groups: int


class Role(TypedDict):
    """A named set of permissions. Built-in roles (``owner``, ``admin``, ``member``, ``viewer``) can't change."""

    id: str
    tenant_id: str
    name: str
    description: NotRequired[str]
    is_system: bool
    created_at: str
    holders: NotRequired[RoleHolderCounts]
    """How many hold the role, directly or through groups."""


class RoleHolderGroup(TypedDict):
    id: str
    name: str


class RoleHolder(TypedDict):
    user_id: str
    email: str
    display_name: str
    direct: bool
    via_groups: list[RoleHolderGroup]


class RoleHolders(TypedDict):
    """Who holds a role: people (directly or through groups) and the groups granted it."""

    people: list[RoleHolder]
    groups: list[RoleHolderGroup]
    next_cursor: NotRequired[str]
    """Pass as ``cursor`` for the next page of people; absent on the last."""


class Permission(TypedDict):
    """A permission key, such as ``user.read``, from the platform's fixed catalogue."""

    id: str
    key: str
    description: NotRequired[str]


class DecidedBy(TypedDict):
    """Which model decided an authorization question, and by which rule."""

    model: Literal["tenant", "abac", "rbac", "rebac", "none"] | str
    rule: NotRequired[str]
    reason_code: NotRequired[str]
    reason_params: NotRequired[dict[str, Any]]
    policy_id: NotRequired[str]
    """The deciding ABAC policy, named only to a caller allowed to read policies."""


class GrantStep(TypedDict):
    """One grant behind a permission: the role, held directly or through a group."""

    permission: str
    granted_by: str
    via: str
    """``direct``, or ``group:<name>``."""
    group_id: NotRequired[str]
    group_name: NotRequired[str]
    role_id: str
    role_name: NotRequired[str]


class PermissionDecision(TypedDict):
    """A permission check's answer with its reasons."""

    allowed: bool
    decided_by: NotRequired[DecidedBy]
    paths: NotRequired[list[GrantStep]]
    """On an allow: the grants behind it."""
    reason: NotRequired[str]
    """On a deny: why."""
    reason_code: NotRequired[
        Literal["authz.no_role_grant", "authz.denied_by_policy", "authz.attribute_absent", "authz.condition_error"]
        | str
    ]
    reason_params: NotRequired[dict[str, Any]]
    trace: NotRequired[list[str]]


class EffectivePermissions(TypedDict):
    """Every permission a user holds in an organisation, and the grants behind them."""

    permissions: list[str]
    grants: list[GrantStep]


# ---------------------------------------------------------------------------
# Relationships (ReBAC)


class RelationTuple(TypedDict):
    """``subject`` holds ``relation`` on ``object``.

    ``object`` is ``type:id``; ``subject`` is ``type:id``, or a userset ``type:id#relation``
    (such as ``group:eng#member``).
    """

    id: str
    object: str
    relation: str
    subject: str
    subject_name: NotRequired[str]
    """A readable name for the subject, when known."""


class RelationPathStep(TypedDict):
    object: str
    relation: str
    subject: str
    depth: int


class RelationDecision(TypedDict):
    """A relationship check's answer. ``path`` and ``trace`` come with ``explain``."""

    allowed: bool
    decided_by: NotRequired[DecidedBy]
    trace: NotRequired[list[str]]
    path: NotRequired[list[RelationPathStep]]


class RelationGraphNode(TypedDict):
    id: str
    type: str
    label: str
    name: NotRequired[str]


# ``from`` is a Python keyword, so the edge is declared functionally.
RelationGraphEdge = TypedDict("RelationGraphEdge", {"from": str, "to": str, "relation": str})


class RelationGraph(TypedDict):
    """Every identity reachable from an object and relation."""

    nodes: list[RelationGraphNode]
    edges: list[RelationGraphEdge]


class RelationObjectType(TypedDict):
    type: str
    objects: int
    tuples: int


class RelationObject(TypedDict):
    object: str
    id: str
    tuples: int


# ---------------------------------------------------------------------------
# AuthZEN decisions


class AuthzenEntity(TypedDict, total=False):
    """An AuthZEN subject or resource: a type and id with optional attributes."""

    type: str
    id: str
    properties: dict[str, Any]


class AuthzenAction(TypedDict, total=False):
    name: str
    properties: dict[str, Any]


class EvaluationRequest(TypedDict, total=False):
    """One request inside ``decisions.evaluate_many``; each field replaces the call's default."""

    subject: AuthzenEntity
    resource: AuthzenEntity
    action: AuthzenAction
    context: dict[str, Any]


class Evaluation(TypedDict):
    """An AuthZEN decision. ``context`` always carries ``decided_by``."""

    decision: bool
    context: NotRequired[dict[str, Any]]


class EvaluationsOptions(TypedDict, total=False):
    evaluations_semantic: Literal["execute_all", "deny_on_first_deny", "permit_on_first_permit"]


class Evaluations(TypedDict):
    evaluations: list[Evaluation]


DecisionSource = Literal["check", "relation_check", "authzen", "abac_evaluate", "abac_draft"]


class DecisionLogEntry(TypedDict):
    """One recorded access decision."""

    id: str
    decided_at: str
    source: DecisionSource | str
    caller_type: NotRequired[str]
    caller_id: NotRequired[str]
    caller_client: NotRequired[str]
    subject: str
    resource: str
    action: str
    allowed: bool
    model: str
    rule: NotRequired[str]
    reason_code: NotRequired[str]


# ---------------------------------------------------------------------------
# Sign-in policy


class LockoutSettings(TypedDict, total=False):
    threshold: int
    window_minutes: int
    duration_minutes: int


class LockoutLimits(TypedDict, total=False):
    defaults: LockoutSettings
    min: LockoutSettings
    max: LockoutSettings


class AuthPolicyUpdateParams(TypedDict, total=False):
    """How people may sign in. ``auth_policies.update`` replaces the policy: send it back whole."""

    password_enabled: bool
    password_min_length: int
    """8 to 128; clamped."""
    password_require_uppercase: bool
    password_require_number: bool
    password_require_symbol: bool
    magic_link_enabled: bool
    magic_link_ttl_minutes: int
    """5 to 1440; clamped."""
    passkey_enabled: bool
    otp_email_enabled: bool
    otp_sms_enabled: bool
    self_registration_enabled: bool
    remember_device_enabled: bool
    remember_device_days: int
    lockout_threshold: int | None
    """``None``: the platform default."""
    lockout_window_minutes: int | None
    lockout_duration_minutes: int | None


class AuthPolicy(AuthPolicyUpdateParams, total=False):
    """How people may sign in to the organisation."""

    lockout_limits: LockoutLimits
    """Read-only: the platform defaults and bounds of the lockout settings."""


class AuthPolicyUsageMethod(TypedDict):
    people: int
    only: int


class AuthPolicyUsageSocial(TypedDict):
    provider: str
    linked: int
    only: int


class AuthPolicyUsage(TypedDict):
    """How many live accounts sign in each way, and how many have no other way in."""

    people: int
    password: AuthPolicyUsageMethod
    passkey: AuthPolicyUsageMethod
    social: list[AuthPolicyUsageSocial]
    magic_link_enabled: bool


# ---------------------------------------------------------------------------
# Security policy


class SecurityPolicyUpdateParams(TypedDict, total=False):
    """Session bounds, MFA enforcement and step-up rules. Durations are Go-style strings such as ``"720h"``."""

    password_min_length: int
    password_complexity: str
    session_max_age: str
    session_idle_timeout: str
    max_sessions: int | None
    """``None``: no limit."""
    session_limit_action: Literal["evict_oldest", "refuse"]
    mfa_enforcement: Literal["optional", "required", "admin_only"]
    mfa_grace_days: int
    mfa_enforced_since: str | None
    step_up_window: str
    step_up_methods: list[Literal["totp", "recovery_code", "otp", "webauthn", "push"]]
    settings: dict[str, Any]


class SecurityPolicy(SecurityPolicyUpdateParams, total=False):
    """The organisation's security policy, or the platform defaults when none is saved."""

    tenant_id: str


# ---------------------------------------------------------------------------
# Address rules

IPRuleReasonCode = Literal[
    "ip.allowed", "ip.deny_rule", "ip.not_in_allow_rules", "ip.address_unknown", "ip.enforcement_disabled"
]


class IPRule(TypedDict):
    """An allow or deny rule for an address range. Deny wins over allow."""

    id: str
    tenant_id: str
    action: Literal["allow", "deny"] | str
    cidr: str
    label: str
    created_at: str


class IPRuleList(TypedDict):
    """The organisation's address rules, and whether they are enforced."""

    enabled: bool
    data: list[IPRule]


class IPRuleDecision(TypedDict):
    allowed: bool
    reason: str
    reason_code: IPRuleReasonCode | str
    reason_params: NotRequired[dict[str, Any]]


class IPRuleCheck(IPRuleDecision):
    """What the rules make of an address: the decision a sign-in gets."""

    enabled: bool
    rules: NotRequired[IPRuleDecision]
    """What the rules alone decide, whether or not they are enforced."""


class IPRuleEnforcement(TypedDict):
    enabled: bool


# ---------------------------------------------------------------------------
# Threat detection


class BotEvent(TypedDict):
    """One bot-detection verdict on a sign-in attempt."""

    id: str
    ip: NotRequired[str]
    user_agent: str
    score: float
    verdict: Literal["allowed", "challenged", "blocked"] | str
    outcome: Literal["signed_in", "failed", "unknown"] | str
    user_id: NotRequired[str]
    user_email: NotRequired[str]
    created_at: str


class BotActivityStats(TypedDict):
    blocked_24h: int
    challenged_24h: int
    threshold: float


class BotActivity(TypedDict):
    """Recent bot-detection verdicts, a page at a time, with totals."""

    recent: list[BotEvent]
    next_cursor: NotRequired[str]
    total: int
    stats: BotActivityStats


class BotSettings(TypedDict):
    """Bot-detection settings. Replaced whole on update."""

    ua_check: bool
    honeypot: bool
    captcha: bool
    signature: bool
    score_threshold: float


class RiskSettingsUpdateParams(TypedDict, total=False):
    """Adaptive-MFA risk settings. Replaced whole on update."""

    medium_threshold: Required[int]
    high_threshold: Required[int]
    force_mfa_at_level: Required[Literal["medium", "high"]]
    """The risk level at which a second factor is required even on a trusted device."""
    impossible_travel_enabled: Required[bool]
    """Flags a sign-in from a new country sooner than ``min_travel_hours`` after the last one."""
    min_travel_hours: Required[int]
    device_reputation_enabled: Required[bool]
    """Flags a sign-in from a browser and OS never seen for the user."""


class RiskSettings(RiskSettingsUpdateParams, total=False):
    country_header_configured: bool
    """Read-only: whether the deployment receives a country header."""
    country_last_seen_at: str | None


class Anomaly(TypedDict):
    """A detected sign-in anomaly."""

    id: str
    type: str
    severity: str
    detail: str
    status: Literal["open", "resolved"] | str
    user_id: NotRequired[str]
    user_email: NotRequired[str]
    ip: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]
    created_at: str
    resolved_at: NotRequired[str]
    resolved_by: NotRequired[str]
    resolved_by_email: NotRequired[str]


class AnomalySummary(TypedDict):
    open: int
    resolved_24h: int
    affected_accounts: int
    high_severity_24h: int
