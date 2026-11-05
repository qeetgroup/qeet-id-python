# Generated from qeet_id/_async/resources/operations.py by scripts/unasync.py. Edit that file, not this one.
"""Operations: audit log, analytics, billing, GDPR, email, retention, log sinks, rate limits (operations.yaml)."""

from collections.abc import Mapping
from typing import Literal, Unpack

from qeet_id._options import RequestOptions
from qeet_id._pagination import ListResult, Page
from qeet_id._request import path
from qeet_id._sync._resource import APIResource
from qeet_id._sync._transport import Transport
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
    "GDPR",
    "Analytics",
    "AuditAnomalies",
    "AuditLogs",
    "Billing",
    "EmailTemplates",
    "GDPRErasures",
    "GDPRExports",
    "LogSinks",
    "RateLimits",
    "Retention",
]


class AuditAnomalies(APIResource):
    """Behavioural anomalies found in the audit log."""

    def list(
        self,
        tenant_id: str,
        /,
        *,
        status: Literal["open", "resolved"] | None = None,
        limit: int | None = None,
        request_options: RequestOptions | None = None,
    ) -> ListResult[AuditAnomaly]:
        return self._list(
            path("/v1/tenants/{}/audit/anomalies", tenant_id),
            {"status": status, "limit": limit},
            request_options=request_options,
        )

    def get_summary(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> AuditAnomalySummary:
        return self._request(
            "GET", path("/v1/tenants/{}/audit/anomalies/summary", tenant_id), request_options=request_options
        )

    def resolve(self, tenant_id: str, anomaly_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        self._request(
            "POST",
            path("/v1/tenants/{}/audit/anomalies/{}/resolve", tenant_id, anomaly_id),
            request_options=request_options,
        )

    def get_settings(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> AuditAnomalySettings:
        return self._request(
            "GET", path("/v1/tenants/{}/audit/anomaly-settings", tenant_id), request_options=request_options
        )

    def update_settings(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **settings: Unpack[AuditAnomalySettings],
    ) -> AuditAnomalySettings:
        """Replace the anomaly-detection settings."""
        return self._request(
            "PUT",
            path("/v1/tenants/{}/audit/anomaly-settings", tenant_id),
            json=settings,
            request_options=request_options,
        )


class AuditLogs(APIResource):
    """The hash-chained audit log and its integrity."""

    __slots__ = ("anomalies",)

    def __init__(self, transport: Transport) -> None:
        super().__init__(transport)
        self.anomalies = AuditAnomalies(transport)
        """Behavioural anomalies found in the log."""

    def list(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None, **params: Unpack[AuditLogListParams]
    ) -> Page[AuditLogEntry]:
        """List entries, newest first. ``from_`` and ``to`` bound ``created_at``."""
        return self._paginate(path("/v1/tenants/{}/audit", tenant_id), params, request_options=request_options)

    def verify(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> AuditChainVerification:
        """Walk the whole chain now and recompute every row's hash. Changes nothing."""
        return self._request("GET", path("/v1/tenants/{}/audit/verify", tenant_id), request_options=request_options)

    def get_verification_status(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> AuditVerificationStatus:
        """The latest scheduled verification's outcome."""
        return self._request(
            "GET", path("/v1/tenants/{}/audit/verification", tenant_id), request_options=request_options
        )


class Analytics(APIResource):
    """Sign-in analytics."""

    def get_overview(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[AnalyticsOverviewParams],
    ) -> AnalyticsOverview:
        """The sign-in dashboard; a range with ``from_`` and ``to``, or ``days``, adds ``range``."""
        return self._request(
            "GET",
            path("/v1/tenants/{}/analytics/overview", tenant_id),
            query=params,
            request_options=request_options,
        )


class Billing(APIResource):
    """The organisation's Qeet ID billing: subscription, invoices and plan."""

    def get_subscription(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> Subscription:
        return self._request(
            "GET", path("/v1/tenants/{}/billing/subscription", tenant_id), request_options=request_options
        )

    def update_subscription(
        self,
        tenant_id: str,
        /,
        *,
        plan_code: str,
        currency: str,
        request_options: RequestOptions | None = None,
    ) -> Subscription:
        """Change the plan or currency."""
        return self._request(
            "PUT",
            path("/v1/tenants/{}/billing/subscription", tenant_id),
            json={"plan_code": plan_code, "currency": currency},
            request_options=request_options,
        )

    def cancel_subscription(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> SubscriptionCancellation:
        """End the subscription at the end of the current period."""
        return self._request(
            "POST", path("/v1/tenants/{}/billing/subscription/cancel", tenant_id), request_options=request_options
        )

    def checkout(
        self,
        tenant_id: str,
        /,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
        **params: Unpack[CheckoutParams],
    ) -> CheckoutResult:
        """Start a checkout for a plan. Idempotent: safe to retry."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/billing/checkout", tenant_id),
            json=params,
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    def list_invoices(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[Invoice]:
        return self._list(path("/v1/tenants/{}/billing/invoices", tenant_id), request_options=request_options)

    def pay_invoice(
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
        return self._request(
            "POST",
            path("/v1/tenants/{}/billing/invoices/{}/pay", tenant_id, invoice_id),
            json={"success_url": success_url, "cancel_url": cancel_url},
            idempotent=True,
            idempotency_key=idempotency_key,
            request_options=request_options,
        )

    def get_payment_method(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> PaymentMethod | None:
        """The card or mandate on file, or ``None``."""
        body = self._request(
            "GET", path("/v1/tenants/{}/billing/payment-method", tenant_id), request_options=request_options
        )
        return body.get("payment_method") if isinstance(body, dict) else None

    def get_profile(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> BillingProfile:
        return self._request("GET", path("/v1/tenants/{}/billing/profile", tenant_id), request_options=request_options)

    def update_profile(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **profile: Unpack[BillingProfile],
    ) -> BillingProfile:
        return self._request(
            "PUT", path("/v1/tenants/{}/billing/profile", tenant_id), json=profile, request_options=request_options
        )

    def get_entitlements(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> Entitlements:
        """The plan's features and limits."""
        return self._request("GET", path("/v1/tenants/{}/entitlements", tenant_id), request_options=request_options)

    def get_usage(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> dict[str, int]:
        """How much of each limit is used."""
        body = self._request(
            "GET", path("/v1/tenants/{}/entitlements/usage", tenant_id), request_options=request_options
        )
        usage = body.get("usage") if isinstance(body, dict) else None
        return dict(usage) if isinstance(usage, dict) else {}


class GDPRErasures(APIResource):
    """Erasure requests (the right to be forgotten)."""

    def create(
        self, *, tenant_id: str, user_id: str, reason: str, request_options: RequestOptions | None = None
    ) -> ErasureRequest:
        """Request a user's erasure, after a grace period."""
        return self._request(
            "POST",
            "/v1/gdpr/purge",
            json={"tenant_id": tenant_id, "user_id": user_id, "reason": reason},
            request_options=request_options,
        )

    def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[ErasureRequest]:
        return self._list(path("/v1/tenants/{}/gdpr/purge", tenant_id), request_options=request_options)

    def cancel(self, request_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Cancel a request still in its grace period."""
        self._request("DELETE", path("/v1/gdpr/purge/{}", request_id), request_options=request_options)


class GDPRExports(APIResource):
    """Data export requests (the right of access)."""

    def create(self, *, tenant_id: str, user_id: str, request_options: RequestOptions | None = None) -> ExportRequest:
        """Start an export. It runs in the background: poll ``get`` until ``status`` is ``ready`` or ``failed``."""
        return self._request(
            "POST",
            "/v1/gdpr/export",
            json={"tenant_id": tenant_id, "user_id": user_id},
            request_options=request_options,
        )

    def get(self, tenant_id: str, export_id: str, /, *, request_options: RequestOptions | None = None) -> ExportRequest:
        return self._request(
            "GET", path("/v1/tenants/{}/gdpr/export/{}", tenant_id, export_id), request_options=request_options
        )

    def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[ExportRequest]:
        return self._list(path("/v1/tenants/{}/gdpr/export", tenant_id), request_options=request_options)


class GDPR(APIResource):
    """Data-subject requests: erasure and export."""

    __slots__ = ("erasures", "exports")

    def __init__(self, transport: Transport) -> None:
        super().__init__(transport)
        self.erasures = GDPRErasures(transport)
        self.exports = GDPRExports(transport)


class EmailTemplates(APIResource):
    """The organisation's email templates. The set is fixed; each can be overridden and reset."""

    def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[EmailTemplate]:
        return self._list(path("/v1/tenants/{}/email-templates", tenant_id), request_options=request_options)

    def get(self, tenant_id: str, key: str, /, *, request_options: RequestOptions | None = None) -> EmailTemplate:
        return self._request(
            "GET", path("/v1/tenants/{}/email-templates/{}", tenant_id, key), request_options=request_options
        )

    def update(
        self,
        tenant_id: str,
        key: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **content: Unpack[EmailTemplateContent],
    ) -> EmailTemplate:
        """Save the organisation's override of a template."""
        return self._request(
            "PUT",
            path("/v1/tenants/{}/email-templates/{}", tenant_id, key),
            json=content,
            request_options=request_options,
        )

    def reset(self, tenant_id: str, key: str, /, *, request_options: RequestOptions | None = None) -> EmailTemplate:
        """Discard the override, going back to the platform's default."""
        return self._request(
            "DELETE", path("/v1/tenants/{}/email-templates/{}", tenant_id, key), request_options=request_options
        )

    def preview(
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
        return self._request(
            "POST",
            path("/v1/tenants/{}/email-templates/{}/preview", tenant_id, key),
            json={k: v for k, v in body.items() if v is not None},
            retry_safe=True,
            request_options=request_options,
        )

    def send_test(
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
        self._request(
            "POST",
            path("/v1/tenants/{}/email-templates/{}/test", tenant_id, key),
            json=body,
            request_options=request_options,
        )


class Retention(APIResource):
    """The organisation's data-retention policy."""

    def get(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> RetentionPolicy:
        return self._request("GET", path("/v1/tenants/{}/retention", tenant_id), request_options=request_options)

    def update(
        self,
        tenant_id: str,
        /,
        *,
        deleted_users_enabled: bool,
        deleted_users_days: int,
        request_options: RequestOptions | None = None,
    ) -> RetentionPolicy:
        """Purge soft-deleted users ``deleted_users_days`` (1 to 3650) after deletion, when enabled."""
        return self._request(
            "PUT",
            path("/v1/tenants/{}/retention", tenant_id),
            json={"deleted_users_enabled": deleted_users_enabled, "deleted_users_days": deleted_users_days},
            request_options=request_options,
        )

    def preview(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> RetentionPreview:
        """Count what the policy would purge now. Deletes nothing."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/retention/preview", tenant_id),
            retry_safe=True,
            request_options=request_options,
        )

    def run(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> RetentionRun:
        """Purge what is due now, ahead of the scheduled run."""
        return self._request("POST", path("/v1/tenants/{}/retention/run", tenant_id), request_options=request_options)


class LogSinks(APIResource):
    """Audit-log streaming to SIEMs."""

    def create(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[LogSinkCreateParams],
    ) -> LogSink:
        return self._request(
            "POST", path("/v1/tenants/{}/log-sinks", tenant_id), json=params, request_options=request_options
        )

    def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[LogSink]:
        return self._list(path("/v1/tenants/{}/log-sinks", tenant_id), request_options=request_options)

    def set_enabled(
        self, tenant_id: str, sink_id: str, /, enabled: bool, *, request_options: RequestOptions | None = None
    ) -> None:
        """Switch streaming to the sink on or off."""
        self._request(
            "PATCH",
            path("/v1/tenants/{}/log-sinks/{}", tenant_id, sink_id),
            json={"enabled": enabled},
            request_options=request_options,
        )

    def delete(self, tenant_id: str, sink_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        self._request(
            "DELETE", path("/v1/tenants/{}/log-sinks/{}", tenant_id, sink_id), request_options=request_options
        )

    def test(
        self, tenant_id: str, sink_id: str, /, *, request_options: RequestOptions | None = None
    ) -> LogSinkTestResult:
        """Send a test event to a saved sink."""
        return self._request(
            "POST", path("/v1/tenants/{}/log-sinks/{}/test", tenant_id, sink_id), request_options=request_options
        )

    def test_destination(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[LogSinkCreateParams],
    ) -> LogSinkTestResult:
        """Send a test event to a destination before saving it."""
        return self._request(
            "POST", path("/v1/tenants/{}/log-sinks/test", tenant_id), json=params, request_options=request_options
        )


class RateLimits(APIResource):
    """The organisation's rate limits."""

    def get(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> TenantRateLimits:
        return self._request("GET", path("/v1/tenants/{}/rate-limits", tenant_id), request_options=request_options)

    def update(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[RateLimitsUpdateParams],
    ) -> TenantRateLimits:
        """Set the buckets given; the others keep their values."""
        return self._request(
            "PUT", path("/v1/tenants/{}/rate-limits", tenant_id), json=params, request_options=request_options
        )

    def reset(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Go back to the platform defaults."""
        self._request("DELETE", path("/v1/tenants/{}/rate-limits", tenant_id), request_options=request_options)
