# ADR-0001: One core; the async client is the source, the sync one is generated

**Status:** Accepted

## Context

Python callers need both a blocking client (Django, Flask, scripts, Celery) and an `asyncio` one
(FastAPI, Starlette, aiohttp apps). The Azure guidelines say not to mix them in one class, and every
SDK we compared ships two (`OpenAI`/`AsyncOpenAI`, `WorkOSClient`/`AsyncWorkOSClient`). Writing about
270 methods twice by hand doubles the code and lets the two drift.

## Decision

- Everything that isn't I/O is written once and shared: the error mapping (`_errors.py`), the retry
  policy (`_retry.py`), request encoding and path building (`_request.py`), configuration
  (`_config.py`), pagination types (`_pagination.py`), JWT checks (`_jwt.py`), webhook verification.
- The I/O layer is written once, for `async`, under `src/qeet_id/_async/`: the transport, the
  credentials, the client, the token verifier and every resource.
- `scripts/unasync.py` generates `src/qeet_id/_sync/` from it: `async`/`await` removed, `Async*`
  names renamed, `httpx2.AsyncClient` → `httpx2.Client`, AnyIO's lock and sleep → `threading` and
  `time` (through a two-line `_compat` module per tree). Ruff then sorts and formats the output.
- Three modules differ in more than syntax and are kept by hand in both trees: `__init__.py`,
  `_compat.py` and `_resource.py` (the sync `list()` fetches its first page at once; the async one
  returns an awaitable, async-iterable `AsyncPaginator`).
- The generated tree is committed, so the package needs no build step and its source is readable.
  `make lint` and CI run `scripts/unasync.py --check`, which fails on a hand edit or a stale copy.

## Consequences

- A method is written, reviewed and tested once; the request table runs it on both clients.
- Contributors edit `_async/` only. The generated files say so in their first line.
- The approach is httpcore's, whose `scripts/unasync.py` does the same.
