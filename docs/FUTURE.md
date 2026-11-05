# Future

What this SDK doesn't cover yet, and why. The list matches the Node.js SDK's, so the two stay level.

## API areas an API key may call but the SDK doesn't wrap yet

These exist in `qeet-id-server` and accept an API key (`tests/contract/openapi.json` lists them). Each is
additive.

- **Attribute-based access control** — `/v1/tenants/{tenantID}/abac/*` (policies, versions, evaluate).
- **Directory sync** — `/v1/tenants/{tenantID}/directory/*` (connection mappings, errors, activity,
  alerts, profiles).
- **OpenID Connect enterprise connections** — `/v1/tenants/{tenantID}/oidc-connections`.
- **Compliance evidence** — `/v1/tenants/{tenantID}/compliance/*`.
- **Activity feed** — `/v1/activity*`.
- **Group templates and import** — `/v1/groups/templates*`, `/v1/groups/import`.
- **User administration extras** — suspended-user review (`/v1/users/suspended`,
  `PUT /v1/users/{id}/suspension`), statistics and trends, trusted and push devices, passkeys, sign-in
  history, break-glass members and login-domain checks.
- **Email delivery** — messages and suppressions.
- **Qeet AI tenant settings and usage**, **service health**, **billing trial**.

## Not wrapped on purpose

These need a person's own session rather than a server's credential, and the server refuses API keys on
them: a person's sessions, second factors, passkeys, email change and account export; the end-user
approval steps of the device and backchannel flows; the token vault's connect flow and a person's own
connected accounts; notifications; Qeet AI conversations. The hosted pages and the browser SDK cover them.

## Waiting on the API

- A brokered call for the token vault, so code never handles a raw third-party token
  (`token_vault.get_access_token` warns until then).
- Nested organisations and workload identity, once the server has them.
