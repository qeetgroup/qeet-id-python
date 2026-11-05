# GitHub Copilot — qeet-id-python

**Canonical instructions: [`AGENTS.md`](../AGENTS.md).** This file is a summary; it adds no
architecture.

## Repository

The server-side **Python SDK for Qeet ID** — `qeet-id`, imported as `qeet_id`. Python 3.11+, uv, Ruff,
`mypy --strict`, three runtime dependencies. It wraps a contract owned by `qeet-id-server`.

## Structure

`src/qeet_id/_async/` (the source: transport, credentials, client, token verifier, resources) ·
`src/qeet_id/_sync/` (generated from it) · `src/qeet_id/_*.py` (shared: errors, retries, requests,
pagination, JWT checks) · `src/qeet_id/types/` (the API's request and response types) ·
`src/qeet_id/webhooks.py` · `src/qeet_id/tokens.py` · `src/qeet_id/__init__.py` (every export).

## Rules

1. **Edit `_async/`, never `_sync/`;** run `make sync`.
2. **Three runtime dependencies.**
3. **Wire fields are the API's own;** bodies are keyword arguments, identifiers positional.
4. **Only routes an API key may call.**
5. **Retries never repeat a write:** GET, DELETE, `retry_safe` POSTs and idempotency-keyed requests only.
6. **Never weaken** webhook or token verification.

## Commands

`uv sync` · `make check` · `make lint` · `make typecheck` · `make test` · `make sync`

## Do not

- suggest adding a runtime dependency
- hand-edit a file under `src/qeet_id/_sync/` that starts with "Generated from"
- rename a wire field
- make PUT, PATCH, a non-idempotent POST, a single-use OAuth grant or directory sign-in retryable
- log, embed or echo an API key, client secret or token — including inside a raised error
- invent commands — read the `Makefile`
