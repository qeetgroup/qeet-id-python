import logging
import re
from typing import Any

import httpx2
import pytest

from qeet_id import (
    APIError,
    ConflictError,
    InternalServerError,
    NetworkError,
    QeetIDError,
    RateLimitError,
    RequestOptions,
    RequestTimeoutError,
    ServiceUnavailableError,
    SessionRevokedError,
)
from qeet_id._request import HTTPMethod, QueryValue, Request, check_idempotency_key, path
from qeet_id._retry import is_retryable, retry_delay

from .conftest import Client, Kind, MockAPI, envelope, run

pytestmark = pytest.mark.anyio

UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


async def send(
    client: Client,
    method: HTTPMethod = "GET",
    url_path: str = "/v1/things",
    *,
    idempotency_key: str | None = None,
    request_options: RequestOptions | None = None,
    query: dict[str, QueryValue] | None = None,
    **fields: Any,
) -> Any:
    request = Request(method=method, path=url_path, query=query, **fields)
    return await run(
        client._transport.request(request, idempotency_key=idempotency_key, request_options=request_options)
    )


# ---------------------------------------------------------------------------
# What goes on the wire


async def test_headers_identify_and_authenticate(api: MockAPI, kind: Kind) -> None:
    client = api.client(kind, default_headers={"X-Team": "billing"}, app_info={"name": "brightleaf"})
    assert await send(client, request_options={"headers": {"traceparent": "00-abc-def-01"}}) == {}
    headers = api.last.headers
    assert headers["authorization"] == "ApiKey qk_test_key"
    assert headers["accept"] == "application/json"
    assert headers["user-agent"].startswith("brightleaf qeet-id-python/")
    assert headers["x-team"] == "billing"
    assert headers["traceparent"] == "00-abc-def-01"
    assert "content-type" not in headers
    assert "idempotency-key" not in headers


async def test_per_call_headers_cant_replace_the_sdks(api: MockAPI, kind: Kind) -> None:
    with pytest.raises(ValueError, match="sets it itself"):
        await send(api.client(kind), request_options={"headers": {"Authorization": "Bearer stolen"}})
    assert api.requests == []


async def test_json_body_and_query(api: MockAPI, kind: Kind) -> None:
    await send(
        api.client(kind),
        "POST",
        query={"q": "meera", "mfa": True, "verified": False, "tags": ["a", "b"], "skip": None, "from_": "2026-11-01"},
        json={"display_name": "Meera Iyer", "phone": None},
    )
    assert api.last.method == "POST"
    assert api.last.query == [
        ("q", "meera"),
        ("mfa", "true"),
        ("verified", "false"),
        ("tags", "a"),
        ("tags", "b"),
        ("from", "2026-11-01"),
    ]
    assert api.last.headers["content-type"] == "application/json"
    assert api.last.json == {"display_name": "Meera Iyer", "phone": None}


async def test_form_and_raw_bodies(api: MockAPI, kind: Kind) -> None:
    client = api.client(kind)
    await send(client, "POST", form={"grant_type": "client_credentials", "scope": None, "x": "a b&c"})
    assert api.last.headers["content-type"] == "application/x-www-form-urlencoded"
    assert api.last.content == b"grant_type=client_credentials&x=a+b%26c"
    await send(client, "POST", content=b'{"a":1}\n', content_type="application/x-ndjson")
    assert api.last.headers["content-type"] == "application/x-ndjson"
    assert api.last.content == b'{"a":1}\n'


async def test_unauthenticated_calls_send_no_credential(api: MockAPI, kind: Kind) -> None:
    await send(api.client(kind), "POST", authenticate=False)
    assert "authorization" not in api.last.headers


async def test_oauth_client_authentication_is_basic_and_form_encoded(api: MockAPI, kind: Kind) -> None:
    await send(api.client(kind), "POST", client_auth=("app 1", "s3cr:t+/="))
    # RFC 6749 §2.3.1: form-encode each part, then Basic-encode.
    assert api.last.headers["authorization"] == "Basic YXBwKzE6czNjciUzQXQlMkIlMkYlM0Q="


async def test_a_call_needing_credentials_fails_without_any(api: MockAPI, kind: Kind) -> None:
    client = api.client(kind, api_key=None)
    with pytest.raises(QeetIDError) as caught:
        await send(client)
    assert caught.value.code == "missing_credentials"
    assert api.requests == []


async def test_empty_and_no_content_answers_are_none(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 204}, {"status": 200, "content": b""})
    client = api.client(kind)
    assert await send(client, "DELETE") is None
    assert await send(client) is None


async def test_an_answer_that_isnt_json_is_an_error(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 200, "content": b"<html>", "headers": {"X-Request-Id": "req_1"}})
    with pytest.raises(APIError) as caught:
        await send(api.client(kind))
    assert (caught.value.code, caught.value.status, caught.value.request_id) == ("invalid_response", 200, "req_1")


