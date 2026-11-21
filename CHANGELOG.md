# Changelog

All notable changes to the Qeet ID Python SDK are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-11-21

Follows the API's rename of tenant to organization, and its single OAuth token endpoint. The API accepts
no old names alongside the new ones, so 0.1.0 can't call it: upgrade, then rename in your code as below.

### Changed (breaking)

- **Organization, not tenant, everywhere.** `client.tenants` is `client.organizations`
  (`AsyncTenants` is `AsyncOrganizations`); every path under `/v1/tenants/{id}/…` is
  `/v1/organizations/{id}/…`, and `/v1/users/{id}/tenants/{id}/…` is `/v1/users/{id}/organizations/{id}/…`.
  Every `tenant_id` argument, request field and response field is `organization_id`. Types:
  `Tenant` → `Organization`, `TenantUpdateParams` → `OrganizationUpdateParams`, `TenantDeletion` →
  `OrganizationDeletion`, `TenantBranding` → `OrganizationBranding`, `TenantRateLimits` →
  `OrganizationRateLimits` (its `tenant` bucket is `organization`). `home_tenant_name` is
  `home_organization_name`; a decision's `decided_by.model` and an email template's `delivery_scope` say
  `organization`.
- **Access tokens** carry `organization_id` in place of `tenant_id`: `AccessTokenClaims` follows.
- **Webhooks:** an event's `organization_id` replaces `tenant_id` (`construct_webhook_event` requires it), and
  `tenant.suspended`, `tenant.reactivated` and `tenant.deleted` are `organization.suspended`,
  `organization.reactivated` and `organization.deleted`.
- **One token endpoint.** The authorization-code, refresh, token-exchange, device and CIBA grants post to
  `POST /v1/oauth/token`, with `grant_type` choosing the grant; `/v1/oauth/token-code` is gone.
- **Agent tokens** (`agents.create_token`) are the client-credentials grant at `POST /v1/oauth/token`: the
  agent's id and secret go as HTTP Basic client credentials, in place of a JSON body to `/v1/agents/token`. A
  refusal is an `OAuthError` (`invalid_client`, or `unauthorized_client` for an agent that isn't active), and
  `AgentToken` gains `expires_at`. Asking again only issues another token, so the call is retried like a read.
- `organizations.update` no longer takes `plan`, which the API refuses there, and takes `logo_url`;
  `Organization` gains `logo_url`, its `plan` may be `starter`, and its `metadata` may be `None`.
- Every request body field, query parameter and enum value the SDK sends or expects was compared with the API
  documents, and these follow them:
  - `users.list(mfa=…)` takes `"on"` or `"off"`: a boolean was sent as `true`/`false`, which the API refuses with
    400. It also takes the API's newer filters `admins_without_mfa`, `in_group`, `id` and `email` (each a list,
    sent repeated), `include_deleted`, `sort` (`created`, `name`, `last_seen`) and `order` (`asc`, `desc`).
  - `User.status` may be `deleted`, with `deleted_at`, on a member listed with `include_deleted`.
  - `audit_logs.anomalies.update_settings` takes `AuditAnomalySettingsUpdateParams`, with `enabled`,
    `score_threshold` and `min_baseline_events` all required (an update replaces all three);
    `AuditAnomalySettings` gains `organization_id`.
  - `SecurityPolicyUpdateParams` drops `password_min_length` and `password_complexity`, which the API retired
    and ignores, and `mfa_enforced_since`, which is read-only (it stays on `SecurityPolicy`).
  - `BotActivity`'s verdicts are `items`, as the API sends them, not `recent`.
  - `IPRuleList` gains `truncated`.
  - `SAMLConnectionUpdateParams` takes `allow_idp_initiated`, and `SAMLServiceProviderCreateParams` and
    `SAMLServiceProviderUpdateParams` take `status`.
  - Enum values the API added: `audit.chain_checkpoint_gone` and `audit.chain_checkpoint_unsigned` on an audit
    chain verification, `expired` on a data export.

### Changed

- The contract snapshot and webhook fixtures come from the server's `develop`, whose documents are
  `identity.yaml` and `access.yaml` (formerly `management.yaml` and `auth.yaml`), its event catalogue in
  `internal/developer/webhook`, and its request signing in `internal/platform/crypto/requestsig`.
- Docstrings and documents spell organization as the API does.

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

[Unreleased]: https://github.com/qeetgroup/qeet-id-python/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/qeetgroup/qeet-id-python/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/qeetgroup/qeet-id-python/releases/tag/v0.1.0
