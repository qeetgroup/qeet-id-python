# ADR-0002: httpx2 for HTTP

**Status:** Accepted

## Context

The SDK needs one HTTP library with the same API for sync and async, timeouts per phase, connection
pooling, HTTP/2 when asked, a mock transport for tests, and active maintenance.

`httpx` has all of that except the last: 0.28.1 (December 2024) is its latest release, its issues and
discussions are closed, and its 1.0 is being written elsewhere with breaking changes. Pydantic forked
it as `httpx2`: the same public API (`Client`, `AsyncClient`, `Timeout`, `MockTransport`), Python 3.11
or later, the operating system's trust store through `truststore` rather than `certifi`, and regular
releases (2.16.0 on 21 October 2026). OpenAI's and WorkOS's Python SDKs moved to it; WorkOS still
accepts an `httpx` 0.28 client.

## Decision

Depend on `httpx2>=2.12,<3`. Callers who pass their own client pass an `httpx2.Client` or
`httpx2.AsyncClient`.

## Consequences

- Security fixes reach users; the minimum Python matches ours (3.11).
- TLS trusts the system's certificate store, which is what enterprises with inspection proxies need.
- An application that only has `httpx` installed gets `httpx2` alongside it; the two don't conflict.
- Switching back would be an import rename: the API is the same.
