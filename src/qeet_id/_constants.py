"""Defaults shared by both clients."""

from typing import Final

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "INITIAL_RETRY_DELAY",
    "MAX_RETRY_AFTER",
    "MAX_RETRY_DELAY",
]

DEFAULT_BASE_URL: Final = "https://api.id.qeet.in"
"""The production API."""

DEFAULT_TIMEOUT: Final = 30.0
"""Seconds each attempt may wait to connect, send, or read the response."""

DEFAULT_MAX_RETRIES: Final = 2
"""How many times a retry-safe request is retried after a transient failure."""

INITIAL_RETRY_DELAY: Final = 0.5
"""Seconds before the first retry; each later one doubles it."""

MAX_RETRY_DELAY: Final = 8.0
"""No computed retry waits longer than this."""

MAX_RETRY_AFTER: Final = 60.0
"""A ``Retry-After`` longer than this is not waited out: the error is raised instead."""
