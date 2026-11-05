<div align="center">

# 🐍 Qeet ID for Python

**The server-side Python SDK for Qeet ID: manage an organisation's people and access, verify webhooks and access tokens, and run OAuth flows from Python.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](#-you-need)
[![Typed](https://img.shields.io/badge/typing-fully%20typed-2EA043)](#-whats-inside)
[![Sync + async](https://img.shields.io/badge/clients-sync%20%2B%20async-7C3AED)](#-whats-inside)
[![OpenID Connect](https://img.shields.io/badge/OpenID%20Connect-%E2%9C%93-F78C40?logo=openid&logoColor=white)](#-whats-inside)

[🌐 Qeet ID](https://id.qeet.in) · [📖 Docs](https://docs.qeet.in) · [🧩 API](https://apis.qeet.in) · [🟢 Node SDK](https://github.com/qeetgroup/qeet-id-node) · [🐹 Go SDK](https://github.com/qeetgroup/qeet-id-go)

</div>

## 🧭 What it's for

`qeet-id` brings Qeet ID to Python servers: Django, FastAPI, Flask or plain scripts. Your backend manages people, roles and organisations through the API, checks that a webhook really came from Qeet ID, and verifies the access tokens your APIs receive, without writing the HTTP, signing or retry code itself.

## 📦 What's inside

| | |
|:--|:--|
| 🧩 **Typed client** | Every resource with typed requests and responses, in a synchronous and an `asyncio` client |
| 🚨 **Typed errors** | One exception per kind of failure, each with the stable error `code` and the request ID |
| 🔁 **Retries and timeouts** | Safe retries with backoff for idempotent requests, `Retry-After` honoured, never for a revoked session |
| 📄 **Pagination** | Iterate over every item of a list, page by page underneath |
| 🔁 **Idempotency** | An `Idempotency-Key` on the create calls that accept one |
| 🪝 **Webhooks** | Signature checks in constant time, rotation-aware, with typed events |
| 🔑 **Access tokens** | ES256 verification against the JWKS, with the issuer and audience required |
| 🤝 **OAuth** | Client credentials, code exchange, refresh, token exchange, introspection and revocation |

## 🔗 How it fits

| SDK | Language | Role |
|:--|:--|:--|
| **`qeet-id`** | Python | This package: the API, webhooks and tokens from Python servers |
| [`@qeet-id/node`](https://github.com/qeetgroup/qeet-id-node) | Node.js / TypeScript | The same for Node.js |
| [`qeet-id-go`](https://github.com/qeetgroup/qeet-id-go) | Go | The same for Go |

## 🧱 You need

| | |
|:--|:--|
| 🐍 **Python** | 3.11 or later |
| 🔐 **Credentials** | An API key, or a service principal's client ID and secret |

## 🛠️ Working on it

| | |
|:--|:--|
| 🌿 **Branches** | Work lands on `develop`; `main` changes only by a pull request from `develop` |
| 🏷️ **Versions** | `vX.Y.Z` tags, made when the release workflow is run on `main` |

<div align="center">

Made with 🧡 by Qeet Group · [⬆️ Back to top](#-qeet-id-for-python)

</div>
