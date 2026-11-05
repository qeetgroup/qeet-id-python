# Generated from qeet_id/_async/resources/developer.py by scripts/unasync.py. Edit that file, not this one.
"""Developer: API keys, agents, credentials, auth hooks, webhooks, secrets, token vault (developer.yaml)."""

import warnings
from collections.abc import Mapping
from typing import Any, Literal, Unpack

from qeet_id._options import RequestOptions
from qeet_id._pagination import ListResult, Page
from qeet_id._request import path
from qeet_id._sync._resource import APIResource
from qeet_id._sync._transport import Transport
from qeet_id.types.developer import (
    Agent,
    AgentCreateParams,
    AgentSecret,
    AgentsResumed,
    AgentsSuspended,
    AgentStatus,
    AgentToken,
    APIKey,
    APIKeyCreated,
    APIKeyCreateParams,
    AuthHook,
    AuthHookCreateParams,
    AuthHookState,
    AuthHookTestResult,
    AuthHookUpdateParams,
    CredentialVerification,
    IssuedCredential,
    Secret,
    SecretCreateParams,
    SecretUpdateParams,
    SecretValue,
    SponsorshipTransfer,
    TokenVaultAccessToken,
    TokenVaultProvider,
    TokenVaultProviderCreateParams,
    VerifiableCredential,
    WebhookCreateParams,
    WebhookDeliveriesRequeued,
    WebhookDelivery,
    WebhookDeliveryAttempt,
    WebhookEventTypeInfo,
    WebhookSecret,
    WebhookSubscription,
    WebhookTestQueued,
    WebhookUpdateParams,
)

__all__ = [
    "APIKeys",
    "Agents",
    "AuthHooks",
    "Secrets",
    "TokenVault",
    "VerifiableCredentials",
    "WebhookDeliveries",
    "Webhooks",
]


def _overlap(overlap_hours: int | None) -> dict[str, int]:
    return {} if overlap_hours is None else {"overlap_hours": overlap_hours}


