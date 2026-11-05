"""What resource methods do beyond sending their request: shaping answers, checking arguments."""

import re
from typing import Any

import pytest

from qeet_id import ListResult, ServiceUnavailableError

from .conftest import Kind, MockAPI, collect, envelope, run

pytestmark = pytest.mark.anyio

UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


@pytest.mark.parametrize(
    "create",
    [
        lambda c, **k: c.users.create(tenant_id="t1", email="a@b.in", **k),
        lambda c, **k: c.groups.create(name="Finance", **k),
        lambda c, **k: c.invitations.create(tenant_id="t1", email="a@b.in", **k),
        lambda c, **k: c.service_principals.create(tenant_id="t1", name="etl", **k),
        lambda c, **k: c.api_keys.create(tenant_id="t1", name="ci", **k),
        lambda c, **k: c.agents.create("t1", name="bot", sponsor_user_id="u1", **k),
        lambda c, **k: c.webhooks.create(url="https://h.example", events=["user.created"], **k),
        lambda c, **k: c.billing.checkout(
            "t1", plan_code="pro", currency="INR", success_url="https://a.example", cancel_url="https://a.example", **k
        ),
        lambda c, **k: c.billing.pay_invoice(
            "t1", "inv1", success_url="https://a.example", cancel_url="https://a.example", **k
        ),
    ],
    ids=[
        "users",
        "groups",
        "invitations",
        "service_principals",
        "api_keys",
        "agents",
        "webhooks",
        "checkout",
        "pay_invoice",
    ],
)
async def test_the_nine_idempotent_creates(api: MockAPI, kind: Kind, create: Any) -> None:
    api.answer({"status": 503, "json": envelope("server.overloaded")}, {"status": 201, "json": {}})
    client = api.client(kind)
    await run(create(client))
    generated = [r.headers["idempotency-key"] for r in api.requests]
    assert UUID4.match(generated[0])
    assert generated == [generated[0]] * 2  # retried with the same key
    await run(create(client, idempotency_key="onboarding-42"))
    assert api.last.headers["idempotency-key"] == "onboarding-42"


async def test_other_writes_are_not_retried(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 503, "json": envelope("server.overloaded")})
    with pytest.raises(ServiceUnavailableError):
        await run(api.client(kind).roles.create("t1", "Auditor"))
    assert len(api.requests) == 1
    assert "idempotency-key" not in api.last.headers


async def test_permission_check_reads_allowed(api: MockAPI, kind: Kind) -> None:
    client = api.answer({"json": {"allowed": True}}, {"json": {"allowed": "yes"}}).client(kind)
    assert await run(client.permissions.check(user_id="u1", tenant_id="t1", permission="x")) is True
    assert await run(client.permissions.check(user_id="u1", tenant_id="t1", permission="x")) is False


async def test_relationship_checks(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 503}, {"json": {"allowed": True, "path": []}})
    client = api.client(kind)
    assert await run(client.relationships.check("t1", object="doc:1", relation="viewer", user_id="u1")) is True
    assert len(api.requests) == 2  # a check changes nothing, so it is retried


async def test_relationship_list_needs_one_side(api: MockAPI, kind: Kind) -> None:
    client = api.client(kind)
    with pytest.raises(ValueError, match="exactly one"):
        await run(client.relationships.list("t1"))
    with pytest.raises(ValueError, match="exactly one"):
        await run(client.relationships.list("t1", object="doc:1", subject="user:u1"))


async def test_grants_revoke_many_needs_one_selector(api: MockAPI, kind: Kind) -> None:
    client = api.client(kind)
    with pytest.raises(ValueError, match="exactly one"):
        await run(client.oauth.grants.revoke_many("t1"))
    with pytest.raises(ValueError, match="exactly one"):
        await run(client.oauth.grants.revoke_many("t1", ids=["g1"], client_id="app"))
    await run(client.oauth.grants.revoke_many("t1", ids=("g1", "g2")))
    assert api.last.json == {"ids": ["g1", "g2"]}


async def test_answers_are_shaped(api: MockAPI, kind: Kind) -> None:
    client = api.answer(
        {"json": {"enabled": True, "items": [{"id": "ir1"}]}},
        {"json": {"items": [{"id": "p1"}]}},
        {"json": {}},
        {"json": {"evaluations": [{"decision": True}]}},
        {"json": {}},
        {"json": {"payment_method": None}},
        {"json": {"usage": {"users": 12}}},
        {"json": {}},
        {"json": {"keys": [{"kid": "k1"}]}},
    ).client(kind)
    assert await run(client.ip_rules.list("t1")) == {"enabled": True, "data": [{"id": "ir1"}]}
    assert await run(client.roles.set_permissions("t1", "r1", ["p1"])) == ListResult([{"id": "p1"}])
    assert await run(client.permissions.list_effective("t1", "u1")) == {"permissions": [], "grants": []}
    assert await run(client.decisions.evaluate_many("t1", [{"action": {"name": "read"}}])) == {
        "evaluations": [{"decision": True}]
    }
    assert await run(client.saml_service_providers.list_assignments("t1", "sp1")) == {"users": [], "groups": []}
    assert await run(client.billing.get_payment_method("t1")) is None
    assert await run(client.billing.get_usage("t1")) == {"users": 12}
    assert await run(client.billing.get_usage("t1")) == {}
    assert (await run(client.oauth.signing_keys.list())).data == [{"kid": "k1"}]


