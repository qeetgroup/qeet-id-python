"""The base class of the synchronous resource namespaces. Hand-written: paging differs from the async one."""

from collections.abc import Mapping
from typing import Any

from qeet_id._options import RequestOptions
from qeet_id._pagination import ListResult, Page
from qeet_id._request import HTTPMethod, Request
from qeet_id._sync._transport import Transport

__all__ = ["APIResource"]


class APIResource:
    """A namespace of API calls on the synchronous client (``client.users``, …). Internal."""

    __slots__ = ("_transport",)

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"

    def _request(
        self,
        method: HTTPMethod,
        path: str,
        *,
        query: Mapping[str, object] | None = None,
        json: object = None,
        form: Mapping[str, str | None] | None = None,
        content: bytes | None = None,
        content_type: str | None = None,
        authenticate: bool = True,
        client_auth: tuple[str, str] | None = None,
        retry_safe: bool = False,
        idempotent: bool = False,
        retries: bool = True,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> Any:
        request = Request(
            method=method,
            path=path,
            query=query,
            json=json,
            form=form,
            content=content,
            content_type=content_type,
            authenticate=authenticate,
            client_auth=client_auth,
            retry_safe=retry_safe,
            idempotent=idempotent,
            retries=retries,
        )
        return self._transport.request(request, idempotency_key=idempotency_key, request_options=request_options)

    def _list(
        self,
        path: str,
        query: Mapping[str, object] | None = None,
        *,
        key: str = "items",
        request_options: RequestOptions | None = None,
    ) -> ListResult[Any]:
        body = self._request("GET", path, query=query, request_options=request_options)
        return ListResult.from_response(body, key=key)

    def _paginate(
        self,
        path: str,
        query: Mapping[str, object],
        *,
        request_options: RequestOptions | None = None,
    ) -> Page[Any]:
        """Fetch the first page now; iterating it fetches the rest."""
        params = dict(query)
        start = params.pop("cursor", None)

        def fetch(cursor: str | None) -> Page[Any]:
            body = self._request("GET", path, query={**params, "cursor": cursor}, request_options=request_options)
            return Page(body, fetch)

        return fetch(start if isinstance(start, str) else None)
