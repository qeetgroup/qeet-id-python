# Generated from qeet_id/_async/resources/identity.py by scripts/unasync.py. Edit that file, not this one.
"""Identity: the organisation, its domains, people, groups, invitations and branding (management.yaml)."""

from typing import Literal, Unpack

from qeet_id._options import RequestOptions
from qeet_id._pagination import ListResult, Page
from qeet_id._request import path
from qeet_id._sync._resource import APIResource
from qeet_id.types.identity import (
    BrandingUpdateParams,
    BulkImportResult,
    BulkImportSource,
    DeletedUser,
    Domain,
    DomainUpdateParams,
    Group,
    GroupCreateParams,
    GroupMember,
    GroupRole,
    GroupUpdateParams,
    Invitation,
    InvitationCreateParams,
    InvitationResult,
    LinkedIdentity,
    MembershipRemoval,
    MfaRequirement,
    Tenant,
    TenantBranding,
    TenantDeletion,
    TenantUpdateParams,
    User,
    UserAccess,
    UserBulkCreateParams,
    UserCreateParams,
    UserDeletion,
    UserListParams,
    UserSecurity,
    UserSession,
    UserSessionsRevocation,
    UserUpdateParams,
)

__all__ = ["Branding", "Domains", "Groups", "Invitations", "Tenants", "Users"]

_IMPORT_CONTENT_TYPES: dict[BulkImportSource, str] = {
    "auth0": "application/x-ndjson",
    "cognito": "text/csv",
    "azure_b2c": "application/json",
}