async def test_redirects_are_not_followed(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 302, "headers": {"Location": "https://elsewhere.example/steal"}})
    with pytest.raises(APIError) as caught:
        await send(api.client(kind))
    assert caught.value.status == 302
    assert len(api.requests) == 1


async def test_network_failures_are_typed_and_chained(api: MockAPI, kind: Kind) -> None:
    api.answer(httpx2.ConnectError("connection refused"))
    with pytest.raises(NetworkError) as caught:
        await send(api.client(kind, max_retries=0))
    assert caught.value.code == "network_error"
    assert isinstance(caught.value.__cause__, httpx2.ConnectError)
    assert not isinstance(caught.value, RequestTimeoutError)


async def test_timeouts_are_typed(api: MockAPI, kind: Kind) -> None:
    api.answer(httpx2.ReadTimeout("read timed out"))
    with pytest.raises(RequestTimeoutError) as caught:
        await send(api.client(kind, max_retries=0))
    assert caught.value.code == "timeout"
    assert isinstance(caught.value, NetworkError)


async def test_per_call_options_are_checked(api: MockAPI, kind: Kind) -> None:
    client = api.client(kind)
    with pytest.raises(ValueError, match="timeout"):
        await send(client, request_options={"timeout": -1})
    with pytest.raises(ValueError, match="max_retries"):
        await send(client, request_options={"max_retries": -1})


async def test_logs_hold_no_secret_query_or_body(api: MockAPI, kind: Kind, caplog: pytest.LogCaptureFixture) -> None:
    api.answer({"status": 503, "json": envelope("server.overloaded")}, {"json": {}})
    caplog.set_level(logging.DEBUG, logger="qeet_id")
    await send(api.client(kind), query={"q": "meera@brightleaffoods.in"}, json={"password": "hunter2-secret"})
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "GET /v1/things -> 503" in text
    assert "retrying GET /v1/things" in text
    for secret in ("qk_test_key", "meera@brightleaffoods.in", "hunter2-secret"):
        assert secret not in text


# ---------------------------------------------------------------------------
# Retries


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
async def test_safe_requests_are_retried_after_transient_failures(
    api: MockAPI, kind: Kind, status: int, sleeps: list[float]
) -> None:
    api.answer({"status": status, "json": envelope("x")}, {"json": {"ok": True}})
    assert await send(api.client(kind)) == {"ok": True}
    assert len(api.requests) == 2
    assert len(sleeps) == 1
    assert 0.25 <= sleeps[0] <= 0.5


async def test_retries_stop_at_max_retries(api: MockAPI, kind: Kind, sleeps: list[float]) -> None:
    api.answer({"status": 500, "json": envelope("internal")})
    with pytest.raises(InternalServerError):
        await send(api.client(kind, max_retries=3))
    assert len(api.requests) == 4
    for delay, bound in zip(sleeps, (0.5, 1.0, 2.0), strict=True):
        assert bound / 2 <= delay <= bound


async def test_per_call_max_retries_overrides_the_client(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 500, "json": envelope("internal")})
    with pytest.raises(InternalServerError):
        await send(api.client(kind), request_options={"max_retries": 0})
    assert len(api.requests) == 1


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH"])
async def test_writes_are_not_retried(api: MockAPI, kind: Kind, method: HTTPMethod) -> None:
    api.answer({"status": 503, "json": envelope("server.overloaded")})
    with pytest.raises(ServiceUnavailableError):
        await send(api.client(kind), method, json={})
    assert len(api.requests) == 1


async def test_writes_are_not_retried_after_a_network_failure(api: MockAPI, kind: Kind) -> None:
    api.answer(httpx2.ConnectError("reset"))
    with pytest.raises(NetworkError):
        await send(api.client(kind), "POST", json={})
    assert len(api.requests) == 1


async def test_reads_are_retried_after_network_failures_and_timeouts(api: MockAPI, kind: Kind) -> None:
    api.answer(httpx2.ConnectError("reset"), httpx2.ReadTimeout("slow"), {"json": {"ok": 1}})
    assert await send(api.client(kind)) == {"ok": 1}
    assert len(api.requests) == 3


async def test_retry_safe_posts_are_retried(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 502}, {"json": {"allowed": True}})
    assert await send(api.client(kind), "POST", json={}, retry_safe=True) == {"allowed": True}
    assert len(api.requests) == 2


async def test_calls_that_must_not_repeat_are_never_retried(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 503})
    with pytest.raises(ServiceUnavailableError):
        await send(api.client(kind), "POST", retry_safe=True, retries=False)
    assert len(api.requests) == 1


async def test_session_revoked_is_never_retried(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 401, "json": envelope("auth.session_revoked", retryable=True)})
    with pytest.raises(SessionRevokedError):
        await send(api.client(kind))
    assert len(api.requests) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
async def test_client_errors_are_not_retried(api: MockAPI, kind: Kind, status: int) -> None:
    api.answer({"status": status, "json": envelope("x")})
    with pytest.raises(APIError):
        await send(api.client(kind))
    assert len(api.requests) == 1


