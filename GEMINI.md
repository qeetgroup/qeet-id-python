# GEMINI.md — qeet-id-python

**Read [AGENTS.md](AGENTS.md) first.** It is the model-neutral instruction file and the source of
truth for this repository. This file is a pointer and adds no architecture.

```text
GEMINI.md  →  AGENTS.md  →  docs/llm/*
```

## Canonical context

| File | For |
| --- | --- |
| [qeet-repo.yml](qeet-repo.yml) | Machine-readable repository identity |
| [AGENTS.md](AGENTS.md) | **Rules, commands, what CI enforces** |
| [docs/llm/context.md](docs/llm/context.md) | How this repository actually works |
| [docs/llm/boundaries.md](docs/llm/boundaries.md) | What it owns, and what it must not touch |
| [docs/llm/workflows.md](docs/llm/workflows.md) | Step-by-step for common changes |
| [docs/llm/architecture-map.md](docs/llm/architecture-map.md) | "Where is X?" — fastest path to a file |

Parent context: **L0** `qeetgroup/qeet-context` · **L1** `qeetgroup/qeet-id-context`.

## What this repository is

The server-side **Python SDK for Qeet ID** — `qeet-id`, imported as `qeet_id`. Python 3.11+, uv, Ruff,
`mypy --strict`, three runtime dependencies (`httpx2`, `anyio`, `cryptography`). A sync and an async
client; the sync one is generated from the async one. It wraps a contract owned by `qeet-id-server`.

## Non-negotiables

1. **Edit `_async/`; `_sync/` is generated.**
2. **Three runtime dependencies.**
3. **Wire fields are the API's own** (ADR-0004).
4. **Only routes an API key may call** — the request table checks the contract snapshot.
5. **Retries never repeat a write** (ADR-0005).
6. **Never weaken** webhook or token verification.

## Commands

`uv sync` · `make check` · `make lint` · `make typecheck` · `make test` · `make coverage` · `make matrix` · `make sync` · `make package` · `make audit`

That list is complete — **do not invent commands.**

## Before finishing

```bash
make check
git diff
```
