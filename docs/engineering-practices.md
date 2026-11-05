# Engineering practices

The practices this SDK follows, and where each comes from. Researched on 5 November 2026. When a
practice changes, change it here first and record why. The Node.js and Go SDKs are the bar for
coverage and behaviour; this page records how the same behaviour is made idiomatic Python.

## Supported Python

| Practice | How this SDK applies it | Source |
| --- | --- | --- |
| Support every Python still maintained, no more | `requires-python = ">=3.11"`; CI on 3.11, 3.12, 3.13, 3.14 and 3.15. On 5 November 2026, 3.15 and 3.14 receive bug fixes, 3.13, 3.12 and 3.11 security fixes (3.11 until October 2027); 3.10 reached end of life on 1 October 2026 | [Python developer's guide: status of Python versions](https://devguide.python.org/versions/) |
| Drop a version when it reaches end of life | in a minor release, recorded in the changelog | [Azure SDK Python guidelines: supported versions](https://azure.github.io/azure-sdk/python_design.html) (Azure keeps 3.10+, a year behind the CPython schedule) |

## Packaging

| Practice | How | Source |
| --- | --- | --- |
| One `pyproject.toml`, PEP 621 metadata | name, version, dependencies, classifiers and URLs in `[project]`; development tools in a PEP 735 `[dependency-groups]` table, so they never reach users | [PyPA: writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/); [pyproject.toml specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/); [PEP 735](https://peps.python.org/pep-0735/) |
| A modern, pure-Python build backend, with an upper bound | `uv_build>=0.13.7,<0.14`; it builds the sdist and wheel in milliseconds and needs no configuration for a `src/` layout | [uv: the build backend](https://docs.astral.sh/uv/concepts/build-backend/) |
| `src/` layout | `src/qeet_id/`: tests run against the installed package, never the working tree by accident | [PyPA: src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) |
| Typed package marker | `src/qeet_id/py.typed`, shipped in the wheel (a test checks the built wheel holds it) | [PEP 561](https://peps.python.org/pep-0561/) |
| uv for development | `uv sync` installs the locked environment from `uv.lock`; every task is a `uv run` command behind `make` | [uv: projects](https://docs.astral.sh/uv/concepts/projects/) |
| Trusted publishing, with attestations | `release.yml` builds in one job and publishes in another that has only `id-token: write`, through `pypa/gh-action-pypi-publish` in a `pypi` environment; no API token is stored; PEP 740 attestations are made by default | [PyPI: trusted publishers](https://docs.pypi.org/trusted-publishers/using-a-publisher/); [PyPA: publishing with GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/); [PEP 740](https://peps.python.org/pep-0740/) |
| Release only by hand | `release.yml` runs only on `workflow_dispatch` (patch, minor or major); merging into `main` publishes nothing | the Node.js and Go SDKs' release workflows |
| Check the artifacts before publishing | `twine check --strict` on the sdist and wheel in CI and in the release | [twine](https://twine.readthedocs.io/en/stable/#twine-check) |
| Versions and history | Semantic Versioning; a Keep a Changelog `CHANGELOG.md`; `qeet_id.__version__` read from the installed distribution, so it can't disagree with it | [semver.org](https://semver.org/spec/v2.0.0.html); [keepachangelog.com](https://keepachangelog.com/en/1.1.0/); [importlib.metadata](https://docs.python.org/3/library/importlib.metadata.html) |

## Dependencies

| Practice | How | Source |
| --- | --- | --- |
| As few runtime dependencies as the job allows | three: `httpx2` (HTTP, sync and async), `anyio` (sleep and locks in the async client; `httpx2` already requires it) and `cryptography` (ES256). No pydantic, no JWT library | [Azure SDK Python guidelines](https://azure.github.io/azure-sdk/python_design.html) (minimal dependencies); the Node.js SDK's zero-dependency rule, adapted to a standard library without an HTTP/2-capable async client or ECDSA |
| httpx2, the maintained httpx | `httpx` has had no release since 0.28.1 (December 2024) and its issues are closed; `httpx2` is Pydantic's fork with the same API, Python 3.11+, the operating system's trust store (truststore), and releases every few weeks. OpenAI's and WorkOS's Python SDKs moved to it (ADR-0002) | [httpx on PyPI](https://pypi.org/project/httpx/); [httpx2 on PyPI](https://pypi.org/project/httpx2/); [httpx2 migration guide](https://pydantic.dev/docs/httpx2/get-started/migration/); [OpenAI Python](https://github.com/openai/openai-python); [WorkOS Python](https://github.com/workos/workos-python) |
| Floors that exclude known-vulnerable releases, no upper bound on libraries users share | `cryptography>=44.0.1`, `httpx2>=2.12,<3` (its own major), `anyio>=4.10,<5` | [pip-audit](https://github.com/pypa/pip-audit) on the lock file |

## Typing

| Practice | How | Source |
| --- | --- | --- |
| Strict static typing of the whole package | `mypy --strict` plus `warn_unreachable` and extra error codes, over `src/`, `tests/` and `scripts/` | [mypy: --strict](https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-strict); [Azure: use mypy on the public surface](https://azure.github.io/azure-sdk/python_implementation.html) |
| The lightest typing that still checks requests and responses | `TypedDict` for every request and response (wire names kept, ADR-0004); request bodies are keyword arguments typed with `Unpack[...Params]`, so a misspelt or missing field is a type error. No runtime models: no pydantic dependency, no conversion layer, and fields the API adds later reach the caller untouched. Dataclasses only for the SDK's own values (`ListResult`, `FieldError`) | [PEP 589](https://peps.python.org/pep-0589/), [PEP 655](https://peps.python.org/pep-0655/), [PEP 692](https://peps.python.org/pep-0692/); compared with [OpenAI](https://github.com/openai/openai-python) (TypedDict params, pydantic responses), [WorkOS](https://github.com/workos/workos-python) (dataclasses), [Stripe](https://github.com/stripe/stripe-python) (TypedDict params) |
| Open enumerations | response fields the server may extend are `Literal[...] \| str`; request fields are closed `Literal`s | [Stripe Python typing](https://github.com/stripe/stripe-python#types) |
| Explicit public surface | `__all__` in every public module; everything else lives in `_private` modules | [Azure: implementation](https://azure.github.io/azure-sdk/python_implementation.html) ("add public methods and types to the module's `__all__`", "use a leading underscore for internal modules") |

## API shape

| Practice | How | Source |
| --- | --- | --- |
| A sync and an async client with the same shape | `QeetID` and `AsyncQeetID`, separate classes with identical namespaces and methods | [Azure: "do not combine async and sync operations in the same class"](https://azure.github.io/azure-sdk/python_design.html); OpenAI (`OpenAI`/`AsyncOpenAI`), WorkOS (`WorkOSClient`/`AsyncWorkOSClient`) |
| One core, no hand-copied sync code | the async client and its resources are the source; `scripts/unasync.py` generates the sync tree and `make check` fails when they drift. Retry, error, pagination and validation logic are shared pure functions | [httpcore's unasync script](https://github.com/encode/httpcore/blob/master/scripts/unasync.py) |
| Resources as namespaces | `client.users`, `client.webhooks.deliveries`, `client.oauth.grants` (ADR-0003) | Stripe, WorkOS and OpenAI clients |
| Standard verbs, snake_case, no repeated noun | `create`, `get`, `list`, `update`, `delete`, `list_*`, plus domain verbs (`revoke`, `rotate_secret`); `users.create`, not `users.create_user` | [Azure: method naming](https://azure.github.io/azure-sdk/python_design.html); [PEP 8](https://peps.python.org/pep-0008/) |
| PEP 8 names | `APIKeys`, `SAMLConnection`, `APIError` (acronyms in capitals); the brand keeps its spelling, `QeetID` | [PEP 8: descriptive naming styles](https://peps.python.org/pep-0008/#descriptive-naming-styles) |
| Identifiers positional, everything else keyword-only | `client.roles.assign(tenant_id, user_id, role_id)`; bodies and filters as keywords; per-call settings in `request_options` | [Azure: "provide optional operation-specific arguments as keyword only"](https://azure.github.io/azure-sdk/python_design.html); [WorkOS and Auth0 `request_options`](https://github.com/workos/workos-python) |
| Paged lists iterate | `for user in client.users.list()` walks every page; `async for` on the async client, whose `list()` is also awaitable for one page | [Azure: `ItemPaged`](https://azure.github.io/azure-sdk/python_design.html); [OpenAI auto-pagination](https://github.com/openai/openai-python#pagination) |
| Context managers close what they own | `with QeetID(...) as client`, `async with AsyncQeetID(...)`; a caller's own `http_client` is never closed | OpenAI and WorkOS clients |

## Errors

| Practice | How | Source |
| --- | --- | --- |
| One base class, one subclass per actionable status | `QeetIDError` → `APIError` → `BadRequestError`, `AuthenticationError` (→ `SessionRevokedError`), `PaymentRequiredError`, `PermissionDeniedError`, `NotFoundError`, `ConflictError`, `ValidationError`, `RateLimitError`, `InternalServerError` (→ `ServiceUnavailableError`); `OAuthError`; `NetworkError` → `RequestTimeoutError` | [OpenAI errors](https://github.com/openai/openai-python#handling-errors); [WorkOS errors](https://github.com/workos/workos-python); the Node.js SDK |
| Errors carry what support needs | `code`, `message`, `status`, `request_id`, `detail`, `fields`, `metadata`, `retryable`, `retry_after`, `headers`, from the server's envelope `{"error": {...}}` | the server's `httpx.WriteError`; [Azure: include service error details](https://azure.github.io/azure-sdk/python_design.html) |
| OAuth errors in their own shape | `OAuthError` for RFC 6749 §5.2 `{error, error_description, error_uri}` | [RFC 6749 §5.2](https://www.rfc-editor.org/rfc/rfc6749#section-5.2); [RFC 8628 §3.5](https://www.rfc-editor.org/rfc/rfc8628#section-3.5) |
| Argument mistakes are built-in exceptions | `ValueError` and `TypeError`, outside the `QeetIDError` tree | [Python: built-in exceptions](https://docs.python.org/3/library/exceptions.html) |
| Causes are chained | network failures raise `NetworkError` `from` the httpx2 exception | [PEP 3134](https://peps.python.org/pep-3134/); [Azure: implementation](https://azure.github.io/azure-sdk/python_implementation.html) |
| No name shadows a built-in | `RequestTimeoutError`, not `TimeoutError` | [Python: built-in exceptions](https://docs.python.org/3/library/exceptions.html#TimeoutError) |

## Reliability

| Practice | How | Source |
| --- | --- | --- |
| Retry only what is safe to repeat | GET and DELETE, POSTs that change nothing, requests carrying an `Idempotency-Key`; never PUT or PATCH | [RFC 9110 §9.2.2](https://www.rfc-editor.org/rfc/rfc9110#section-9.2.2); [Stripe: idempotent requests](https://docs.stripe.com/api/idempotent_requests) |
| Retry only transient failures | no response, a timeout, 408, 429, 500, 502, 503, 504, and 409 `idempotency.in_progress`; never a 401, so never `auth.session_revoked` | [Stripe: low-level error handling](https://docs.stripe.com/error-low-level); [Azure Core: retry policy](https://azure.github.io/azure-sdk/general_azurecore.html) |
| Exponential backoff with jitter; honour `Retry-After` | 0.5 s doubling to 8 s with equal jitter; `Retry-After` (header, or the envelope's `metadata.retry_after`) up to 60 s is waited out, a longer one is raised | [AWS: exponential backoff and jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/); [RFC 9110 §10.2.3](https://www.rfc-editor.org/rfc/rfc9110#section-10.2.3) |
| Idempotency keys make creates retryable | a UUID4 per call on the nine routes the API makes idempotent, kept across that call's retries; callers may pass their own | [Stripe: idempotency](https://docs.stripe.com/api/idempotent_requests); the server's `internal/platform/http/idempotency` |
| Timeouts on every attempt | 30 s by default, per client and per call; an `httpx2.Timeout` for finer control | OpenAI (10 min), WorkOS (60 s), Auth0 (60 s) defaults; [httpx2: timeouts](https://pydantic.dev/docs/httpx2/) |
| Token caching for machine credentials | client credentials are exchanged for a token once and reused until a minute before it expires; concurrent callers share one fetch | the Go SDK's `WithClientCredentials`; [Auth0 Python `ManagementClient`](https://github.com/auth0/auth0-python) |

## Security

| Practice | How | Source |
| --- | --- | --- |
| Credentials never in logs, reprs or errors | the API key, client secret and bearer tokens are kept off `__repr__`; the logger records method, path, status, timing, attempt and request ID only | [Azure: logging](https://azure.github.io/azure-sdk/python_implementation.html) ("redact or remove items such as account keys") |
| Library logging etiquette | `logging.getLogger("qeet_id")` with a `NullHandler`; DEBUG per attempt, INFO per retry; no handler of our own | [Python logging HOWTO: logging for a library](https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library) |
| No plaintext transport, no redirects | `base_url` must be https except for a loopback host; redirects are not followed, so `Authorization` never leaves the API's origin | — |
| OAuth client authentication by `client_secret_basic`, form-encoded first (ADR-0007) | as RFC 6749 §2.3.1 asks, and the server decodes it (`httpx.ClientBasicAuth`); a public client sends only `client_id` in the form | [RFC 6749 §2.3.1](https://www.rfc-editor.org/rfc/rfc6749#section-2.3.1); the server's discovery document (`token_endpoint_auth_methods_supported`) |
| Webhooks: HMAC over timestamp and body, constant time, replay window | `hmac.compare_digest` of every `sha256=` value against every secret; five minutes of tolerance; fixtures captured from the server's own `deliver` and `sign` | [Standard Webhooks](https://www.standardwebhooks.com/); [Stripe: verify webhook signatures](https://docs.stripe.com/webhooks#verify-manually); the server's `internal/developer/webhooks` |
| JWTs: pinned algorithm, required issuer and audience, bounded leeway, kid-driven refresh with a cooldown | ES256 only, `kid` required, `crit` refused, 30 s leeway, JWKS cached 5 minutes, an unknown `kid` refetches at most every 30 s, stale keys kept through an outage | [RFC 8725 (JWT BCP)](https://www.rfc-editor.org/rfc/rfc8725); [RFC 9068](https://www.rfc-editor.org/rfc/rfc9068); [RFC 7515 §4.1.11](https://www.rfc-editor.org/rfc/rfc7515#section-4.1.11) |
| Well-reviewed cryptography | `cryptography` for ECDSA P-256 (its `hazmat` primitives, used only to verify); `hmac` and `hashlib` from the standard library for webhooks | [cryptography: elliptic curve signing](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ec/) |
| Supply chain | `pip-audit` over the locked dependencies, gitleaks, CodeQL, Ruff's bandit rules (`S`) | [pip-audit](https://github.com/pypa/pip-audit); [CodeQL](https://codeql.github.com/); [Ruff rules](https://docs.astral.sh/ruff/rules/) |

## Tooling and tests

| Practice | How | Source |
| --- | --- | --- |
| One linter and formatter | Ruff (`ruff check`, `ruff format --check`), with pydocstyle on the public surface | [Ruff](https://docs.astral.sh/ruff/) |
| Tests without a server | pytest with httpx2's `MockTransport`; async tests through AnyIO's pytest plugin (no extra dependency) | [pytest](https://docs.pytest.org/); [AnyIO: testing](https://anyio.readthedocs.io/en/stable/testing.html) |
| Examples are type-checked | `examples/` is part of the `mypy --strict` run, so the documented usage compiles against the real types | the Node.js SDK's type-checked examples |
| The contract is checked, not assumed | `tests/contract/openapi.json` is a snapshot of the server's five OpenAPI documents (`scripts/snapshot_contract.py`); a test sends every SDK method through both clients and checks its method, path, query, body fields, idempotency header and API-key security against it | the Node.js SDK's request table, made mechanical |
| Warnings are errors in tests | `filterwarnings = ["error"]` | [pytest: warnings](https://docs.pytest.org/en/stable/how-to/capture-warnings.html) |
| CI equivalent locally | `make check` runs lint, format, the unasync check, mypy, tests with coverage, the build, `twine check` and `pip-audit` | — |
