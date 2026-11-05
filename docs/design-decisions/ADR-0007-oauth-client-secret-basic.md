# ADR-0007: OAuth clients authenticate with `client_secret_basic`

**Status:** Accepted

## Context

The token, introspection, revocation, device and backchannel endpoints accept a confidential client's
credentials either in the form body (`client_secret_post`) or with HTTP Basic (`client_secret_basic`);
the discovery document lists both. RFC 6749 §2.3.1 says the server must support Basic and that the
form body "is NOT RECOMMENDED". Basic requires the client to form-encode the ID and secret before
Base64, and the server decodes them (`httpx.ClientBasicAuth`).

The Node.js SDK sends the form body, on the grounds that the server didn't decode Basic credentials;
it does now.

## Decision

A confidential client authenticates with HTTP Basic, each part form-encoded first. A public client (no
secret) sends `client_id` in the form, where the endpoint allows public clients. Endpoints that refuse
public clients (client credentials, introspection, CIBA) raise `ValueError` without a secret.

## Consequences

- Client secrets travel in a header, which proxies and servers already treat as sensitive, not in a
  body that may be logged.
- The behaviour differs from the Node.js SDK's on the wire, not in what the server accepts.
