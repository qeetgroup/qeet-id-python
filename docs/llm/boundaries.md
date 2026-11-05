# Boundaries — qeet-id-python

**Level:** L2 · **Last verified:** 2026-11-05

## Owns

Typed Python bindings, sync and async, for the Qeet ID API calls an API key may make · HTTP execution with
timeouts and safe retries · credentials (API key, cached client-credentials tokens) · cursor pagination ·
the exception hierarchy · webhook delivery verification · access-token verification · the OAuth flows ·
the PyPI package.

## Does not own

| Not owned | Owner |
| --- | --- |
| **The API contract** | `qeet-id-server` — `api/openapi/*.yaml`, handlers, route policy |
| Authorization, tenancy, token issuance | `qeet-id-server` |
| A person's own account (sessions, factors, passkeys, email change) | the hosted pages and `qeet-id-react` |
| The Node.js and Go stories | `qeet-id-node`, `qeet-id-go` |
| Documentation site | `qeet-id-docs` |
| Organization / product standards | `qeet-context` (L0) / `qeet-id-context` (L1) |

**The SDK never adds behaviour the API lacks.** A missing endpoint is server work.

## Consumes

`api.id.qeet.in` over HTTPS: `Authorization: ApiKey <key>` or `Bearer <token>` for management calls;
HTTP Basic (or `client_id` in the form, for public clients) for the OAuth endpoints; the JWKS and discovery
documents. Nothing else — no database, no filesystem, no environment variables.

## Provides

A PyPI package whose **public names** (`qeet_id.__all__`, `qeet_id.types`, `qeet_id.webhooks`,
`qeet_id.tokens`) are its contract. Once published, every one is a semver promise.

## Security boundaries

| Boundary | Enforcement |
| --- | --- |
| Credential → wire | `_async/_transport.py`, `_async/_credentials.py` — https only; no redirects; never logged or in an error or repr |
| Token → claims | `_jwt.py`, `_async/_token_verifier.py` — ES256, known kid, issuer and audience required |
| Webhook body → event | `webhooks.py` — HMAC over timestamp and body, constant-time, replay window |
| Retry → side effects | `_retry.py`, `_async/_transport.py` — writes retried only with an idempotency key |
| Identifier → path | `_request.py` `path()` — percent-encoded; empty and dot segments refused |

**This SDK is not a trust boundary.** It runs in the caller's process with the caller's credentials.

## Requires coordination

| Change | Why |
| --- | --- |
| **Any public name** | It is the package's contract |
| Auth scheme or OAuth client authentication | Must match the server |
| Retry policy | A wrong change duplicates server-side writes |
| Webhook signature or header | Must match `internal/developer/webhooks` |
| Exception classes | Callers catch them |
| Python version floor | Affects who can install |
| A runtime dependency | Changes what every consumer installs |

## Hard limits

1. **Never hand-edit the generated sync tree.**
2. **Never add a runtime dependency** without the owner.
3. **Never retry a write without an idempotency key**, a single-use grant, a directory sign-in, or a 401.
4. **Never rename a wire field** (ADR-0004).
5. **Never log or embed a credential**, including in a raised error or a repr.
6. **Never skip signature, timestamp, issuer, audience or kid checks**, even in tests.
7. **Never wrap a route an API key can't call.**
8. **Never change another repository** from a task scoped to this one.
