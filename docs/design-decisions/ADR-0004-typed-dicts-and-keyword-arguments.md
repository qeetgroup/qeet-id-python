# ADR-0004: Wire objects are TypedDicts with the API's names; bodies are keyword arguments

**Status:** Accepted

## Context

The SDK needs typed requests and responses for about 240 shapes. The options were pydantic models
(OpenAI), dataclasses with conversion code (WorkOS), or `TypedDict` (Stripe's request parameters,
OpenAI's too).

## Decision

- Every request and response is a `TypedDict` whose keys are the API's own field names (snake_case,
  as the Node.js SDK keeps them, its ADR-0004). Responses are the decoded JSON, as is: `user["email"]`.
- Request bodies are keyword arguments typed with `Unpack[...Params]` (PEP 692):
  `client.users.create(tenant_id=..., email=...)`. Identifiers come first and are positional-only;
  everything else is keyword-only. A Python keyword is spelt with a trailing underscore and sent
  without it (`from_` → `from`).
- Per-call settings are one `request_options` argument (`timeout`, `max_retries`, `headers`), and
  `idempotency_key` exists only on the nine methods the API makes idempotent.
- Response fields the server may extend are `Literal[...] | str`; request fields are closed
  `Literal`s, so a type checker catches a misspelt value.
- The SDK's own values are dataclasses: `ListResult`, `FieldError`.

## Why

- The lightest option that still type-checks every call: no runtime dependency, no conversion layer,
  no model to keep in step with the server. mypy and pyright check keys and value types, and editors
  complete them.
- Fields the API adds later reach the caller untouched instead of being dropped by a model.
- PATCH semantics stay exact: a key that isn't passed isn't sent, and `None` is sent as `null`.

## Consequences

- No runtime validation of responses: the server is the source of truth, as in the Node.js SDK.
- Attribute access (`user.email`) isn't available; that would take a model layer, a dependency or
  generated classes. Revisit if callers ask for it; it would be additive.