class Tenants(APIResource):
    """The API key's organisation. Listing and creating organisations are a signed-in person's actions."""

    def get(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> Tenant:
        return self._request("GET", path("/v1/tenants/{}", tenant_id), request_options=request_options)

    def update(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None, **params: Unpack[TenantUpdateParams]
    ) -> Tenant:
        """Change only the fields given."""
        return self._request("PATCH", path("/v1/tenants/{}", tenant_id), json=params, request_options=request_options)

    def delete(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> TenantDeletion:
        """Schedule the organisation's deletion seven days from now. An owner may call it off."""
        return self._request("DELETE", path("/v1/tenants/{}", tenant_id), request_options=request_options)

    def cancel_deletion(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> Tenant:
        """Call off a scheduled deletion."""
        return self._request("POST", path("/v1/tenants/{}/deletion/cancel", tenant_id), request_options=request_options)


class Domains(APIResource):
    """The organisation's domains: claim, verify by DNS, and route sign-in."""

    def create(self, tenant_id: str, /, domain: str, *, request_options: RequestOptions | None = None) -> Domain:
        """Claim a domain and return the TXT record to publish."""
        return self._request(
            "POST", path("/v1/tenants/{}/domains", tenant_id), json={"domain": domain}, request_options=request_options
        )

    def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[Domain]:
        return self._list(path("/v1/tenants/{}/domains", tenant_id), request_options=request_options)

    def verify(self, tenant_id: str, domain_id: str, /, *, request_options: RequestOptions | None = None) -> Domain:
        """Look the TXT record up now and, on a match, mark the domain verified."""
        return self._request(
            "POST", path("/v1/tenants/{}/domains/{}/verify", tenant_id, domain_id), request_options=request_options
        )

    def update(
        self,
        tenant_id: str,
        domain_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[DomainUpdateParams],
    ) -> Domain:
        """Turn SSO routing and just-in-time provisioning on or off."""
        return self._request(
            "PATCH",
            path("/v1/tenants/{}/domains/{}", tenant_id, domain_id),
            json=params,
            request_options=request_options,
        )

    def delete(self, tenant_id: str, domain_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        self._request(
            "DELETE", path("/v1/tenants/{}/domains/{}", tenant_id, domain_id), request_options=request_options
        )


class Users(APIResource):
    """The organisation's people."""

    def create(
        self,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
        **params: Unpack[UserCreateParams],
    ) -> User:
        """Create a user in the API key's organisation. Idempotent: safe to retry."""
        return self._request(
            "POST",
            "/v1/users",
            json=params,
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    def get(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> User:
        return self._request("GET", path("/v1/users/{}", user_id), request_options=request_options)

    def update(
        self, user_id: str, /, *, request_options: RequestOptions | None = None, **params: Unpack[UserUpdateParams]
    ) -> User:
        """Change only the fields given."""
        return self._request("PATCH", path("/v1/users/{}", user_id), json=params, request_options=request_options)

    def list(self, *, request_options: RequestOptions | None = None, **params: Unpack[UserListParams]) -> Page[User]:
        """List the organisation's users, newest first.

        Iterate the result for every user across every page, or take one page::

            for user in client.users.list(status="active"):
                ...
        """
        return self._paginate("/v1/users", params, request_options=request_options)

    def suspend(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> User:
        """Suspend the user: they can't sign in, and every session of theirs ends."""
        return self.update(user_id, status="suspended", request_options=request_options)

    def reactivate(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> User:
        """Reactivate a suspended user. Their ended sessions don't come back."""
        return self._request("POST", path("/v1/users/{}/reactivate", user_id), request_options=request_options)

    def delete(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> UserDeletion:
        """Soft-delete the user into the recycle bin and end every way they are signed in. Undo with ``restore``."""
        return self._request("DELETE", path("/v1/users/{}", user_id), request_options=request_options)

    def list_deleted(
        self, *, limit: int | None = None, request_options: RequestOptions | None = None
    ) -> ListResult[DeletedUser]:
        """List the recycle bin."""
        return self._list("/v1/users/deleted", {"limit": limit}, request_options=request_options)

    def restore(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> User:
        """Bring a soft-deleted user back."""
        return self._request("POST", path("/v1/users/{}/restore", user_id), request_options=request_options)

    def purge(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Permanently delete a soft-deleted user. Irreversible."""
        self._request("DELETE", path("/v1/users/{}/purge", user_id), request_options=request_options)

    def set_password(self, user_id: str, /, password: str, *, request_options: RequestOptions | None = None) -> None:
        """Set or replace the user's password, ending every way they are signed in."""
        self._request(
            "POST", path("/v1/users/{}/password", user_id), json={"password": password}, request_options=request_options
        )

    def reset_mfa(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Clear every second factor of a locked-out user (account recovery)."""
        self._request("DELETE", path("/v1/users/{}/mfa", user_id), request_options=request_options)

    def set_mfa_required(
        self, user_id: str, /, required: bool, *, request_options: RequestOptions | None = None
    ) -> MfaRequirement:
        """Require (or stop requiring) a second factor of this user."""
        return self._request(
            "PUT",
            path("/v1/users/{}/mfa-required", user_id),
            json={"required": required},
            request_options=request_options,
        )

    def bulk_create(
        self, *, request_options: RequestOptions | None = None, **params: Unpack[UserBulkCreateParams]
    ) -> BulkImportResult:
        """Create up to 1000 users in one call; each row succeeds or fails on its own."""
        return self._request("POST", "/v1/users/bulk", json=params, request_options=request_options)

    def bulk_import(
        self, source: BulkImportSource, file: bytes | str, *, request_options: RequestOptions | None = None
    ) -> BulkImportResult:
        """Import another identity provider's user export as it is.

        NDJSON for Auth0, CSV for Cognito, Microsoft Graph JSON for Azure AD B2C.
        Imported users have no password.
        """
        if source not in _IMPORT_CONTENT_TYPES:
            raise ValueError(f"source must be one of {', '.join(_IMPORT_CONTENT_TYPES)}.")
        return self._request(
            "POST",
            "/v1/users/bulk/import",
            query={"source": source},
            content=file.encode() if isinstance(file, str) else bytes(file),
            content_type=_IMPORT_CONTENT_TYPES[source],
            request_options=request_options,
        )

    def list_sessions(
        self, user_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[UserSession]:
        """List the user's live sessions in the organisation, most recently seen first."""
        return self._list(path("/v1/users/{}/sessions", user_id), request_options=request_options)

    def revoke_session(
        self, tenant_id: str, user_id: str, session_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """End one of the user's sessions."""
        self._request(
            "DELETE",
            path("/v1/tenants/{}/users/{}/sessions/{}", tenant_id, user_id, session_id),
            request_options=request_options,
        )

    def revoke_all_sessions(
        self, user_id: str, /, *, request_options: RequestOptions | None = None
    ) -> UserSessionsRevocation:
        """Sign the user out everywhere: sessions, hosted sign-in sessions and application refresh grants."""
        return self._request("POST", path("/v1/users/{}/sessions/revoke-all", user_id), request_options=request_options)

    def get_security(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> UserSecurity:
        """The user's authentication posture: factors, passkeys, password and sessions."""
        return self._request("GET", path("/v1/users/{}/security", user_id), request_options=request_options)

    def get_access(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> UserAccess:
        """The user's roles, groups and permission counts in the organisation."""
        return self._request("GET", path("/v1/users/{}/access", user_id), request_options=request_options)

    def remove_membership(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> MembershipRemoval:
        """Remove a member whose account belongs to another organisation from this one."""
        return self._request("DELETE", path("/v1/users/{}/membership", user_id), request_options=request_options)

    def list_linked_identities(
        self, user_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[LinkedIdentity]:
        """List the social accounts linked to the user."""
        return self._list(path("/v1/users/{}/social/identities", user_id), request_options=request_options)


class Groups(APIResource):
    """Groups, their members and the roles they grant."""

    def create(
        self,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
        **params: Unpack[GroupCreateParams],
    ) -> Group:
        """Create a group. Idempotent: safe to retry."""
        return self._request(
            "POST",
            "/v1/groups",
            json=params,
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    def update(
        self, group_id: str, /, *, request_options: RequestOptions | None = None, **params: Unpack[GroupUpdateParams]
    ) -> Group:
        return self._request("PATCH", path("/v1/groups/{}", group_id), json=params, request_options=request_options)

    def delete(self, group_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Delete the group and its subgroups. Members keep their accounts."""
        self._request("DELETE", path("/v1/groups/{}", group_id), request_options=request_options)

    def list(
        self,
        tenant_id: str,
        /,
        *,
        role: str | None = None,
        grants: Literal["some", "none"] | None = None,
        request_options: RequestOptions | None = None,
    ) -> ListResult[Group]:
        """List the organisation's groups.

        Args:
            tenant_id: The organisation.
            role: Only groups granted this role (needs ``role.read``).
            grants: ``some``: groups granted at least one role; ``none``: groups granted none.
            request_options: Settings for this call.
        """
        return self._list(
            path("/v1/tenants/{}/groups", tenant_id), {"role": role, "grants": grants}, request_options=request_options
        )

    def list_members(
        self, group_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[GroupMember]:
        return self._list(path("/v1/groups/{}/members", group_id), request_options=request_options)

    def add_member(self, group_id: str, user_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Add a user to the group, giving them its roles. Adding a member twice changes nothing."""
        self._request("POST", path("/v1/groups/{}/members/{}", group_id, user_id), request_options=request_options)

    def remove_member(self, group_id: str, user_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        self._request("DELETE", path("/v1/groups/{}/members/{}", group_id, user_id), request_options=request_options)

    def list_roles(
        self, tenant_id: str, group_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[GroupRole]:
        """List the roles granted to the group."""
        return self._list(path("/v1/tenants/{}/groups/{}/roles", tenant_id, group_id), request_options=request_options)

    def grant_role(
        self, tenant_id: str, group_id: str, role_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """Grant a role to the group; every member inherits it."""
        self._request(
            "POST",
            path("/v1/tenants/{}/groups/{}/roles/{}", tenant_id, group_id, role_id),
            request_options=request_options,
        )

    def revoke_role(
        self, tenant_id: str, group_id: str, role_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        self._request(
            "DELETE",
            path("/v1/tenants/{}/groups/{}/roles/{}", tenant_id, group_id, role_id),
            request_options=request_options,
        )


class Invitations(APIResource):
    """Invitations to join the organisation. Accepting one is the invitee's own action."""

    def create(
        self,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
        **params: Unpack[InvitationCreateParams],
    ) -> InvitationResult:
        """Create an invitation and email its link to the invited address. Idempotent: safe to retry."""
        return self._request(
            "POST",
            "/v1/invites",
            json=params,
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[Invitation]:
        return self._list(path("/v1/tenants/{}/invites", tenant_id), request_options=request_options)

    def resend(self, invitation_id: str, /, *, request_options: RequestOptions | None = None) -> InvitationResult:
        """Issue a new link, extend the expiry and email the invitation again."""
        return self._request("POST", path("/v1/invites/{}/resend", invitation_id), request_options=request_options)

    def delete(self, invitation_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Withdraw a pending invitation; its link stops working."""
        self._request("DELETE", path("/v1/invites/{}", invitation_id), request_options=request_options)


class Branding(APIResource):
    """The organisation's branding. Shown only while the plan includes custom branding."""

    def get(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> TenantBranding:
        return self._request("GET", path("/v1/tenants/{}/branding", tenant_id), request_options=request_options)

    def update(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[BrandingUpdateParams],
    ) -> TenantBranding:
        """Replace the branding."""
        return self._request(
            "PUT", path("/v1/tenants/{}/branding", tenant_id), json=params, request_options=request_options
        )
