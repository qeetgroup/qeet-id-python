"""Federation: applications, service principals, SAML, LDAP, SCIM, social, admin portal (federation.yaml)."""

from collections.abc import Sequence
from typing import Unpack, cast

from qeet_id._async._resource import AsyncAPIResource
from qeet_id._async._transport import AsyncTransport
from qeet_id._options import RequestOptions
from qeet_id._pagination import AsyncPaginator, ListResult
from qeet_id._request import path
from qeet_id.types.federation import (
    AdminPortalCapability,
    AdminPortalLink,
    AdminPortalLinkCreated,
    Application,
    ApplicationAuthFailures,
    ApplicationCreated,
    ApplicationCreateParams,
    ApplicationSecret,
    ApplicationUpdateParams,
    ConnectionTestResult,
    LDAPAuthenticationResult,
    LDAPConnection,
    LDAPConnectionCreateParams,
    LDAPConnectionUpdateParams,
    LDAPTestResult,
    MfaChallenge,
    OAuthResource,
    SAMLCertificate,
    SAMLConnection,
    SAMLConnectionCreateParams,
    SAMLConnectionImportParams,
    SAMLConnectionUpdateParams,
    SAMLServiceProvider,
    SAMLServiceProviderAssignments,
    SAMLServiceProviderCreateParams,
    SAMLServiceProviderUpdateParams,
    SCIMConfig,
    SCIMGroup,
    SCIMToken,
    SCIMTokenCreated,
    SCIMTokenRotated,
    SCIMUser,
    ServicePrincipal,
    ServicePrincipalCreated,
    ServicePrincipalCreateParams,
    ServicePrincipalSecret,
    ShadowAIApplication,
    SocialProvider,
    SocialProviderUpdateParams,
    SocialProviderUpsertParams,
    SSOGroupMapping,
    TokenPair,
)

__all__ = [
    "AsyncAdminPortalLinks",
    "AsyncApplications",
    "AsyncLDAPConnections",
    "AsyncOAuthResources",
    "AsyncSAMLConnections",
    "AsyncSAMLServiceProviders",
    "AsyncSCIM",
    "AsyncServicePrincipals",
    "AsyncSocialProviders",
]


