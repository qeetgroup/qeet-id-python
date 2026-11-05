# ADR-0005: Retry only what can't happen twice

**Status:** Accepted (the Node.js SDK's ADR-0005, unchanged in substance)

## Decision

A request is **retry-safe** when it is a `GET` or `DELETE`, a POST that changes nothing (checks,
evaluations, previews, introspection, revocation, the client-credentials grant), or it carries an
`Idempotency-Key`. Only retry-safe requests are retried, and only after no response, a timeout,
`408`, `429`, `500`, `502`, `503`, `504`, or `409 idempotency.in_progress`.

- `PUT`, `PATCH` and other POSTs are never retried, nor are single-use OAuth grants (code, refresh,
  token exchange, device code, CIBA) and directory sign-ins (each attempt counts toward the lockout).
- A `401` is never retried, so neither is `auth.session_revoked`, though the server marks it
  `retryable` (meaning "sign in again").
- The nine routes that honour `Idempotency-Key` always get one: a UUID4 per call, kept across that
  call's retries, or the caller's own (1 to 255 printable ASCII characters, checked before sending).
- Backoff: `Retry-After` (the header, or the envelope's `metadata.retry_after`) when it is at most
  60 s, otherwise the error is raised; else 0.5 s doubling to 8 s with equal jitter. Two retries by
  default.
- Fetching the client-credentials token happens outside the request's retry loop: a refused client
  is reported at once, not retried as if the request had failed.

## Difference from the Node.js SDK

The client-credentials grant is retried like a read: asking again only issues another token. Node.js
treats every grant as single-use.
