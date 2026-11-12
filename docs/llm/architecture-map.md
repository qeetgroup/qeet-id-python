# Architecture Map — qeet-id-python

**Level:** L2 · **Last verified:** 2026-11-05
**Verification scope:** every path below was confirmed to exist.

| Need | Path |
| --- | --- |
| Repository identity | [`qeet-repo.yml`](../../qeet-repo.yml) |
| Agent instructions | [`AGENTS.md`](../../AGENTS.md) |
| **Public exports — the package's contract** | `src/qeet_id/__init__.py`, `src/qeet_id/types/__init__.py`, `src/qeet_id/webhooks.py`, `src/qeet_id/tokens.py` |
| The clients and their options | `src/qeet_id/_async/_client.py` (source), `src/qeet_id/_sync/_client.py` (generated) |
| Per-call options, `AppInfo` | `src/qeet_id/_options.py` |
| Defaults | `src/qeet_id/_constants.py` |
| Version | `src/qeet_id/_version.py` (read from the installed distribution) |

## Core

| Concern | Path |
| --- | --- |
| **Request execution: headers, body, timeouts, errors, retries, logging** | `src/qeet_id/_async/_transport.py` |
| **Credentials: API key, client-credentials token cache** | `src/qeet_id/_async/_credentials.py` |
| Retry policy and backoff | `src/qeet_id/_retry.py` |
| **Error classes and response → error mapping** | `src/qeet_id/_errors.py` |
| `Request`, `path()`, encoding, idempotency keys | `src/qeet_id/_request.py` |
| Pagination types | `src/qeet_id/_pagination.py` |
| Resource base classes (hand-written in both trees) | `src/qeet_id/_async/_resource.py`, `src/qeet_id/_sync/_resource.py` |
| Base URL, header and User-Agent rules | `src/qeet_id/_config.py` |
| Sleep and lock per tree (hand-written) | `src/qeet_id/_async/_compat.py`, `src/qeet_id/_sync/_compat.py` |

## Security-critical

| Concern | Path |
| --- | --- |
| **Webhook verification and event catalogue** | `src/qeet_id/webhooks.py` |
| **JWT parsing, ES256, claims, JWKS parsing** | `src/qeet_id/_jwt.py` |
| **JWKS cache and refresh** | `src/qeet_id/_async/_token_verifier.py` |
| OAuth grants, introspection, `TokenGuard` | `src/qeet_id/_async/resources/oauth.py` |

## Resources — one module per OpenAPI document

```text
src/qeet_id/_async/resources/identity.py     management.yaml   tenants · domains · users · groups · invitations · branding
src/qeet_id/_async/resources/access.py       auth.yaml         roles · permissions · relationships · decisions · auth_policies
                                                               security_policies · ip_rules · threat_detection
src/qeet_id/_async/resources/federation.py   federation.yaml   applications · service_principals · saml_connections
                                                               saml_service_providers · ldap_connections · scim
                                                               social_providers · admin_portal_links
src/qeet_id/_async/resources/oauth.py        federation.yaml   oauth (grants, devices, signing_keys), TokenGuard
src/qeet_id/_async/resources/developer.py    developer.yaml    api_keys · agents · verifiable_credentials · auth_hooks
                                                               webhooks · secrets · token_vault
src/qeet_id/_async/resources/operations.py   operations.yaml   audit_logs · analytics · billing · gdpr · email_templates
                                                               retention · log_sinks · rate_limits
src/qeet_id/types/{identity,access,federation,developer,operations}.py   the TypedDicts, same split
```

## Build, test, CI

| | |
| --- | --- |
| Tasks | `Makefile` (`make check` is CI) |
| Package and tool config | `pyproject.toml` |
| **Sync generator** | `scripts/unasync.py` |
| Contract snapshot and its generator | `tests/contract/openapi.json`, `scripts/snapshot_contract.py` |
| Webhook fixtures and their capture | `tests/fixtures/webhook_deliveries.json`, `scripts/capture_webhook_fixtures.sh` |
| Wheel and sdist contents check | `scripts/check_wheel.py` |
| Test helpers (`MockAPI`, `run`, `collect`) | `tests/conftest.py` |
| **Every method's request, checked against the contract** | `tests/test_resources.py` |
| Examples (type-checked) | `examples/` |
| CI (Verify) and release | `.github/workflows/{ci,release}.yml` |

## Decisions

| ADR | Decision |
| --- | --- |
| `docs/design-decisions/ADR-0001-async-source-generated-sync.md` | One core; async is the source, sync generated |
| `docs/design-decisions/ADR-0002-httpx2.md` | httpx2 for HTTP |
| `docs/design-decisions/ADR-0003-namespaces-and-area-modules.md` | Namespaces, one module per API area |
| `docs/design-decisions/ADR-0004-typed-dicts-and-keyword-arguments.md` | TypedDicts with the API's names; keyword bodies |
| `docs/design-decisions/ADR-0005-retries-and-idempotency.md` | Retry only what can't happen twice |
| `docs/design-decisions/ADR-0006-tokens-with-cryptography.md` | ES256 with `cryptography`, no JWT library |
| `docs/design-decisions/ADR-0007-oauth-client-secret-basic.md` | OAuth clients use `client_secret_basic` |

Also `docs/architecture/ARCHITECTURE.md`, `docs/engineering-practices.md`, `docs/FUTURE.md`.

## Upstream

The API contract lives in **`qeet-id-server`**: `api/openapi/*.yaml` and the handlers under `internal/`.
Snapshotted, not vendored, in `tests/contract/openapi.json`.
