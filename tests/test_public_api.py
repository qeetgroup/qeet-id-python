"""The package's public surface: what ``__all__`` promises, and what must never leak."""

import importlib
import importlib.metadata
import logging
from types import ModuleType

import httpx2
import pytest

import qeet_id
import qeet_id.tokens
import qeet_id.types
import qeet_id.webhooks
from qeet_id import QeetIDError

from .conftest import Kind, MockAPI, run

PUBLIC_MODULES = [qeet_id, qeet_id.types, qeet_id.webhooks, qeet_id.tokens]


@pytest.mark.parametrize("module", PUBLIC_MODULES, ids=lambda m: m.__name__)
def test_every_public_name_resolves_once(module: ModuleType) -> None:
    names = module.__all__
    assert len(names) == len(set(names))
    for name in names:
        assert hasattr(module, name), f"{module.__name__}.{name} is in __all__ but not defined"


@pytest.mark.parametrize("module", PUBLIC_MODULES, ids=lambda m: m.__name__)
def test_star_import_gives_exactly_all(module: ModuleType) -> None:
    namespace: dict[str, object] = {}
    exec(f"from {module.__name__} import *", namespace)  # noqa: S102 - the import statement under test
    assert set(namespace) - {"__builtins__"} == set(module.__all__)


def test_the_top_level_api() -> None:
    expected = {
        "QeetID",
        "AsyncQeetID",
        "QeetIDError",
        "APIError",
        "OAuthError",
        "NetworkError",
        "RequestTimeoutError",
        "SessionRevokedError",
        "TokenVerifier",
        "AsyncTokenVerifier",
        "TokenGuard",
        "AsyncTokenGuard",
        "construct_webhook_event",
        "ListResult",
        "Page",
        "AsyncPaginator",
        "RequestOptions",
        "__version__",
    }
    assert expected <= set(qeet_id.__all__)
    assert not [name for name in qeet_id.__all__ if name.startswith("_") and name != "__version__"]


def test_errors_share_one_base() -> None:
    for name in qeet_id.__all__:
        value = getattr(qeet_id, name)
        if isinstance(value, type) and issubclass(value, Exception):
            assert issubclass(value, QeetIDError), name


def test_the_version_is_the_installed_distributions() -> None:
    assert qeet_id.__version__ == importlib.metadata.version("qeet-id")


def test_importing_has_no_side_effects_on_logging() -> None:
    logger = logging.getLogger("qeet_id")
    assert [type(h) for h in logger.handlers] == [logging.NullHandler]
    assert logger.level == logging.NOTSET


def test_no_shadowed_builtins() -> None:
    import builtins  # noqa: PLC0415 - only this test needs it

    assert not set(qeet_id.__all__) & set(dir(builtins))


@pytest.mark.anyio
async def test_secrets_never_reach_an_error(api: MockAPI, kind: Kind, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="qeet_id")
    secrets = ("qk_live_do_not_leak", "sp-secret-do-not-leak", "client-secret-do-not-leak")
    api.answer(
        {"status": 401, "json": {"error": "invalid_client", "error_description": "Unknown client."}},
    )
    failures: list[BaseException] = []
    clients = [
        api.client(kind, api_key=secrets[0]),
        api.client(kind, api_key=None, client_id="sp_1", client_secret=secrets[1]),
    ]
    for client in clients:
        try:
            await run(client.users.get("u1"))
        except QeetIDError as error:
            failures.append(error)
        try:
            await run(client.oauth.introspect("tok", client_id="app", client_secret=secrets[2]))
        except QeetIDError as error:
            failures.append(error)
    network = MockAPI().answer(httpx2.ConnectError("connection refused"))
    try:
        await run(network.client(kind, api_key=secrets[0], max_retries=0).users.get("u1"))
    except QeetIDError as error:
        failures.append(error)
    assert len(failures) == 5
    text = " ".join(f"{e!s} {e!r} {e.__dict__!r}" for e in failures)
    text += " ".join(record.getMessage() for record in caplog.records)
    text += " ".join(repr(c) + repr(vars(c)) for c in clients)
    for secret in secrets:
        assert secret not in text


def test_the_generated_tree_mirrors_the_source() -> None:
    sync = importlib.import_module("qeet_id._sync.resources.identity")
    source = importlib.import_module("qeet_id._async.resources.identity")
    assert sorted(sync.__all__) == sorted(name.removeprefix("Async") for name in source.__all__)
