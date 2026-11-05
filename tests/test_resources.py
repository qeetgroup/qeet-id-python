"""Every method's request, on both clients, checked against the API contract.

Each row is one SDK method: how to call it, and the HTTP method, path and body it
must send. On top of the row's own expectations, every request is matched to the
operation of the server's OpenAPI documents it calls (tests/contract/openapi.json)
and must agree with it: an API key only where the operation accepts one, query
parameters and body fields the operation documents, an Idempotency-Key exactly
where the operation honours one, and the list shape (``items``, ``next_cursor``)
the method's return type expects.
"""

import inspect
import json
import re
import typing
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import pytest

from qeet_id import ListResult, Page, QeetID
from qeet_id._async._resource import AsyncAPIResource
from qeet_id._sync._resource import APIResource
from qeet_id.webhooks import WEBHOOK_EVENT_TYPES

from .conftest import Kind, MockAPI, Recorded, run

pytestmark = pytest.mark.anyio

CONTRACT = json.loads((Path(__file__).parent / "contract" / "openapi.json").read_text())

UNDOCUMENTED_FIELDS = {
    # The operation's description says "a public client may revoke its own tokens with its
    # client_id alone", and the handler reads it from the form (internal/federation/oidc
    # http_token.go, clientCreds); the request schema lists only token and token_type_hint.
    ("POST", "/oauth/revoke"): {"client_id"},
}
"""Fields the server reads but its OpenAPI schema leaves out; each one is a contract finding."""


@dataclass(frozen=True)
class Row:
    name: str
    call: Callable[[Any], Any]
    method: str
    path: str
    json: Any = None
    query: list[tuple[str, str]] | None = None
    form: dict[str, str] | None = None
    warns: type[Warning] | None = None
    answer: dict[str, Any] = field(default_factory=dict)


