"""The exception hierarchy, and the mapping from an error response to it.

Every exception the SDK raises on purpose is a :class:`QeetIDError`; mistakes in
the caller's own arguments are ``ValueError`` or ``TypeError``::

    QeetIDError
    ├── APIError                        the API answered with an error
    │   ├── BadRequestError             400
    │   ├── AuthenticationError         401
    │   │   └── SessionRevokedError     401 auth.session_revoked
    │   ├── PaymentRequiredError        402
    │   ├── PermissionDeniedError       403
    │   ├── NotFoundError               404
    │   ├── ConflictError               409
    │   ├── ValidationError             422
    │   ├── RateLimitError              429
    │   ├── InternalServerError         5xx
    │   │   └── ServiceUnavailableError 503
    │   └── OAuthError                  an RFC 6749 error answer
    ├── NetworkError                    no response: DNS, TCP, TLS, reset
    │   └── RequestTimeoutError         no response in time
    ├── WebhookVerificationError        a webhook delivery failed verification
    └── TokenVerificationError          an access token failed verification
"""

import json
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Literal

__all__ = [
    "SESSION_REVOKED",
    "APIError",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "FieldError",
    "InternalServerError",
    "NetworkError",
    "NotFoundError",
    "OAuthError",
    "OAuthErrorCode",
    "PaymentRequiredError",
    "PermissionDeniedError",
    "QeetIDError",
    "RateLimitError",
    "RequestTimeoutError",
    "ServiceUnavailableError",
    "SessionRevokedError",
    "TokenVerificationError",
    "TokenVerificationErrorCode",
    "ValidationError",
    "WebhookVerificationError",
    "WebhookVerificationErrorCode",
    "error_from_response",
    "parse_retry_after",
]

SESSION_REVOKED = "auth.session_revoked"
"""The code the API answers with when the session behind a token has ended."""


class QeetIDError(Exception):
    """The base class of every exception the SDK raises on purpose.

    Attributes:
        code: A stable, machine-readable code. Branch on it, never on ``message``.
        message: A human-readable explanation.
    """

    code: str
    message: str

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


@dataclass(frozen=True, slots=True)
class FieldError:
    """One field the API refused in a ``422 validation_failed`` answer.

    Attributes:
        field: The field, as the API names it (snake_case).
        code: Why, as a stable code: ``required``, ``invalid_email``, ``too_short``, ``too_long``,
            ``invalid_uuid``, ``invalid_url``, ``not_allowed``, ``invalid_phone`` or ``invalid``.
        message: A message safe to show a person.
    """

    field: str
    code: str
    message: str