async def test_lists_report_truncation(api: MockAPI, kind: Kind) -> None:
    api.answer({"json": {"items": [{"id": "s1"}], "truncated": True}})
    secrets = await run(api.client(kind).secrets.list("t1"))
    assert secrets.truncated is True
    assert [s["id"] for s in secrets] == ["s1"]


async def test_paged_lists_walk_every_page(api: MockAPI, kind: Kind) -> None:
    api.answer({"json": {"items": [{"id": "u1"}], "next_cursor": "c2"}}, {"json": {"items": [{"id": "u2"}]}})
    users = await collect(api.client(kind).users.list(status="active"))
    assert [u["id"] for u in users] == ["u1", "u2"]
    assert api.last.query == [("status", "active"), ("cursor", "c2")]


async def test_directory_sign_in_answers_tokens_or_a_challenge(api: MockAPI, kind: Kind) -> None:
    tokens = {"access_token": "at", "refresh_token": "rt", "session_id": "s1"}
    challenge = {"mfa_required": True, "mfa_token": "mt"}
    client = api.answer({"json": tokens}, {"json": challenge}).client(kind)
    first = await run(client.ldap_connections.authenticate("l1", username="meera", password="pw"))
    assert first == {"type": "tokens", "tokens": tokens}
    assert "authorization" not in api.last.headers
    second = await run(client.ldap_connections.authenticate("l1", username="meera", password="pw"))
    assert second == {"type": "mfa_challenge", "challenge": {**challenge, "methods": [], "factors": []}}


async def test_directory_sign_in_is_never_retried(api: MockAPI, kind: Kind) -> None:
    api.answer({"status": 503, "json": envelope("server.overloaded")})
    with pytest.raises(ServiceUnavailableError):
        await run(api.client(kind).ldap_connections.authenticate("l1", username="u", password="p"))
    assert len(api.requests) == 1


@pytest.mark.parametrize(
    ("source", "content_type"),
    [("auth0", "application/x-ndjson"), ("cognito", "text/csv"), ("azure_b2c", "application/json")],
)
async def test_bulk_import_sends_the_file_as_is(api: MockAPI, kind: Kind, source: str, content_type: str) -> None:
    await run(api.client(kind).users.bulk_import(source, b'{"email":"a@b.in"}\n'))  # type: ignore[arg-type]
    assert api.last.headers["content-type"] == content_type
    assert api.last.content == b'{"email":"a@b.in"}\n'


async def test_bulk_import_refuses_an_unknown_source(api: MockAPI, kind: Kind) -> None:
    with pytest.raises(ValueError, match="source"):
        await run(api.client(kind).users.bulk_import("okta", "x"))  # type: ignore[arg-type]


async def test_raw_vault_tokens_warn(api: MockAPI, kind: Kind) -> None:
    with pytest.warns(DeprecationWarning, match="raw third-party token"):
        await run(api.client(kind).token_vault.get_access_token("slack"))


async def test_identifiers_are_checked_before_sending(api: MockAPI, kind: Kind) -> None:
    client = api.client(kind)
    with pytest.raises(ValueError, match="non-empty"):
        await run(client.users.get(""))
    with pytest.raises(ValueError, match="non-empty"):
        await run(client.webhooks.deliveries.list(".."))
    assert api.requests == []


async def test_identifiers_are_escaped(api: MockAPI, kind: Kind) -> None:
    await run(api.client(kind).email_templates.get("t1", "password reset/v2"))
    assert api.last.path == "/v1/tenants/t1/email-templates/password%20reset%2Fv2"


async def test_optional_fields_are_left_out(api: MockAPI, kind: Kind) -> None:
    client = api.client(kind)
    await run(client.roles.update("t1", "r1"))
    assert api.last.json == {}
    await run(client.service_principals.rotate_secret("t1", "sp1"))
    assert api.last.json == {}
    await run(client.verifiable_credentials.issue("t1", subject="s", type="T", ttl_seconds=60, claims={"a": 1}))
    assert api.last.json == {"subject": "s", "type": "T", "claims": {"a": 1}, "ttl_seconds": 60}
    await run(client.email_templates.send_test("t1", "invite", draft={"subject": "s", "body": "b"}, locale="hi"))
    assert api.last.json == {"draft": {"subject": "s", "body": "b"}, "locale": "hi"}
    await run(client.applications.resources.create("t1", "https://mcp.example", name="MCP", server_client_id="app"))
    assert api.last.json == {"identifier": "https://mcp.example", "name": "MCP", "server_client_id": "app"}
    await run(client.admin_portal_links.create("t1", ["saml"]))
    assert api.last.json == {"capabilities": ["saml"]}


def test_resources_have_a_plain_repr() -> None:
    client = MockAPI().client("sync")
    assert repr(client.users) == "<Users>"
    assert repr(MockAPI().client("async").users) == "<AsyncUsers>"
