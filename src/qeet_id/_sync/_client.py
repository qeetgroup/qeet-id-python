# Generated from qeet_id/_async/_client.py by scripts/unasync.py. Edit that file, not this one.
"""The synchronous Qeet ID client."""

from collections.abc import Mapping
from types import TracebackType
from typing import Self

import httpx2

from qeet_id._config import build_user_agent, check_headers, check_max_retries, check_timeout, normalize_base_url
from qeet_id._constants import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from qeet_id._options import AppInfo
from qeet_id._sync._credentials import APIKeyAuth, ClientCredentialsAuth, Credential
from qeet_id._sync._transport import Transport
from qeet_id._sync.resources.access import (
    AuthPolicies,
    Decisions,
    IPRules,
    Permissions,
    Relationships,
    Roles,
    SecurityPolicies,
    ThreatDetection,
)
from qeet_id._sync.resources.developer import (
    Agents,
    APIKeys,
    AuthHooks,
    Secrets,
    TokenVault,
    VerifiableCredentials,
    Webhooks,
)
from qeet_id._sync.resources.federation import (
    SCIM,
    AdminPortalLinks,
    Applications,
    LDAPConnections,
    SAMLConnections,
    SAMLServiceProviders,
    ServicePrincipals,
    SocialProviders,
)
from qeet_id._sync.resources.identity import (
    Branding,
    Domains,
    Groups,
    Invitations,
    Tenants,
    Users,
)
from qeet_id._sync.resources.oauth import OAuth
from qeet_id._sync.resources.operations import (
    GDPR,
    Analytics,
    AuditLogs,
    Billing,
    EmailTemplates,
    LogSinks,
    RateLimits,
    Retention,
)

__all__ = ["QeetID"]


class QeetID:
    """The synchronous Qeet ID API client.

    Create one per process and share it: it is safe for concurrent use and
    reuses connections and cached tokens. Close it when done, or use it as a
    context manager::

        with QeetID(api_key=os.environ["QEET_ID_API_KEY"]) as client:
            user = client.users.get(user_id)

    Give it one credential: an ``api_key`` (sent as ``Authorization: ApiKey <key>``),
    or a service principal's ``client_id`` and ``client_secret``, exchanged for an
    access token that is cached and renewed shortly before it expires. A client
    without one can still call the endpoints that authenticate otherwise: the
    OAuth endpoints, directory sign-in, agent tokens and credential verification.

    Args:
        api_key: A server-side API key (``qk_…``). Keep it out of browsers, source control and logs.
        client_id: A service principal's client ID, with ``client_secret``.
        client_secret: The service principal's secret.
        base_url: The API. Must be https, except for a loopback host. Default ``https://api.id.qeet.in``.
        timeout: Seconds each attempt may wait to connect, send or read; or an ``httpx2.Timeout``. Default 30.
        max_retries: Retries of a retry-safe request after a transient failure. Default 2; 0 turns them off.
        default_headers: Headers sent with every request, such as tracing headers. They can't replace
            ``Authorization``, ``Accept``, ``Content-Type``, ``User-Agent`` or ``Idempotency-Key``.
        app_info: Your application's name, version and URL, put in front of the ``User-Agent``.
        http_client: An ``httpx2.Client`` of your own, for a proxy, custom TLS or tests.
            The client never closes it. Don't let it follow redirects.

    Raises:
        ValueError: when an argument is invalid, or more than one credential is given.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | httpx2.Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        app_info: AppInfo | None = None,
        http_client: httpx2.Client | None = None,
    ) -> None:
        credential: Credential | None = None
        if api_key is not None:
            if client_id is not None or client_secret is not None:
                raise ValueError("Give the client one credential: an api_key, or a client_id and client_secret.")
            if not isinstance(api_key, str) or not api_key.strip():
                raise ValueError("api_key must be a non-empty string when given.")
            credential = APIKeyAuth(api_key.strip())
        elif client_id is not None or client_secret is not None:
            if not client_id or not client_secret:
                raise ValueError("client_id and client_secret go together: give both.")
            credential = ClientCredentialsAuth(client_id, client_secret)
        check_timeout(timeout)
        self._transport = Transport(
            base_url=normalize_base_url(base_url),
            timeout=timeout,
            max_retries=check_max_retries(max_retries),
            headers=check_headers(default_headers, name="default_headers"),
            user_agent=build_user_agent(app_info),
            credential=credential,
            http_client=http_client,
        )
        transport = self._transport

        # Identity: the organisation, its people and groups.
        self.tenants = Tenants(transport)
        self.domains = Domains(transport)
        self.users = Users(transport)
        self.groups = Groups(transport)
        self.invitations = Invitations(transport)
        self.branding = Branding(transport)

        # Access: who may do what, and how people sign in.
        self.roles = Roles(transport)
        self.permissions = Permissions(transport)
        self.relationships = Relationships(transport)
        self.decisions = Decisions(transport)
        self.auth_policies = AuthPolicies(transport)
        self.security_policies = SecurityPolicies(transport)
        self.ip_rules = IPRules(transport)
        self.threat_detection = ThreatDetection(transport)

        # Federation: OAuth and OpenID Connect, SAML, directories, SCIM, social sign-in.
        self.oauth = OAuth(transport)
        self.applications = Applications(transport)
        self.service_principals = ServicePrincipals(transport)
        self.saml_connections = SAMLConnections(transport)
        self.saml_service_providers = SAMLServiceProviders(transport)
        self.ldap_connections = LDAPConnections(transport)
        self.scim = SCIM(transport)
        self.social_providers = SocialProviders(transport)
        self.admin_portal_links = AdminPortalLinks(transport)

        # Developer: API keys, agents, credentials, hooks, webhooks, secrets.
        self.api_keys = APIKeys(transport)
        self.agents = Agents(transport)
        self.verifiable_credentials = VerifiableCredentials(transport)
        self.auth_hooks = AuthHooks(transport)
        self.webhooks = Webhooks(transport)
        self.secrets = Secrets(transport)
        self.token_vault = TokenVault(transport)

        # Operations: audit, analytics, billing, compliance and limits.
        self.audit_logs = AuditLogs(transport)
        self.analytics = Analytics(transport)
        self.billing = Billing(transport)
        self.gdpr = GDPR(transport)
        self.email_templates = EmailTemplates(transport)
        self.retention = Retention(transport)
        self.log_sinks = LogSinks(transport)
        self.rate_limits = RateLimits(transport)

    @property
    def base_url(self) -> str:
        """The API the client sends requests to."""
        return self._transport.base_url

    def close(self) -> None:
        """Close the client's connections. A ``http_client`` you passed in is left open."""
        self._transport.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(base_url={self.base_url!r})"
