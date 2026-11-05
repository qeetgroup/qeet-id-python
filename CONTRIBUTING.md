# Contributing

## Setup

```bash
git clone https://github.com/qeetgroup/qeet-id-python
cd qeet-id-python
uv sync
make check   # lint, generated client, mypy, tests with coverage, package, audit
```

Requires [uv](https://docs.astral.sh/uv/) 0.13 or later (CI uses 0.13.7; `uv self update` upgrades it); it installs the Python the project needs.

## Conventions

- **The contract is the server's.** Every route comes from `qeet-id-server`'s OpenAPI documents and must be
  one an API key may call; `tests/test_resources.py` checks each method against the snapshot in
  `tests/contract/openapi.json`. Where a document is ambiguous, the server's handler decides.
- **Edit `src/qeet_id/_async/`; generate `_sync/`** with `make sync` (ADR-0001).
- **One module per API area** for resources and types (ADR-0003).
- **Names:** PEP 8 — snake_case methods and namespaces, CapWords classes with acronyms in capitals
  (`APIKeys`, `SAMLConnection`), standard verbs without the resource's noun (`users.create`).
- **Wire objects keep the API's field names** as `TypedDict`s; bodies are keyword arguments (ADR-0004).
- **Every method raises.** Use `path()` for paths; let the transport make errors.
- **Retries:** `retry_safe` only if repeating changes nothing; `idempotent` only where the route honours an
  `Idempotency-Key` (ADR-0005).
- **No new runtime dependency** without the owner.
- **No credentials** in errors, logs, reprs, tests' output or examples.

## Commands

| Command | |
| --- | --- |
| `make lint` | `ruff check`, `ruff format --check`, the generated client is up to date |
| `make format` | fix what Ruff can and format |
| `make typecheck` | `mypy --strict` over `src`, `tests`, `scripts` and `examples` |
| `make test` · `make coverage` | pytest; with branch coverage and a 95% floor |
| `make matrix` | the tests on Python 3.11, 3.12, 3.13, 3.14 and 3.15 |
| `make sync` | regenerate `src/qeet_id/_sync` |
| `make package` | build, `twine check --strict`, and the wheel's contents |
| `make audit` | pip-audit over every locked dependency |
| `make check` | all of the above that CI runs |

## Tests

Every method has a row in `tests/test_resources.py`; the test fails for a method without one. Behaviour gets
its own test, usually run on both clients through the `kind` fixture. Use `tests/conftest.py`'s `MockAPI`.
Webhook fixtures are captured from the server's own signing code; never edit them by hand.

## Commits and branches

Conventional commit titles (`feat(resources): …`, `fix(core): …`). Work lands on `develop`; `main` changes
only by a pull request from `develop`.

## Reporting bugs

Open an issue with the call, what you expected, what happened, and the `request_id` of the error.
