import json
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx2
import pytest

from qeet_id import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    FieldError,
    InternalServerError,
    NotFoundError,
    OAuthError,
    PaymentRequiredError,
    PermissionDeniedError,
    QeetIDError,
    RateLimitError,
    ServiceUnavailableError,
    SessionRevokedError,
    ValidationError,
)
from qeet_id._errors import error_from_response, parse_retry_after

from .conftest import envelope


def build(status: int, body: object = None, headers: dict[str, str] | None = None) -> APIError:
    content = b"" if body is None else body if isinstance(body, bytes) else json.dumps(body).encode()
    return error_from_response(status, httpx2.Headers(headers or {}), content)


@pytest.mark.parametrize(
    ("status", "code", "cls"),
    [
        (400, "bad_request", BadRequestError),
        (401, "unauthorized", AuthenticationError),
        (401, "auth.session_revoked", SessionRevokedError),
        (402, "entitlement.feature_not_in_plan", PaymentRequiredError),
        (403, "forbidden", PermissionDeniedError),
        (404, "not_found", NotFoundError),
        (409, "idempotency.outcome_unknown", ConflictError),
        (410, "gone", APIError),
        (422, "validation_failed", ValidationError),
        (429, "too_many_requests", RateLimitError),
        (500, "internal", InternalServerError),
        (501, "not_implemented", InternalServerError),
        (502, "bad_gateway", InternalServerError),
        (503, "server.overloaded", ServiceUnavailableError),
    ],
)
def test_each_status_has_its_class(status: int, code: str, cls: type[APIError]) -> None:
    error = build(status, envelope(code))
    assert type(error) is cls
    assert isinstance(error, APIError)
    assert isinstance(error, QeetIDError)
    assert (error.status, error.code, error.message, error.request_id) == (status, code, "Refused.", "req_body")


def test_session_revoked_is_an_authentication_error() -> None:
    error = build(401, envelope("auth.session_revoked", retryable=True))
    assert isinstance(error, AuthenticationError)
    assert error.retryable is True


def test_the_whole_envelope_is_read() -> None:
    error = build(
        422,
        envelope(
            "validation_failed",
            "Check the highlighted fields.",
            detail="email: invalid",
            translation_key="errors.validation_failed",
            fields=[{"field": "email", "code": "invalid_email", "message": "Must be a valid email address."}, "x"],
            metadata={"remaining_attempts": 2},
        ),
        {"X-Request-Id": "req_header"},
    )
    assert isinstance(error, ValidationError)
    assert error.detail == "email: invalid"
    assert error.translation_key == "errors.validation_failed"
    assert error.fields == (FieldError("email", "invalid_email", "Must be a valid email address."),)
    assert error.metadata == {"remaining_attempts": 2}
    assert error.request_id == "req_body"  # the server's own ID wins over a header a proxy may set
    assert error.headers["x-request-id"] == "req_header"
    assert error.retryable is False


def test_request_id_falls_back_to_the_header() -> None:
    error = build(500, {"error": {"code": "internal", "message": "Boom."}}, {"X-Request-Id": "req_header"})
    assert error.request_id == "req_header"


def test_a_body_that_isnt_an_envelope_still_maps_by_status() -> None:
    error = build(502, b"<html>Bad gateway</html>")
    assert isinstance(error, InternalServerError)
    assert error.code == "http_502"
    assert error.message == "The request failed with HTTP status 502."
    assert error.request_id is None
    assert error.fields == ()


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (400, {"error": "invalid_grant", "error_description": "The code has expired."}, "invalid_grant"),
        (401, {"error": "invalid_client", "error_description": "Unknown client."}, "invalid_client"),
        (400, {"error": "authorization_pending"}, "authorization_pending"),
        (400, {"error": "slow_down"}, "slow_down"),
    ],
)
def test_oauth_errors_keep_their_rfc_6749_shape(status: int, body: dict[str, str], expected: str) -> None:
    error = build(status, {**body, "error_uri": "https://docs.qeet.in/oauth"})
    assert isinstance(error, OAuthError)
    assert error.status == status
    assert error.code == error.error == expected
    assert error.error_description == body.get("error_description")
    assert error.message == body.get("error_description", expected)
    assert error.error_uri == "https://docs.qeet.in/oauth"


def test_retry_after_comes_from_the_header_or_the_metadata() -> None:
    assert build(429, envelope("too_many_requests"), {"Retry-After": "7"}).retry_after == 7.0
    assert build(503, envelope("server.overloaded", metadata={"retry_after": 2})).retry_after == 2.0
    assert build(503, envelope("server.overloaded", metadata={"retry_after": True})).retry_after is None
    assert build(429, envelope("too_many_requests")).retry_after is None


def test_retry_after_reads_seconds_and_http_dates() -> None:
    now = datetime(2026, 11, 5, 9, 30, tzinfo=UTC)
    later = format_datetime(now + timedelta(seconds=12), usegmt=True)
    assert parse_retry_after("12") == 12.0
    assert parse_retry_after(later, now=now.timestamp()) == 12.0
    assert parse_retry_after(format_datetime(now - timedelta(seconds=5), usegmt=True), now=now.timestamp()) == 0.0
    assert parse_retry_after(None) is None
    assert parse_retry_after(" ") is None
    assert parse_retry_after("soon") is None
    assert parse_retry_after("-3") is None


def test_text_names_status_code_and_request() -> None:
    error = build(404, envelope("user.not_found", "No such user."))
    assert str(error) == "404 user.not_found: No such user. (request req_body)"
    assert repr(error) == (
        "NotFoundError(status=404, code='user.not_found', message='No such user.', request_id='req_body')"
    )
    assert str(build(404, {"error": {"code": "not_found", "message": "Gone."}})) == "404 not_found: Gone."
    assert repr(QeetIDError("Broken.", code="x")) == "QeetIDError(code='x', message='Broken.')"
