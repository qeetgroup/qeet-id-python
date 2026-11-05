"""Verify webhook deliveries and read their events. No client or API key needed.

Each delivery is a signed POST whose body is an event::

    {"id": "…", "type": "user.created", "tenant_id": "…", "occurred_at": "2026-11-05T09:30:00Z", "data": {…}}

``X-Qeet-Signature`` is ``sha256=`` and the hex HMAC-SHA256, keyed by the
subscription's signing secret, of ``X-Qeet-Timestamp`` (Unix seconds), ``"."``
and the raw body. During a secret rotation the header holds two such values,
comma-separated. :func:`construct_webhook_event` checks it and returns the event::

    event = construct_webhook_event(request.body, request.headers, os.environ["QEET_ID_WEBHOOK_SECRET"])

Always pass the raw body, exactly as received: a parsed and re-serialised one won't match.
"""

import hashlib
import hmac
import json
import re
import time
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any, Final, Literal, Protocol, TypedDict, cast, get_args

from qeet_id._errors import WebhookVerificationError

__all__ = [
    "DEFAULT_WEBHOOK_TOLERANCE",
    "TEST_WEBHOOK_EVENT",
    "WEBHOOK_EVENT_TYPES",
    "WEBHOOK_HEADERS",
    "TestPingData",
    "WebhookEvent",
    "WebhookEventType",
    "WebhookHeaders",
    "construct_webhook_event",
    "sign_webhook_payload",
    "verify_webhook_signature",
]

DEFAULT_WEBHOOK_TOLERANCE: Final = 300
"""By default a delivery signed more than five minutes away from now is refused."""


class _Headers(TypedDict):
    signature: str
    timestamp: str
    event: str
    delivery_id: str


WEBHOOK_HEADERS: Final[_Headers] = {
    "signature": "X-Qeet-Signature",
    "timestamp": "X-Qeet-Timestamp",
    "event": "X-Qeet-Event",
    "delivery_id": "X-Qeet-Delivery-Id",
}
"""A delivery's headers. ``X-Qeet-Event`` and ``X-Qeet-Delivery-Id`` aren't signed: read the verified event instead."""

WebhookEventType = Literal[
    "user.created",
    "user.updated",
    "user.suspended",
    "user.reactivated",
    "user.deleted",
    "user.password_set",
    "user.bulk_imported",
    "auth.password_changed",
    "session.revoked",
    "token.claims_change",
    "group.created",
    "group.updated",
    "group.deleted",
    "group.member_added",
    "group.member_removed",
    "group_template.applied",
    "domain.created",
    "domain.verified",
    "domain.deleted",
    "agent.created",
    "agent.suspended",
    "agent.resumed",
    "agent.decommissioned",
    "agent.deleted",
    "agent.sponsor_transferred",
    "agent.kill_switch",
    "agent.resume_all",
    "rebac.tuple_written",
    "rebac.tuple_deleted",
    "abac_policy.created",
    "abac_policy.updated",
    "abac_policy.deleted",
    "auth_hook.created",
    "auth_hook.updated",
    "auth_hook.deleted",
    "siem.sink_created",
    "siem.sink_updated",
    "siem.sink_deleted",
    "rate_limits.updated",
    "rate_limits.deleted",
    "credential.issued",
    "credential.revoked",
    "oidc.client_locked_out",
    "tenant.suspended",
    "tenant.reactivated",
    "tenant.deleted",
]
"""An event a subscription can name, from the API's event catalogue.

An event's name is its version: a payload that changes incompatibly gets a new
name, while adding a field to one does not. ``client.webhooks.list_event_types()``
reads the catalogue live.
"""

WEBHOOK_EVENT_TYPES: Final[tuple[WebhookEventType, ...]] = get_args(WebhookEventType)
"""Every event this version of the SDK knows."""

TEST_WEBHOOK_EVENT: Final = "test.ping"
"""The event the test call sends. No subscription names it."""


class WebhookEvent(TypedDict):
    """A verified delivery's body.

    ``id`` is the same in every delivery of one event, retries included:
    deduplicate on it. ``type`` may be an event newer than this SDK, so
    ignore the types you don't handle. ``data`` is the event's own payload,
    such as :class:`TestPingData` for ``test.ping``.
    """

    id: str
    type: WebhookEventType | Literal["test.ping"] | str
    tenant_id: str
    occurred_at: str
    """When the change happened (RFC 3339)."""
    data: dict[str, Any]


class TestPingData(TypedDict):
    """The data of a ``test.ping`` event."""

    subscription_id: str


class WebhookHeaders(Protocol):
    """A delivery's headers: Django's, Flask's and Starlette's ``request.headers``, or a ``dict``."""

    def get(self, key: str, /) -> Any:  # noqa: D102
        ...


_SCHEME = "sha256="
_HEX_DIGEST = re.compile(r"^[0-9a-fA-F]{64}$")
_TIMESTAMP = re.compile(r"^[0-9]{1,15}$")


def construct_webhook_event(
    payload: bytes | bytearray | memoryview | str,
    headers: WebhookHeaders | Mapping[str, str],
    secret: str | Sequence[str],
    *,
    tolerance: float = DEFAULT_WEBHOOK_TOLERANCE,
    now: datetime | float | None = None,
) -> WebhookEvent:
    """Verify a webhook delivery and return its event.

    Args:
        payload: The raw request body exactly as received, never a re-serialised object.
        headers: The request's headers.
        secret: The subscription's signing secret. While you rotate it, pass both the new and the
            old one: a delivery signed with either is accepted.
        tolerance: The largest gap, in seconds, between the delivery's timestamp and now, either
            way. Keep it small: it bounds how long a captured delivery can be replayed.
        now: The current time, as a ``datetime`` or Unix seconds; for tests.

    Returns:
        The event. Answer the delivery with a 2xx once it is handled; deduplicate on its ``id``.

    Raises:
        WebhookVerificationError: when the delivery isn't authentic, is too old, or isn't an event.
            Answer it with a 400 and don't act on it.
    """
    verify_webhook_signature(payload, headers, secret, tolerance=tolerance, now=now)
    return _parse_event(_as_bytes(payload))


