from typing import Any

import httpx2
import pytest

from qeet_id import AsyncPage, AsyncPaginator, AsyncQeetID, ListResult, Page, QeetID
from qeet_id._async._resource import AsyncAPIResource
from qeet_id._sync._resource import APIResource

from .conftest import Kind, MockAPI, collect, run

pytestmark = pytest.mark.anyio


def pages(api: MockAPI, *bodies: dict[str, Any]) -> MockAPI:
    return api.answer(*({"json": body} for body in bodies))


def paginate(client: QeetID | AsyncQeetID, **query: Any) -> Page[Any] | AsyncPaginator[Any]:
    if isinstance(client, QeetID):
        return APIResource(client._transport)._paginate("/v1/users", query)
    return AsyncAPIResource(client._transport)._paginate("/v1/users", query)


async def test_iterating_walks_every_page(api: MockAPI, kind: Kind) -> None:
    pages(
        api,
        {"items": [{"id": "u1"}, {"id": "u2"}], "next_cursor": "c2"},
        {"items": [{"id": "u3"}], "next_cursor": "c3"},
        {"items": [{"id": "u4"}], "next_cursor": ""},
    )
    users = await collect(paginate(api.client(kind), limit=2, status="active"))
    assert [u["id"] for u in users] == ["u1", "u2", "u3", "u4"]
    assert [r.query for r in api.requests] == [
        [("limit", "2"), ("status", "active")],
        [("limit", "2"), ("status", "active"), ("cursor", "c2")],
        [("limit", "2"), ("status", "active"), ("cursor", "c3")],
    ]


async def test_one_page_at_a_time(api: MockAPI, kind: Kind) -> None:
    pages(api, {"items": [{"id": "u1"}], "next_cursor": "c2"}, {"items": [{"id": "u2"}], "next_cursor": None})
    page = await run(paginate(api.client(kind), cursor="c1"))
    assert isinstance(page, Page | AsyncPage)
    assert api.last.query == [("cursor", "c1")]
    assert page.data == [{"id": "u1"}]
    assert page.next_cursor == "c2"
    assert page.has_next_page()
    second = await run(page.get_next_page())
    assert second.data == [{"id": "u2"}]
    assert not second.has_next_page()
    with pytest.raises(RuntimeError, match="last page"):
        await run(second.get_next_page())
    assert repr(second).endswith("Page(items=1, next_cursor=None)")


async def test_iter_pages_yields_each_page(api: MockAPI, kind: Kind) -> None:
    pages(api, {"items": [1, 2], "next_cursor": "c2"}, {"items": [3]})
    first = await run(paginate(api.client(kind)))
    sizes = [len(p.data) for p in await collect(first.iter_pages())]
    assert sizes == [2, 1]


async def test_a_repeated_cursor_ends_the_walk(api: MockAPI, kind: Kind) -> None:
    pages(api, {"items": [1], "next_cursor": "c2"}, {"items": [2], "next_cursor": "c2"})
    assert await collect(paginate(api.client(kind))) == [1, 2]
    assert len(api.requests) == 2


async def test_a_malformed_page_is_empty(api: MockAPI, kind: Kind) -> None:
    pages(api, {"items": "nope", "next_cursor": 7})
    page = await run(paginate(api.client(kind)))
    assert page.data == []
    assert page.next_cursor is None


async def test_the_sync_list_sends_at_once_and_the_async_one_when_used(api: MockAPI) -> None:
    pages(api, {"items": [1]})
    paginate(api.client("sync"))
    assert len(api.requests) == 1
    paginator = paginate(api.client("async"))
    assert len(api.requests) == 1
    assert isinstance(paginator, AsyncPaginator)
    first = await paginator
    assert first is await paginator  # awaited twice, fetched once
    assert len(api.requests) == 2


def test_list_results() -> None:
    result = ListResult.from_response({"items": [{"id": "d1"}, {"id": "d2"}], "truncated": True})
    assert len(result) == 2
    assert result[1] == {"id": "d2"}
    assert [d["id"] for d in result] == ["d1", "d2"]
    assert result.truncated is True
    assert ListResult.from_response({"keys": [1]}, key="keys").data == [1]
    assert ListResult.from_response(None) == ListResult([], truncated=False)
    assert ListResult.from_response({"items": None, "truncated": "yes"}) == ListResult()


async def test_list_errors_propagate(api: MockAPI, kind: Kind) -> None:
    api.answer({"json": {"items": [1], "next_cursor": "c2"}}, httpx2.ConnectError("reset"))
    client = api.client(kind, max_retries=0)
    with pytest.raises(Exception, match="could not reach"):
        await collect(paginate(client))
