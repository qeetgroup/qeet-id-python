# Architecture

## Layers

```text
src/qeet_id/__init__.py          every export: the package's contract
src/qeet_id/_async/              the source: transport, credentials, client, token verifier, resources
src/qeet_id/_sync/               generated from _async by scripts/unasync.py (but _compat, _resource)
src/qeet_id/_errors.py           the exception hierarchy and error_from_response
src/qeet_id/_retry.py            which failures are retried, and after how long
src/qeet_id/_request.py          Request, path(), query and body encoding, idempotency keys, Basic auth
src/qeet_id/_pagination.py       ListResult, Page, AsyncPage, AsyncPaginator
src/qeet_id/_config.py           base URL rules, headers, User-Agent
src/qeet_id/_jwt.py              ES256 JWS parsing, signature and claim checks, JWKS parsing
src/qeet_id/types/               the API's request and response TypedDicts, one module per area
src/qeet_id/webhooks.py          webhook verification (no client needed)
src/qeet_id/tokens.py            TokenVerifier and AsyncTokenVerifier (no client needed)
```

Nothing shared imports a resource; the generated tree imports only shared modules and itself.

## A request's path

1. A resource method builds the path with `path()`, which percent-encodes each identifier as one segment
   and refuses empty and dot segments, then calls `_request`, `_list` or `_paginate` with a query, a JSON
   body, a form or raw content, and flags: `authenticate=False` for endpoints that authenticate otherwise,
   `client_auth` for OAuth client authentication, `idempotent` for routes that honour `Idempotency-Key`,
   `retry_safe` for POSTs that change nothing, `retries=False` for calls that must not repeat.
2. The transport merges the headers (the client's, the call's, then `Accept`, `User-Agent`,
   `Idempotency-Key`, `Content-Type`, which callers can't replace), encodes the body and the query (booleans
   as `true`/`false`, `from_` as `from`), and runs attempts.
3. Before each attempt it asks the credential for `Authorization`: the API key, or a cached
   client-credentials token, fetched outside the retry loop. A 401 drops a cached token.
4. Each attempt has its own timeout. Redirects aren't followed. A response that isn't 2xx becomes a typed
   error (`error_from_response`); no response becomes `NetworkError` or `RequestTimeoutError`, chained to
   the httpx2 exception.
5. A failed attempt is retried only if the request is retry-safe and the failure transient
   (`is_retryable`), after `retry_delay`.

## Pagination

On the sync client, a paged `list()` fetches its first page and returns a `Page`; iterating it fetches the
rest. On the async client it returns an `AsyncPaginator`, which sends nothing until awaited (one
`AsyncPage`) or iterated (every item). Both stop if the server repeats a cursor. Whole lists are a
`ListResult` with `truncated`.

## Webhooks and tokens

`construct_webhook_event` and the token verifiers need no client, so webhook receivers and resource servers
need no API key. Webhooks use `hmac` and `hashlib`; tokens use `cryptography` for ECDSA (ADR-0006). The
verifier caches the JWKS for five minutes, refetches for an unknown `kid` at most every 30 seconds, and
keeps verifying with the keys in hand while the issuer can't be reached.