R = Row
ROWS: list[Row] = [
    # Identity
    R("tenants.get", lambda c: c.tenants.get("t1"), "GET", "/v1/tenants/t1"),
    R("tenants.update", lambda c: c.tenants.update("t1", name="Brightleaf Foods"), "PATCH", "/v1/tenants/t1",
      {"name": "Brightleaf Foods"}),
    R("tenants.delete", lambda c: c.tenants.delete("t1"), "DELETE", "/v1/tenants/t1"),
    R("tenants.cancel_deletion", lambda c: c.tenants.cancel_deletion("t1"), "POST", "/v1/tenants/t1/deletion/cancel"),
    R("domains.create", lambda c: c.domains.create("t1", "brightleaffoods.in"), "POST", "/v1/tenants/t1/domains",
      {"domain": "brightleaffoods.in"}),
    R("domains.list", lambda c: c.domains.list("t1"), "GET", "/v1/tenants/t1/domains"),
    R("domains.verify", lambda c: c.domains.verify("t1", "d1"), "POST", "/v1/tenants/t1/domains/d1/verify"),
    R("domains.update", lambda c: c.domains.update("t1", "d1", sso_enabled=True), "PATCH", "/v1/tenants/t1/domains/d1",
      {"sso_enabled": True}),
    R("domains.delete", lambda c: c.domains.delete("t1", "d1"), "DELETE", "/v1/tenants/t1/domains/d1"),
    R("users.create", lambda c: c.users.create(tenant_id="t1", email="meera@brightleaffoods.in", display_name="Meera"),
      "POST", "/v1/users", {"tenant_id": "t1", "email": "meera@brightleaffoods.in", "display_name": "Meera"}),
    R("users.get", lambda c: c.users.get("u1"), "GET", "/v1/users/u1"),
    R("users.update", lambda c: c.users.update("u1", avatar_url="", display_name=None), "PATCH", "/v1/users/u1",
      {"avatar_url": "", "display_name": None}),
    R("users.list", lambda c: c.users.list(status="active", mfa=False, limit=50), "GET", "/v1/users",
      query=[("status", "active"), ("mfa", "false"), ("limit", "50")]),
    R("users.suspend", lambda c: c.users.suspend("u1"), "PATCH", "/v1/users/u1", {"status": "suspended"}),
    R("users.reactivate", lambda c: c.users.reactivate("u1"), "POST", "/v1/users/u1/reactivate"),
    R("users.delete", lambda c: c.users.delete("u1"), "DELETE", "/v1/users/u1"),
    R("users.list_deleted", lambda c: c.users.list_deleted(limit=5), "GET", "/v1/users/deleted", query=[("limit", "5")]),
    R("users.restore", lambda c: c.users.restore("u1"), "POST", "/v1/users/u1/restore"),
    R("users.purge", lambda c: c.users.purge("u1"), "DELETE", "/v1/users/u1/purge"),
    R("users.set_password", lambda c: c.users.set_password("u1", "correct horse battery staple"), "POST",
      "/v1/users/u1/password", {"password": "correct horse battery staple"}),
    R("users.reset_mfa", lambda c: c.users.reset_mfa("u1"), "DELETE", "/v1/users/u1/mfa"),
    R("users.set_mfa_required", lambda c: c.users.set_mfa_required("u1", True), "PUT", "/v1/users/u1/mfa-required",
      {"required": True}),
    R("users.bulk_create", lambda c: c.users.bulk_create(users=[{"email": "a@b.in"}]), "POST", "/v1/users/bulk",
      {"users": [{"email": "a@b.in"}]}),
    R("users.bulk_import", lambda c: c.users.bulk_import("cognito", "email\na@b.in\n"), "POST", "/v1/users/bulk/import",
      query=[("source", "cognito")]),
    R("users.list_sessions", lambda c: c.users.list_sessions("u1"), "GET", "/v1/users/u1/sessions"),
    R("users.revoke_session", lambda c: c.users.revoke_session("t1", "u1", "s1"), "DELETE",
      "/v1/tenants/t1/users/u1/sessions/s1"),
    R("users.revoke_all_sessions", lambda c: c.users.revoke_all_sessions("u1"), "POST",
      "/v1/users/u1/sessions/revoke-all"),
    R("users.get_security", lambda c: c.users.get_security("u1"), "GET", "/v1/users/u1/security"),
    R("users.get_access", lambda c: c.users.get_access("u1"), "GET", "/v1/users/u1/access"),
    R("users.remove_membership", lambda c: c.users.remove_membership("u1"), "DELETE", "/v1/users/u1/membership"),
    R("users.list_linked_identities", lambda c: c.users.list_linked_identities("u1"), "GET",
      "/v1/users/u1/social/identities"),
    R("groups.create", lambda c: c.groups.create(name="Finance", parent_id=None), "POST", "/v1/groups",
      {"name": "Finance", "parent_id": None}),
    R("groups.update", lambda c: c.groups.update("g1", parent_id=None), "PATCH", "/v1/groups/g1", {"parent_id": None}),
    R("groups.delete", lambda c: c.groups.delete("g1"), "DELETE", "/v1/groups/g1"),
    R("groups.list", lambda c: c.groups.list("t1", grants="none"), "GET", "/v1/tenants/t1/groups",
      query=[("grants", "none")]),
    R("groups.list_members", lambda c: c.groups.list_members("g1"), "GET", "/v1/groups/g1/members"),
    R("groups.add_member", lambda c: c.groups.add_member("g1", "u1"), "POST", "/v1/groups/g1/members/u1"),
    R("groups.remove_member", lambda c: c.groups.remove_member("g1", "u1"), "DELETE", "/v1/groups/g1/members/u1"),
    R("groups.list_roles", lambda c: c.groups.list_roles("t1", "g1"), "GET", "/v1/tenants/t1/groups/g1/roles"),
    R("groups.grant_role", lambda c: c.groups.grant_role("t1", "g1", "r1"), "POST", "/v1/tenants/t1/groups/g1/roles/r1"),
    R("groups.revoke_role", lambda c: c.groups.revoke_role("t1", "g1", "r1"), "DELETE",
      "/v1/tenants/t1/groups/g1/roles/r1"),
    R("invitations.create", lambda c: c.invitations.create(tenant_id="t1", email="ravi@brightleaffoods.in", role_id="r1"),
      "POST", "/v1/invites", {"tenant_id": "t1", "email": "ravi@brightleaffoods.in", "role_id": "r1"}),
    R("invitations.list", lambda c: c.invitations.list("t1"), "GET", "/v1/tenants/t1/invites"),
    R("invitations.resend", lambda c: c.invitations.resend("i1"), "POST", "/v1/invites/i1/resend"),
    R("invitations.delete", lambda c: c.invitations.delete("i1"), "DELETE", "/v1/invites/i1"),
    R("branding.get", lambda c: c.branding.get("t1"), "GET", "/v1/tenants/t1/branding"),
    R("branding.update", lambda c: c.branding.update("t1", primary_color="#0a7d3b"), "PUT", "/v1/tenants/t1/branding",
      {"primary_color": "#0a7d3b"}),
    # Access
    R("roles.list", lambda c: c.roles.list("t1"), "GET", "/v1/tenants/t1/roles"),
    R("roles.create", lambda c: c.roles.create("t1", "Auditor"), "POST", "/v1/tenants/t1/roles", {"name": "Auditor"}),
    R("roles.update", lambda c: c.roles.update("t1", "r1", description="Reads the audit log"), "PATCH",
      "/v1/tenants/t1/roles/r1", {"description": "Reads the audit log"}),
    R("roles.delete", lambda c: c.roles.delete("t1", "r1"), "DELETE", "/v1/tenants/t1/roles/r1"),
    R("roles.list_permissions", lambda c: c.roles.list_permissions("r1"), "GET", "/v1/roles/r1/permissions"),
    R("roles.set_permissions", lambda c: c.roles.set_permissions("t1", "r1", ["p1", "p2"]), "PUT",
      "/v1/tenants/t1/roles/r1/permissions", {"permission_ids": ["p1", "p2"]}),
    R("roles.grant_permission", lambda c: c.roles.grant_permission("r1", "p1"), "POST", "/v1/roles/r1/permissions/p1"),
    R("roles.revoke_permission", lambda c: c.roles.revoke_permission("r1", "p1"), "DELETE",
      "/v1/roles/r1/permissions/p1"),
    R("roles.list_holders", lambda c: c.roles.list_holders("t1", "r1", limit=20), "GET",
      "/v1/tenants/t1/roles/r1/holders", query=[("limit", "20")]),
    R("roles.assign", lambda c: c.roles.assign("t1", "u1", "r1"), "POST", "/v1/users/u1/tenants/t1/roles/r1"),
    R("roles.unassign", lambda c: c.roles.unassign("t1", "u1", "r1"), "DELETE", "/v1/users/u1/tenants/t1/roles/r1"),
    R("permissions.list", lambda c: c.permissions.list(), "GET", "/v1/permissions"),
    R("permissions.check", lambda c: c.permissions.check(user_id="u1", tenant_id="t1", permission="invoice.write"),
      "GET", "/v1/check", query=[("user_id", "u1"), ("tenant_id", "t1"), ("permission", "invoice.write")]),
    R("permissions.explain", lambda c: c.permissions.explain(user_id="u1", tenant_id="t1", permission="invoice.write"),
      "GET", "/v1/check",
      query=[("user_id", "u1"), ("tenant_id", "t1"), ("permission", "invoice.write"), ("explain", "true")]),
    R("permissions.list_effective", lambda c: c.permissions.list_effective("t1", "u1"), "GET",
      "/v1/users/u1/tenants/t1/permissions"),
    R("relationships.create", lambda c: c.relationships.create("t1", object="doc:1", relation="viewer", subject="user:u1"),
      "POST", "/v1/tenants/t1/relation-tuples", {"object": "doc:1", "relation": "viewer", "subject": "user:u1"}),
    R("relationships.list", lambda c: c.relationships.list("t1", subject="user:u1"), "GET",
      "/v1/tenants/t1/relation-tuples", query=[("subject", "user:u1")]),
    R("relationships.delete", lambda c: c.relationships.delete("t1", "tu1"), "DELETE",
      "/v1/tenants/t1/relation-tuples/tu1"),
    R("relationships.check", lambda c: c.relationships.check("t1", object="doc:1", relation="viewer", user_id="u1"),
      "POST", "/v1/tenants/t1/relation-tuples/check", {"object": "doc:1", "relation": "viewer", "user_id": "u1"},
      query=[]),
    R("relationships.explain", lambda c: c.relationships.explain("t1", object="doc:1", relation="viewer", user_id="u1"),
      "POST", "/v1/tenants/t1/relation-tuples/check", {"object": "doc:1", "relation": "viewer", "user_id": "u1"},
      query=[("explain", "true")]),
    R("relationships.graph", lambda c: c.relationships.graph("t1", object="doc:1", relation="viewer", depth=3), "GET",
      "/v1/tenants/t1/relation-tuples/graph", query=[("object", "doc:1"), ("relation", "viewer"), ("depth", "3")]),
    R("relationships.list_types", lambda c: c.relationships.list_types("t1"), "GET",
      "/v1/tenants/t1/relation-tuples/types"),
    R("relationships.list_objects", lambda c: c.relationships.list_objects("t1", type="doc"), "GET",
      "/v1/tenants/t1/relation-tuples/objects", query=[("type", "doc")]),
    R("decisions.evaluate", lambda c: c.decisions.evaluate("t1", subject={"type": "user", "id": "u1"},
      action={"name": "invoice.write"}, resource={"type": "permission"}), "POST", "/v1/tenants/t1/access/v1/evaluation",
      {"subject": {"type": "user", "id": "u1"}, "resource": {"type": "permission"}, "action": {"name": "invoice.write"}}),
    R("decisions.evaluate_many", lambda c: c.decisions.evaluate_many("t1", [], options={"evaluations_semantic":
      "execute_all"}), "POST", "/v1/tenants/t1/access/v1/evaluations",
      {"evaluations": [], "options": {"evaluations_semantic": "execute_all"}}),
    R("decisions.list", lambda c: c.decisions.list("t1", allowed=False), "GET", "/v1/tenants/t1/authorization/decisions",
      query=[("allowed", "false")]),
    R("auth_policies.get", lambda c: c.auth_policies.get("t1"), "GET", "/v1/tenants/t1/auth-policy"),
    R("auth_policies.update", lambda c: c.auth_policies.update("t1", passkey_enabled=True), "PUT",
      "/v1/tenants/t1/auth-policy", {"passkey_enabled": True}),
    R("auth_policies.get_usage", lambda c: c.auth_policies.get_usage("t1"), "GET", "/v1/tenants/t1/auth-policy/usage"),
    R("security_policies.get", lambda c: c.security_policies.get("t1"), "GET", "/v1/tenants/t1/policy"),
    R("security_policies.update", lambda c: c.security_policies.update("t1", mfa_enforcement="required"), "PATCH",
      "/v1/tenants/t1/policy", {"mfa_enforcement": "required"}),
    R("security_policies.replace", lambda c: c.security_policies.replace("t1", mfa_enforcement="optional"), "PUT",
      "/v1/tenants/t1/policy", {"mfa_enforcement": "optional"}),
    R("ip_rules.list", lambda c: c.ip_rules.list("t1"), "GET", "/v1/tenants/t1/ip-rules"),
    R("ip_rules.create", lambda c: c.ip_rules.create("t1", action="deny", cidr="203.0.113.0/24", label="Blocked"),
      "POST", "/v1/tenants/t1/ip-rules", {"action": "deny", "cidr": "203.0.113.0/24", "label": "Blocked"}),
    R("ip_rules.delete", lambda c: c.ip_rules.delete("t1", "ir1"), "DELETE", "/v1/tenants/t1/ip-rules/ir1"),
    R("ip_rules.check", lambda c: c.ip_rules.check("t1", "203.0.113.9"), "POST", "/v1/tenants/t1/ip-rules/check",
      {"ip": "203.0.113.9"}),
    R("ip_rules.set_enforcement", lambda c: c.ip_rules.set_enforcement("t1", True), "PUT",
      "/v1/tenants/t1/ip-rules/config", {"enabled": True}),
    R("threat_detection.get_bot_activity", lambda c: c.threat_detection.get_bot_activity("t1", verdict="blocked"), "GET",
      "/v1/tenants/t1/security/bots", query=[("verdict", "blocked")]),
    R("threat_detection.get_bot_settings", lambda c: c.threat_detection.get_bot_settings("t1"), "GET",
      "/v1/tenants/t1/security/bots/settings"),
    R("threat_detection.update_bot_settings", lambda c: c.threat_detection.update_bot_settings("t1", ua_check=True,
      honeypot=True, captcha=False, signature=True, score_threshold=0.7), "PUT", "/v1/tenants/t1/security/bots/settings",
      {"ua_check": True, "honeypot": True, "captcha": False, "signature": True, "score_threshold": 0.7}),
    R("threat_detection.get_risk_settings", lambda c: c.threat_detection.get_risk_settings("t1"), "GET",
      "/v1/tenants/t1/security/risk-settings"),
    R("threat_detection.update_risk_settings", lambda c: c.threat_detection.update_risk_settings("t1",
      medium_threshold=40, high_threshold=70, force_mfa_at_level="high", impossible_travel_enabled=True,
      min_travel_hours=2, device_reputation_enabled=True), "PUT", "/v1/tenants/t1/security/risk-settings",
      {"medium_threshold": 40, "high_threshold": 70, "force_mfa_at_level": "high", "impossible_travel_enabled": True,
       "min_travel_hours": 2, "device_reputation_enabled": True}),
    R("threat_detection.list_anomalies", lambda c: c.threat_detection.list_anomalies("t1", status="open"), "GET",
      "/v1/tenants/t1/security/anomalies", query=[("status", "open")]),
    R("threat_detection.get_anomaly_summary", lambda c: c.threat_detection.get_anomaly_summary("t1"), "GET",
      "/v1/tenants/t1/security/anomalies/summary"),
    R("threat_detection.resolve_anomaly", lambda c: c.threat_detection.resolve_anomaly("t1", "an1"), "POST",
      "/v1/tenants/t1/security/anomalies/an1/resolve"),
    # Federation
    R("applications.create", lambda c: c.applications.create("t1", name="Portal", type="confidential",
      redirect_uris=["https://portal.example/cb"]), "POST", "/v1/tenants/t1/oidc/clients",
      {"name": "Portal", "type": "confidential", "redirect_uris": ["https://portal.example/cb"], "tenant_id": "t1"}),
    R("applications.get", lambda c: c.applications.get("t1", "a1"), "GET", "/v1/tenants/t1/oidc/clients/a1"),
    R("applications.list", lambda c: c.applications.list("t1"), "GET", "/v1/tenants/t1/oidc/clients"),
    R("applications.update", lambda c: c.applications.update("t1", "a1", pkce_exempt_until=None), "PATCH",
      "/v1/tenants/t1/oidc/clients/a1", {"pkce_exempt_until": None}),
    R("applications.delete", lambda c: c.applications.delete("t1", "a1"), "DELETE", "/v1/tenants/t1/oidc/clients/a1"),
    R("applications.rotate_secret", lambda c: c.applications.rotate_secret("t1", "a1"), "POST",
      "/v1/tenants/t1/oidc/clients/a1/rotate-secret"),
    R("applications.get_auth_failures", lambda c: c.applications.get_auth_failures("t1", "a1"), "GET",
      "/v1/tenants/t1/oidc/clients/a1/auth-failures"),
    R("applications.list_shadow_ai", lambda c: c.applications.list_shadow_ai("t1"), "GET",
      "/v1/tenants/t1/oidc/clients/shadow-ai"),
    R("applications.mark_reviewed", lambda c: c.applications.mark_reviewed("t1", "a1"), "POST",
      "/v1/tenants/t1/oidc/clients/a1/review"),
    R("applications.resources.list", lambda c: c.applications.resources.list("t1"), "GET", "/v1/tenants/t1/oidc/resources"),
    R("applications.resources.create", lambda c: c.applications.resources.create("t1", "https://mcp.brightleaffoods.in"),
      "POST", "/v1/tenants/t1/oidc/resources", {"identifier": "https://mcp.brightleaffoods.in"}),
    R("applications.resources.delete", lambda c: c.applications.resources.delete("t1", "res1"), "DELETE",
      "/v1/tenants/t1/oidc/resources/res1"),
    R("oauth.grants.list", lambda c: c.oauth.grants.list("t1", client_id="app"), "GET", "/v1/tenants/t1/oauth/grants",
      query=[("client_id", "app")]),
    R("oauth.grants.revoke", lambda c: c.oauth.grants.revoke("t1", "gr1"), "DELETE", "/v1/tenants/t1/oauth/grants/gr1"),
    R("oauth.grants.revoke_many", lambda c: c.oauth.grants.revoke_many("t1", client_id="app"), "POST",
      "/v1/tenants/t1/oauth/grants/revoke", {"client_id": "app"}),
    R("oauth.devices.list", lambda c: c.oauth.devices.list("t1"), "GET", "/v1/tenants/t1/oauth/devices"),
    R("oauth.devices.revoke", lambda c: c.oauth.devices.revoke("t1", "dv1"), "DELETE", "/v1/tenants/t1/oauth/devices/dv1"),
    R("oauth.signing_keys.list", lambda c: c.oauth.signing_keys.list(), "GET", "/v1/oidc/signing-keys"),
    R("oauth.client_credentials_grant", lambda c: c.oauth.client_credentials_grant(client_id="sp1", client_secret="s"),
      "POST", "/v1/oauth/token", form={"grant_type": "client_credentials"}),
    R("oauth.authorization_code_grant", lambda c: c.oauth.authorization_code_grant(client_id="app", code="c1",
      redirect_uri="https://app.example/cb", code_verifier="v"), "POST", "/v1/oauth/token-code",
      form={"grant_type": "authorization_code", "code": "c1", "redirect_uri": "https://app.example/cb",
            "code_verifier": "v", "client_id": "app"}),
    R("oauth.refresh_token_grant", lambda c: c.oauth.refresh_token_grant(client_id="app", client_secret="s",
      refresh_token="rt"), "POST", "/v1/oauth/token-code", form={"grant_type": "refresh_token", "refresh_token": "rt"}),
    R("oauth.token_exchange_grant", lambda c: c.oauth.token_exchange_grant(client_id="app", client_secret="s",
      subject_token="st", actor_token="at", scope="files:read"), "POST", "/v1/oauth/token-code",
      form={"grant_type": "urn:ietf:params:oauth:grant-type:token-exchange", "subject_token": "st",
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token", "actor_token": "at",
            "actor_token_type": "urn:ietf:params:oauth:token-type:access_token", "scope": "files:read"}),
    R("oauth.device_code_grant", lambda c: c.oauth.device_code_grant(client_id="tv", device_code="dc"), "POST",
      "/v1/oauth/token-code",
      form={"grant_type": "urn:ietf:params:oauth:grant-type:device_code", "device_code": "dc", "client_id": "tv"}),
    R("oauth.ciba_grant", lambda c: c.oauth.ciba_grant(client_id="app", client_secret="s", auth_req_id="ar"), "POST",
      "/v1/oauth/token-code", form={"grant_type": "urn:openid:params:grant-type:ciba", "auth_req_id": "ar"}),
    R("oauth.device_authorization", lambda c: c.oauth.device_authorization(client_id="tv", scope="openid"), "POST",
      "/v1/oauth/device_authorization", form={"scope": "openid", "client_id": "tv"}),
    R("oauth.backchannel_authentication", lambda c: c.oauth.backchannel_authentication(client_id="app",
      client_secret="s", login_hint="meera@brightleaffoods.in", binding_message="INV-42"), "POST",
      "/v1/oauth/bc-authorize", form={"login_hint": "meera@brightleaffoods.in", "binding_message": "INV-42"}),
    R("oauth.introspect", lambda c: c.oauth.introspect("tok", client_id="api", client_secret="s"), "POST",
      "/oauth/introspect", form={"token": "tok"}),
    R("oauth.revoke", lambda c: c.oauth.revoke("rt", client_id="app", token_type_hint="refresh_token"), "POST",
      "/oauth/revoke", form={"token": "rt", "token_type_hint": "refresh_token", "client_id": "app"}),
    R("oauth.discover", lambda c: c.oauth.discover(), "GET", "/.well-known/openid-configuration"),
    R("service_principals.create", lambda c: c.service_principals.create(tenant_id="t1", name="reporting"), "POST",
      "/v1/service-principals", {"tenant_id": "t1", "name": "reporting"}),
    R("service_principals.list", lambda c: c.service_principals.list("t1"), "GET", "/v1/tenants/t1/service-principals"),
    R("service_principals.disable", lambda c: c.service_principals.disable("sp1"), "DELETE", "/v1/service-principals/sp1"),
    R("service_principals.enable", lambda c: c.service_principals.enable("t1", "sp1"), "POST",
      "/v1/tenants/t1/service-principals/sp1/enable"),
    R("service_principals.rotate_secret", lambda c: c.service_principals.rotate_secret("t1", "sp1", overlap_hours=48),
      "POST", "/v1/tenants/t1/service-principals/sp1/rotate-secret", {"overlap_hours": 48}),
    R("saml_connections.create", lambda c: c.saml_connections.create("t1", name="Okta"), "POST", "/v1/tenants/t1/saml",
      {"name": "Okta"}),
    R("saml_connections.import_metadata", lambda c: c.saml_connections.import_metadata("t1", name="Okta",
      metadata_url="https://idp.example/md"), "POST", "/v1/tenants/t1/saml/import",
      {"name": "Okta", "metadata_url": "https://idp.example/md"}),
    R("saml_connections.get", lambda c: c.saml_connections.get("t1", "sc1"), "GET", "/v1/tenants/t1/saml/sc1"),
    R("saml_connections.list", lambda c: c.saml_connections.list("t1"), "GET", "/v1/tenants/t1/saml"),
    R("saml_connections.update", lambda c: c.saml_connections.update("t1", "sc1", status="active"), "PATCH",
      "/v1/tenants/t1/saml/sc1", {"status": "active"}),
    R("saml_connections.delete", lambda c: c.saml_connections.delete("t1", "sc1"), "DELETE", "/v1/tenants/t1/saml/sc1"),
    R("saml_connections.update_metadata", lambda c: c.saml_connections.update_metadata("t1", "sc1", metadata_xml="<md/>"),
      "POST", "/v1/tenants/t1/saml/sc1/metadata", {"metadata_xml": "<md/>"}),
    R("saml_connections.add_certificate", lambda c: c.saml_connections.add_certificate("t1", "sc1", "MIIC"), "POST",
      "/v1/tenants/t1/saml/sc1/certificates", {"certificate": "MIIC"}),
    R("saml_connections.remove_certificate", lambda c: c.saml_connections.remove_certificate("t1", "sc1", "ce1"),
      "DELETE", "/v1/tenants/t1/saml/sc1/certificates/ce1"),
    R("saml_connections.test", lambda c: c.saml_connections.test("t1", "sc1"), "POST", "/v1/tenants/t1/saml/sc1/test"),
    R("saml_connections.list_group_mappings", lambda c: c.saml_connections.list_group_mappings("t1", "sc1"), "GET",
      "/v1/tenants/t1/saml/sc1/group-mappings"),
    R("saml_connections.create_group_mapping", lambda c: c.saml_connections.create_group_mapping("t1", "sc1",
      idp_group="Finance", group_id="g1"), "POST", "/v1/tenants/t1/saml/sc1/group-mappings",
      {"idp_group": "Finance", "group_id": "g1"}),
    R("saml_connections.delete_group_mapping", lambda c: c.saml_connections.delete_group_mapping("t1", "sc1", "m1"),
      "DELETE", "/v1/tenants/t1/saml/sc1/group-mappings/m1"),
    R("saml_service_providers.create", lambda c: c.saml_service_providers.create("t1", name="Payroll",
      entity_id="urn:payroll", acs_url="https://payroll.example/acs"), "POST", "/v1/tenants/t1/saml-providers",
      {"name": "Payroll", "entity_id": "urn:payroll", "acs_url": "https://payroll.example/acs"}),
    R("saml_service_providers.get", lambda c: c.saml_service_providers.get("t1", "sp1"), "GET",
      "/v1/tenants/t1/saml-providers/sp1"),
    R("saml_service_providers.list", lambda c: c.saml_service_providers.list("t1"), "GET", "/v1/tenants/t1/saml-providers"),
    R("saml_service_providers.update", lambda c: c.saml_service_providers.update("t1", "sp1", assignment_required=True),
      "PATCH", "/v1/tenants/t1/saml-providers/sp1", {"assignment_required": True}),
    R("saml_service_providers.delete", lambda c: c.saml_service_providers.delete("t1", "sp1"), "DELETE",
      "/v1/tenants/t1/saml-providers/sp1"),
    R("saml_service_providers.list_assignments", lambda c: c.saml_service_providers.list_assignments("t1", "sp1"), "GET",
      "/v1/tenants/t1/saml-providers/sp1/assignments"),
    R("saml_service_providers.assign_user", lambda c: c.saml_service_providers.assign_user("t1", "sp1", "u1"), "POST",
      "/v1/tenants/t1/saml-providers/sp1/assignments/users/u1"),
    R("saml_service_providers.unassign_user", lambda c: c.saml_service_providers.unassign_user("t1", "sp1", "u1"),
      "DELETE", "/v1/tenants/t1/saml-providers/sp1/assignments/users/u1"),
    R("saml_service_providers.assign_group", lambda c: c.saml_service_providers.assign_group("t1", "sp1", "g1"), "POST",
      "/v1/tenants/t1/saml-providers/sp1/assignments/groups/g1"),
    R("saml_service_providers.unassign_group", lambda c: c.saml_service_providers.unassign_group("t1", "sp1", "g1"),
      "DELETE", "/v1/tenants/t1/saml-providers/sp1/assignments/groups/g1"),
    R("ldap_connections.create", lambda c: c.ldap_connections.create("t1", name="AD", server_url="ldaps://ad.example",
      bind_dn="cn=svc", bind_password="x", base_dn="dc=example"), "POST", "/v1/tenants/t1/ldap",
      {"name": "AD", "server_url": "ldaps://ad.example", "bind_dn": "cn=svc", "bind_password": "x",
       "base_dn": "dc=example"}),
    R("ldap_connections.get", lambda c: c.ldap_connections.get("t1", "l1"), "GET", "/v1/tenants/t1/ldap/l1"),
    R("ldap_connections.list", lambda c: c.ldap_connections.list("t1"), "GET", "/v1/tenants/t1/ldap"),
    R("ldap_connections.update", lambda c: c.ldap_connections.update("t1", "l1", status="active"), "PATCH",
      "/v1/tenants/t1/ldap/l1", {"status": "active"}),
    R("ldap_connections.delete", lambda c: c.ldap_connections.delete("t1", "l1"), "DELETE", "/v1/tenants/t1/ldap/l1"),
    R("ldap_connections.test", lambda c: c.ldap_connections.test("t1", "l1"), "POST", "/v1/tenants/t1/ldap/l1/test"),
    R("ldap_connections.list_group_mappings", lambda c: c.ldap_connections.list_group_mappings("t1", "l1"), "GET",
      "/v1/tenants/t1/ldap/l1/group-mappings"),
    R("ldap_connections.create_group_mapping", lambda c: c.ldap_connections.create_group_mapping("t1", "l1",
      idp_group="cn=finance", group_id="g1"), "POST", "/v1/tenants/t1/ldap/l1/group-mappings",
      {"idp_group": "cn=finance", "group_id": "g1"}),
    R("ldap_connections.delete_group_mapping", lambda c: c.ldap_connections.delete_group_mapping("t1", "l1", "m1"),
      "DELETE", "/v1/tenants/t1/ldap/l1/group-mappings/m1"),
    R("ldap_connections.authenticate", lambda c: c.ldap_connections.authenticate("l1", username="meera",
      password="pw"), "POST", "/ldap/l1/authenticate", {"username": "meera", "password": "pw"}),
    R("scim.get_config", lambda c: c.scim.get_config("t1"), "GET", "/v1/tenants/t1/scim"),
    R("scim.list_tokens", lambda c: c.scim.list_tokens("t1"), "GET", "/v1/tenants/t1/scim/tokens"),
    R("scim.create_token", lambda c: c.scim.create_token("t1", "Okta"), "POST", "/v1/tenants/t1/scim/tokens",
      {"name": "Okta", "expires_at": None}),
    R("scim.rotate_token", lambda c: c.scim.rotate_token("t1", "st1", overlap_hours=24), "POST",
      "/v1/tenants/t1/scim/tokens/st1/rotate", {"overlap_hours": 24}),
    R("scim.revoke_token", lambda c: c.scim.revoke_token("t1", "st1"), "DELETE", "/v1/tenants/t1/scim/tokens/st1"),
    R("scim.revoke_all_tokens", lambda c: c.scim.revoke_all_tokens("t1"), "DELETE", "/v1/tenants/t1/scim/token"),
    R("scim.list_users", lambda c: c.scim.list_users("t1"), "GET", "/v1/tenants/t1/scim/users"),
    R("scim.list_groups", lambda c: c.scim.list_groups("t1", limit=10), "GET", "/v1/tenants/t1/scim/groups",
      query=[("limit", "10")]),
    R("social_providers.list", lambda c: c.social_providers.list("t1"), "GET", "/v1/tenants/t1/social/providers"),
    R("social_providers.upsert", lambda c: c.social_providers.upsert(provider="github", client_id="gh",
      client_secret="s"), "POST", "/v1/social/providers", {"provider": "github", "client_id": "gh", "client_secret": "s"}),
    R("social_providers.update", lambda c: c.social_providers.update("github", enabled=False), "PATCH",
      "/v1/social/providers/github", {"enabled": False}),
    R("social_providers.delete", lambda c: c.social_providers.delete("github"), "DELETE", "/v1/social/providers/github"),
    R("social_providers.unlink_identity", lambda c: c.social_providers.unlink_identity("x1"), "DELETE",
      "/v1/social/identities/x1"),
    R("admin_portal_links.create", lambda c: c.admin_portal_links.create("t1", ["saml", "scim"], ttl_seconds=3600),
      "POST", "/v1/tenants/t1/admin-portal/links", {"capabilities": ["saml", "scim"], "ttl_seconds": 3600}),
    R("admin_portal_links.list", lambda c: c.admin_portal_links.list("t1"), "GET", "/v1/tenants/t1/admin-portal/links"),
    R("admin_portal_links.revoke", lambda c: c.admin_portal_links.revoke("t1", "ln1"), "DELETE",
      "/v1/tenants/t1/admin-portal/links/ln1"),
    # Developer
    R("api_keys.create", lambda c: c.api_keys.create(tenant_id="t1", name="ci", scopes=["user.read"]), "POST",
      "/v1/api-keys", {"tenant_id": "t1", "name": "ci", "scopes": ["user.read"]}),
    R("api_keys.list", lambda c: c.api_keys.list("t1"), "GET", "/v1/tenants/t1/api-keys"),
    R("api_keys.rotate", lambda c: c.api_keys.rotate("t1", "k1", overlap_hours=24), "POST",
      "/v1/tenants/t1/api-keys/k1/rotate", {"overlap_hours": 24}),
    R("api_keys.revoke", lambda c: c.api_keys.revoke("k1"), "DELETE", "/v1/api-keys/k1"),
    R("agents.create", lambda c: c.agents.create("t1", name="invoice-bot", sponsor_user_id="u1"), "POST",
      "/v1/tenants/t1/agents", {"name": "invoice-bot", "sponsor_user_id": "u1"}),
    R("agents.list", lambda c: c.agents.list("t1"), "GET", "/v1/tenants/t1/agents"),
    R("agents.delete", lambda c: c.agents.delete("t1", "ag1"), "DELETE", "/v1/tenants/t1/agents/ag1"),
    R("agents.set_disabled", lambda c: c.agents.set_disabled("t1", "ag1", True), "PATCH", "/v1/tenants/t1/agents/ag1",
      {"disabled": True}),
    R("agents.suspend", lambda c: c.agents.suspend("t1", "ag1"), "POST", "/v1/tenants/t1/agents/ag1/suspend"),
    R("agents.resume", lambda c: c.agents.resume("t1", "ag1"), "POST", "/v1/tenants/t1/agents/ag1/resume"),
    R("agents.decommission", lambda c: c.agents.decommission("t1", "ag1"), "POST",
      "/v1/tenants/t1/agents/ag1/decommission"),
    R("agents.suspend_all", lambda c: c.agents.suspend_all("t1"), "POST", "/v1/tenants/t1/agents/kill-all"),
    R("agents.resume_all", lambda c: c.agents.resume_all("t1"), "POST", "/v1/tenants/t1/agents/resume-all"),
    R("agents.rotate_secret", lambda c: c.agents.rotate_secret("t1", "ag1"), "POST",
      "/v1/tenants/t1/agents/ag1/rotate-secret", {}),
    R("agents.list_sponsored_by", lambda c: c.agents.list_sponsored_by("t1", "u1"), "GET",
      "/v1/tenants/t1/agents/sponsored-by/u1"),
    R("agents.transfer_sponsorship", lambda c: c.agents.transfer_sponsorship("t1", "u1", "u2"), "POST",
      "/v1/tenants/t1/agents/sponsored-by/u1/transfer", {"to_user_id": "u2"}),
    R("agents.create_token", lambda c: c.agents.create_token("ag1", "agent-secret"), "POST", "/v1/agents/token",
      {"agent_id": "ag1", "secret": "agent-secret"}),
    R("verifiable_credentials.issue", lambda c: c.verifiable_credentials.issue("t1", subject="did:example:1",
      type="EmployeeCredential"), "POST", "/v1/tenants/t1/credentials",
      {"subject": "did:example:1", "type": "EmployeeCredential"}),
    R("verifiable_credentials.list", lambda c: c.verifiable_credentials.list("t1"), "GET", "/v1/tenants/t1/credentials"),
    R("verifiable_credentials.revoke", lambda c: c.verifiable_credentials.revoke("t1", "vc1"), "POST",
      "/v1/tenants/t1/credentials/vc1/revoke"),
    R("verifiable_credentials.verify", lambda c: c.verifiable_credentials.verify("eyJ.vc.jwt"), "POST",
      "/v1/credentials/verify", {"credential": "eyJ.vc.jwt"}),
    R("auth_hooks.list", lambda c: c.auth_hooks.list("t1"), "GET", "/v1/tenants/t1/auth-hooks"),
    R("auth_hooks.create", lambda c: c.auth_hooks.create("t1", url="https://hooks.example/login"), "POST",
      "/v1/tenants/t1/auth-hooks", {"url": "https://hooks.example/login"}),
    R("auth_hooks.update", lambda c: c.auth_hooks.update("t1", "h1", enabled=False), "PATCH",
      "/v1/tenants/t1/auth-hooks/h1", {"enabled": False}),
    R("auth_hooks.delete", lambda c: c.auth_hooks.delete("t1", "h1"), "DELETE", "/v1/tenants/t1/auth-hooks/h1"),
    R("auth_hooks.test", lambda c: c.auth_hooks.test("t1", "h1"), "POST", "/v1/tenants/t1/auth-hooks/h1/test"),
    R("webhooks.create", lambda c: c.webhooks.create(url="https://hooks.example/qeet", events=["user.created"]), "POST",
      "/v1/webhooks", {"url": "https://hooks.example/qeet", "events": ["user.created"]}),
    R("webhooks.get", lambda c: c.webhooks.get("w1"), "GET", "/v1/webhooks/w1"),
    R("webhooks.list", lambda c: c.webhooks.list("t1"), "GET", "/v1/tenants/t1/webhooks"),
    R("webhooks.update", lambda c: c.webhooks.update("t1", "w1", events=["user.deleted"]), "PATCH",
      "/v1/tenants/t1/webhooks/w1", {"events": ["user.deleted"]}),
    R("webhooks.disable", lambda c: c.webhooks.disable("w1"), "DELETE", "/v1/webhooks/w1"),
    R("webhooks.enable", lambda c: c.webhooks.enable("t1", "w1"), "POST", "/v1/tenants/t1/webhooks/w1/enable"),
    R("webhooks.rotate_secret", lambda c: c.webhooks.rotate_secret("t1", "w1"), "POST",
      "/v1/tenants/t1/webhooks/w1/rotate-secret"),
    R("webhooks.test", lambda c: c.webhooks.test("w1"), "POST", "/v1/webhooks/w1/test"),
    R("webhooks.list_event_types", lambda c: c.webhooks.list_event_types("t1"), "GET", "/v1/tenants/t1/webhooks/events"),
    R("webhooks.deliveries.list", lambda c: c.webhooks.deliveries.list("w1", status="dead"), "GET",
      "/v1/webhooks/w1/deliveries", query=[("status", "dead")]),
    R("webhooks.deliveries.retry", lambda c: c.webhooks.deliveries.retry("w1", "dl1"), "POST",
      "/v1/webhooks/w1/deliveries/dl1/retry"),
    R("webhooks.deliveries.retry_failed", lambda c: c.webhooks.deliveries.retry_failed("t1", "w1"), "POST",
      "/v1/tenants/t1/webhooks/w1/deliveries/retry"),
    R("webhooks.deliveries.list_attempts", lambda c: c.webhooks.deliveries.list_attempts("t1", "w1", "dl1"), "GET",
      "/v1/tenants/t1/webhooks/w1/deliveries/dl1/attempts"),
    R("secrets.list", lambda c: c.secrets.list("t1"), "GET", "/v1/tenants/t1/secrets"),
    R("secrets.create", lambda c: c.secrets.create("t1", name="stripe", scope="billing", value="v"), "POST",
      "/v1/tenants/t1/secrets", {"name": "stripe", "scope": "billing", "value": "v"}),
    R("secrets.update", lambda c: c.secrets.update("t1", "s1", rotation_interval_days=90), "PATCH",
      "/v1/tenants/t1/secrets/s1", {"rotation_interval_days": 90}),
    R("secrets.delete", lambda c: c.secrets.delete("t1", "s1"), "DELETE", "/v1/tenants/t1/secrets/s1"),
    R("secrets.reveal", lambda c: c.secrets.reveal("t1", "s1"), "POST", "/v1/tenants/t1/secrets/s1/reveal"),
    R("secrets.get_value", lambda c: c.secrets.get_value("stripe"), "GET", "/v1/vault/stripe"),
    R("token_vault.create_provider", lambda c: c.token_vault.create_provider("t1", provider="slack", client_id="c",
      client_secret="s", authorize_url="https://slack.com/oauth", token_url="https://slack.com/token"), "POST",
      "/v1/tenants/t1/vault/tokens/providers",
      {"provider": "slack", "client_id": "c", "client_secret": "s", "authorize_url": "https://slack.com/oauth",
       "token_url": "https://slack.com/token"}),
    R("token_vault.list_providers", lambda c: c.token_vault.list_providers("t1"), "GET",
      "/v1/tenants/t1/vault/tokens/providers"),
    R("token_vault.delete_provider", lambda c: c.token_vault.delete_provider("t1", "slack"), "DELETE",
      "/v1/tenants/t1/vault/tokens/providers/slack"),
    R("token_vault.get_access_token", lambda c: c.token_vault.get_access_token("slack"), "GET",
      "/v1/vault/tokens/slack/access-token", warns=DeprecationWarning),
    # Operations
    R("audit_logs.list", lambda c: c.audit_logs.list("t1", action="user.deleted", from_="2026-11-01T00:00:00Z"), "GET",
      "/v1/tenants/t1/audit", query=[("action", "user.deleted"), ("from", "2026-11-01T00:00:00Z")]),
    R("audit_logs.verify", lambda c: c.audit_logs.verify("t1"), "GET", "/v1/tenants/t1/audit/verify"),
    R("audit_logs.get_verification_status", lambda c: c.audit_logs.get_verification_status("t1"), "GET",
      "/v1/tenants/t1/audit/verification"),
    R("audit_logs.anomalies.list", lambda c: c.audit_logs.anomalies.list("t1", status="open"), "GET",
      "/v1/tenants/t1/audit/anomalies", query=[("status", "open")]),
    R("audit_logs.anomalies.get_summary", lambda c: c.audit_logs.anomalies.get_summary("t1"), "GET",
      "/v1/tenants/t1/audit/anomalies/summary"),
    R("audit_logs.anomalies.resolve", lambda c: c.audit_logs.anomalies.resolve("t1", "aa1"), "POST",
      "/v1/tenants/t1/audit/anomalies/aa1/resolve"),
    R("audit_logs.anomalies.get_settings", lambda c: c.audit_logs.anomalies.get_settings("t1"), "GET",
      "/v1/tenants/t1/audit/anomaly-settings"),
    R("audit_logs.anomalies.update_settings", lambda c: c.audit_logs.anomalies.update_settings("t1", enabled=True,
      score_threshold=0.8, min_baseline_events=50), "PUT", "/v1/tenants/t1/audit/anomaly-settings",
      {"enabled": True, "score_threshold": 0.8, "min_baseline_events": 50}),
    R("analytics.get_overview", lambda c: c.analytics.get_overview("t1", days=30, method="passkey"), "GET",
      "/v1/tenants/t1/analytics/overview", query=[("days", "30"), ("method", "passkey")]),
    R("billing.get_subscription", lambda c: c.billing.get_subscription("t1"), "GET",
      "/v1/tenants/t1/billing/subscription"),
    R("billing.update_subscription", lambda c: c.billing.update_subscription("t1", plan_code="pro", currency="INR"),
      "PUT", "/v1/tenants/t1/billing/subscription", {"plan_code": "pro", "currency": "INR"}),
    R("billing.cancel_subscription", lambda c: c.billing.cancel_subscription("t1"), "POST",
      "/v1/tenants/t1/billing/subscription/cancel"),
    R("billing.checkout", lambda c: c.billing.checkout("t1", plan_code="pro", currency="INR",
      success_url="https://a.example/ok", cancel_url="https://a.example/no"), "POST", "/v1/tenants/t1/billing/checkout",
      {"plan_code": "pro", "currency": "INR", "success_url": "https://a.example/ok", "cancel_url": "https://a.example/no"}),
    R("billing.list_invoices", lambda c: c.billing.list_invoices("t1"), "GET", "/v1/tenants/t1/billing/invoices"),
    R("billing.pay_invoice", lambda c: c.billing.pay_invoice("t1", "inv1", success_url="https://a.example/ok",
      cancel_url="https://a.example/no"), "POST", "/v1/tenants/t1/billing/invoices/inv1/pay",
      {"success_url": "https://a.example/ok", "cancel_url": "https://a.example/no"}),
    R("billing.get_payment_method", lambda c: c.billing.get_payment_method("t1"), "GET",
      "/v1/tenants/t1/billing/payment-method"),
    R("billing.get_profile", lambda c: c.billing.get_profile("t1"), "GET", "/v1/tenants/t1/billing/profile"),
    R("billing.update_profile", lambda c: c.billing.update_profile("t1", legal_name="Brightleaf Foods Pvt Ltd"), "PUT",
      "/v1/tenants/t1/billing/profile", {"legal_name": "Brightleaf Foods Pvt Ltd"}),
    R("billing.get_entitlements", lambda c: c.billing.get_entitlements("t1"), "GET", "/v1/tenants/t1/entitlements"),
    R("billing.get_usage", lambda c: c.billing.get_usage("t1"), "GET", "/v1/tenants/t1/entitlements/usage"),
    R("gdpr.erasures.create", lambda c: c.gdpr.erasures.create(tenant_id="t1", user_id="u1", reason="Customer request"),
      "POST", "/v1/gdpr/purge", {"tenant_id": "t1", "user_id": "u1", "reason": "Customer request"}),
    R("gdpr.erasures.list", lambda c: c.gdpr.erasures.list("t1"), "GET", "/v1/tenants/t1/gdpr/purge"),
    R("gdpr.erasures.cancel", lambda c: c.gdpr.erasures.cancel("pr1"), "DELETE", "/v1/gdpr/purge/pr1"),
    R("gdpr.exports.create", lambda c: c.gdpr.exports.create(tenant_id="t1", user_id="u1"), "POST", "/v1/gdpr/export",
      {"tenant_id": "t1", "user_id": "u1"}),
    R("gdpr.exports.get", lambda c: c.gdpr.exports.get("t1", "ex1"), "GET", "/v1/tenants/t1/gdpr/export/ex1"),
    R("gdpr.exports.list", lambda c: c.gdpr.exports.list("t1"), "GET", "/v1/tenants/t1/gdpr/export"),
    R("email_templates.list", lambda c: c.email_templates.list("t1"), "GET", "/v1/tenants/t1/email-templates"),
    R("email_templates.get", lambda c: c.email_templates.get("t1", "invite"), "GET",
      "/v1/tenants/t1/email-templates/invite"),
    R("email_templates.update", lambda c: c.email_templates.update("t1", "invite", subject="Join {{org}}", body="Hi"),
      "PUT", "/v1/tenants/t1/email-templates/invite", {"subject": "Join {{org}}", "body": "Hi"}),
    R("email_templates.reset", lambda c: c.email_templates.reset("t1", "invite"), "DELETE",
      "/v1/tenants/t1/email-templates/invite"),
    R("email_templates.preview", lambda c: c.email_templates.preview("t1", "invite", vars={"org": "Brightleaf"}),
      "POST", "/v1/tenants/t1/email-templates/invite/preview", {"vars": {"org": "Brightleaf"}}),
    R("email_templates.send_test", lambda c: c.email_templates.send_test("t1", "invite", draft={"subject": "s",
      "body": "b"}), "POST", "/v1/tenants/t1/email-templates/invite/test", {"draft": {"subject": "s", "body": "b"}}),
    R("retention.get", lambda c: c.retention.get("t1"), "GET", "/v1/tenants/t1/retention"),
    R("retention.update", lambda c: c.retention.update("t1", deleted_users_enabled=True, deleted_users_days=30), "PUT",
      "/v1/tenants/t1/retention", {"deleted_users_enabled": True, "deleted_users_days": 30}),
    R("retention.preview", lambda c: c.retention.preview("t1"), "POST", "/v1/tenants/t1/retention/preview"),
    R("retention.run", lambda c: c.retention.run("t1"), "POST", "/v1/tenants/t1/retention/run"),
    R("log_sinks.create", lambda c: c.log_sinks.create("t1", type="datadog",
      endpoint="https://http-intake.logs.datadoghq.com", token="dd"), "POST", "/v1/tenants/t1/log-sinks",
      {"type": "datadog", "endpoint": "https://http-intake.logs.datadoghq.com", "token": "dd"}),
    R("log_sinks.list", lambda c: c.log_sinks.list("t1"), "GET", "/v1/tenants/t1/log-sinks"),
    R("log_sinks.set_enabled", lambda c: c.log_sinks.set_enabled("t1", "ls1", False), "PATCH",
      "/v1/tenants/t1/log-sinks/ls1", {"enabled": False}),
    R("log_sinks.delete", lambda c: c.log_sinks.delete("t1", "ls1"), "DELETE", "/v1/tenants/t1/log-sinks/ls1"),
    R("log_sinks.test", lambda c: c.log_sinks.test("t1", "ls1"), "POST", "/v1/tenants/t1/log-sinks/ls1/test"),
    R("log_sinks.test_destination", lambda c: c.log_sinks.test_destination("t1", type="http",
      endpoint="https://siem.example"), "POST", "/v1/tenants/t1/log-sinks/test",
      {"type": "http", "endpoint": "https://siem.example"}),
    R("rate_limits.get", lambda c: c.rate_limits.get("t1"), "GET", "/v1/tenants/t1/rate-limits"),
    R("rate_limits.update", lambda c: c.rate_limits.update("t1", api_key={"rate": 50, "capacity": 100}), "PUT",
      "/v1/tenants/t1/rate-limits", {"api_key": {"rate": 50, "capacity": 100}}),
    R("rate_limits.reset", lambda c: c.rate_limits.reset("t1"), "DELETE", "/v1/tenants/t1/rate-limits"),
]  # fmt: skip


