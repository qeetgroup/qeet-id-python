"""The base class of the asynchronous resource namespaces. Hand-written: paging differs from the sync one."""

from collections.abc import Mapping
from typing import Any

from qeet_id._async._transport import AsyncTransport
from qeet_id._options import RequestOptions
from qeet_id._pagination import AsyncPage, AsyncPaginator, ListResult
from qeet_id._request import HTTPMethod, QueryValue, Request

__all__ = ["AsyncAPIResource"]


class AsyncAPIResource:
    """A namespace of API calls on the asynchronous client (``client.users``, …). Internal."""

    __slots__ = ("_transport",)

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"

    async def _request(
        self,
        method: HTTPMethod,
        path: str,
        *,
        query: Mapping[str, QueryValue] | None = None,
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
        return await self._transport.request(request, idempotency_key=idempotency_key, request_options=request_options)

    async def _list(
        self,
        path: str,
        query: Mapping[str, QueryValue] | None = None,
        *,
        key: str = "items",
        request_options: RequestOptions | None = None,
    ) -> ListResult[Any]:
        body = await self._request("GET", path, query=query, request_options=request_options)
        return ListResult.from_response(body, key=key)

    def _paginate(
        self,
        path: str,
        query: Mapping[str, QueryValue],
        *,
        request_options: RequestOptions | None = None,
    ) -> AsyncPaginator[Any]:
        params = dict(query)
        start = params.pop("cursor", None)

        async def fetch(cursor: str | None) -> AsyncPage[Any]:
            body = await self._request("GET", path, query={**params, "cursor": cursor}, request_options=request_options)
            return AsyncPage(body, fetch)

        return AsyncPaginator(lambda: fetch(start if isinstance(start, str) else None))
