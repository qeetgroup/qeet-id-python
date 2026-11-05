"""How a resource method describes a request, and the encoding shared by both clients."""

import base64
import json
import keyword
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias
from urllib.parse import quote, quote_plus

__all__ = [
    "HTTPMethod",
    "QueryPairs",
    "Request",
    "basic_authorization",
    "check_idempotency_key",
    "encode_body",
    "encode_query",
    "new_idempotency_key",
    "path",
]

HTTPMethod: TypeAlias = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]

QueryPairs: TypeAlias = list[tuple[str, str | int | float | bool | None]]
"""Encoded query-string pairs, as httpx2 takes them."""


@dataclass(frozen=True, slots=True, kw_only=True)
class Request:
    """One API call, as a resource method describes it. Internal."""

    method: HTTPMethod
    path: str
    """Already encoded: build it with :func:`path`."""
    query: Mapping[str, object] | None = None
    json: object = None
    """Sent as JSON when not ``None``."""
    form: Mapping[str, str | None] | None = None
    """Sent as ``application/x-www-form-urlencoded``; ``None`` entries are left out."""
    content: bytes | None = None
    """Sent as is, with ``content_type``."""
    content_type: str | None = None
    authenticate: bool = True
    """Send the client's credential. False for the endpoints that authenticate otherwise."""
    client_auth: tuple[str, str] | None = None
    """An OAuth client's ID and secret, sent with HTTP Basic instead of the client's credential."""
    retry_safe: bool = False
    """A POST that changes nothing (a check, a preview), or nothing more when repeated."""
    idempotent: bool = False
    """The route honours ``Idempotency-Key``: one is sent (generated when the caller gives none)."""
    retries: bool = True
    """False for calls that must never be repeated: single-use OAuth grants, directory sign-in."""


def path(template: str, *ids: str) -> str:
    """Fill ``template``'s ``{}`` placeholders with ``ids``, each percent-encoded as one path segment.

    Refuses an empty identifier and the dot segments ``.`` and ``..``, which a URL
    parser would resolve into another endpoint::

        path("/v1/users/{}/sessions", "u/1")  # "/v1/users/u%2F1/sessions"

    Raises:
        TypeError: when an identifier isn't a string.
        ValueError: when an identifier is empty, ``.`` or ``..``.
    """
    pieces = template.split("{}")
    if len(pieces) != len(ids) + 1:
        raise ValueError(f"{template} needs {len(pieces) - 1} identifiers, got {len(ids)}.")
    out = [pieces[0]]
    for value, piece in zip(ids, pieces[1:], strict=True):
        if not isinstance(value, str):
            raise TypeError(f"Each identifier in {template} must be a string; got {type(value).__name__}.")
        if value.strip() in ("", ".", ".."):
            raise ValueError(f"Each identifier in {template} must be a non-empty string; got {value!r}.")
        out.append(quote(value, safe=""))
        out.append(piece)
    return "".join(out)


def _wire_name(key: str) -> str:
    # A Python keyword can't be a keyword argument, so `from` is spelt `from_`.
    if key.endswith("_") and keyword.iskeyword(key[:-1]):
        return key[:-1]
    return key


def _query_text(value: str | int | float | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def encode_query(query: Mapping[str, object] | None) -> QueryPairs:
    """The query string's pairs: ``None`` left out, sequences repeated, ``from_`` sent as ``from``."""
    pairs: QueryPairs = []
    for key, value in (query or {}).items():
        if value is None:
            continue
        name = _wire_name(key)
        if isinstance(value, str | int | float | bool):
            pairs.append((name, _query_text(value)))
        elif isinstance(value, list | tuple):
            pairs.extend((name, _query_text(item)) for item in value)
        else:
            raise TypeError(f"Query parameter {key} must be a string, number, boolean or list of them.")
    return pairs


def encode_body(request: Request) -> tuple[bytes | None, str | None]:
    """The request body and its content type."""
    if request.content is not None:
        return request.content, request.content_type
    if request.form is not None:
        pairs = [(key, value) for key, value in request.form.items() if value is not None]
        text = "&".join(f"{quote_plus(key)}={quote_plus(value)}" for key, value in pairs)
        return text.encode("ascii"), "application/x-www-form-urlencoded"
    if request.json is None:
        return None, None
    body: Any = request.json
    return json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), "application/json"


def basic_authorization(client_id: str, client_secret: str) -> str:
    """``Authorization: Basic`` for an OAuth client, each part form-encoded first as RFC 6749 §2.3.1 asks."""
    raw = f"{quote_plus(client_id)}:{quote_plus(client_secret)}".encode()
    return "Basic " + base64.b64encode(raw).decode("ascii")


def check_idempotency_key(key: object) -> str:
    """Return ``key`` after checking it is 1 to 255 printable ASCII characters without spaces, as the API requires.

    Raises:
        ValueError: when it isn't.
    """
    if not isinstance(key, str) or not 1 <= len(key) <= 255 or any(not 0x21 <= ord(c) <= 0x7E for c in key):
        raise ValueError("idempotency_key must be 1 to 255 printable ASCII characters, without spaces.")
    return key


def new_idempotency_key() -> str:
    """A random version 4 UUID."""
    return str(uuid.uuid4())
