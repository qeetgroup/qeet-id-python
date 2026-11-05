# ADR-0003: Resources as namespaces, one module per API area

**Status:** Accepted

## Decision

One client, with every resource a direct attribute named in snake_case (`client.users`,
`client.api_keys`, `client.saml_connections`). Where the API nests a collection, the SDK nests too:
`webhooks.deliveries`, `oauth.grants`, `oauth.devices`, `oauth.signing_keys`,
`applications.resources`, `audit_logs.anomalies`, `gdpr.erasures`, `gdpr.exports`. No other nesting.
The namespaces and method names are the Node.js SDK's, in snake_case.

The resource classes live in one module per OpenAPI document of the server, in both trees:
`resources/identity.py` (management.yaml), `access.py` (auth.yaml), `federation.py` and `oauth.py`
(federation.yaml), `developer.py`, `operations.py`. The types follow the same split under
`qeet_id/types/`.

Class and type names follow PEP 8, acronyms in capitals (`APIKeys`, `SAMLConnection`, `IPRules`,
`APIError`); the brand keeps its own spelling (`QeetID`). Methods use standard verbs without repeating
the resource (`users.create`, `users.list_sessions`).

Verification that needs no API key is standalone: `qeet_id.webhooks` and `qeet_id.tokens`.

## Why

- One attribute access to any call, as in the Stripe, WorkOS and OpenAI clients.
- A file per area keeps a resource's contract one document away, as in the Node.js SDK (its
  ADR-0001), without a file per class in two trees.
