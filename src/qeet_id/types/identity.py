"""Identity: the organisation (tenant), its domains, users, groups, invitations and branding.

Field names are the API's own (ADR-0004). Response fields the API may extend are
typed ``Literal[...] | str``.
"""

from typing import Any, Literal, NotRequired, Required, TypedDict

__all__ = [
    "AssignedRole",
    "BrandingSettings",
    "BrandingUpdateParams",
    "BulkImportCreatedRow",
    "BulkImportResult",
    "BulkImportRowError",
    "BulkImportSource",
    "BulkUserRow",
    "DeletedUser",
    "Domain",
    "DomainUpdateParams",
    "Group",
    "GroupCreateParams",
    "GroupMember",
    "GroupRole",
    "GroupRoleRef",
    "GroupUpdateParams",
    "Invitation",
    "InvitationCreateParams",
    "InvitationDelivery",
    "InvitationResult",
    "LinkedIdentity",
    "MembershipRemoval",
    "MfaRequirement",
    "Tenant",
    "TenantBranding",
    "TenantDeletion",
    "TenantUpdateParams",
    "User",
    "UserAccess",
    "UserAccessEntry",
    "UserAccessOrganization",
    "UserBulkCreateParams",
    "UserCreateParams",
    "UserDeletion",
    "UserListParams",
    "UserSecurity",
    "UserSession",
    "UserSessionsRevocation",
    "UserStatus",
    "UserSuspension",
    "UserUpdateParams",
]

# ---------------------------------------------------------------------------
# Tenants


class Tenant(TypedDict):
    """An organisation (a tenant). Every API key belongs to one."""

    id: str
    slug: str
    name: str
    status: Literal["active", "suspended"] | str
    plan: Literal["free", "pro", "enterprise"] | str
    region: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    deletion_due_at: NotRequired[str | None]
    """When a scheduled deletion takes effect; ``None`` when none is scheduled."""
    member_count: NotRequired[int]
    mfa_enabled_count: NotRequired[int]


class TenantUpdateParams(TypedDict, total=False):
    """The fields an update may change. Changing ``status`` is an owner's; the region can't change."""

    name: str
    status: Literal["active", "suspended"]
    plan: Literal["free", "pro", "enterprise"]
    metadata: dict[str, Any]


class TenantDeletion(TypedDict):
    """A scheduled deletion."""

    tenant_id: str
    deletion_due_at: str


# ---------------------------------------------------------------------------
# Domains


class Domain(TypedDict):
    """A domain the organisation claimed, with the DNS record that proves it."""

    id: str
    domain: str
    status: str
    """The verification state, such as ``pending`` or ``verified``."""
    verification_token: str
    dns_record_name: str
    """Publish this TXT record, then call ``verify``."""
    dns_record_type: str
    dns_record_value: str
    verified_at: NotRequired[str]
    last_checked_at: NotRequired[str]
    last_error: NotRequired[str]
    sso_enabled: bool
    """People on the domain sign in only through the organisation's SSO connection."""
    jit_enabled: bool
    """Accounts are created on first SSO sign-in (just-in-time provisioning)."""
    created_at: str


class DomainUpdateParams(TypedDict, total=False):
    sso_enabled: bool
    jit_enabled: bool


# ---------------------------------------------------------------------------
# Users

UserStatus = Literal["active", "invited", "suspended"]
"""A user's state. ``invited`` users haven't accepted their invitation yet."""


class UserSuspension(TypedDict):
    """Why, by whom and when an organisation's own user was suspended."""

    reason: str
    source: str
    suspended_at: str | None
    suspended_by: str | None
    suspended_by_email: str | None


class AssignedRole(TypedDict):
    id: str
    name: str


