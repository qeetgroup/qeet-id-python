"""Shared test helpers: a scripted mock API, and running one test on both clients."""

import inspect
import json
from collections.abc import AsyncIterable, Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import parse_qsl

import httpx2
import pytest

from qeet_id import AsyncQeetID, QeetID
from qeet_id._async import _transport as async_transport
from qeet_id._sync import _transport as sync_transport

Kind = Literal["sync", "async"]
Client = QeetID | AsyncQeetID


@dataclass
class Recorded:
    """One request a client under test sent."""

    method: str
    url: httpx2.URL
    headers: httpx2.Headers
    content: bytes

    @property
    def path(self) -> str:
        return self.url.raw_path.decode().split("?", 1)[0]

    @property
    def query(self) -> list[tuple[str, str]]:
        return parse_qsl(self.url.query.decode(), keep_blank_values=True)

    @property
    def json(self) -> Any:
        return json.loads(self.content) if self.content else None

    @property
    def form(self) -> dict[str, str]:
        return dict(parse_qsl(self.content.decode(), keep_blank_values=True))


Step = dict[str, Any] | Exception | Callable[[httpx2.Request], httpx2.Response]


@dataclass
class MockAPI:
    """Answers each request from ``script`` in order (the last step repeats) and records it.

    A step is ``{"status": 200, "json": {...}, "headers": {...}, "content": b"..."}``,
    an exception to raise (a network failure), or a function of the request.
    """

    script: list[Step] = field(default_factory=list)
    requests: list[Recorded] = field(default_factory=list)
    _step: int = 0

    def answer(self, *steps: Step) -> "MockAPI":
        """Answer the next requests with ``steps``, from the first."""
        self.script = list(steps)
        self._step = 0
        return self

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(Recorded(request.method, request.url, request.headers, request.read()))
        if not self.script:
            return httpx2.Response(200, json={})
        step = self.script[min(self._step, len(self.script) - 1)]
        self._step += 1
        if isinstance(step, Exception):
            raise step
        if callable(step):
            return step(request)
        status = step.get("status", 200)
        headers = step.get("headers", {})
        if "content" in step:
            return httpx2.Response(status, headers=headers, content=step["content"])
        if "json" in step:
            return httpx2.Response(status, headers=headers, json=step["json"])
        return httpx2.Response(status, headers=headers)

    def client(self, kind: Kind, **options: Any) -> Client:
        options.setdefault("api_key", "qk_test_key")
        if kind == "sync":
            return QeetID(http_client=httpx2.Client(transport=httpx2.MockTransport(self.handler)), **options)
        return AsyncQeetID(http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(self.handler)), **options)

    @property
    def last(self) -> Recorded:
        return self.requests[-1]


@pytest.fixture
def api() -> MockAPI:
    return MockAPI()


@pytest.fixture(params=["sync", "async"])
def kind(request: pytest.FixtureRequest) -> Kind:
    """Runs a test once on each client."""
    param: Kind = request.param
    return param


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Retries record their delay instead of sleeping."""
    delays: list[float] = []

    def fake_sleep(seconds: float) -> None:
        delays.append(seconds)

    async def fake_async_sleep(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr(sync_transport, "sleep", fake_sleep)
    monkeypatch.setattr(async_transport, "sleep", fake_async_sleep)
    return delays


async def run(value: Any) -> Any:
    """Await ``value`` when the async client returned an awaitable; return it otherwise."""
    if inspect.isawaitable(value):
        return await value
    return value


async def collect(items: Iterable[Any] | AsyncIterable[Any]) -> list[Any]:
    """Every item of a sync or async iterable."""
    if isinstance(items, AsyncIterable):
        return [item async for item in items]
    return list(items)


def envelope(code: str, message: str = "Refused.", **extra: Any) -> dict[str, Any]:
    """An error envelope as the API sends it."""
    return {"error": {"code": code, "message": message, "request_id": "req_body", **extra}}
