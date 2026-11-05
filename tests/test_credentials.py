import base64

import anyio
import httpx2
import pytest

from qeet_id import AsyncQeetID, OAuthError, QeetID
from qeet_id._async import _credentials as async_credentials
from qeet_id._request import Request
from qeet_id._sync import _credentials as sync_credentials

from .conftest import Kind, MockAPI, run

pytestmark = pytest.mark.anyio

TOKEN = {"access_token": "eyJ.service.token", "token_type": "Bearer", "expires_in": 900, "scope": "user:read"}


class Clock:
    """Stands in for time.monotonic in the credential modules."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    for module in (sync_credentials, async_credentials):
        monkeypatch.setattr(module, "monotonic", fake)
    return fake


def routed(api: MockAPI) -> MockAPI:
    """Answer the token endpoint with TOKEN and anything else with {}."""

    def answer(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/v1/oauth/token":
            return httpx2.Response(200, json=TOKEN)
        return httpx2.Response(200, json={"ok": True})

    return api.answer(answer)


async def get(client: QeetID | AsyncQeetID) -> object:
    return await run(client._transport.request(Request(method="GET", path="/v1/users")))


async def test_client_credentials_get_a_token_once_and_reuse_it(api: MockAPI, kind: Kind, clock: Clock) -> None:
    client = routed(api).client(kind, api_key=None, client_id="sp_1", client_secret="s3cret+/=")
    await get(client)
    await get(client)
    token_requests = [r for r in api.requests if r.path == "/v1/oauth/token"]
    assert len(token_requests) == 1
    grant = token_requests[0]
    assert grant.method == "POST"
    assert grant.form == {"grant_type": "client_credentials"}
    assert grant.headers["authorization"] == "Basic " + base64.b64encode(b"sp_1:s3cret%2B%2F%3D").decode()
    calls = [r for r in api.requests if r.path == "/v1/users"]
    assert [r.headers["authorization"] for r in calls] == ["Bearer eyJ.service.token"] * 2


async def test_the_token_is_renewed_a_minute_before_it_expires(api: MockAPI, kind: Kind, clock: Clock) -> None:
    client = routed(api).client(kind, api_key=None, client_id="sp_1", client_secret="s")
    await get(client)
    clock.now += 900 - 61
    await get(client)
    assert sum(r.path == "/v1/oauth/token" for r in api.requests) == 1
    clock.now += 2
    await get(client)
    assert sum(r.path == "/v1/oauth/token" for r in api.requests) == 2


async def test_a_refused_token_is_dropped(api: MockAPI, kind: Kind, clock: Clock) -> None:
    def answer(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/v1/oauth/token":
            return httpx2.Response(200, json=TOKEN)
        if len(api.requests) == 2:
            return httpx2.Response(401, json={"error": {"code": "unauthorized", "message": "No."}})
        return httpx2.Response(200, json={})

    client = api.answer(answer).client(kind, api_key=None, client_id="sp_1", client_secret="s")
    with pytest.raises(Exception, match="401"):
        await get(client)
    await get(client)
    assert sum(r.path == "/v1/oauth/token" for r in api.requests) == 2


async def test_a_refused_client_raises_the_oauth_error_without_calling_the_api(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 401, "json": {"error": "invalid_client", "error_description": "Unknown client."}})
    client = api.client(kind, api_key=None, client_id="sp_1", client_secret="wrong")
    with pytest.raises(OAuthError) as caught:
        await get(client)
    assert caught.value.code == "invalid_client"
    assert [r.path for r in api.requests] == ["/v1/oauth/token"]


async def test_a_token_answer_without_a_token_is_an_error(api: MockAPI, kind: Kind) -> None:
    api.answer({"json": {"token_type": "Bearer"}})
    client = api.client(kind, api_key=None, client_id="sp_1", client_secret="s")
    with pytest.raises(Exception, match="access_token"):
        await get(client)


async def test_a_token_without_a_lifetime_isnt_reused(api: MockAPI, kind: Kind, clock: Clock) -> None:
    def answer(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/v1/oauth/token":
            return httpx2.Response(200, json={"access_token": "t", "token_type": "Bearer"})
        return httpx2.Response(200, json={})

    client = api.answer(answer).client(kind, api_key=None, client_id="sp_1", client_secret="s")
    await get(client)
    await get(client)
    assert sum(r.path == "/v1/oauth/token" for r in api.requests) == 2


async def test_concurrent_async_callers_share_one_fetch(api: MockAPI, clock: Clock) -> None:
    client = routed(api).client("async", api_key=None, client_id="sp_1", client_secret="s")
    assert isinstance(client, AsyncQeetID)
    async with anyio.create_task_group() as group:
        for _ in range(10):
            group.start_soon(get, client)
    assert sum(r.path == "/v1/oauth/token" for r in api.requests) == 1
    assert sum(r.path == "/v1/users" for r in api.requests) == 10
