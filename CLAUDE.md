# CLAUDE.md — qeet-id-python

**Read [AGENTS.md](AGENTS.md) first.** It is the model-neutral instruction file and the source of
truth for this repository. This file adds only Claude-specific guidance.

```text
CLAUDE.md  →  AGENTS.md  →  docs/llm/*
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

## The things most likely to trip you up here

1. **`src/qeet_id/_sync/` is generated.** Edit `_async/`, then `make sync`.
2. **Three runtime dependencies**, no more.
3. **Wire fields are the API's own** in `TypedDict`s; bodies are keyword arguments (ADR-0004).
4. **Only routes an API key may call;** the request table checks the contract snapshot.
5. **Retries never repeat a write** (ADR-0005); never retry a 401.
6. **Never weaken** `webhooks.py`, `_jwt.py`, the token verifier or the transport.

## Working style

- **Read before editing.** Match the neighbouring method rather than introducing an abstraction.
- Use the architecture map instead of guessing a path.
- **Do not read `.env*` or secret files** into anything you write.

## Finishing a change

```bash
make check
git diff
```

## Escalate rather than proceed

Stop and report if a task would weaken a security control, change a published contract, or require
modifying another repository.
