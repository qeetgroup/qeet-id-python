import httpx2
import pytest

from qeet_id import DEFAULT_BASE_URL, AsyncQeetID, QeetID, __version__
from qeet_id._config import build_user_agent, check_headers, is_loopback_host, normalize_base_url

from .conftest import Kind, MockAPI


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("https://api.id.qeet.in", "https://api.id.qeet.in"),
        ("https://api.id.qeet.in/", "https://api.id.qeet.in"),
        ("https://api.example/base/", "https://api.example/base"),
        ("http://localhost:4001", "http://localhost:4001"),
        ("http://api.test.id.qeet.localhost", "http://api.test.id.qeet.localhost"),
        ("http://127.0.0.1:4001/", "http://127.0.0.1:4001"),
        ("http://[::1]:4001", "http://[::1]:4001"),
    ],
)
def test_base_url_accepted(given: str, expected: str) -> None:
    assert normalize_base_url(given) == expected


@pytest.mark.parametrize(
    "given",
    [
        "",
        "api.id.qeet.in",
        "ftp://api.id.qeet.in",
        "http://api.id.qeet.in",
        "http://10.0.0.5",
        "https://user:pass@api.id.qeet.in",
        "https://api.id.qeet.in?x=1",
        "https://api.id.qeet.in#top",
    ],
)
def test_base_url_refused(given: str) -> None:
    with pytest.raises(ValueError, match="base_url"):
        normalize_base_url(given)


def test_loopback_hosts() -> None:
    assert is_loopback_host("LOCALHOST")
    assert is_loopback_host("127.8.9.1")
    assert not is_loopback_host("localhost.example")
    assert not is_loopback_host("192.168.1.1")


def test_user_agent_names_the_sdk_and_runtime() -> None:
    agent = build_user_agent()
    assert agent.startswith(f"qeet-id-python/{__version__} ")
    assert "python/" in agent


def test_user_agent_puts_the_application_first() -> None:
    agent = build_user_agent({"name": "brightleaf-onboarding", "version": "1.4 .0", "url": "https://x.example/(a b)"})
    # Spaces and parentheses are dropped: they would break the header's structure.
    assert agent.startswith("brightleaf-onboarding/1.4.0 (+https://x.example/ab) qeet-id-python/")


def test_user_agent_refuses_a_name_that_isnt_a_token() -> None:
    with pytest.raises(ValueError, match="app_info"):
        build_user_agent({"name": "Brightleaf Foods"})


@pytest.mark.parametrize("name", ["Authorization", "accept", "Content-Type", "User-Agent", "Idempotency-Key", "Host"])
def test_reserved_headers_are_refused(name: str) -> None:
    with pytest.raises(ValueError, match="sets it itself"):
        check_headers({name: "x"}, name="default_headers")


def test_header_line_breaks_are_refused() -> None:
    with pytest.raises(ValueError, match="line break"):
        check_headers({"X-Trace": "a\r\nInjected: 1"}, name="default_headers")


def test_header_names_and_values_must_be_strings() -> None:
    with pytest.raises(TypeError):
        check_headers({"X-Count": 1}, name="default_headers")  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="empty name"):
        check_headers({" ": "x"}, name="default_headers")


@pytest.mark.parametrize("cls", [QeetID, AsyncQeetID])
def test_one_credential_only(cls: type[QeetID] | type[AsyncQeetID]) -> None:
    with pytest.raises(ValueError, match="one credential"):
        cls(api_key="qk_x", client_id="c", client_secret="s")
    with pytest.raises(ValueError, match="go together"):
        cls(client_id="c")
    with pytest.raises(ValueError, match="non-empty"):
        cls(api_key="  ")


@pytest.mark.parametrize("cls", [QeetID, AsyncQeetID])
def test_options_are_checked(cls: type[QeetID] | type[AsyncQeetID]) -> None:
    with pytest.raises(ValueError, match="timeout"):
        cls(timeout=0)
    with pytest.raises(TypeError, match="timeout"):
        cls(timeout=True)
    with pytest.raises(ValueError, match="max_retries"):
        cls(max_retries=-1)
    with pytest.raises(ValueError, match="https"):
        cls(base_url="http://api.example")
    assert cls().base_url == DEFAULT_BASE_URL
    cls(timeout=httpx2.Timeout(5.0, connect=2.0))


@pytest.mark.parametrize("cls", [QeetID, AsyncQeetID])
def test_reprs_hold_no_secret(cls: type[QeetID] | type[AsyncQeetID]) -> None:
    for client in (cls(api_key="qk_live_secret"), cls(client_id="sp_1", client_secret="sp-secret-value")):
        text = repr(client) + repr(vars(client)) + repr(client._transport) + repr(client._transport._credential)
        assert "qk_live_secret" not in text
        assert "sp-secret-value" not in text


@pytest.mark.anyio
async def test_context_managers_close_their_own_client_only(kind: Kind) -> None:
    owned = QeetID(api_key="qk") if kind == "sync" else AsyncQeetID(api_key="qk")
    if isinstance(owned, QeetID):
        with owned:
            pass
        assert owned._transport._http.is_closed
    else:
        async with owned:
            pass
        assert owned._transport._http.is_closed

    api = MockAPI()
    client = api.client(kind)
    if isinstance(client, QeetID):
        with client:
            pass
    else:
        async with client:
            pass
    assert not client._transport._http.is_closed