class APIKeys(APIResource):
    """API keys."""

    def create(
        self,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
        **params: Unpack[APIKeyCreateParams],
    ) -> APIKeyCreated:
        """Create a key; ``secret`` is shown only in the answer. Idempotent: safe to retry."""
        return self._request(
            "POST",
            "/v1/api-keys",
            json=params,
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[APIKey]:
        return self._list(path("/v1/tenants/{}/api-keys", tenant_id), request_options=request_options)

    def rotate(
        self,
        tenant_id: str,
        api_key_id: str,
        /,
        *,
        overlap_hours: int | None = None,
        request_options: RequestOptions | None = None,
    ) -> APIKeyCreated:
        """Replace a key with a new one, shown once. The old one keeps working for ``overlap_hours``."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/api-keys/{}/rotate", tenant_id, api_key_id),
            json=_overlap(overlap_hours),
            request_options=request_options,
        )

    def revoke(self, api_key_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Revoke a key at once."""
        self._request("DELETE", path("/v1/api-keys/{}", api_key_id), request_options=request_options)


class Agents(APIResource):
    """AI agent identities: their tokens, secrets and lifecycle."""

    def create(
        self,
        tenant_id: str,
        /,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
        **params: Unpack[AgentCreateParams],
    ) -> Agent:
        """Register an agent; its ``secret`` is in the answer, once. Idempotent: safe to retry."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/agents", tenant_id),
            json=params,
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[Agent]:
        return self._list(path("/v1/tenants/{}/agents", tenant_id), request_options=request_options)

    def delete(self, tenant_id: str, agent_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        self._request("DELETE", path("/v1/tenants/{}/agents/{}", tenant_id, agent_id), request_options=request_options)

    def set_disabled(
        self, tenant_id: str, agent_id: str, /, disabled: bool, *, request_options: RequestOptions | None = None
    ) -> None:
        """Suspend (``True``) or resume (``False``) the agent. Prefer ``suspend`` and ``resume``."""
        self._request(
            "PATCH",
            path("/v1/tenants/{}/agents/{}", tenant_id, agent_id),
            json={"disabled": disabled},
            request_options=request_options,
        )

    def suspend(
        self, tenant_id: str, agent_id: str, /, *, request_options: RequestOptions | None = None
    ) -> AgentStatus:
        """Suspend the agent: its tokens stop working at once. Reversible with ``resume``."""
        return self._request(
            "POST", path("/v1/tenants/{}/agents/{}/suspend", tenant_id, agent_id), request_options=request_options
        )

    def resume(self, tenant_id: str, agent_id: str, /, *, request_options: RequestOptions | None = None) -> AgentStatus:
        return self._request(
            "POST", path("/v1/tenants/{}/agents/{}/resume", tenant_id, agent_id), request_options=request_options
        )

    def decommission(
        self, tenant_id: str, agent_id: str, /, *, request_options: RequestOptions | None = None
    ) -> AgentStatus:
        """Retire the agent for good."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/agents/{}/decommission", tenant_id, agent_id),
            request_options=request_options,
        )

    def suspend_all(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> AgentsSuspended:
        """Incident response: suspend every active agent of the organisation at once."""
        return self._request("POST", path("/v1/tenants/{}/agents/kill-all", tenant_id), request_options=request_options)

    def resume_all(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> AgentsResumed:
        """Resume every suspended agent of the organisation at once."""
        return self._request(
            "POST", path("/v1/tenants/{}/agents/resume-all", tenant_id), request_options=request_options
        )

    def rotate_secret(
        self,
        tenant_id: str,
        agent_id: str,
        /,
        *,
        overlap_hours: int | None = None,
        request_options: RequestOptions | None = None,
    ) -> AgentSecret:
        """Issue a new secret, shown once; the old one keeps working for ``overlap_hours``."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/agents/{}/rotate-secret", tenant_id, agent_id),
            json=_overlap(overlap_hours),
            request_options=request_options,
        )

    def list_sponsored_by(
        self, tenant_id: str, user_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[Agent]:
        """List the agents a person sponsors."""
        return self._list(
            path("/v1/tenants/{}/agents/sponsored-by/{}", tenant_id, user_id), request_options=request_options
        )

    def transfer_sponsorship(
        self,
        tenant_id: str,
        from_user_id: str,
        to_user_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
    ) -> SponsorshipTransfer:
        """Give every agent a person sponsors to another sponsor, as when the person leaves."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/agents/sponsored-by/{}/transfer", tenant_id, from_user_id),
            json={"to_user_id": to_user_id},
            request_options=request_options,
        )

    def create_token(
        self, agent_id: str, /, secret: str, *, request_options: RequestOptions | None = None
    ) -> AgentToken:
        """Get a short-lived access token for an agent from its id and secret. Sends no client credential."""
        return self._request(
            "POST",
            "/v1/agents/token",
            json={"agent_id": agent_id, "secret": secret},
            authenticate=False,
            request_options=request_options,
        )


