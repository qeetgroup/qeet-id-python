"""Operations: audit log, analytics, billing, GDPR, email, retention, log sinks, rate limits (operations.yaml)."""

from collections.abc import Mapping
from typing import Literal, Unpack

from qeet_id._async._resource import AsyncAPIResource
from qeet_id._async._transport import AsyncTransport
from qeet_id._options import RequestOptions
from qeet_id._pagination import AsyncPaginator, ListResult
from qeet_id._request import path
from qeet_id.types.operations import (
    AnalyticsOverview,
    AnalyticsOverviewParams,
    AuditAnomaly,
    AuditAnomalySettings,
    AuditAnomalySummary,
    AuditChainVerification,
    AuditLogEntry,
    AuditLogListParams,
    AuditVerificationStatus,
    BillingProfile,
    CheckoutParams,
    CheckoutResult,
    EmailTemplate,
    EmailTemplateContent,
    EmailTemplatePreview,
    Entitlements,
    ErasureRequest,
    ExportRequest,
    Invoice,
    LogSink,
    LogSinkCreateParams,
    LogSinkTestResult,
    PaymentMethod,
    RateLimitsUpdateParams,
    RetentionPolicy,
    RetentionPreview,
    RetentionRun,
    Subscription,
    SubscriptionCancellation,
    TenantRateLimits,
)

__all__ = [
    "AsyncAnalytics",
    "AsyncAuditAnomalies",
    "AsyncAuditLogs",
    "AsyncBilling",
    "AsyncEmailTemplates",
    "AsyncGDPR",
    "AsyncGDPRErasures",
    "AsyncGDPRExports",
    "AsyncLogSinks",
    "AsyncRateLimits",
    "AsyncRetention",
]