# ---------------------------------------------------------------------------
# The contract


@cache
def operations() -> list[tuple[re.Pattern[str], dict[str, Any]]]:
    """Every operation with a pattern for its path, the most specific (fewest parameters) first."""
    out = []
    for op in CONTRACT["operations"]:
        pattern = re.compile("^" + re.sub(r"\\\{[^/]+?\\\}", "[^/]+", re.escape(op["path"])) + "$")
        out.append((pattern, op))
    return sorted(out, key=lambda item: item[1]["path"].count("{"))


def operation_for(method: str, url_path: str) -> dict[str, Any] | None:
    return next((op for pattern, op in operations() if op["method"] == method and pattern.match(url_path)), None)


def return_shape(client: QeetID, name: str) -> type | None:
    """ListResult or Page when the method returns one; None otherwise."""
    target: Any = client
    for part in name.split("."):
        target = getattr(target, part)
    hint = typing.get_type_hints(target).get("return")
    origin = typing.get_origin(hint) or hint
    return origin if origin in (ListResult, Page) else None


def check_against_contract(row: Row, request: Recorded, shape: type | None) -> None:
    op = operation_for(request.method, request.path)
    assert op is not None, f"{request.method} {request.path} is not an operation of the API"
    where = f"{row.name}: {op['method']} {op['path']}"

    authorization = request.headers.get("authorization", "")
    if authorization.startswith("ApiKey "):
        assert "apiKeyAuth" in op["security"], f"{where} doesn't accept an API key"
    elif authorization.startswith("Basic "):
        assert "clientCredentials" in op["security"], f"{where} doesn't take client authentication"
    else:
        assert not authorization, f"{where}: unexpected Authorization"
        public_client = "clientCredentials" in op["security"] and "client_id" in request.form
        assert not op["security"] or public_client, f"{where} needs a credential the SDK didn't send"

    unknown_query = {name for name, _ in request.query} - set(op["query"])
    assert not unknown_query, f"{where} documents no query parameter {sorted(unknown_query)}"

    content_type = request.headers.get("content-type", "").split(";")[0]
    if request.content:
        assert content_type in op["body"]["content_types"], f"{where} takes no {content_type} body"
        fields: Any = None
        if content_type == "application/x-www-form-urlencoded":
            fields = request.form
        elif content_type == "application/json":
            fields = request.json
        if isinstance(fields, dict) and op["body"]["fields"]:
            allowed = set(op["body"]["fields"]) | UNDOCUMENTED_FIELDS.get((op["method"], op["path"]), set())
            unknown = set(fields) - allowed
            assert not unknown, f"{where} documents no body field {sorted(unknown)}"

    sent_key = "idempotency-key" in request.headers
    assert sent_key == op["idempotency_key"], (
        f"{where}: Idempotency-Key sent={sent_key}, honoured={op['idempotency_key']}"
    )

    if shape is ListResult:
        assert {"items", "keys"} & set(op["response"]["fields"]), f"{where} answers no list"
    if shape is Page:
        assert {"items", "next_cursor"} <= set(op["response"]["fields"]), f"{where} answers no cursor page"