class VerifiableCredentials(APIResource):
    """W3C verifiable credentials (JWT-VC): issue, list, revoke and verify."""

    def issue(
        self,
        tenant_id: str,
        /,
        *,
        subject: str,
        type: str,
        claims: Mapping[str, Any] | None = None,
        ttl_seconds: int | None = None,
        user_id: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> IssuedCredential:
        """Issue a credential as a signed JWT; ``user_id`` names the organisation's user it is about."""
        body: dict[str, object] = {"subject": subject, "type": type}
        for key, value in (("claims", claims), ("ttl_seconds", ttl_seconds), ("user_id", user_id)):
            if value is not None:
                body[key] = value
        return self._request(
            "POST", path("/v1/tenants/{}/credentials", tenant_id), json=body, request_options=request_options
        )

    def list(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[VerifiableCredential]:
        return self._list(path("/v1/tenants/{}/credentials", tenant_id), request_options=request_options)

    def revoke(self, tenant_id: str, credential_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        self._request(
            "POST",
            path("/v1/tenants/{}/credentials/{}/revoke", tenant_id, credential_id),
            retry_safe=True,
            request_options=request_options,
        )

    def verify(self, credential: str, /, *, request_options: RequestOptions | None = None) -> CredentialVerification:
        """Check a presented JWT-VC. Public: sends no client credential."""
        return self._request(
            "POST",
            "/v1/credentials/verify",
            json={"credential": credential},
            authenticate=False,
            retry_safe=True,
            request_options=request_options,
        )


class AuthHooks(APIResource):
    """Authentication hooks: signed calls to your endpoint during sign-in."""

    def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[AuthHook]:
        return self._list(path("/v1/tenants/{}/auth-hooks", tenant_id), request_options=request_options)

    def create(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[AuthHookCreateParams],
    ) -> AuthHook:
        return self._request(
            "POST", path("/v1/tenants/{}/auth-hooks", tenant_id), json=params, request_options=request_options
        )

    def update(
        self,
        tenant_id: str,
        hook_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[AuthHookUpdateParams],
    ) -> AuthHookState:
        """Change only the fields given."""
        return self._request(
            "PATCH",
            path("/v1/tenants/{}/auth-hooks/{}", tenant_id, hook_id),
            json=params,
            request_options=request_options,
        )

    def delete(self, tenant_id: str, hook_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        self._request(
            "DELETE", path("/v1/tenants/{}/auth-hooks/{}", tenant_id, hook_id), request_options=request_options
        )

    def test(
        self, tenant_id: str, hook_id: str, /, *, request_options: RequestOptions | None = None
    ) -> AuthHookTestResult:
        """Call the hook with a sample payload and report what it answered."""
        return self._request(
            "POST", path("/v1/tenants/{}/auth-hooks/{}/test", tenant_id, hook_id), request_options=request_options
        )


class WebhookDeliveries(APIResource):
    """A webhook subscription's deliveries."""

    def list(
        self,
        webhook_id: str,
        /,
        *,
        status: Literal["delivered", "pending", "retrying", "dead"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> Page[WebhookDelivery]:
        """List a subscription's deliveries, newest first."""
        return self._paginate(
            path("/v1/webhooks/{}/deliveries", webhook_id),
            {"status": status, "limit": limit, "cursor": cursor},
            request_options=request_options,
        )

    def retry(self, webhook_id: str, delivery_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Send a delivery again now."""
        self._request(
            "POST",
            path("/v1/webhooks/{}/deliveries/{}/retry", webhook_id, delivery_id),
            request_options=request_options,
        )

    def retry_failed(
        self, tenant_id: str, webhook_id: str, /, *, request_options: RequestOptions | None = None
    ) -> WebhookDeliveriesRequeued:
        """Send again, each with fresh attempts, up to 1,000 of the subscription's given-up deliveries."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/webhooks/{}/deliveries/retry", tenant_id, webhook_id),
            request_options=request_options,
        )

    def list_attempts(
        self,
        tenant_id: str,
        webhook_id: str,
        delivery_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
    ) -> ListResult[WebhookDeliveryAttempt]:
        """Every attempt to send a delivery, oldest first."""
        return self._list(
            path("/v1/tenants/{}/webhooks/{}/deliveries/{}/attempts", tenant_id, webhook_id, delivery_id),
            request_options=request_options,
        )


class Webhooks(APIResource):
    """Webhook subscriptions. To verify the deliveries your endpoint receives, see :mod:`qeet_id.webhooks`."""

    __slots__ = ("deliveries",)

    def __init__(self, transport: Transport) -> None:
        super().__init__(transport)
        self.deliveries = WebhookDeliveries(transport)
        """A subscription's deliveries."""

    def create(
        self,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
        **params: Unpack[WebhookCreateParams],
    ) -> WebhookSubscription:
        """Subscribe an endpoint. The signing secret is in the answer, once: store it. Idempotent: safe to retry."""
        return self._request(
            "POST",
            "/v1/webhooks",
            json=params,
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    def get(self, webhook_id: str, /, *, request_options: RequestOptions | None = None) -> WebhookSubscription:
        return self._request("GET", path("/v1/webhooks/{}", webhook_id), request_options=request_options)

    def list(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[WebhookSubscription]:
        return self._list(path("/v1/tenants/{}/webhooks", tenant_id), request_options=request_options)

    def update(
        self,
        tenant_id: str,
        webhook_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[WebhookUpdateParams],
    ) -> WebhookSubscription:
        """Change the URL, the events, or both."""
        return self._request(
            "PATCH",
            path("/v1/tenants/{}/webhooks/{}", tenant_id, webhook_id),
            json=params,
            request_options=request_options,
        )

    def disable(self, webhook_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Stop deliveries to the subscription. Undo with ``enable``."""
        self._request("DELETE", path("/v1/webhooks/{}", webhook_id), request_options=request_options)

    def enable(
        self, tenant_id: str, webhook_id: str, /, *, request_options: RequestOptions | None = None
    ) -> WebhookSubscription:
        """Turn a disabled subscription back on; deliveries held meanwhile are then sent."""
        return self._request(
            "POST", path("/v1/tenants/{}/webhooks/{}/enable", tenant_id, webhook_id), request_options=request_options
        )

    def rotate_secret(
        self, tenant_id: str, webhook_id: str, /, *, request_options: RequestOptions | None = None
    ) -> WebhookSecret:
        """Replace the signing secret and return the new one, once.

        The old one keeps signing alongside it until ``previous_secret_expires_at`` (24 hours):
        verify with both meanwhile.
        """
        return self._request(
            "POST",
            path("/v1/tenants/{}/webhooks/{}/rotate-secret", tenant_id, webhook_id),
            request_options=request_options,
        )

    def test(self, webhook_id: str, /, *, request_options: RequestOptions | None = None) -> WebhookTestQueued:
        """Queue a ``test.ping`` event for this subscription alone."""
        return self._request("POST", path("/v1/webhooks/{}/test", webhook_id), request_options=request_options)

    def list_event_types(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[WebhookEventTypeInfo]:
        """The catalogue of events a subscription can name."""
        return self._list(path("/v1/tenants/{}/webhooks/events", tenant_id), request_options=request_options)


class Secrets(APIResource):
    """The organisation's encrypted secrets store."""

    def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[Secret]:
        return self._list(path("/v1/tenants/{}/secrets", tenant_id), request_options=request_options)

    def create(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[SecretCreateParams],
    ) -> Secret:
        return self._request(
            "POST", path("/v1/tenants/{}/secrets", tenant_id), json=params, request_options=request_options
        )

    def update(
        self,
        tenant_id: str,
        secret_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[SecretUpdateParams],
    ) -> Secret:
        return self._request(
            "PATCH",
            path("/v1/tenants/{}/secrets/{}", tenant_id, secret_id),
            json=params,
            request_options=request_options,
        )

    def delete(self, tenant_id: str, secret_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        self._request(
            "DELETE", path("/v1/tenants/{}/secrets/{}", tenant_id, secret_id), request_options=request_options
        )

    def reveal(
        self, tenant_id: str, secret_id: str, /, *, request_options: RequestOptions | None = None
    ) -> SecretValue:
        """Return the secret's value. Audited."""
        return self._request(
            "POST", path("/v1/tenants/{}/secrets/{}/reveal", tenant_id, secret_id), request_options=request_options
        )

    def get_value(self, name: str, /, *, request_options: RequestOptions | None = None) -> SecretValue:
        """Return a secret's value by name. Needs the ``vault:read`` scope for it."""
        return self._request("GET", path("/v1/vault/{}", name), request_options=request_options)


class TokenVault(APIResource):
    """Third-party OAuth tokens held for your users (Slack, GitHub, Google, or any OAuth 2.0 provider).

    People connect their accounts in the browser; this manages the providers and fetches live tokens.
    """

    def create_provider(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[TokenVaultProviderCreateParams],
    ) -> TokenVaultProvider:
        """Register a provider, or replace one's settings."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/vault/tokens/providers", tenant_id),
            json=params,
            request_options=request_options,
        )

    def list_providers(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[TokenVaultProvider]:
        return self._list(path("/v1/tenants/{}/vault/tokens/providers", tenant_id), request_options=request_options)

    def delete_provider(
        self, tenant_id: str, provider: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        self._request(
            "DELETE",
            path("/v1/tenants/{}/vault/tokens/providers/{}", tenant_id, provider),
            request_options=request_options,
        )

    def get_access_token(
        self, provider: str, /, *, request_options: RequestOptions | None = None
    ) -> TokenVaultAccessToken:
        """Return a live access token for ``provider``, refreshed first when it has expired.

        Deprecated: this hands your code the raw third-party token, which then tends to be
        stored, logged or put in a model's prompt, outside the vault's controls; an AI agent must
        never receive it. Keep it in memory for one request only. It will be replaced by a
        brokered call once the API offers one. Needs the ``vault:read`` scope.
        """
        warnings.warn(
            "token_vault.get_access_token() returns a raw third-party token: keep it out of storage, logs and prompts.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._request("GET", path("/v1/vault/tokens/{}/access-token", provider), request_options=request_options)