class APIError(QeetIDError):
    """The API answered with an error.

    Carries the error envelope (``{"error": {"code", "message", "detail", "fields",
    "metadata", "retryable", "request_id"}}``) and the HTTP status and headers.
    Quote ``request_id`` when you contact support.

    Attributes:
        status: The HTTP status code.
        request_id: The server's ID for the request, when it gave one.
        detail: Developer-facing context, when the server gave any. Never localised.
        translation_key: The key a client may localise ``message`` with.
        fields: Per-field problems, on a ``422 validation_failed``; empty otherwise.
        metadata: Structured, error-specific context, such as ``{"retry_after": 2}``.
        retryable: The server's hint that the action may succeed if tried again,
            possibly after signing in again. Advice only: the SDK retries by its own rules.
        retry_after: Seconds to wait before trying again, from ``Retry-After`` or the
            envelope's ``metadata.retry_after``; on 429 and 503.
        headers: The response headers.
    """

    status: int
    request_id: str | None
    detail: str | None
    translation_key: str | None
    fields: tuple[FieldError, ...]
    metadata: Mapping[str, Any]
    retryable: bool
    retry_after: float | None
    headers: Mapping[str, str]

    def __init__(
        self,
        message: str,
        *,
        status: int,
        code: str,
        request_id: str | None = None,
        detail: str | None = None,
        translation_key: str | None = None,
        fields: Sequence[FieldError] = (),
        metadata: Mapping[str, Any] | None = None,
        retryable: bool = False,
        retry_after: float | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.status = status
        self.request_id = request_id
        self.detail = detail
        self.translation_key = translation_key
        self.fields = tuple(fields)
        self.metadata = dict(metadata or {})
        self.retryable = retryable
        self.retry_after = retry_after
        self.headers = headers if headers is not None else {}

    def __str__(self) -> str:
        text = f"{self.status} {self.code}: {self.message}"
        return f"{text} (request {self.request_id})" if self.request_id else text

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(status={self.status!r}, code={self.code!r}, "
            f"message={self.message!r}, request_id={self.request_id!r})"
        )


class BadRequestError(APIError):
    """400: the request was malformed."""


class AuthenticationError(APIError):
    """401: the credential is missing, wrong, expired or revoked."""


class SessionRevokedError(AuthenticationError):
    """401 ``auth.session_revoked``: the session behind the token has ended.

    Signed out, revoked by an administrator, or timed out. Never retried: sign in again instead.
    """


class PaymentRequiredError(APIError):
    """402: the organisation's plan doesn't include this, or one of its limits is reached."""


class PermissionDeniedError(APIError):
    """403: the credential is valid but may not do this."""


class NotFoundError(APIError):
    """404: there is no such resource, or the credential may not see it."""


class ConflictError(APIError):
    """409: the request conflicts with the resource's state, or an idempotency key is in use."""


class ValidationError(APIError):
    """422: the request was well formed but refused; see ``fields``."""


class RateLimitError(APIError):
    """429: too many requests. Wait ``retry_after`` seconds before trying again."""


class InternalServerError(APIError):
    """5xx: the server failed."""


class ServiceUnavailableError(InternalServerError):
    """503: the server is overloaded (``server.overloaded``). Wait ``retry_after`` seconds."""


OAuthErrorCode = Literal[
    "invalid_request",
    "invalid_client",
    "invalid_grant",
    "unauthorized_client",
    "unsupported_grant_type",
    "unsupported_token_type",
    "invalid_scope",
    "invalid_target",
    "authorization_pending",
    "slow_down",
    "access_denied",
    "expired_token",
]
"""The RFC 6749 §5.2, RFC 7009, RFC 8628 §3.5 and RFC 8707 error codes the OAuth endpoints answer with."""


class OAuthError(APIError):
    """An OAuth endpoint refused the request, answering in the RFC 6749 §5.2 shape.

    ``code`` is the RFC ``error`` (such as ``invalid_grant``) and ``message`` its
    description. ``status`` is 401 for ``invalid_client`` and 400 otherwise.

    Attributes:
        error: The RFC 6749 ``error`` value; the same as ``code``.
        error_description: The RFC 6749 ``error_description``, when the server gave one.
        error_uri: The RFC 6749 ``error_uri``, when the server gave one.
    """

    error: OAuthErrorCode | str
    error_description: str | None
    error_uri: str | None

    def __init__(
        self,
        *,
        status: int,
        error: str,
        error_description: str | None = None,
        error_uri: str | None = None,
        request_id: str | None = None,
        retry_after: float | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(
            error_description or error,
            status=status,
            code=error,
            request_id=request_id,
            retry_after=retry_after,
            headers=headers,
        )
        self.error = error
        self.error_description = error_description
        self.error_uri = error_uri


class NetworkError(QeetIDError):
    """The request got no response: DNS, connection, TLS, or a reset. The cause is chained."""

    def __init__(self, message: str, *, code: str = "network_error") -> None:
        super().__init__(message, code=code)


class RequestTimeoutError(NetworkError):
    """The request got no response within the timeout."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="timeout")


WebhookVerificationErrorCode = Literal[
    "missing_secret",
    "missing_signature",
    "missing_timestamp",
    "invalid_timestamp",
    "timestamp_outside_tolerance",
    "invalid_signature_header",
    "signature_mismatch",
    "invalid_payload",
]
"""Why a webhook delivery was refused."""


class WebhookVerificationError(QeetIDError):
    """A webhook delivery failed verification. Answer it with a 400 and don't act on it."""

    code: WebhookVerificationErrorCode

    def __init__(self, code: WebhookVerificationErrorCode, message: str) -> None:
        super().__init__(message, code=code)


TokenVerificationErrorCode = Literal[
    "malformed_token",
    "unsupported_algorithm",
    "unknown_key",
    "invalid_signature",
    "token_expired",
    "token_not_yet_valid",
    "invalid_issuer",
    "invalid_audience",
    "jwks_unavailable",
]
"""Why an access token was refused."""


class TokenVerificationError(QeetIDError):
    """An access token failed local verification. Treat the caller as unauthenticated."""

    code: TokenVerificationErrorCode

    def __init__(self, code: TokenVerificationErrorCode, message: str) -> None:
        super().__init__(message, code=code)


def parse_retry_after(value: str | None, *, now: float | None = None) -> float | None:
    """Read ``Retry-After`` (delta-seconds or an HTTP date) as seconds; ``None`` when absent or unreadable."""
    if value is None or not value.strip():
        return None
    text = value.strip()
    if text.isdigit():
        return float(int(text))
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
    if when.tzinfo is None:
        return None
    seconds = when.timestamp() - (time.time() if now is None else now)
    return float(max(0, math.ceil(seconds)))


def error_from_response(status: int, headers: Mapping[str, str], content: bytes) -> APIError:
    """Build the typed exception for a failed response from its status, headers and body."""
    parsed = _parse_json(content)
    header_request_id = headers.get("x-request-id") or None
    retry_after = parse_retry_after(headers.get("retry-after"))
    body = parsed if isinstance(parsed, dict) else {}
    error_field = body.get("error")

    if isinstance(error_field, str) and error_field:
        # RFC 6749 §5.2: {"error": "invalid_grant", "error_description": "..."}
        return OAuthError(
            status=status,
            error=error_field,
            error_description=_str_or_none(body.get("error_description")),
            error_uri=_str_or_none(body.get("error_uri")),
            request_id=header_request_id,
            retry_after=retry_after,
            headers=headers,
        )

    envelope: dict[str, Any] = error_field if isinstance(error_field, dict) else {}
    metadata = envelope.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    if retry_after is None:
        hinted = metadata.get("retry_after")
        if isinstance(hinted, int | float) and not isinstance(hinted, bool) and hinted >= 0:
            retry_after = float(hinted)
    raw_fields = envelope.get("fields")
    fields = [_field_error(f) for f in raw_fields if isinstance(f, dict)] if isinstance(raw_fields, list) else []
    code = _str_or_none(envelope.get("code")) or f"http_{status}"
    kwargs: dict[str, Any] = {
        "status": status,
        "code": code,
        # The envelope's request ID is the server's own; a proxy may set the header.
        "request_id": _str_or_none(envelope.get("request_id")) or header_request_id,
        "detail": _str_or_none(envelope.get("detail")),
        "translation_key": _str_or_none(envelope.get("translation_key")),
        "fields": fields,
        "metadata": metadata,
        "retryable": envelope.get("retryable") is True,
        "retry_after": retry_after,
        "headers": headers,
    }
    message = _str_or_none(envelope.get("message")) or f"The request failed with HTTP status {status}."
    cls: type[APIError]
    if status == 401:
        cls = SessionRevokedError if code == SESSION_REVOKED else AuthenticationError
    else:
        cls = _STATUS_CLASSES.get(status) or (InternalServerError if status >= 500 else APIError)
    return cls(message, **kwargs)


_STATUS_CLASSES: dict[int, type[APIError]] = {
    400: BadRequestError,
    402: PaymentRequiredError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    422: ValidationError,
    429: RateLimitError,
    503: ServiceUnavailableError,
}


def _parse_json(content: bytes) -> object:
    if not content:
        return None
    try:
        return json.loads(content)
    except ValueError:
        return None  # a proxy's HTML page, say: the status still tells the story


def _str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _field_error(value: dict[str, Any]) -> FieldError:
    return FieldError(
        field=_str_or_none(value.get("field")) or "",
        code=_str_or_none(value.get("code")) or "invalid",
        message=_str_or_none(value.get("message")) or "",
    )