# ---------------------------------------------------------------------------
# The tests


@pytest.mark.parametrize("row", ROWS, ids=[row.name for row in ROWS])
async def test_request(row: Row, kind: Kind, api: MockAPI) -> None:
    client = api.answer({"json": row.answer}).client(kind)
    if row.warns is not None:
        with pytest.warns(row.warns):
            await run(row.call(client))
    else:
        await run(row.call(client))
    assert len(api.requests) == 1, f"{row.name} sent {len(api.requests)} requests"
    request = api.last
    assert (request.method, request.path) == (row.method, row.path)
    if row.json is not None:
        assert request.json == row.json
    if row.form is not None:
        assert request.form == row.form
    if row.query is not None:
        assert request.query == row.query
    if row.method in ("GET", "DELETE"):
        assert request.content == b""
    check_against_contract(row, request, return_shape(QeetID(api_key="qk"), row.name))


def public_methods(namespace: object, prefix: str) -> set[str]:
    names = set()
    for attr, value in vars(type(namespace)).items():
        if attr.startswith("_"):
            continue
        if inspect.isfunction(value) and attr != "create_token_guard":
            names.add(f"{prefix}{attr}")
    for attr in getattr(type(namespace), "__slots__", ()):
        child = getattr(namespace, attr, None)
        if isinstance(child, APIResource | AsyncAPIResource):
            names |= public_methods(child, f"{prefix}{attr}.")
    return names


@pytest.mark.parametrize("kind", ["sync", "async"])
def test_every_method_has_a_row(kind: Kind) -> None:
    client = MockAPI().client(kind)
    methods = set()
    for attr, value in vars(client).items():
        if isinstance(value, APIResource | AsyncAPIResource):
            methods |= public_methods(value, f"{attr}.")
    rows = {row.name for row in ROWS}
    assert methods - rows == set(), "methods without a row"
    assert rows - methods == set(), "rows without a method"
    assert len(rows) == len(ROWS), "a method has two rows"


def test_the_event_catalogue_matches_the_server() -> None:
    assert list(WEBHOOK_EVENT_TYPES) == CONTRACT["webhook_events"]


@pytest.mark.parametrize("kind", ["sync", "async"])
def test_async_and_sync_namespaces_match(kind: Kind) -> None:
    sync = MockAPI().client("sync")
    other = MockAPI().client(kind)
    assert {k for k in vars(sync) if not k.startswith("_")} == {k for k in vars(other) if not k.startswith("_")}
