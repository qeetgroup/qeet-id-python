import hashlib
import hmac
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from qeet_id import WebhookVerificationError
from qeet_id.webhooks import (
    DEFAULT_WEBHOOK_TOLERANCE,
    TEST_WEBHOOK_EVENT,
    WEBHOOK_EVENT_TYPES,
    WEBHOOK_HEADERS,
    construct_webhook_event,
    sign_webhook_payload,
    verify_webhook_signature,
)

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "webhook_deliveries.json").read_text())["deliveries"]
DELIVERY = FIXTURES[0]
ROTATION = FIXTURES[1]
SIGNED_AT = int(DELIVERY["headers"]["X-Qeet-Timestamp"])


def code_of(call: Any) -> str:
    with pytest.raises(WebhookVerificationError) as caught:
        call()
    return caught.value.code


@pytest.mark.parametrize("delivery", FIXTURES, ids=[d["name"] for d in FIXTURES])
def test_deliveries_signed_by_the_server_verify(delivery: dict[str, Any]) -> None:
    body = delivery["body"].encode("utf-8")
    now = int(delivery["headers"]["X-Qeet-Timestamp"])
    event = construct_webhook_event(body, delivery["headers"], delivery["signed_with"], now=now)
    assert event == json.loads(body)
    assert event["type"] == delivery["headers"]["X-Qeet-Event"]


def test_the_fixture_signature_is_the_documented_hmac() -> None:
    # An independent recomputation: HMAC-SHA256(secret, timestamp + "." + body).
    digest = hmac.new(
        DELIVERY["signed_with"][0].encode(),
        f"{SIGNED_AT}.{DELIVERY['body']}".encode(),
        hashlib.sha256,
    ).hexdigest()
    assert DELIVERY["headers"]["X-Qeet-Signature"] == f"sha256={digest}"


@pytest.mark.parametrize("secret", ROTATION["signed_with"])
def test_either_secret_verifies_during_a_rotation(secret: str) -> None:
    event = construct_webhook_event(ROTATION["body"], ROTATION["headers"], secret, now=SIGNED_AT)
    assert event["type"] == TEST_WEBHOOK_EVENT
    assert event["data"] == {"subscription_id": "e1f2a3b4-c5d6-4e7f-8a9b-0c1d2e3f4a5b"}


def test_any_of_several_secrets_verifies() -> None:
    secrets = ["wrong-one", DELIVERY["signed_with"][0], ""]
    construct_webhook_event(DELIVERY["body"], DELIVERY["headers"], secrets, now=SIGNED_AT)


def test_payload_may_be_bytes_bytearray_memoryview_or_text() -> None:
    body = DELIVERY["body"]
    for payload in (body, body.encode(), bytearray(body.encode()), memoryview(body.encode())):
        construct_webhook_event(payload, DELIVERY["headers"], DELIVERY["signed_with"], now=SIGNED_AT)


def test_a_parsed_body_is_refused() -> None:
    with pytest.raises(TypeError, match="raw request body"):
        construct_webhook_event(json.loads(DELIVERY["body"]), DELIVERY["headers"], "s", now=SIGNED_AT)


def test_headers_are_found_whatever_their_case() -> None:
    lower = {k.lower(): v for k, v in DELIVERY["headers"].items()}
    upper = {k.upper(): v for k, v in DELIVERY["headers"].items()}
    for headers in (lower, upper):
        construct_webhook_event(DELIVERY["body"], headers, DELIVERY["signed_with"], now=SIGNED_AT)


def test_a_header_given_as_a_list_is_joined() -> None:
    headers: dict[str, Any] = dict(ROTATION["headers"])
    headers["X-Qeet-Signature"] = headers["X-Qeet-Signature"].split(",")
    construct_webhook_event(ROTATION["body"], headers, ROTATION["signed_with"][1], now=SIGNED_AT)


def test_a_wrong_secret_is_refused() -> None:
    call = lambda: construct_webhook_event(DELIVERY["body"], DELIVERY["headers"], "not-the-secret", now=SIGNED_AT)  # noqa: E731
    assert code_of(call) == "signature_mismatch"


def test_a_changed_byte_is_refused() -> None:
    tampered = DELIVERY["body"].replace("admin", "admiN")
    call = lambda: construct_webhook_event(tampered, DELIVERY["headers"], DELIVERY["signed_with"], now=SIGNED_AT)  # noqa: E731
    assert code_of(call) == "signature_mismatch"


def test_a_changed_timestamp_is_refused() -> None:
    headers = {**DELIVERY["headers"], "X-Qeet-Timestamp": str(SIGNED_AT + 1)}
    call = lambda: construct_webhook_event(DELIVERY["body"], headers, DELIVERY["signed_with"], now=SIGNED_AT)  # noqa: E731
    assert code_of(call) == "signature_mismatch"


@pytest.mark.parametrize("offset", [-DEFAULT_WEBHOOK_TOLERANCE - 1, DEFAULT_WEBHOOK_TOLERANCE + 1])
def test_a_delivery_outside_the_tolerance_is_refused(offset: int) -> None:
    call = lambda: construct_webhook_event(  # noqa: E731
        DELIVERY["body"], DELIVERY["headers"], DELIVERY["signed_with"], now=SIGNED_AT + offset
    )
    assert code_of(call) == "timestamp_outside_tolerance"


