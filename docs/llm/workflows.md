# Workflows — qeet-id-python

**Level:** L2 · **Last verified:** 2026-11-05
**Verification scope:** every command checked against the `Makefile`, `pyproject.toml` and `.github/workflows/`.

## Set up

```bash
uv sync
make check   # lint + generated client + mypy + tests with coverage + package + audit
```

No services required — tests use `httpx2.MockTransport`.

## Add a method to an existing resource

```text
1  find the route        tests/contract/openapi.json (or the server's api/openapi/<area>.yaml);
                         its "security" must include apiKeyAuth
2  open src/qeet_id/_async/resources/<area>.py — never the _sync copy
3  match the neighbours  identifiers positional-only, then keyword-only arguments, request_options last;
                         path("/v1/…/{}", id) for the path
4  types                 a <Resource><Action>Params TypedDict for a body of several fields, used with
                         **params: Unpack[...]; response TypedDicts in src/qeet_id/types/<area>.py and
                         its __all__, then in src/qeet_id/types/__init__.py
5  retries               idempotent=True only where the route honours Idempotency-Key (the snapshot says);
                         retry_safe=True only where repeating changes nothing; retries=False for single use
6  make sync             regenerate src/qeet_id/_sync
7  test                  a row in tests/test_resources.py (it fails until there is one); behaviour in
                         tests/test_behaviour.py
8  README and CHANGELOG
9  make check
```

## Add a whole resource

```text
1  a class Async<Name>(AsyncAPIResource) in the area's module, in its __all__
2  an attribute on AsyncQeetID in src/qeet_id/_async/_client.py, under its area
3  steps 6–9 above
```

## Lists

A route answering `{items, next_cursor}` returns `self._paginate(path, query)` (`AsyncPaginator[T]`; the
generated sync method returns `Page[T]`). A route answering `{items, truncated?}` returns
`await self._list(path, query)` (`ListResult[T]`).

## Refresh the contract snapshot

```bash
uv run --with pyyaml python scripts/snapshot_contract.py /path/to/qeet-id-server origin/main
make test    # a request the contract no longer allows fails here
```

## Recapture the webhook fixtures

```bash
scripts/capture_webhook_fixtures.sh /path/to/qeet-id-server origin/main > tests/fixtures/webhook_deliveries.json
```

Needs Go. It runs the server's own `deliver` and `sign`, copied from the ref, against a local receiver.

## Change transport, retries or errors

**Review required.** `src/qeet_id/_async/_transport.py`, `_retry.py`, `_errors.py`. Keep ADR-0005: never
make a write retryable without an idempotency key, never retry a 401. Add a test in `tests/test_transport.py`.

## Change cryptography

**Security review required.** `webhooks.py`, `_jwt.py` or `_async/_token_verifier.py`. Cite the RFC or the
server code; constant-time comparisons; negative tests (bad signature, wrong secret, stale timestamp,
unknown kid, wrong issuer or audience).

## Release

```text
1  CHANGELOG.md: move [Unreleased] under the version being released
2  make check
3  merge develop into main (pull request), which publishes nothing
4  run release.yml on main by hand, choosing patch, minor or major: it takes the latest vX.Y.Z tag, bumps
   it, writes it into pyproject.toml (uv version), runs the gate, builds, publishes to PyPI by trusted
   publishing, then commits the bump and tags it
```

Before the first release, the PyPI project needs a trusted publisher for this repository, `release.yml`
and the `pypi` environment.

## Finish any task

```bash
make check
git diff
```
