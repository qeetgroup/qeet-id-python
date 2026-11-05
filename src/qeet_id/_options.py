"""Options shared by both clients: per-call settings and application info."""

from collections.abc import Mapping
from typing import Required, TypedDict

import httpx2

__all__ = ["AppInfo", "RequestOptions"]


class RequestOptions(TypedDict, total=False):
    """Settings for one call, overriding the client's.

    Every method takes them as ``request_options``::

        client.users.get(user_id, request_options={"timeout": 5, "max_retries": 0})
    """

    timeout: float | httpx2.Timeout
    """Seconds each attempt may wait to connect, send, or read; or an ``httpx2.Timeout``."""

    max_retries: int
    """How many times a retry-safe call is retried after a transient failure. ``0`` turns retries off."""

    headers: Mapping[str, str]
    """Extra request headers, such as ``traceparent``.

    They can't replace ``Authorization``, ``Accept``, ``Content-Type``, ``User-Agent`` or ``Idempotency-Key``.
    """


class AppInfo(TypedDict, total=False):
    """Identifies your application in the ``User-Agent`` of every request.

    ``{"name": "brightleaf-onboarding", "version": "1.4.0", "url": "https://brightleaffoods.in"}``
    becomes ``brightleaf-onboarding/1.4.0 (+https://brightleaffoods.in) qeet-id-python/…``.
    """

    name: Required[str]
    version: str
    url: str
