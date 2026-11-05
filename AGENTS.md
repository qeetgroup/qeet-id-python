# AGENTS.md — qeet-id-python

**The model-neutral instruction file for coding agents.** [CLAUDE.md](CLAUDE.md),
[GEMINI.md](GEMINI.md) and [.github/copilot-instructions.md](.github/copilot-instructions.md) point
here and add nothing architectural.

## What this repository is

The **server-side Python SDK for Qeet ID**, `qeet-id` on PyPI, imported as `qeet_id`. Python 3.11 or
later, uv and Ruff, `mypy --strict`, three runtime dependencies (`httpx2`, `anyio`, `cryptography`),
built with `uv_build`.

It is a **client of a contract it does not own.** The contract is `qeet-id-server`'s five OpenAPI
documents (`api/openapi/{auth,management,federation,developer,operations}.yaml`), snapshotted in
`tests/contract/openapi.json`, with the server's handlers as the tiebreaker. The SDK wraps them and never
adds behaviour the API lacks.

## Read before changing code

| File | For |
| --- | --- |
| [qeet-repo.yml](qeet-repo.yml) | Machine-readable identity |
| [docs/llm/architecture-map.md](docs/llm/architecture-map.md) | "Where is X?" |
| [docs/llm/context.md](docs/llm/context.md) | How this SDK works |
| [docs/llm/boundaries.md](docs/llm/boundaries.md) | What it owns, and what it must not touch |
| [docs/llm/workflows.md](docs/llm/workflows.md) | Adding a method; regenerating; releasing |
| [docs/engineering-practices.md](docs/engineering-practices.md) | The practices followed, with sources |

Decisions: `docs/design-decisions/` (ADR-0001 to ADR-0007), all binding.

## Rules

1. **Edit `src/qeet_id/_async/`, never `src/qeet_id/_sync/`.** The sync tree is generated
   (`uv run python scripts/unasync.py`), except `__init__.py`, `_compat.py` and `_resource.py`, which are
   kept by hand in both trees (ADR-0001).
2. **Three runtime dependencies.** Adding one is the owner's decision. Development tools go in the `dev`
   dependency group.
3. **One module per API area** — `resources/{identity,access,federation,oauth,developer,operations}.py`,
   types in `qeet_id/types/` (ADR-0003).
4. **Wire objects are `TypedDict`s with the API's field names;** bodies are keyword arguments typed with
   `Unpack`, identifiers positional-only, per-call settings in `request_options` (ADR-0004).
5. **Every method raises on failure;** errors the SDK makes extend `QeetIDError`; argument mistakes are
   `ValueError`/`TypeError`.
6. **Never wrap a route an API key can't call.** The request table checks every method against the
   snapshot's security, query, body, idempotency and list shape.
7. **Retries must never do anything twice** (ADR-0005). Only `GET`, `DELETE`, POSTs marked `retry_safe`
   and requests with an `Idempotency-Key` are retried. Never make `PUT`, `PATCH`, another POST, a
   single-use grant or directory sign-in retryable. Never retry a 401.
8. **Never weaken verification:** `src/qeet_id/webhooks.py`, `src/qeet_id/_jwt.py`,
   `src/qeet_id/_async/_token_verifier.py`, `src/qeet_id/_async/_transport.py` (credentials, redirects).
9. **No credentials anywhere they could leak:** not in errors, logs, reprs or tests' output.
10. **Public names** are in `__all__`; everything else lives in an `_underscored` module.
11. **Tests:** add the method's row to `tests/test_resources.py`; behaviour to `tests/test_behaviour.py`.
    Webhook fixtures come from the server's own signing code (`scripts/capture_webhook_fixtures.sh`), never
    from hand.

## Commands

```bash
uv sync                                  # the locked environment
make check                               # what CI runs: lint, generated client, mypy, tests, package, audit
make lint                                # ruff check, ruff format --check, unasync --check
make typecheck                           # mypy --strict
make test                                # pytest
make coverage                            # pytest with branch coverage, 95% floor
make matrix                              # the tests on Python 3.11 to 3.15
make sync                                # regenerate src/qeet_id/_sync
make package                             # uv build, twine check, wheel contents
make audit                               # pip-audit over every locked dependency
```

## What CI enforces

`ci.yml` on Python 3.11, 3.12, 3.13, 3.14 and 3.15: tests with coverage; then build, `twine check` and the
wheel's contents. `lint.yml`: Ruff, the generated client and mypy. `security.yml`: pip-audit and gitleaks.
`codeql.yml`: Python and the workflows. `version.yml` bumps the patch in `pyproject.toml` on every pull request into `main`
(raise minor or major by hand). `release.yml` runs on every push to `main`: when PyPI does not have that
version yet, it runs the gate, builds, publishes by trusted publishing, then tags `vX.Y.Z` and opens a
GitHub Release; otherwise it does nothing. The
workflows run on pushes to `main` and pull requests to it, not on other branches.

## Branches

Two long-lived branches: `develop`, where work lands, and `main`, what is released. Changes reach `main`
only by a pull request from `develop`. There are no release branches: a version is a `vX.Y.Z` tag, made
by `release.yml` when a pull request is merged into `main`.

## Before you finish

```bash
make check
git diff
```

## Escalate rather than proceed

A runtime dependency · renaming or removing a public name · the auth scheme · weakening verification ·
making a non-idempotent call retryable · anything requiring another repository · the package name, the
first published version or the licence.