@pytest.mark.parametrize("offset", [-DEFAULT_WEBHOOK_TOLERANCE, DEFAULT_WEBHOOK_TOLERANCE])
def test_the_tolerance_is_inclusive(offset: int) -> None:
    construct_webhook_event(DELIVERY["body"], DELIVERY["headers"], DELIVERY["signed_with"], now=SIGNED_AT + offset)


def test_tolerance_and_now_can_be_set() -> None:
    now = datetime.fromtimestamp(SIGNED_AT + 30, UTC)
    call = lambda: construct_webhook_event(  # noqa: E731
        DELIVERY["body"], DELIVERY["headers"], DELIVERY["signed_with"], now=now, tolerance=10
    )
    assert code_of(call) == "timestamp_outside_tolerance"
    construct_webhook_event(DELIVERY["body"], DELIVERY["headers"], DELIVERY["signed_with"], now=now, tolerance=60)
    for bad in (0, -1, True):
        with pytest.raises(ValueError, match="tolerance"):
            verify_webhook_signature(DELIVERY["body"], DELIVERY["headers"], "s", tolerance=bad)


def test_the_current_time_is_used_by_default() -> None:
    signed = sign_webhook_payload(DELIVERY["body"], "s")
    construct_webhook_event(DELIVERY["body"], signed, "s")
    stale = sign_webhook_payload(DELIVERY["body"], "s", timestamp=SIGNED_AT - 86_400 * 400)
    assert code_of(lambda: construct_webhook_event(DELIVERY["body"], stale, "s")) == "timestamp_outside_tolerance"


@pytest.mark.parametrize(
    ("headers", "code"),
    [
        ({"X-Qeet-Signature": "sha256=" + "0" * 64}, "missing_timestamp"),
        ({"X-Qeet-Timestamp": " ", "X-Qeet-Signature": "sha256=" + "0" * 64}, "missing_timestamp"),
        ({"X-Qeet-Timestamp": "17938.5", "X-Qeet-Signature": "sha256=" + "0" * 64}, "invalid_timestamp"),
        ({"X-Qeet-Timestamp": "-1", "X-Qeet-Signature": "sha256=" + "0" * 64}, "invalid_timestamp"),
        ({"X-Qeet-Timestamp": str(SIGNED_AT)}, "missing_signature"),
        ({"X-Qeet-Timestamp": str(SIGNED_AT), "X-Qeet-Signature": "v1=abc"}, "invalid_signature_header"),
        ({"X-Qeet-Timestamp": str(SIGNED_AT), "X-Qeet-Signature": "sha256=xyz"}, "invalid_signature_header"),
        ({"X-Qeet-Timestamp": str(SIGNED_AT), "X-Qeet-Signature": "sha256=" + "a" * 63}, "invalid_signature_header"),
    ],
)
def test_malformed_headers_are_refused(headers: dict[str, str], code: str) -> None:
    assert code_of(lambda: construct_webhook_event(DELIVERY["body"], headers, "s", now=SIGNED_AT)) == code


@pytest.mark.parametrize("secret", ["", [], ["", ""]])
def test_a_secret_is_required(secret: str | list[str]) -> None:
    call = lambda: construct_webhook_event(DELIVERY["body"], DELIVERY["headers"], secret, now=SIGNED_AT)  # noqa: E731
    assert code_of(call) == "missing_secret"


def test_unknown_schemes_are_ignored_not_trusted() -> None:
    headers = {
        **DELIVERY["headers"],
        "X-Qeet-Signature": "v2=deadbeef, " + DELIVERY["headers"]["X-Qeet-Signature"],
    }
    construct_webhook_event(DELIVERY["body"], headers, DELIVERY["signed_with"], now=SIGNED_AT)


@pytest.mark.parametrize(
    "body",
    [
        "not json",
        "[1, 2]",
        '{"id": "e1", "type": "user.created", "tenant_id": "t1", "occurred_at": "2026-11-05T09:30:00Z"}',
        '{"id": 1, "type": "user.created", "tenant_id": "t1", "occurred_at": "x", "data": {}}',
    ],
)
def test_a_body_that_isnt_an_event_is_refused(body: str) -> None:
    headers = sign_webhook_payload(body, "s", timestamp=SIGNED_AT)
    assert code_of(lambda: construct_webhook_event(body, headers, "s", now=SIGNED_AT)) == "invalid_payload"


def test_signing_matches_the_server() -> None:
    signed = sign_webhook_payload(DELIVERY["body"].encode(), DELIVERY["signed_with"][0], timestamp=SIGNED_AT)
    assert signed == {
        "X-Qeet-Timestamp": str(SIGNED_AT),
        "X-Qeet-Signature": DELIVERY["headers"]["X-Qeet-Signature"],
    }


def test_the_catalogue_and_headers() -> None:
    assert len(WEBHOOK_EVENT_TYPES) == len(set(WEBHOOK_EVENT_TYPES)) == 46
    assert "user.created" in WEBHOOK_EVENT_TYPES
    assert TEST_WEBHOOK_EVENT not in WEBHOOK_EVENT_TYPES
    assert WEBHOOK_HEADERS["signature"] == "X-Qeet-Signature"
