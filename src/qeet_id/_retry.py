"""When a failed attempt is retried, and after how long. Shared by both clients (ADR-0005)."""

import random
from collections.abc import Callable

from qeet_id._constants import INITIAL_RETRY_DELAY, MAX_RETRY_AFTER, MAX_RETRY_DELAY
from qeet_id._errors import SESSION_REVOKED, APIError, NetworkError

__all__ = ["IDEMPOTENCY_IN_PROGRESS", "SAFE_METHODS", "is_retryable", "retry_delay"]

IDEMPOTENCY_IN_PROGRESS = "idempotency.in_progress"
"""The code the API answers while the first request with the same idempotency key is still running."""

SAFE_METHODS = frozenset({"GET", "DELETE"})
"""Methods that are safe to repeat. PUT and PATCH are not retried: replaying a write is the caller's decision."""

_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


def is_retryable(error: BaseException, *, retry_safe: bool) -> bool:
    """Whether a failed attempt may be retried.

    Only a retry-safe request is retried (GET, DELETE, a POST that changes
    nothing, or one carrying an ``Idempotency-Key``), and only after a failure a
    later attempt can fix: no response, a timeout, 408, 429, 500, 502, 503, 504,
    or a 409 saying the first request with the same key is still running. A 401
    is never retried, so neither is ``auth.session_revoked``, whatever the
    server's ``retryable`` hint says: only a new sign-in helps.
    """
    if not retry_safe:
        return False
    if isinstance(error, NetworkError):
        return True  # RequestTimeoutError included
    if not isinstance(error, APIError) or error.code == SESSION_REVOKED or error.status == 401:
        return False
    if error.status == 409:
        return error.code == IDEMPOTENCY_IN_PROGRESS
    return error.status in _TRANSIENT_STATUSES


def retry_delay(retry: int, error: BaseException, *, rand: Callable[[], float] = random.random) -> float | None:
    """Seconds to wait before retry number ``retry`` (0 for the first).

    Honours the server's ``Retry-After``; otherwise exponential backoff with
    "equal jitter": half the capped exponential delay plus a random share of the
    other half, so clients that failed together don't retry together. Returns
    ``None`` when the server asks for a wait longer than ``MAX_RETRY_AFTER``,
    meaning: don't retry, raise.
    """
    if isinstance(error, APIError) and error.retry_after is not None:
        return None if error.retry_after > MAX_RETRY_AFTER else max(0.0, error.retry_after)
    exponential = min(MAX_RETRY_DELAY, INITIAL_RETRY_DELAY * 2.0 ** min(retry, 32))
    return exponential / 2 + rand() * (exponential / 2)
