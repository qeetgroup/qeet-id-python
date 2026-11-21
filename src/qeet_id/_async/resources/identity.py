"""Identity: the organization, its domains, people, groups, invitations and branding (identity.yaml)."""

from typing import Literal, Unpack

from qeet_id._async._resource import AsyncAPIResource
from qeet_id._options import RequestOptions
from qeet_id._pagination import AsyncPaginator, ListResult
from qeet_id._request import path
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
    Organization,
    OrganizationBranding,
    OrganizationDeletion,
    OrganizationUpdateParams,
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

__all__ = ["AsyncBranding", "AsyncDomains", "AsyncGroups", "AsyncInvitations", "AsyncOrganizations", "AsyncUsers"]

_IMPORT_CONTENT_TYPES: dict[BulkImportSource, str] = {
    "auth0": "application/x-ndjson",
    "cognito": "text/csv",
    "azure_b2c": "application/json",
}


class AsyncOrganizations(AsyncAPIResource):
    """The API key's organization. Listing and creating organizations are a signed-in person's actions."""

    async def get(self, organization_id: str, /, *, request_options: RequestOptions | None = None) -> Organization:
        return await self._request(
            "GET", path("/v1/organizations/{}", organization_id), request_options=request_options
        )

    async def update(
        self,
        organization_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[OrganizationUpdateParams],
    ) -> Organization:
        """Change only the fields given."""
        return await self._request(
            "PATCH", path("/v1/organizations/{}", organization_id), json=params, request_options=request_options
        )

    async def delete(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> OrganizationDeletion:
        """Schedule the organization's deletion seven days from now. An owner may call it off."""
        return await self._request(
            "DELETE", path("/v1/organizations/{}", organization_id), request_options=request_options
        )

    async def cancel_deletion(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> Organization:
        """Call off a scheduled deletion."""
        return await self._request(
            "POST", path("/v1/organizations/{}/deletion/cancel", organization_id), request_options=request_options
        )


class AsyncDomains(AsyncAPIResource):
    """The organization's domains: claim, verify by DNS, and route sign-in."""

    async def create(
        self, organization_id: str, /, domain: str, *, request_options: RequestOptions | None = None
    ) -> Domain:
        """Claim a domain and return the TXT record to publish."""
        return await self._request(
            "POST",
            path("/v1/organizations/{}/domains", organization_id),
            json={"domain": domain},
            request_options=request_options,
        )

    async def list(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[Domain]:
        return await self._list(path("/v1/organizations/{}/domains", organization_id), request_options=request_options)

    async def verify(
        self, organization_id: str, domain_id: str, /, *, request_options: RequestOptions | None = None
    ) -> Domain:
        """Look the TXT record up now and, on a match, mark the domain verified."""
        return await self._request(
            "POST",
            path("/v1/organizations/{}/domains/{}/verify", organization_id, domain_id),
            request_options=request_options,
        )

    async def update(
        self,
        organization_id: str,
        domain_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[DomainUpdateParams],
    ) -> Domain:
        """Turn SSO routing and just-in-time provisioning on or off."""
        return await self._request(
            "PATCH",
            path("/v1/organizations/{}/domains/{}", organization_id, domain_id),
            json=params,
            request_options=request_options,
        )

    async def delete(
        self, organization_id: str, domain_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/domains/{}", organization_id, domain_id),
            request_options=request_options,
        )


class AsyncUsers(AsyncAPIResource):
    """The organization's people."""

    async def create(
        self,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
        **params: Unpack[UserCreateParams],
    ) -> User:
        """Create a user in the API key's organization. Idempotent: safe to retry."""
        return await self._request(
            "POST",
            "/v1/users",
            json=params,
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    async def get(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> User:
        return await self._request("GET", path("/v1/users/{}", user_id), request_options=request_options)

    async def update(
        self, user_id: str, /, *, request_options: RequestOptions | None = None, **params: Unpack[UserUpdateParams]
    ) -> User:
        """Change only the fields given."""
        return await self._request("PATCH", path("/v1/users/{}", user_id), json=params, request_options=request_options)

    def list(
        self, *, request_options: RequestOptions | None = None, **params: Unpack[UserListParams]
    ) -> AsyncPaginator[User]:
        """List the organization's users, newest first.

        Iterate the result for every user across every page, or take one page::

            async for user in client.users.list(status="active"):
                ...
        """
        return self._paginate("/v1/users", params, request_options=request_options)

    async def suspend(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> User:
        """Suspend the user: they can't sign in, and every session of theirs ends."""
        return await self.update(user_id, status="suspended", request_options=request_options)

    async def reactivate(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> User:
        """Reactivate a suspended user. Their ended sessions don't come back."""
        return await self._request("POST", path("/v1/users/{}/reactivate", user_id), request_options=request_options)

    async def delete(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> UserDeletion:
        """Soft-delete the user into the recycle bin and end every way they are signed in. Undo with ``restore``."""
        return await self._request("DELETE", path("/v1/users/{}", user_id), request_options=request_options)

    async def list_deleted(
        self, *, limit: int | None = None, request_options: RequestOptions | None = None
    ) -> ListResult[DeletedUser]:
        """List the recycle bin."""
        return await self._list("/v1/users/deleted", {"limit": limit}, request_options=request_options)

    async def restore(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> User:
        """Bring a soft-deleted user back."""
        return await self._request("POST", path("/v1/users/{}/restore", user_id), request_options=request_options)

    async def purge(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Permanently delete a soft-deleted user. Irreversible."""
        await self._request("DELETE", path("/v1/users/{}/purge", user_id), request_options=request_options)

    async def set_password(
        self, user_id: str, /, password: str, *, request_options: RequestOptions | None = None
    ) -> None:
        """Set or replace the user's password, ending every way they are signed in."""
        await self._request(
            "POST", path("/v1/users/{}/password", user_id), json={"password": password}, request_options=request_options
        )

    async def reset_mfa(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Clear every second factor of a locked-out user (account recovery)."""
        await self._request("DELETE", path("/v1/users/{}/mfa", user_id), request_options=request_options)

    async def set_mfa_required(
        self, user_id: str, /, required: bool, *, request_options: RequestOptions | None = None
    ) -> MfaRequirement:
        """Require (or stop requiring) a second factor of this user."""
        return await self._request(
            "PUT",
            path("/v1/users/{}/mfa-required", user_id),
            json={"required": required},
            request_options=request_options,
        )

    async def bulk_create(
        self, *, request_options: RequestOptions | None = None, **params: Unpack[UserBulkCreateParams]
    ) -> BulkImportResult:
        """Create up to 1000 users in one call; each row succeeds or fails on its own."""
        return await self._request("POST", "/v1/users/bulk", json=params, request_options=request_options)

    async def bulk_import(
        self, source: BulkImportSource, file: bytes | str, *, request_options: RequestOptions | None = None
    ) -> BulkImportResult:
        """Import another identity provider's user export as it is.

        NDJSON for Auth0, CSV for Cognito, Microsoft Graph JSON for Azure AD B2C.
        Imported users have no password.
        """
        if source not in _IMPORT_CONTENT_TYPES:
            raise ValueError(f"source must be one of {', '.join(_IMPORT_CONTENT_TYPES)}.")
        return await self._request(
            "POST",
            "/v1/users/bulk/import",
            query={"source": source},
            content=file.encode() if isinstance(file, str) else bytes(file),
            content_type=_IMPORT_CONTENT_TYPES[source],
            request_options=request_options,
        )

    async def list_sessions(
        self, user_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[UserSession]:
        """List the user's live sessions in the organization, most recently seen first."""
        return await self._list(path("/v1/users/{}/sessions", user_id), request_options=request_options)

    async def revoke_session(
        self, organization_id: str, user_id: str, session_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """End one of the user's sessions."""
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/users/{}/sessions/{}", organization_id, user_id, session_id),
            request_options=request_options,
        )

    async def revoke_all_sessions(
        self, user_id: str, /, *, request_options: RequestOptions | None = None
    ) -> UserSessionsRevocation:
        """Sign the user out everywhere: sessions, hosted sign-in sessions and application refresh grants."""
        return await self._request(
            "POST", path("/v1/users/{}/sessions/revoke-all", user_id), request_options=request_options
        )

    async def get_security(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> UserSecurity:
        """The user's authentication posture: factors, passkeys, password and sessions."""
        return await self._request("GET", path("/v1/users/{}/security", user_id), request_options=request_options)

    async def get_access(self, user_id: str, /, *, request_options: RequestOptions | None = None) -> UserAccess:
        """The user's roles, groups and permission counts in the organization."""
        return await self._request("GET", path("/v1/users/{}/access", user_id), request_options=request_options)

    async def remove_membership(
        self, user_id: str, /, *, request_options: RequestOptions | None = None
    ) -> MembershipRemoval:
        """Remove a member whose account belongs to another organization from this one."""
        return await self._request("DELETE", path("/v1/users/{}/membership", user_id), request_options=request_options)

    async def list_linked_identities(
        self, user_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[LinkedIdentity]:
        """List the social accounts linked to the user."""
        return await self._list(path("/v1/users/{}/social/identities", user_id), request_options=request_options)


class AsyncGroups(AsyncAPIResource):
    """Groups, their members and the roles they grant."""

    async def create(
        self,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
        **params: Unpack[GroupCreateParams],
    ) -> Group:
        """Create a group. Idempotent: safe to retry."""
        return await self._request(
            "POST",
            "/v1/groups",
            json=params,
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    async def update(
        self, group_id: str, /, *, request_options: RequestOptions | None = None, **params: Unpack[GroupUpdateParams]
    ) -> Group:
        return await self._request(
            "PATCH", path("/v1/groups/{}", group_id), json=params, request_options=request_options
        )

    async def delete(self, group_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Delete the group and its subgroups. Members keep their accounts."""
        await self._request("DELETE", path("/v1/groups/{}", group_id), request_options=request_options)

    async def list(
        self,
        organization_id: str,
        /,
        *,
        role: str | None = None,
        grants: Literal["some", "none"] | None = None,
        request_options: RequestOptions | None = None,
    ) -> ListResult[Group]:
        """List the organization's groups.

        Args:
            organization_id: The organization.
            role: Only groups granted this role (needs ``role.read``).
            grants: ``some``: groups granted at least one role; ``none``: groups granted none.
            request_options: Settings for this call.
        """
        return await self._list(
            path("/v1/organizations/{}/groups", organization_id),
            {"role": role, "grants": grants},
            request_options=request_options,
        )

    async def list_members(
        self, group_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[GroupMember]:
        return await self._list(path("/v1/groups/{}/members", group_id), request_options=request_options)

    async def add_member(
        self, group_id: str, user_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """Add a user to the group, giving them its roles. Adding a member twice changes nothing."""
        await self._request(
            "POST", path("/v1/groups/{}/members/{}", group_id, user_id), request_options=request_options
        )

    async def remove_member(
        self, group_id: str, user_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        await self._request(
            "DELETE", path("/v1/groups/{}/members/{}", group_id, user_id), request_options=request_options
        )

    async def list_roles(
        self, organization_id: str, group_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[GroupRole]:
        """List the roles granted to the group."""
        return await self._list(
            path("/v1/organizations/{}/groups/{}/roles", organization_id, group_id), request_options=request_options
        )

    async def grant_role(
        self, organization_id: str, group_id: str, role_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """Grant a role to the group; every member inherits it."""
        await self._request(
            "POST",
            path("/v1/organizations/{}/groups/{}/roles/{}", organization_id, group_id, role_id),
            request_options=request_options,
        )

    async def revoke_role(
        self, organization_id: str, group_id: str, role_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/groups/{}/roles/{}", organization_id, group_id, role_id),
            request_options=request_options,
        )


class AsyncInvitations(AsyncAPIResource):
    """Invitations to join the organization. Accepting one is the invitee's own action."""

    async def create(
        self,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
        **params: Unpack[InvitationCreateParams],
    ) -> InvitationResult:
        """Create an invitation and email its link to the invited address. Idempotent: safe to retry."""
        return await self._request(
            "POST",
            "/v1/invites",
            json=params,
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    async def list(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[Invitation]:
        return await self._list(path("/v1/organizations/{}/invites", organization_id), request_options=request_options)

    async def resend(self, invitation_id: str, /, *, request_options: RequestOptions | None = None) -> InvitationResult:
        """Issue a new link, extend the expiry and email the invitation again."""
        return await self._request(
            "POST", path("/v1/invites/{}/resend", invitation_id), request_options=request_options
        )

    async def delete(self, invitation_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Withdraw a pending invitation; its link stops working."""
        await self._request("DELETE", path("/v1/invites/{}", invitation_id), request_options=request_options)


class AsyncBranding(AsyncAPIResource):
    """The organization's branding. Shown only while the plan includes custom branding."""

    async def get(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> OrganizationBranding:
        return await self._request(
            "GET", path("/v1/organizations/{}/branding", organization_id), request_options=request_options
        )

    async def update(
        self,
        organization_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[BrandingUpdateParams],
    ) -> OrganizationBranding:
        """Replace the branding."""
        return await self._request(
            "PUT", path("/v1/organizations/{}/branding", organization_id), json=params, request_options=request_options
        )