class User(TypedDict):
    """A user, as the API returns one."""

    id: str
    tenant_id: str
    """The user's home organisation."""
    email: str
    email_verified_at: str | None
    phone: str | None
    phone_verified_at: str | None
    display_name: str | None
    avatar_url: str | None
    status: UserStatus | str
    metadata: dict[str, Any]
    """Free-form data. Empty when the user's home is another organisation, which keeps it."""
    created_at: str
    updated_at: str
    roles: NotRequired[list[str]]
    """Role names in the organisation reading the user; on lists and a member's own record."""
    assigned_roles: NotRequired[list[AssignedRole]]
    mfa_enabled: NotRequired[bool]
    groups_count: NotRequired[int]
    last_seen_at: NotRequired[str | None]
    last_seen_ip: NotRequired[str | None]
    home_tenant_name: NotRequired[str | None]
    """The name of the organisation that manages the account."""
    suspension: NotRequired[UserSuspension]


class UserCreateParams(TypedDict, total=False):
    tenant_id: Required[str]
    """The organisation; must be the API key's own."""
    email: Required[str]
    password: str
    """An initial password. It must meet the organisation's password rules."""
    display_name: str
    phone: str
    """E.164, such as ``+919876543210``."""
    metadata: dict[str, Any]


class UserUpdateParams(TypedDict, total=False):
    """The fields an update may change. Changing the email address is the user's own email-change flow."""

    display_name: str | None
    avatar_url: str
    """A small ``data:image/…`` URL; an empty string clears it."""
    phone: str | None
    status: Literal["active", "suspended"]
    metadata: dict[str, Any]


class UserListParams(TypedDict, total=False):
    """Filters for ``users.list``. They combine."""

    limit: int
    cursor: str
    q: str
    """Matches the display name, email or phone, case-insensitively."""
    role: str
    """A role name in the organisation."""
    department: str
    """Matches ``metadata.department``."""
    mfa: bool
    """Whether the user has a confirmed second factor."""
    email_verified: bool
    status: UserStatus
    last_seen: Literal["today", "week", "month", "older", "never"]


class DeletedUser(TypedDict):
    """A soft-deleted user, as the recycle bin shows it."""

    id: str
    email: str
    display_name: str | None
    deleted_at: str
    deleted_by: str | None
    created_at: str


class UserDeletion(TypedDict):
    """Who was deleted, when and by whom."""

    id: str
    deleted_at: str
    deleted_by: str | None


class BulkUserRow(TypedDict, total=False):
    email: Required[str]
    password: str
    display_name: str
    phone: str


class UserBulkCreateParams(TypedDict, total=False):
    tenant_id: str
    """Optional; when present it must be the API key's own organisation."""
    role_id: str
    """A role every created user receives."""
    users: Required[list[BulkUserRow]]
    """1 to 1000 rows."""


class BulkImportRowError(TypedDict):
    """One row of a bulk create or import that failed."""

    line: NotRequired[int]
    """1-based: the row of ``users``, or the line of the uploaded file."""
    email: NotRequired[str]
    code: str
    """Why, as a stable code such as ``auth.email_exists`` or ``user.import_field_invalid``."""
    field: NotRequired[Literal["email", "password", "display_name", "phone"]]
    message: str


class BulkImportCreatedRow(TypedDict):
    line: int
    email: str
    id: str


class BulkImportResult(TypedDict):
    """The per-row outcome of a bulk create or import."""

    succeeded: int
    failed: int
    created: list[BulkImportCreatedRow]
    errors: NotRequired[list[BulkImportRowError]]


BulkImportSource = Literal["auth0", "cognito", "azure_b2c"]
"""The identity provider a bulk import file comes from: NDJSON, CSV, or Microsoft Graph JSON."""


class UserSession(TypedDict):
    """One of a user's live sessions."""

    id: str
    ip: str | None
    user_agent: str | None
    created_at: str
    last_seen_at: str
    device: NotRequired[str]
    device_kind: NotRequired[Literal["desktop", "mobile", "tablet", "unknown"]]
    country: NotRequired[str]
    city: NotRequired[str]


class UserSessionsRevocation(TypedDict):
    """What signing a user out everywhere ended."""

    revoked: int
    sessions: int
    hosted_login_sessions: int
    app_grants: int
    trusted_devices: int
    pending_authorizations: int


class UserSecurity(TypedDict):
    """A user's authentication posture."""

    mfa_required: bool
    mfa_enabled: bool
    totp_enabled: bool
    otp_factors: int
    push_devices: int
    passkeys: int
    passkey_last_used_at: str | None
    recovery_codes_remaining: int
    password_set: bool
    password_changed_at: str | None
    active_sessions: int
    distinct_devices: int


