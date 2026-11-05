"""The server-side Python SDK for Qeet ID.

::

    from qeet_id import QeetID

    client = QeetID(api_key=os.environ["QEET_ID_API_KEY"])
    for user in client.users.list(status="active"):
        print(user["email"])

``AsyncQeetID`` is the same client for ``asyncio`` and trio. Request and
response types are in :mod:`qeet_id.types`; webhook verification is in
:mod:`qeet_id.webhooks`.
"""

from qeet_id._async._client import AsyncQeetID
from qeet_id._constants import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from qeet_id._errors import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    FieldError,
    InternalServerError,
    NetworkError,
    NotFoundError,
    OAuthError,
    OAuthErrorCode,
    PaymentRequiredError,
    PermissionDeniedError,
    QeetIDError,
    RateLimitError,
    RequestTimeoutError,
    ServiceUnavailableError,
    SessionRevokedError,
    TokenVerificationError,
    TokenVerificationErrorCode,
    ValidationError,
    WebhookVerificationError,
    WebhookVerificationErrorCode,
)
from qeet_id._options import AppInfo, RequestOptions
from qeet_id._pagination import AsyncPage, AsyncPaginator, ListResult, Page
from qeet_id._sync._client import QeetID
from qeet_id._version import __version__
from qeet_id.webhooks import (
    WebhookEvent,
    construct_webhook_event,
    sign_webhook_payload,
    verify_webhook_signature,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "APIError",
    "AppInfo",
    "AsyncPage",
    "AsyncPaginator",
    "AsyncQeetID",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "FieldError",
    "InternalServerError",
    "ListResult",
    "NetworkError",
    "NotFoundError",
    "OAuthError",
    "OAuthErrorCode",
    "Page",
    "PaymentRequiredError",
    "PermissionDeniedError",
    "QeetID",
    "QeetIDError",
    "RateLimitError",
    "RequestOptions",
    "RequestTimeoutError",
    "ServiceUnavailableError",
    "SessionRevokedError",
    "TokenVerificationError",
    "TokenVerificationErrorCode",
    "ValidationError",
    "WebhookEvent",
    "WebhookVerificationError",
    "WebhookVerificationErrorCode",
    "__version__",
    "construct_webhook_event",
    "sign_webhook_payload",
    "verify_webhook_signature",
]
