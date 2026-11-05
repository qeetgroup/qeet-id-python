# Changelog

All notable changes to the Qeet ID Python SDK are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-11-05

The SDK, built against the API's five OpenAPI documents, with the coverage and behaviour of the Node.js and
Go SDKs.

### Added

- **Two clients on one core.** `QeetID` and `AsyncQeetID` (asyncio and trio), with the same 38 namespaces
  and 269 calls. The async client is the source; the sync one is generated from it (`scripts/unasync.py`).
- **Credentials:** an API key (`Authorization: ApiKey`), or a service principal's `client_id` and
  `client_secret`, exchanged for an access token that is cached, renewed a minute before it expires, shared
  by concurrent calls, and dropped when the API refuses it.
- **Configuration:** `base_url` (https except for loopback hosts), `timeout` (seconds or an
  `httpx2.Timeout`), `max_retries`, `default_headers`, `app_info` and `http_client`; per call,
  `request_options` with `timeout`, `max_retries` and `headers`.
- **Typed errors:** `QeetIDError` → `APIError` with `BadRequestError`, `AuthenticationError`
  (→ `SessionRevokedError`), `PaymentRequiredError`, `PermissionDeniedError`, `NotFoundError`,
  `ConflictError`, `ValidationError`, `RateLimitError`, `InternalServerError` (→ `ServiceUnavailableError`)
  and `OAuthError`; `NetworkError` → `RequestTimeoutError`; `WebhookVerificationError` and
  `TokenVerificationError`. API errors carry `status`, `code`, `message`, `request_id`, `detail`, `fields`,
  `metadata`, `retryable`, `retry_after`, `translation_key` and `headers`.
- **Retries that can't do anything twice:** `GET`, `DELETE`, read-only POSTs and requests carrying an
  `Idempotency-Key`, after no response, a timeout, 408, 429, 500, 502, 503, 504 or
  `409 idempotency.in_progress`; exponential backoff with jitter; `Retry-After` honoured up to 60 s. Never a
  401, so never `auth.session_revoked`.
- **Idempotency keys** on the nine creates the API makes idempotent, generated per call or the caller's own.
- **Pagination:** paged lists iterate every item (`for`, or `async for`); the async `list()` is also
  awaitable for one page. Whole lists are a `ListResult` with `truncated`.
- **Resources** for every call an API key may make in the identity, access, federation, developer and
  operations areas, with `TypedDict` requests and responses in `qeet_id.types`.
- **Webhooks:** `construct_webhook_event`, `verify_webhook_signature`, `sign_webhook_payload`,
  `WEBHOOK_HEADERS`, `WEBHOOK_EVENT_TYPES` and the `WebhookEvent` type. Several secrets during a rotation;
  five minutes of tolerance by default. Tested against deliveries made by the server's own signing code.
- **Access tokens:** `TokenVerifier` and `AsyncTokenVerifier`, with `from_discovery`. ES256 only, `kid`
  required, issuer and audience required, 30 s of leeway, a five-minute JWKS cache, a 30-second cooldown on
  refetching for an unknown `kid`, and cached keys kept through an outage.
- **OAuth:** client credentials (with `expires_in` and `expires_at`), authorization code, refresh, token
  exchange, device and CIBA polling, device and backchannel authorization, introspection, revocation,
  discovery, consent grants, device authorizations, signing keys, and a `TokenGuard` that introspects.
- **Logging** to the `qeet_id` logger: method, path, status, duration, attempt and request ID; never
  credentials, query strings, headers or bodies.
- `py.typed`; `mypy --strict` across the package, tests, scripts and examples.

### Differences from the Node.js SDK

- Names follow PEP 8: snake_case methods and namespaces (`api_keys`, `list_sessions`), acronyms in capitals
  in class names (`APIError`, `SAMLConnection`).
- OAuth clients authenticate with `client_secret_basic`, form-encoded first (RFC 6749 §2.3.1), rather than
  in the form body. The client-credentials grant is retried like a read.
- `groups.create` sends no `tenant_id`: the API takes the organisation from the credential.
- `PaymentRequiredError` for 402.

[Unreleased]: https://github.com/qeetgroup/qeet-id-python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/qeetgroup/qeet-id-python/releases/tag/v0.1.0
