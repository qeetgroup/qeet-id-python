# Repository Context — qeet-id-python

**Level:** L2 · **Status:** active · **Evidence state:** verified · **Last verified:** 2026-11-05
**Verification scope:** exports, transport behaviour, constants, CI jobs and tests read from source; every
method's request checked against `qeet-id-server`'s OpenAPI documents (snapshot of
`fix/server-release-1.0`, commit `ccbb9bde`).

## Identity

`qeet-id` (import `qeet_id`) — the server-side Python SDK for Qeet ID. Python 3.11 or later, uv, Ruff,
`mypy --strict`, built with `uv_build`. Runtime dependencies: `httpx2`, `anyio`, `cryptography`.

**Status: development. No version on PyPI yet.**

## Context inheritance

```text
qeet-context (L0)  →  qeet-id-context (L1)  →  qeet-id-server (the contract)
                                            →  qeet-id-python (L2 — this document)
```

## Architecture

```text
caller
  ↓  QeetID(api_key=…)  or  AsyncQeetID(client_id=…, client_secret=…)
client                 namespaces: client.users, client.webhooks.deliveries, …          (ADR-0003)
  ↓
resources/<area>.py    one class per namespace; path() for paths; TypedDict bodies       (ADR-0004)
  ↓
transport              headers → credential → body → httpx2 with timeout → typed error → retry if safe
  ↓
api.id.qeet.in
```

The async tree is written by hand; the sync tree is generated from it (ADR-0001). Standalone, needing no
client: `qeet_id.webhooks` and `qeet_id.tokens`.

## Transport

| Property | Value |
| --- | --- |
| Base URL | `https://api.id.qeet.in`; https required except for loopback hosts |
| Auth | `Authorization: ApiKey <key>`, or `Bearer <token>` from the client-credentials grant (cached, renewed 60 s early, dropped on a 401); none on the public and OAuth endpoints |
| OAuth client auth | `client_secret_basic`, form-encoded first; `client_id` in the form for a public client (ADR-0007) |
| Timeout | 30 s per attempt (connect, read, write, pool), or an `httpx2.Timeout` |
| Retries | 2, for GET, DELETE, `retry_safe` POSTs and idempotency-keyed requests; after no response, timeout, 408, 429, 500, 502, 503, 504, 409 `idempotency.in_progress`; never a 401 |
| Backoff | 0.5 s doubling to 8 s, equal jitter; `Retry-After` (header or `metadata.retry_after`) honoured up to 60 s |
| Idempotency-Key | UUID4 per call on the nine idempotent routes; caller may pass one |
| Redirects | not followed |
| User-Agent | `[app_info ]qeet-id-python/<version> cpython/<version> (<os>; <arch>)` |
| Logging | `qeet_id` logger; method, path, status, duration, attempt, request ID only |
| Escape hatch | `http_client` |

## Errors

`QeetIDError` → `APIError` (status classes, `SessionRevokedError`, `PaymentRequiredError`, `OAuthError`),
`NetworkError` → `RequestTimeoutError`, `WebhookVerificationError`, `TokenVerificationError`. `APIError`
reads the envelope `{"error": {code, message, detail, translation_key, fields, metadata, retryable,
request_id}}`; the envelope's `request_id` wins over an `X-Request-Id` header. `OAuthError` reads RFC 6749
`{error, error_description, error_uri}`.

## Testing

`tests/` with pytest and AnyIO's plugin; most tests run once per client (`kind` fixture). HTTP is
`httpx2.MockTransport` (`tests/conftest.py`'s `MockAPI`); there is no server. `tests/test_resources.py`
sends all 269 methods through both clients and checks each request against `tests/contract/openapi.json`.
Webhook fixtures are deliveries made by the server's own `deliver` and `sign`. Token tests sign with real
P-256 keys.

## Known constraints

- Three runtime dependencies is a hard rule.
- No version is published, so the public API can still change. That ends at the first release.
- Some server areas are not wrapped yet; see `docs/FUTURE.md`.

## Documentation authority

Source > tests > README > this file. The **API contract** is owned by `qeet-id-server`.
