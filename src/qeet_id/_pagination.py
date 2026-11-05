"""Lists: whole lists (:class:`ListResult`) and cursor-paged ones (:class:`Page`, :class:`AsyncPage`)."""

from collections.abc import AsyncIterator, Awaitable, Callable, Generator, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

__all__ = ["AsyncPage", "AsyncPaginator", "ListResult", "Page"]

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ListResult(Generic[T]):
    """A list the API returns whole, in one response.

    Iterate it, index it or take its ``len()``. ``truncated`` is true when the
    API capped the list and more items exist than ``data`` holds: narrow the
    request (or use the API's paged list where there is one) to see the rest.
    """

    data: list[T] = field(default_factory=list)
    truncated: bool = False

    def __iter__(self) -> Iterator[T]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, index: int) -> T:
        return self.data[index]

    @classmethod
    def from_response(cls, body: object, *, key: str = "items") -> "ListResult[Any]":
        """Read ``{"items": [...], "truncated": bool}`` (or another key) from a response body. Internal."""
        items = body.get(key) if isinstance(body, Mapping) else None
        truncated = isinstance(body, Mapping) and body.get("truncated") is True
        return ListResult(list(items) if isinstance(items, list) else [], truncated)


def _page_parts(body: object) -> tuple[list[Any], str | None]:
    if not isinstance(body, Mapping):
        return [], None
    items = body.get("items")
    cursor = body.get("next_cursor")
    return (list(items) if isinstance(items, list) else []), (cursor if isinstance(cursor, str) and cursor else None)


class Page(Generic[T]):
    """One page of a cursor-paged list, from the synchronous client.

    Iterating a page walks every item from this page to the end of the list,
    fetching later pages as it goes::

        for user in client.users.list(status="active"):
            ...

    Or step through pages: ``data``, ``has_next_page()``, ``get_next_page()``, ``iter_pages()``.
    """

    __slots__ = ("_fetch", "data", "next_cursor")

    data: list[T]
    """The items on this page."""
    next_cursor: str | None
    """The cursor of the next page; ``None`` on the last page."""

    def __init__(self, body: object, fetch: Callable[[str], "Page[T]"]) -> None:
        self.data, self.next_cursor = _page_parts(body)
        self._fetch = fetch

    def has_next_page(self) -> bool:
        """Whether another page follows this one."""
        return self.next_cursor is not None

    def get_next_page(self) -> "Page[T]":
        """Fetch the next page.

        Raises:
            RuntimeError: on the last page; check ``has_next_page()`` first.
        """
        if self.next_cursor is None:
            raise RuntimeError("This is the last page: there is no next page.")
        return self._fetch(self.next_cursor)

    def iter_pages(self) -> Iterator["Page[T]"]:
        """Yield this page and every page after it."""
        page = self
        seen: set[str] = set()
        while True:
            yield page
            cursor = page.next_cursor
            # A server that answered a cursor twice would loop forever.
            if cursor is None or cursor in seen:
                return
            seen.add(cursor)
            page = page.get_next_page()

    def __iter__(self) -> Iterator[T]:
        for page in self.iter_pages():
            yield from page.data

    def __repr__(self) -> str:
        return f"Page(items={len(self.data)}, next_cursor={self.next_cursor!r})"


class AsyncPage(Generic[T]):
    """One page of a cursor-paged list, from the asynchronous client.

    ``async for`` walks every item from this page to the end of the list,
    fetching later pages as it goes. Or step through pages: ``data``,
    ``has_next_page()``, ``await get_next_page()``, ``async for page in iter_pages()``.
    """

    __slots__ = ("_fetch", "data", "next_cursor")

    data: list[T]
    """The items on this page."""
    next_cursor: str | None
    """The cursor of the next page; ``None`` on the last page."""

    def __init__(self, body: object, fetch: Callable[[str], Awaitable["AsyncPage[T]"]]) -> None:
        self.data, self.next_cursor = _page_parts(body)
        self._fetch = fetch

    def has_next_page(self) -> bool:
        """Whether another page follows this one."""
        return self.next_cursor is not None

    async def get_next_page(self) -> "AsyncPage[T]":
        """Fetch the next page.

        Raises:
            RuntimeError: on the last page; check ``has_next_page()`` first.
        """
        if self.next_cursor is None:
            raise RuntimeError("This is the last page: there is no next page.")
        return await self._fetch(self.next_cursor)

    async def iter_pages(self) -> AsyncIterator["AsyncPage[T]"]:
        """Yield this page and every page after it."""
        page = self
        seen: set[str] = set()
        while True:
            yield page
            cursor = page.next_cursor
            if cursor is None or cursor in seen:
                return
            seen.add(cursor)
            page = await page.get_next_page()

    async def __aiter__(self) -> AsyncIterator[T]:
        async for page in self.iter_pages():
            for item in page.data:
                yield item

    def __repr__(self) -> str:
        return f"AsyncPage(items={len(self.data)}, next_cursor={self.next_cursor!r})"


class AsyncPaginator(Generic[T]):
    """What a paged list method of the asynchronous client returns.

    Await it for the first page, or iterate it with ``async for`` to walk every
    item across every page::

        page = await client.users.list(limit=50)
        async for user in client.users.list(status="active"):
            ...

    The first request is sent when it is first awaited or iterated.
    """

    __slots__ = ("_first", "_load")

    def __init__(self, load: Callable[[], Awaitable[AsyncPage[T]]]) -> None:
        self._load = load
        self._first: AsyncPage[T] | None = None

    async def _first_page(self) -> AsyncPage[T]:
        if self._first is None:
            self._first = await self._load()
        return self._first

    def __await__(self) -> Generator[Any, None, AsyncPage[T]]:
        return self._first_page().__await__()

    async def __aiter__(self) -> AsyncIterator[T]:
        page = await self._first_page()
        async for item in page:
            yield item