def verify_webhook_signature(
    payload: bytes | bytearray | memoryview | str,
    headers: WebhookHeaders | Mapping[str, str],
    secret: str | Sequence[str],
    *,
    tolerance: float = DEFAULT_WEBHOOK_TOLERANCE,
    now: datetime | float | None = None,
) -> None:
    """Check a delivery's signature and timestamp; :func:`construct_webhook_event` does this, then parses.

    Every value in ``X-Qeet-Signature`` is compared with the HMAC under every
    secret given, in constant time, without stopping at the first match.

    Raises:
        WebhookVerificationError: unless both the signature and the timestamp are good.
        ValueError: when ``tolerance`` isn't a number of seconds greater than 0.
    """
    secrets = [secret] if isinstance(secret, str) else list(secret)
    keys = [value.encode() for value in secrets if isinstance(value, str) and value]
    if not keys:
        raise WebhookVerificationError("missing_secret", "No webhook signing secret was given.")
    if isinstance(tolerance, bool) or not isinstance(tolerance, int | float) or not tolerance > 0:
        raise ValueError("tolerance must be a number of seconds greater than 0.")

    timestamp = _header(headers, WEBHOOK_HEADERS["timestamp"])
    if timestamp is None:
        raise WebhookVerificationError("missing_timestamp", "The delivery has no X-Qeet-Timestamp header.")
    if not _TIMESTAMP.match(timestamp):
        raise WebhookVerificationError("invalid_timestamp", "X-Qeet-Timestamp is not Unix seconds.")
    if abs(_unix(now) - int(timestamp)) > tolerance:
        raise WebhookVerificationError(
            "timestamp_outside_tolerance",
            f"The delivery was signed more than {tolerance:g} seconds from now; refusing it as a possible replay.",
        )

    header = _header(headers, WEBHOOK_HEADERS["signature"])
    if header is None:
        raise WebhookVerificationError("missing_signature", "The delivery has no X-Qeet-Signature header.")
    signatures = _signatures(header)
    if not signatures:
        raise WebhookVerificationError("invalid_signature_header", "X-Qeet-Signature holds no sha256=<hex> value.")

    signed = timestamp.encode() + b"." + _as_bytes(payload)
    matched = False
    for key in keys:
        expected = hmac.new(key, signed, hashlib.sha256).digest()
        for signature in signatures:
            # No early exit: the work done doesn't depend on which value matched.
            matched |= hmac.compare_digest(expected, signature)
    if not matched:
        raise WebhookVerificationError(
            "signature_mismatch", "The delivery's signature does not match: it was not signed with this secret."
        )


def sign_webhook_payload(
    payload: bytes | bytearray | memoryview | str, secret: str, *, timestamp: int | None = None
) -> dict[str, str]:
    """Sign ``payload`` the way Qeet ID does, to test your webhook handler.

    Returns:
        The ``X-Qeet-Timestamp`` and ``X-Qeet-Signature`` headers, ready to send.
    """
    ts = str(int(time.time()) if timestamp is None else int(timestamp))
    digest = hmac.new(secret.encode(), ts.encode() + b"." + _as_bytes(payload), hashlib.sha256).hexdigest()
    return {WEBHOOK_HEADERS["timestamp"]: ts, WEBHOOK_HEADERS["signature"]: _SCHEME + digest}


def _as_bytes(payload: bytes | bytearray | memoryview | str) -> bytes:
    if isinstance(payload, str):
        return payload.encode("utf-8")
    if isinstance(payload, bytes | bytearray | memoryview):
        return bytes(payload)
    raise TypeError("payload must be the raw request body: bytes or str, not a parsed object.")


def _unix(now: datetime | float | None) -> float:
    if now is None:
        return time.time()
    if isinstance(now, datetime):
        return now.timestamp()
    return float(now)


def _header(headers: WebhookHeaders | Mapping[str, str], name: str) -> str | None:
    value = headers.get(name)
    if value is None:
        value = headers.get(name.lower())
    if value is None and isinstance(headers, Mapping):
        # A plain dict is case-sensitive; framework header objects aren't.
        value = next((v for k, v in headers.items() if isinstance(k, str) and k.lower() == name.lower()), None)
    if isinstance(value, list | tuple):
        value = ",".join(str(v) for v in value)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _signatures(header: str) -> list[bytes]:
    found = []
    for part in header.split(","):
        entry = part.strip()
        if not entry.startswith(_SCHEME):
            continue  # a scheme this SDK doesn't know: ignored, never trusted
        digest = entry[len(_SCHEME) :]
        if _HEX_DIGEST.match(digest):
            found.append(bytes.fromhex(digest))
    return found


def _parse_event(body: bytes) -> WebhookEvent:
    try:
        event = json.loads(body)
    except ValueError:
        raise WebhookVerificationError("invalid_payload", "The delivery's body is not JSON.") from None
    required: Iterable[str] = ("id", "type", "tenant_id", "occurred_at")
    if (
        not isinstance(event, dict)
        or any(not isinstance(event.get(key), str) for key in required)
        or "data" not in event
    ):
        raise WebhookVerificationError(
            "invalid_payload", "The delivery's body is not a Qeet ID event (id, type, tenant_id, occurred_at, data)."
        )
    return cast("WebhookEvent", event)
