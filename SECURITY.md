# Security Policy

## Reporting a vulnerability

Please report security vulnerabilities privately — do not open a public GitHub issue. Email
**security@qeet.in** with:

- A description of the vulnerability and its impact.
- Steps to reproduce (a minimal code sample against this SDK, not the Qeet ID service).
- The SDK version (`python -c "import qeet_id; print(qeet_id.__version__)"`) and Python version affected.

We aim to acknowledge reports within 2 business days.

## Scope

This policy covers the `qeet-id` Python SDK itself. The most sensitive surfaces are access-token
verification (`src/qeet_id/_jwt.py`, `src/qeet_id/_async/_token_verifier.py`), webhook verification
(`src/qeet_id/webhooks.py`), and the transport and credentials (`src/qeet_id/_async/_transport.py`,
`src/qeet_id/_async/_credentials.py`). Vulnerabilities in the Qeet ID service itself should be reported
through Qeet ID's own security channel.

## What the SDK handles

The SDK holds the API key or client secret it is given, and access tokens it obtains, in memory only. It
sends them only to the configured base URL over HTTPS (plain HTTP only to a loopback host), follows no
redirects, and keeps them out of logs, reprs and exceptions. It reads no environment variables and writes
no files.

## Supported versions

Security fixes go to the latest minor version.

## Disclosure

We'll credit reporters (unless anonymity is requested) in the release notes once a fix ships.
