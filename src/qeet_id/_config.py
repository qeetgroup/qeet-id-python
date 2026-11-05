"""Checks and builds the client's configuration: base URL, headers, User-Agent."""

import ipaddress
import platform
import re
from collections.abc import Mapping
from urllib.parse import urlsplit

from qeet_id._constants import DEFAULT_BASE_URL
from qeet_id._options import AppInfo
from qeet_id._version import __version__

__all__ = [
    "RESERVED_HEADERS",
    "build_user_agent",
    "check_headers",
    "check_max_retries",
    "check_timeout",
    "is_loopback_host",
    "normalize_base_url",
]

RESERVED_HEADERS = frozenset(
    {"authorization", "accept", "content-type", "content-length", "host", "user-agent", "idempotency-key"}
)
"""Headers the SDK sets itself; neither client nor per-call headers may replace them."""

_APP_NAME = re.compile(r"^[\w.\-@/]+$")


def is_loopback_host(host: str) -> bool:
    """Whether ``host`` names this machine: ``localhost``, ``*.localhost`` or a loopback address."""
    host = host.lower().rstrip(".")
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def normalize_base_url(base_url: str, *, name: str = "base_url") -> str:
    """Check ``base_url`` and return it without a trailing slash.

    It must be absolute, and https unless it points at this machine: credentials
    must never cross a network in the clear. It may not carry credentials, a
    query or a fragment.

    Raises:
        ValueError: when the URL breaks one of those rules.
    """
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError(f"{name} must be an absolute URL, such as {DEFAULT_BASE_URL}.")
    parts = urlsplit(base_url.strip())
    if parts.scheme not in ("https", "http") or not parts.hostname:
        raise ValueError(f"{name} must be an absolute http(s) URL, such as {DEFAULT_BASE_URL}.")
    if parts.scheme == "http" and not is_loopback_host(parts.hostname):
        raise ValueError(f"{name} must use https (plain http is allowed only for localhost).")
    if parts.username is not None or parts.password is not None or parts.query or parts.fragment:
        raise ValueError(f"{name} must not carry credentials, a query string or a fragment.")
    return parts.geturl().rstrip("/")


def check_headers(headers: Mapping[str, str] | None, *, name: str) -> dict[str, str]:
    """Return ``headers`` as a dict, refusing the SDK's own headers and line breaks.

    Raises:
        ValueError: for a reserved header, an empty name, or a line break.
    """
    out: dict[str, str] = {}
    for key, value in (headers or {}).items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError(f"{name} must map header names to string values.")
        lowered = key.strip().lower()
        if not lowered:
            raise ValueError(f"{name} holds a header with an empty name.")
        if lowered in RESERVED_HEADERS:
            raise ValueError(f"{name} can't set {key}: the client sets it itself.")
        if any(c in key + value for c in "\r\n"):
            raise ValueError(f"{name}: header {key} contains a line break.")
        out[key.strip()] = value
    return out


def check_timeout(timeout: object, *, name: str = "timeout") -> None:
    """Refuse a timeout that isn't a positive number of seconds (an ``httpx2.Timeout`` passes as is).

    Raises:
        ValueError: when ``timeout`` is a number of zero or less.
    """
    if isinstance(timeout, bool):
        raise TypeError(f"{name} must be a number of seconds or an httpx2.Timeout.")
    if isinstance(timeout, int | float) and not timeout > 0:
        raise ValueError(f"{name} must be a number of seconds greater than 0.")


def check_max_retries(max_retries: object, *, name: str = "max_retries") -> int:
    """Return ``max_retries`` after checking it is a whole number, 0 or more.

    Raises:
        ValueError: when it is negative or not a whole number.
    """
    if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
        raise ValueError(f"{name} must be a whole number, 0 or more.")
    return max_retries


def build_user_agent(app_info: AppInfo | None = None) -> str:
    """The User-Agent: the SDK, its version and the runtime, after the application's ``app_info``.

    Raises:
        ValueError: when ``app_info["name"]`` isn't a short token.
    """
    sdk = (
        f"qeet-id-python/{__version__} {platform.python_implementation().lower()}/{platform.python_version()} "
        f"({platform.system().lower() or 'unknown'}; {platform.machine().lower() or 'unknown'})"
    )
    if app_info is None:
        return sdk
    app_name = app_info.get("name")
    if not isinstance(app_name, str) or not _APP_NAME.match(app_name):
        raise ValueError(
            "app_info['name'] must be a short token such as 'acme-billing' (letters, digits and . _ - @ /)."
        )
    app_version = app_info.get("version")
    app_url = app_info.get("url")
    # Computed outside the f-strings: Python 3.11 allows no backslash inside one.
    version = "/" + re.sub(r"\s+", "", app_version) if app_version else ""
    url = " (+" + re.sub(r"[()\s]", "", app_url) + ")" if app_url else ""
    return f"{app_name}{version}{url} {sdk}"
