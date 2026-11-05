# ADR-0006: Verify access tokens with `cryptography`, without a JWT library

**Status:** Accepted

## Context

Resource servers verify Qeet ID access tokens locally: ES256 (ECDSA P-256), a `kid` that names one of
the issuer's JWKS keys, a required issuer and audience, and bounded clock leeway (RFC 8725, RFC 9068).
The standard library has HMAC but no ECDSA.

## Decision

Verify with `cryptography` (its `hazmat` ECDSA primitives, verify only), and do the JWS parsing and
claim checks in `_jwt.py` (about 150 lines). No PyJWT, joserfc or Authlib.

- The algorithm is pinned (`ES256`), so algorithm confusion can't happen; `none`, HMAC and RSA tokens
  are refused before any key is looked up.
- `crit` header parameters are refused (RFC 7515 §4.1.11): we understand none.
- The raw `r || s` signature (RFC 7518 §3.4) is converted to DER for `cryptography`.
- JWKS keys are built from their `x` and `y` coordinates; `cryptography` refuses a point off the curve.

## Why

- `cryptography` is the library every Python JWT package uses for ECDSA anyway; going through one of
  them adds a dependency and its own policy defaults (algorithm lists, optional audience) that we
  would have to override.
- The checks are few and fixed, and every one has a negative test.

## Consequences

- A JWKS cache, rotation-driven refresh with a 30-second cooldown, and outage handling live in the
  verifier (`_async/_token_verifier.py`, sync generated).