class AsyncAuditAnomalies(AsyncAPIResource):
    """Behavioural anomalies found in the audit log."""

    async def list(
        self,
        tenant_id: str,
        /,
        *,
        status: Literal["open", "resolved"] | None = None,
        limit: int | None = None,
        request_options: RequestOptions | None = None,
    ) -> ListResult[AuditAnomaly]:
        return await self._list(
            path("/v1/tenants/{}/audit/anomalies", tenant_id),
            {"status": status, "limit": limit},
            request_options=request_options,
        )

    async def get_summary(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> AuditAnomalySummary:
        return await self._request(
            "GET", path("/v1/tenants/{}/audit/anomalies/summary", tenant_id), request_options=request_options
        )

    async def resolve(
        self, tenant_id: str, anomaly_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        await self._request(
            "POST",
            path("/v1/tenants/{}/audit/anomalies/{}/resolve", tenant_id, anomaly_id),
            request_options=request_options,
        )

    async def get_settings(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> AuditAnomalySettings:
        return await self._request(
            "GET", path("/v1/tenants/{}/audit/anomaly-settings", tenant_id), request_options=request_options
        )

    async def update_settings(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **settings: Unpack[AuditAnomalySettings],
    ) -> AuditAnomalySettings:
        """Replace the anomaly-detection settings."""
        return await self._request(
            "PUT",
            path("/v1/tenants/{}/audit/anomaly-settings", tenant_id),
            json=settings,
            request_options=request_options,
        )


class AsyncAuditLogs(AsyncAPIResource):
    """The hash-chained audit log and its integrity."""

    __slots__ = ("anomalies",)

    def __init__(self, transport: AsyncTransport) -> None:
        super().__init__(transport)
        self.anomalies = AsyncAuditAnomalies(transport)
        """Behavioural anomalies found in the log."""

    def list(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None, **params: Unpack[AuditLogListParams]
    ) -> AsyncPaginator[AuditLogEntry]:
        """List entries, newest first. ``from_`` and ``to`` bound ``created_at``."""
        return self._paginate(path("/v1/tenants/{}/audit", tenant_id), params, request_options=request_options)

    async def verify(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> AuditChainVerification:
        """Walk the whole chain now and recompute every row's hash. Changes nothing."""
        return await self._request(
            "GET", path("/v1/tenants/{}/audit/verify", tenant_id), request_options=request_options
        )

    async def get_verification_status(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> AuditVerificationStatus:
        """The latest scheduled verification's outcome."""
        return await self._request(
            "GET", path("/v1/tenants/{}/audit/verification", tenant_id), request_options=request_options
        )


class AsyncAnalytics(AsyncAPIResource):
    """Sign-in analytics."""

    async def get_overview(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[AnalyticsOverviewParams],
    ) -> AnalyticsOverview:
        """The sign-in dashboard; a range with ``from_`` and ``to``, or ``days``, adds ``range``."""
        return await self._request(
            "GET",
            path("/v1/tenants/{}/analytics/overview", tenant_id),
            query=params,
            request_options=request_options,
        )


class AsyncBilling(AsyncAPIResource):
    """The organisation's Qeet ID billing: subscription, invoices and plan."""

    async def get_subscription(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> Subscription:
        return await self._request(
            "GET", path("/v1/tenants/{}/billing/subscription", tenant_id), request_options=request_options
        )

    async def update_subscription(
        self,
        tenant_id: str,
        /,
        *,
        plan_code: str,
        currency: str,
        request_options: RequestOptions | None = None,
    ) -> Subscription:
        """Change the plan or currency."""
        return await self._request(
            "PUT",
            path("/v1/tenants/{}/billing/subscription", tenant_id),
            json={"plan_code": plan_code, "currency": currency},
            request_options=request_options,
        )

    async def cancel_subscription(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> SubscriptionCancellation:
        """End the subscription at the end of the current period."""
        return await self._request(
            "POST", path("/v1/tenants/{}/billing/subscription/cancel", tenant_id), request_options=request_options
        )

    async def checkout(
        self,
        tenant_id: str,
        /,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
        **params: Unpack[CheckoutParams],
    ) -> CheckoutResult:
        """Start a checkout for a plan. Idempotent: safe to retry."""
        return await self._request(
            "POST",
            path("/v1/tenants/{}/billing/checkout", tenant_id),
            json=params,
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    async def list_invoices(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[Invoice]:
        return await self._list(path("/v1/tenants/{}/billing/invoices", tenant_id), request_options=request_options)

    async def pay_invoice(
        self,
        tenant_id: str,
        invoice_id: str,
        /,
        *,
        success_url: str,
        cancel_url: str,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> CheckoutResult:
        """Start paying an open invoice. Idempotent: safe to retry."""
        return await self._request(
            "POST",
            path("/v1/tenants/{}/billing/invoices/{}/pay", tenant_id, invoice_id),
            json={"success_url": success_url, "cancel_url": cancel_url},
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    async def get_payment_method(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> PaymentMethod | None:
        """The card or mandate on file, or ``None``."""
        body = await self._request(
            "GET", path("/v1/tenants/{}/billing/payment-method", tenant_id), request_options=request_options
        )
        return body.get("payment_method") if isinstance(body, dict) else None

    async def get_profile(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> BillingProfile:
        return await self._request(
            "GET", path("/v1/tenants/{}/billing/profile", tenant_id), request_options=request_options
        )

    async def update_profile(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **profile: Unpack[BillingProfile],
    ) -> BillingProfile:
        return await self._request(
            "PUT", path("/v1/tenants/{}/billing/profile", tenant_id), json=profile, request_options=request_options
        )

    async def get_entitlements(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> Entitlements:
        """The plan's features and limits."""
        return await self._request(
            "GET", path("/v1/tenants/{}/entitlements", tenant_id), request_options=request_options
        )

    async def get_usage(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> dict[str, int]:
        """How much of each limit is used."""
        body = await self._request(
            "GET", path("/v1/tenants/{}/entitlements/usage", tenant_id), request_options=request_options
        )
        usage = body.get("usage") if isinstance(body, dict) else None
        return dict(usage) if isinstance(usage, dict) else {}


class AsyncGDPRErasures(AsyncAPIResource):
    """Erasure requests (the right to be forgotten)."""

    async def create(
        self, *, tenant_id: str, user_id: str, reason: str, request_options: RequestOptions | None = None
    ) -> ErasureRequest:
        """Request a user's erasure, after a grace period."""
        return await self._request(
            "POST",
            "/v1/gdpr/purge",
            json={"tenant_id": tenant_id, "user_id": user_id, "reason": reason},
            request_options=request_options,
        )

    async def list(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[ErasureRequest]:
        return await self._list(path("/v1/tenants/{}/gdpr/purge", tenant_id), request_options=request_options)

    async def cancel(self, request_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Cancel a request still in its grace period."""
        await self._request("DELETE", path("/v1/gdpr/purge/{}", request_id), request_options=request_options)


class AsyncGDPRExports(AsyncAPIResource):
    """Data export requests (the right of access)."""

    async def create(
        self, *, tenant_id: str, user_id: str, request_options: RequestOptions | None = None
    ) -> ExportRequest:
        """Start an export. It runs in the background: poll ``get`` until ``status`` is ``ready`` or ``failed``."""
        return await self._request(
            "POST",
            "/v1/gdpr/export",
            json={"tenant_id": tenant_id, "user_id": user_id},
            request_options=request_options,
        )

    async def get(
        self, tenant_id: str, export_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ExportRequest:
        return await self._request(
            "GET", path("/v1/tenants/{}/gdpr/export/{}", tenant_id, export_id), request_options=request_options
        )

    async def list(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[ExportRequest]:
        return await self._list(path("/v1/tenants/{}/gdpr/export", tenant_id), request_options=request_options)


class AsyncGDPR(AsyncAPIResource):
    """Data-subject requests: erasure and export."""

    __slots__ = ("erasures", "exports")

    def __init__(self, transport: AsyncTransport) -> None:
        super().__init__(transport)
        self.erasures = AsyncGDPRErasures(transport)
        self.exports = AsyncGDPRExports(transport)


class AsyncEmailTemplates(AsyncAPIResource):
    """The organisation's email templates. The set is fixed; each can be overridden and reset."""

    async def list(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[EmailTemplate]:
        return await self._list(path("/v1/tenants/{}/email-templates", tenant_id), request_options=request_options)

    async def get(self, tenant_id: str, key: str, /, *, request_options: RequestOptions | None = None) -> EmailTemplate:
        return await self._request(
            "GET", path("/v1/tenants/{}/email-templates/{}", tenant_id, key), request_options=request_options
        )

    async def update(
        self,
        tenant_id: str,
        key: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **content: Unpack[EmailTemplateContent],
    ) -> EmailTemplate:
        """Save the organisation's override of a template."""
        return await self._request(
            "PUT",
            path("/v1/tenants/{}/email-templates/{}", tenant_id, key),
            json=content,
            request_options=request_options,
        )

    async def reset(
        self, tenant_id: str, key: str, /, *, request_options: RequestOptions | None = None
    ) -> EmailTemplate:
        """Discard the override, going back to the platform's default."""
        return await self._request(
            "DELETE", path("/v1/tenants/{}/email-templates/{}", tenant_id, key), request_options=request_options
        )

    async def preview(
        self,
        tenant_id: str,
        key: str,
        /,
        *,
        vars: Mapping[str, str] | None = None,
        locale: str | None = None,
        draft: EmailTemplateContent | None = None,
        request_options: RequestOptions | None = None,
    ) -> EmailTemplatePreview:
        """Render a template with ``vars``, or render unsaved ``draft`` content. Sends nothing."""
        body = {"vars": vars, "locale": locale, "draft": draft}
        return await self._request(
            "POST",
            path("/v1/tenants/{}/email-templates/{}/preview", tenant_id, key),
            json={k: v for k, v in body.items() if v is not None},
            retry_safe=True,
            request_options=request_options,
        )

    async def send_test(
        self,
        tenant_id: str,
        key: str,
        /,
        *,
        draft: EmailTemplateContent,
        locale: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> None:
        """Send a draft to the caller's own address."""
        body: dict[str, object] = {"draft": draft}
        if locale is not None:
            body["locale"] = locale
        await self._request(
            "POST",
            path("/v1/tenants/{}/email-templates/{}/test", tenant_id, key),
            json=body,
            request_options=request_options,
        )


class AsyncRetention(AsyncAPIResource):
    """The organisation's data-retention policy."""

    async def get(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> RetentionPolicy:
        return await self._request("GET", path("/v1/tenants/{}/retention", tenant_id), request_options=request_options)

    async def update(
        self,
        tenant_id: str,
        /,
        *,
        deleted_users_enabled: bool,
        deleted_users_days: int,
        request_options: RequestOptions | None = None,
    ) -> RetentionPolicy:
        """Purge soft-deleted users ``deleted_users_days`` (1 to 3650) after deletion, when enabled."""
        return await self._request(
            "PUT",
            path("/v1/tenants/{}/retention", tenant_id),
            json={"deleted_users_enabled": deleted_users_enabled, "deleted_users_days": deleted_users_days},
            request_options=request_options,
        )

    async def preview(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> RetentionPreview:
        """Count what the policy would purge now. Deletes nothing."""
        return await self._request(
            "POST",
            path("/v1/tenants/{}/retention/preview", tenant_id),
            retry_safe=True,
            request_options=request_options,
        )

    async def run(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> RetentionRun:
        """Purge what is due now, ahead of the scheduled run."""
        return await self._request(
            "POST", path("/v1/tenants/{}/retention/run", tenant_id), request_options=request_options
        )


class AsyncLogSinks(AsyncAPIResource):
    """Audit-log streaming to SIEMs."""

    async def create(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[LogSinkCreateParams],
    ) -> LogSink:
        return await self._request(
            "POST", path("/v1/tenants/{}/log-sinks", tenant_id), json=params, request_options=request_options
        )

    async def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[LogSink]:
        return await self._list(path("/v1/tenants/{}/log-sinks", tenant_id), request_options=request_options)

    async def set_enabled(
        self, tenant_id: str, sink_id: str, /, enabled: bool, *, request_options: RequestOptions | None = None
    ) -> None:
        """Switch streaming to the sink on or off."""
        await self._request(
            "PATCH",
            path("/v1/tenants/{}/log-sinks/{}", tenant_id, sink_id),
            json={"enabled": enabled},
            request_options=request_options,
        )

    async def delete(self, tenant_id: str, sink_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        await self._request(
            "DELETE", path("/v1/tenants/{}/log-sinks/{}", tenant_id, sink_id), request_options=request_options
        )

    async def test(
        self, tenant_id: str, sink_id: str, /, *, request_options: RequestOptions | None = None
    ) -> LogSinkTestResult:
        """Send a test event to a saved sink."""
        return await self._request(
            "POST", path("/v1/tenants/{}/log-sinks/{}/test", tenant_id, sink_id), request_options=request_options
        )

    async def test_destination(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[LogSinkCreateParams],
    ) -> LogSinkTestResult:
        """Send a test event to a destination before saving it."""
        return await self._request(
            "POST", path("/v1/tenants/{}/log-sinks/test", tenant_id), json=params, request_options=request_options
        )


class AsyncRateLimits(AsyncAPIResource):
    """The organisation's rate limits."""

    async def get(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> TenantRateLimits:
        return await self._request(
            "GET", path("/v1/tenants/{}/rate-limits", tenant_id), request_options=request_options
        )

    async def update(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[RateLimitsUpdateParams],
    ) -> TenantRateLimits:
        """Set the buckets given; the others keep their values."""
        return await self._request(
            "PUT", path("/v1/tenants/{}/rate-limits", tenant_id), json=params, request_options=request_options
        )

    async def reset(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Go back to the platform defaults."""
        await self._request("DELETE", path("/v1/tenants/{}/rate-limits", tenant_id), request_options=request_options)