class AsyncOAuthResources(AsyncAPIResource):
    """The organization's registered RFC 8707 resources: services applications may ask tokens for."""

    async def list(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[OAuthResource]:
        return await self._list(
            path("/v1/organizations/{}/oidc/resources", organization_id), request_options=request_options
        )

    async def create(
        self,
        organization_id: str,
        /,
        identifier: str,
        *,
        name: str | None = None,
        server_client_id: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> OAuthResource:
        """Register a resource: an absolute URI without a fragment, unique on the platform."""
        body = {"identifier": identifier, "name": name, "server_client_id": server_client_id}
        return await self._request(
            "POST",
            path("/v1/organizations/{}/oidc/resources", organization_id),
            json={key: value for key, value in body.items() if value is not None},
            request_options=request_options,
        )

    async def delete(
        self, organization_id: str, resource_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """No new token is issued for it; tokens already issued last out their short lifetime."""
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/oidc/resources/{}", organization_id, resource_id),
            request_options=request_options,
        )


class AsyncApplications(AsyncAPIResource):
    """Applications (OAuth / OpenID Connect clients) and the resources they may ask tokens for."""

    __slots__ = ("resources",)

    def __init__(self, transport: AsyncTransport) -> None:
        super().__init__(transport)
        self.resources = AsyncOAuthResources(transport)
        """RFC 8707 resources."""

    async def create(
        self,
        organization_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[ApplicationCreateParams],
    ) -> ApplicationCreated:
        """Register an application. A confidential one's secret is in the result, once."""
        return await self._request(
            "POST",
            path("/v1/organizations/{}/oidc/clients", organization_id),
            json={**params, "organization_id": organization_id},
            request_options=request_options,
        )

    async def get(
        self, organization_id: str, application_id: str, /, *, request_options: RequestOptions | None = None
    ) -> Application:
        return await self._request(
            "GET",
            path("/v1/organizations/{}/oidc/clients/{}", organization_id, application_id),
            request_options=request_options,
        )

    async def list(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[Application]:
        return await self._list(
            path("/v1/organizations/{}/oidc/clients", organization_id), request_options=request_options
        )

    async def update(
        self,
        organization_id: str,
        application_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[ApplicationUpdateParams],
    ) -> Application:
        """Change only the fields given."""
        return await self._request(
            "PATCH",
            path("/v1/organizations/{}/oidc/clients/{}", organization_id, application_id),
            json=params,
            request_options=request_options,
        )

    async def delete(
        self, organization_id: str, application_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """Delete the application; its tokens and grants stop being honoured."""
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/oidc/clients/{}", organization_id, application_id),
            request_options=request_options,
        )

    async def rotate_secret(
        self, organization_id: str, application_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ApplicationSecret:
        """Issue a new secret for a confidential application, shown once. The old one stops working at once."""
        return await self._request(
            "POST",
            path("/v1/organizations/{}/oidc/clients/{}/rotate-secret", organization_id, application_id),
            request_options=request_options,
        )

    async def get_auth_failures(
        self, organization_id: str, application_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ApplicationAuthFailures:
        """The application's wrong-secret lockout and its last 20 failed authentications."""
        return await self._request(
            "GET",
            path("/v1/organizations/{}/oidc/clients/{}/auth-failures", organization_id, application_id),
            request_options=request_options,
        )

    async def list_shadow_ai(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[ShadowAIApplication]:
        """Applications holding a machine grant that nobody has reviewed."""
        return await self._list(
            path("/v1/organizations/{}/oidc/clients/shadow-ai", organization_id), request_options=request_options
        )

    async def mark_reviewed(
        self, organization_id: str, application_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """Mark the application reviewed: it leaves the shadow-AI list until its grant types change."""
        await self._request(
            "POST",
            path("/v1/organizations/{}/oidc/clients/{}/review", organization_id, application_id),
            request_options=request_options,
        )


class AsyncServicePrincipals(AsyncAPIResource):
    """Service principals: machine identities for machine-to-machine access."""

    async def create(
        self,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
        **params: Unpack[ServicePrincipalCreateParams],
    ) -> ServicePrincipalCreated:
        """Create a principal; its secret is in the result, once. Idempotent: safe to retry."""
        return await self._request(
            "POST",
            "/v1/service-principals",
            json=params,
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    async def list(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[ServicePrincipal]:
        return await self._list(
            path("/v1/organizations/{}/service-principals", organization_id), request_options=request_options
        )

    async def disable(self, service_principal_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Disable the principal: no more tokens, and its tokens are refused at once. Undo with ``enable``."""
        await self._request(
            "DELETE", path("/v1/service-principals/{}", service_principal_id), request_options=request_options
        )

    async def enable(
        self, organization_id: str, service_principal_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """Turn a disabled principal back on."""
        await self._request(
            "POST",
            path("/v1/organizations/{}/service-principals/{}/enable", organization_id, service_principal_id),
            request_options=request_options,
        )

    async def rotate_secret(
        self,
        organization_id: str,
        service_principal_id: str,
        /,
        *,
        overlap_hours: int | None = None,
        request_options: RequestOptions | None = None,
    ) -> ServicePrincipalSecret:
        """Issue a new secret, shown once. The old one keeps working ``overlap_hours`` (default 24, at most 168)."""
        return await self._request(
            "POST",
            path("/v1/organizations/{}/service-principals/{}/rotate-secret", organization_id, service_principal_id),
            json={} if overlap_hours is None else {"overlap_hours": overlap_hours},
            request_options=request_options,
        )


class AsyncSAMLConnections(AsyncAPIResource):
    """Inbound SAML connections: Qeet ID is the service provider for an external identity provider."""

    async def create(
        self,
        organization_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[SAMLConnectionCreateParams],
    ) -> SAMLConnection:
        return await self._request(
            "POST", path("/v1/organizations/{}/saml", organization_id), json=params, request_options=request_options
        )

    async def import_metadata(
        self,
        organization_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[SAMLConnectionImportParams],
    ) -> SAMLConnection:
        """Create a connection from the identity provider's metadata: ``metadata_url`` or ``metadata_xml``."""
        return await self._request(
            "POST",
            path("/v1/organizations/{}/saml/import", organization_id),
            json=params,
            request_options=request_options,
        )

    async def get(
        self, organization_id: str, connection_id: str, /, *, request_options: RequestOptions | None = None
    ) -> SAMLConnection:
        return await self._request(
            "GET", path("/v1/organizations/{}/saml/{}", organization_id, connection_id), request_options=request_options
        )

    async def list(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[SAMLConnection]:
        return await self._list(path("/v1/organizations/{}/saml", organization_id), request_options=request_options)

    async def update(
        self,
        organization_id: str,
        connection_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[SAMLConnectionUpdateParams],
    ) -> SAMLConnection:
        return await self._request(
            "PATCH",
            path("/v1/organizations/{}/saml/{}", organization_id, connection_id),
            json=params,
            request_options=request_options,
        )

    async def delete(
        self, organization_id: str, connection_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/saml/{}", organization_id, connection_id),
            request_options=request_options,
        )

    async def update_metadata(
        self,
        organization_id: str,
        connection_id: str,
        /,
        *,
        metadata_url: str | None = None,
        metadata_xml: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> SAMLConnection:
        """Update the connection from the identity provider's metadata, a URL or the XML."""
        body = {"metadata_url": metadata_url, "metadata_xml": metadata_xml}
        return await self._request(
            "POST",
            path("/v1/organizations/{}/saml/{}/metadata", organization_id, connection_id),
            json={key: value for key, value in body.items() if value is not None},
            request_options=request_options,
        )

    async def add_certificate(
        self,
        organization_id: str,
        connection_id: str,
        /,
        certificate: str,
        *,
        request_options: RequestOptions | None = None,
    ) -> SAMLCertificate:
        """Add a signing certificate, for a rotation without downtime."""
        return await self._request(
            "POST",
            path("/v1/organizations/{}/saml/{}/certificates", organization_id, connection_id),
            json={"certificate": certificate},
            request_options=request_options,
        )

    async def remove_certificate(
        self,
        organization_id: str,
        connection_id: str,
        certificate_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
    ) -> None:
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/saml/{}/certificates/{}", organization_id, connection_id, certificate_id),
            request_options=request_options,
        )

    async def test(
        self, organization_id: str, connection_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ConnectionTestResult:
        """Check the configuration. Changes nothing."""
        return await self._request(
            "POST",
            path("/v1/organizations/{}/saml/{}/test", organization_id, connection_id),
            retry_safe=True,
            request_options=request_options,
        )

    async def list_group_mappings(
        self, organization_id: str, connection_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[SSOGroupMapping]:
        return await self._list(
            path("/v1/organizations/{}/saml/{}/group-mappings", organization_id, connection_id),
            request_options=request_options,
        )

    async def create_group_mapping(
        self,
        organization_id: str,
        connection_id: str,
        /,
        *,
        idp_group: str,
        group_id: str,
        request_options: RequestOptions | None = None,
    ) -> SSOGroupMapping:
        """Map an identity provider group to one of the organization's groups."""
        return await self._request(
            "POST",
            path("/v1/organizations/{}/saml/{}/group-mappings", organization_id, connection_id),
            json={"idp_group": idp_group, "group_id": group_id},
            request_options=request_options,
        )

    async def delete_group_mapping(
        self,
        organization_id: str,
        connection_id: str,
        mapping_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
    ) -> None:
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/saml/{}/group-mappings/{}", organization_id, connection_id, mapping_id),
            request_options=request_options,
        )


class AsyncSAMLServiceProviders(AsyncAPIResource):
    """Service providers that use Qeet ID as their SAML identity provider."""

    async def create(
        self,
        organization_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[SAMLServiceProviderCreateParams],
    ) -> SAMLServiceProvider:
        return await self._request(
            "POST",
            path("/v1/organizations/{}/saml-providers", organization_id),
            json=params,
            request_options=request_options,
        )

    async def get(
        self, organization_id: str, service_provider_id: str, /, *, request_options: RequestOptions | None = None
    ) -> SAMLServiceProvider:
        return await self._request(
            "GET",
            path("/v1/organizations/{}/saml-providers/{}", organization_id, service_provider_id),
            request_options=request_options,
        )

    async def list(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[SAMLServiceProvider]:
        return await self._list(
            path("/v1/organizations/{}/saml-providers", organization_id), request_options=request_options
        )

    async def update(
        self,
        organization_id: str,
        service_provider_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[SAMLServiceProviderUpdateParams],
    ) -> SAMLServiceProvider:
        return await self._request(
            "PATCH",
            path("/v1/organizations/{}/saml-providers/{}", organization_id, service_provider_id),
            json=params,
            request_options=request_options,
        )

    async def delete(
        self, organization_id: str, service_provider_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/saml-providers/{}", organization_id, service_provider_id),
            request_options=request_options,
        )

    async def list_assignments(
        self, organization_id: str, service_provider_id: str, /, *, request_options: RequestOptions | None = None
    ) -> SAMLServiceProviderAssignments:
        """Who may sign in to a service provider that requires assignment."""
        body = await self._request(
            "GET",
            path("/v1/organizations/{}/saml-providers/{}/assignments", organization_id, service_provider_id),
            request_options=request_options,
        )
        body = body if isinstance(body, dict) else {}
        return {"users": body.get("users") or [], "groups": body.get("groups") or []}

    async def assign_user(
        self,
        organization_id: str,
        service_provider_id: str,
        user_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
    ) -> None:
        await self._request(
            "POST",
            path(
                "/v1/organizations/{}/saml-providers/{}/assignments/users/{}",
                organization_id,
                service_provider_id,
                user_id,
            ),
            request_options=request_options,
        )

    async def unassign_user(
        self,
        organization_id: str,
        service_provider_id: str,
        user_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
    ) -> None:
        await self._request(
            "DELETE",
            path(
                "/v1/organizations/{}/saml-providers/{}/assignments/users/{}",
                organization_id,
                service_provider_id,
                user_id,
            ),
            request_options=request_options,
        )

    async def assign_group(
        self,
        organization_id: str,
        service_provider_id: str,
        group_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
    ) -> None:
        await self._request(
            "POST",
            path(
                "/v1/organizations/{}/saml-providers/{}/assignments/groups/{}",
                organization_id,
                service_provider_id,
                group_id,
            ),
            request_options=request_options,
        )

    async def unassign_group(
        self,
        organization_id: str,
        service_provider_id: str,
        group_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
    ) -> None:
        await self._request(
            "DELETE",
            path(
                "/v1/organizations/{}/saml-providers/{}/assignments/groups/{}",
                organization_id,
                service_provider_id,
                group_id,
            ),
            request_options=request_options,
        )


class AsyncLDAPConnections(AsyncAPIResource):
    """Directory connections, and sign-in with a directory password."""

    async def create(
        self,
        organization_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[LDAPConnectionCreateParams],
    ) -> LDAPConnection:
        return await self._request(
            "POST", path("/v1/organizations/{}/ldap", organization_id), json=params, request_options=request_options
        )

    async def get(
        self, organization_id: str, connection_id: str, /, *, request_options: RequestOptions | None = None
    ) -> LDAPConnection:
        return await self._request(
            "GET", path("/v1/organizations/{}/ldap/{}", organization_id, connection_id), request_options=request_options
        )

    async def list(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[LDAPConnection]:
        return await self._list(path("/v1/organizations/{}/ldap", organization_id), request_options=request_options)

    async def update(
        self,
        organization_id: str,
        connection_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[LDAPConnectionUpdateParams],
    ) -> LDAPConnection:
        return await self._request(
            "PATCH",
            path("/v1/organizations/{}/ldap/{}", organization_id, connection_id),
            json=params,
            request_options=request_options,
        )

    async def delete(
        self, organization_id: str, connection_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/ldap/{}", organization_id, connection_id),
            request_options=request_options,
        )

    async def test(
        self, organization_id: str, connection_id: str, /, *, request_options: RequestOptions | None = None
    ) -> LDAPTestResult:
        """Bind to the directory with the stored credentials. A failure raises."""
        return await self._request(
            "POST",
            path("/v1/organizations/{}/ldap/{}/test", organization_id, connection_id),
            retry_safe=True,
            request_options=request_options,
        )

    async def list_group_mappings(
        self, organization_id: str, connection_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[SSOGroupMapping]:
        return await self._list(
            path("/v1/organizations/{}/ldap/{}/group-mappings", organization_id, connection_id),
            request_options=request_options,
        )

    async def create_group_mapping(
        self,
        organization_id: str,
        connection_id: str,
        /,
        *,
        idp_group: str,
        group_id: str,
        request_options: RequestOptions | None = None,
    ) -> SSOGroupMapping:
        return await self._request(
            "POST",
            path("/v1/organizations/{}/ldap/{}/group-mappings", organization_id, connection_id),
            json={"idp_group": idp_group, "group_id": group_id},
            request_options=request_options,
        )

    async def delete_group_mapping(
        self,
        organization_id: str,
        connection_id: str,
        mapping_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
    ) -> None:
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/ldap/{}/group-mappings/{}", organization_id, connection_id, mapping_id),
            request_options=request_options,
        )

    async def authenticate(
        self,
        connection_id: str,
        /,
        *,
        username: str,
        password: str,
        request_options: RequestOptions | None = None,
    ) -> LDAPAuthenticationResult:
        """Sign a person in with their directory username and password.

        The organization's lockout, network, risk and second-factor rules apply. The
        result is tokens, or a challenge to complete at ``POST /v1/auth/mfa``::

            result = await client.ldap_connections.authenticate(connection_id, username=u, password=p)
            if result["type"] == "mfa_challenge":
                ask_for_second_factor(result["challenge"]["mfa_token"])
            else:
                start_session(result["tokens"])

        Sends no credential of the client: the endpoint is public. Never retried, as
        each failed attempt counts towards the lockout.
        """
        body = await self._request(
            "POST",
            path("/ldap/{}/authenticate", connection_id),
            json={"username": username, "password": password},
            authenticate=False,
            retries=False,
            request_options=request_options,
        )
        body = body if isinstance(body, dict) else {}
        if body.get("mfa_required") is True:
            challenge = {**body, "methods": body.get("methods") or [], "factors": body.get("factors") or []}
            return {"type": "mfa_challenge", "challenge": cast("MfaChallenge", challenge)}
        return {"type": "tokens", "tokens": cast("TokenPair", body)}


class AsyncSCIM(AsyncAPIResource):
    """SCIM provisioning: tokens, and what was provisioned. The identity provider calls ``/scim/v2`` itself."""

    async def get_config(self, organization_id: str, /, *, request_options: RequestOptions | None = None) -> SCIMConfig:
        return await self._request(
            "GET", path("/v1/organizations/{}/scim", organization_id), request_options=request_options
        )

    async def list_tokens(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[SCIMToken]:
        return await self._list(
            path("/v1/organizations/{}/scim/tokens", organization_id), request_options=request_options
        )

    async def create_token(
        self,
        organization_id: str,
        /,
        name: str,
        *,
        expires_at: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> SCIMTokenCreated:
        """Issue an additional token, shown once."""
        return await self._request(
            "POST",
            path("/v1/organizations/{}/scim/tokens", organization_id),
            json={"name": name, "expires_at": expires_at},
            request_options=request_options,
        )

    async def rotate_token(
        self,
        organization_id: str,
        token_id: str,
        /,
        *,
        overlap_hours: int | None = None,
        expires_at: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> SCIMTokenRotated:
        """Replace a token with a new one, shown once; the old one keeps working for ``overlap_hours``."""
        body = {"overlap_hours": overlap_hours, "expires_at": expires_at}
        return await self._request(
            "POST",
            path("/v1/organizations/{}/scim/tokens/{}/rotate", organization_id, token_id),
            json={key: value for key, value in body.items() if value is not None},
            request_options=request_options,
        )

    async def revoke_token(
        self, organization_id: str, token_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/scim/tokens/{}", organization_id, token_id),
            request_options=request_options,
        )

    async def revoke_all_tokens(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """Revoke every working token, which stops provisioning."""
        await self._request(
            "DELETE", path("/v1/organizations/{}/scim/token", organization_id), request_options=request_options
        )

    def list_users(
        self,
        organization_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> AsyncPaginator[SCIMUser]:
        return self._paginate(
            path("/v1/organizations/{}/scim/users", organization_id),
            {"limit": limit, "cursor": cursor},
            request_options=request_options,
        )

    def list_groups(
        self,
        organization_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> AsyncPaginator[SCIMGroup]:
        return self._paginate(
            path("/v1/organizations/{}/scim/groups", organization_id),
            {"limit": limit, "cursor": cursor},
            request_options=request_options,
        )


class AsyncSocialProviders(AsyncAPIResource):
    """The organization's social sign-in providers, and linked social accounts."""

    async def list(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[SocialProvider]:
        return await self._list(
            path("/v1/organizations/{}/social/providers", organization_id), request_options=request_options
        )

    async def upsert(
        self, *, request_options: RequestOptions | None = None, **params: Unpack[SocialProviderUpsertParams]
    ) -> SocialProvider:
        """Add a provider, or replace the settings of one the organization has."""
        return await self._request("POST", "/v1/social/providers", json=params, request_options=request_options)

    async def update(
        self,
        provider: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[SocialProviderUpdateParams],
    ) -> SocialProvider:
        """Change only the fields given; ``enabled`` switches the provider on or off."""
        return await self._request(
            "PATCH", path("/v1/social/providers/{}", provider), json=params, request_options=request_options
        )

    async def delete(self, provider: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Remove a provider. Refused with 409 ``social.provider_in_use`` while anyone signs in only through it."""
        await self._request("DELETE", path("/v1/social/providers/{}", provider), request_options=request_options)

    async def unlink_identity(self, identity_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Unlink a social account from the person it belongs to."""
        await self._request("DELETE", path("/v1/social/identities/{}", identity_id), request_options=request_options)


class AsyncAdminPortalLinks(AsyncAPIResource):
    """Links that let a customer's IT administrator set up SSO, SCIM or domains without an account."""

    async def create(
        self,
        organization_id: str,
        /,
        capabilities: Sequence[AdminPortalCapability],
        *,
        ttl_seconds: int | None = None,
        request_options: RequestOptions | None = None,
    ) -> AdminPortalLinkCreated:
        """Create a link; ``token`` and ``url`` are shown only here. ``ttl_seconds``: 15 minutes to 24 hours."""
        body: dict[str, object] = {"capabilities": [*capabilities]}
        if ttl_seconds is not None:
            body["ttl_seconds"] = ttl_seconds
        return await self._request(
            "POST",
            path("/v1/organizations/{}/admin-portal/links", organization_id),
            json=body,
            request_options=request_options,
        )

    async def list(
        self, organization_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[AdminPortalLink]:
        return await self._list(
            path("/v1/organizations/{}/admin-portal/links", organization_id), request_options=request_options
        )

    async def revoke(
        self, organization_id: str, link_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        await self._request(
            "DELETE",
            path("/v1/organizations/{}/admin-portal/links/{}", organization_id, link_id),
            request_options=request_options,
        )