class UserAccessOrganization(TypedDict):
    id: str
    name: str
    slug: str


class UserAccessEntry(TypedDict):
    id: str
    name: str
    description: NotRequired[str]


class UserAccess(TypedDict):
    """A user's access in the organisation: roles, groups and permission counts."""

    organization: UserAccessOrganization
    roles: list[UserAccessEntry]
    groups: list[UserAccessEntry]
    applications_count: int
    policies_count: int
    permissions_direct: int
    permissions_inherited: int
    permissions_total: int


class MfaRequirement(TypedDict):
    mfa_required: bool


class MembershipRemoval(TypedDict):
    """What removing a member who belongs to another organisation took away here."""

    id: str
    roles_removed: int
    sessions_ended: int


class LinkedIdentity(TypedDict):
    """A social account linked to a user."""

    id: str
    user_id: str
    tenant_id: str
    provider: str
    subject: str
    email: str | None
    linked_at: str


# ---------------------------------------------------------------------------
# Groups


class GroupRoleRef(TypedDict):
    role_id: str
    name: str


class Group(TypedDict):
    """A group of users, optionally nested under a parent. Members inherit the group's roles."""

    id: str
    tenant_id: str
    parent_id: str | None
    name: str
    description: str
    member_count: int
    created_at: str
    roles: NotRequired[list[GroupRoleRef]]
    """The roles granted to the group; listed only for a caller holding ``role.read``."""


class GroupCreateParams(TypedDict, total=False):
    """The organisation is the credential's own: the API takes it from there, not from the body."""

    name: Required[str]
    description: str
    parent_id: str | None
    """One of the organisation's groups; omit or ``None`` for a top-level group."""


class GroupUpdateParams(TypedDict, total=False):
    """Changes only the fields given; ``parent_id=None`` makes the group top-level."""

    name: str
    description: str
    parent_id: str | None


class GroupMember(TypedDict):
    user_id: str
    email: str
    display_name: str | None


class GroupRole(TypedDict):
    """A role granted to a group."""

    role_id: str
    name: str
    granted_at: str


# ---------------------------------------------------------------------------
# Invitations


class InvitationDelivery(TypedDict):
    """Whether an invitation's email went out."""

    status: Literal["sent", "not_sent"] | str
    code: NotRequired[str]
    """For ``not_sent``: ``email.suppressed`` or ``email.provider_unavailable``, for example."""
    message: NotRequired[str]


class Invitation(TypedDict):
    """An invitation to join the organisation. Its token is never returned: the link goes only to the invitee."""

    id: str
    tenant_id: str
    email: str
    role_id: str | None
    """The role the invitee receives on accepting."""
    status: str
    expires_at: str
    accepted_at: str | None
    created_at: str
    delivery: NotRequired[InvitationDelivery]
    """Present on ``create`` and ``resend``."""


class InvitationCreateParams(TypedDict, total=False):
    tenant_id: Required[str]
    email: Required[str]
    role_id: str | None


class InvitationResult(TypedDict):
    """What ``invitations.create`` and ``invitations.resend`` answer."""

    invite: Invitation


# ---------------------------------------------------------------------------
# Branding


class BrandingSettings(TypedDict, total=False):
    """``background_color`` (six-digit hex) and ``email_reply_to``; keep unknown keys when writing back."""

    background_color: str
    email_reply_to: str


class TenantBranding(TypedDict):
    """How the hosted sign-in pages and emails look for the organisation."""

    tenant_id: str
    logo_url: str | None
    """A URL or a base64 ``data:`` image (PNG, JPEG, WEBP or SVG, at most 2 MiB)."""
    primary_color: str | None
    secondary_color: str | None
    custom_domain: str | None
    email_from_name: str | None
    email_from_address: str | None
    settings: BrandingSettings


class BrandingUpdateParams(TypedDict, total=False):
    logo_url: str | None
    primary_color: str | None
    secondary_color: str | None
    custom_domain: str | None
    email_from_name: str | None
    email_from_address: str | None
    settings: BrandingSettings