async def test_retry_after_is_honoured(api: MockAPI, kind: Kind, sleeps: list[float]) -> None:
    api.answer({"status": 429, "json": envelope("too_many_requests"), "headers": {"Retry-After": "3"}}, {"json": {}})
    await send(api.client(kind))
    assert sleeps == [3.0]


async def test_a_long_retry_after_is_raised_not_waited(api: MockAPI, kind: Kind, sleeps: list[float]) -> None:
    api.answer({"status": 429, "json": envelope("too_many_requests"), "headers": {"Retry-After": "120"}})
    with pytest.raises(RateLimitError) as caught:
        await send(api.client(kind))
    assert caught.value.retry_after == 120.0
    assert sleeps == []
    assert len(api.requests) == 1


# ---------------------------------------------------------------------------
# Idempotency keys


async def test_idempotent_calls_send_a_generated_key_kept_across_retries(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 503, "json": envelope("server.overloaded")}, {"status": 201, "json": {"id": "u1"}})
    assert await send(api.client(kind), "POST", json={"email": "a@b.in"}, idempotent=True) == {"id": "u1"}
    keys = [request.headers["idempotency-key"] for request in api.requests]
    assert len(keys) == 2
    assert UUID4.match(keys[0])
    assert keys[0] == keys[1]


async def test_each_call_gets_its_own_key(api: MockAPI, kind: Kind) -> None:
    client = api.client(kind)
    await send(client, "POST", idempotent=True)
    await send(client, "POST", idempotent=True)
    assert api.requests[0].headers["idempotency-key"] != api.requests[1].headers["idempotency-key"]


async def test_a_callers_key_is_sent(api: MockAPI, kind: Kind) -> None:
    await send(api.client(kind), "POST", idempotent=True, idempotency_key="onboarding-42")
    assert api.last.headers["idempotency-key"] == "onboarding-42"


async def test_in_progress_is_retried_only_with_a_key(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 409, "json": envelope("idempotency.in_progress")}, {"status": 201, "json": {}})
    await send(api.client(kind), "POST", idempotent=True)
    assert len(api.requests) == 2

    other = MockAPI().answer({"status": 409, "json": envelope("idempotency.outcome_unknown")})
    with pytest.raises(ConflictError):
        await send(other.client(kind), "POST", idempotent=True)
    assert len(other.requests) == 1


async def test_idempotency_key_is_refused_where_the_api_ignores_it(api: MockAPI, kind: Kind) -> None:
    with pytest.raises(TypeError, match="idempotency_key"):
        await send(api.client(kind), "POST", idempotency_key="k1")
    assert api.requests == []


@pytest.mark.parametrize("key", ["", "has space", "x" * 256, "naïve", 42])
def test_malformed_idempotency_keys_are_refused(key: object) -> None:
    with pytest.raises(ValueError, match="idempotency_key"):
        check_idempotency_key(key)


def test_the_longest_key_is_accepted() -> None:
    assert check_idempotency_key("~" * 255) == "~" * 255


# ---------------------------------------------------------------------------
# The policy as pure functions


def test_backoff_doubles_with_equal_jitter_up_to_a_cap() -> None:
    error = InternalServerError("x", status=500, code="internal")
    assert [retry_delay(n, error, rand=lambda: 0.0) for n in range(6)] == [0.25, 0.5, 1.0, 2.0, 4.0, 4.0]
    assert [retry_delay(n, error, rand=lambda: 1.0) for n in range(6)] == [0.5, 1.0, 2.0, 4.0, 8.0, 8.0]
    assert retry_delay(1000, error, rand=lambda: 1.0) == 8.0


def test_retry_after_overrides_backoff() -> None:
    error = RateLimitError("x", status=429, code="too_many_requests", retry_after=0)
    assert retry_delay(3, error) == 0.0
    assert retry_delay(0, RateLimitError("x", status=429, code="t", retry_after=61)) is None


def test_only_transient_failures_are_retryable() -> None:
    assert is_retryable(NetworkError("x"), retry_safe=True)
    assert not is_retryable(NetworkError("x"), retry_safe=False)
    assert not is_retryable(ValueError("x"), retry_safe=True)
    assert not is_retryable(APIError("x", status=401, code="unauthorized", retryable=True), retry_safe=True)


# ---------------------------------------------------------------------------
# Paths


def test_paths_encode_each_identifier_as_one_segment() -> None:
    assert path("/v1/users/{}/sessions", "u/1?x") == "/v1/users/u%2F1%3Fx/sessions"
    assert path("/v1/tenants/{}/roles/{}", "t 1", "r%1") == "/v1/tenants/t%201/roles/r%251"


@pytest.mark.parametrize("bad", ["", " ", ".", ".."])
def test_paths_refuse_empty_and_dot_identifiers(bad: str) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        path("/v1/users/{}", bad)


def test_paths_refuse_non_strings_and_wrong_counts() -> None:
    with pytest.raises(TypeError):
        path("/v1/users/{}", 42)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="needs 2"):
        path("/v1/tenants/{}/users/{}", "t1")
