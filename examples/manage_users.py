"""Onboard a person: create them, give them a role and a group, and check what they may do.

QEET_ID_API_KEY=qk_… QEET_ID_TENANT_ID=… python examples/manage_users.py
"""

import os

from qeet_id import ConflictError, QeetID


def main() -> None:
    """Onboard Meera into the finance team."""
    tenant_id = os.environ["QEET_ID_TENANT_ID"]
    with QeetID(api_key=os.environ["QEET_ID_API_KEY"], app_info={"name": "brightleaf-onboarding"}) as client:
        try:
            user = client.users.create(
                tenant_id=tenant_id,
                email="meera@brightleaffoods.in",
                display_name="Meera Iyer",
                idempotency_key="onboarding-meera-iyer",
            )
        except ConflictError as error:
            print(f"Not created: {error.code} (request {error.request_id})")
            return

        finance = next((role for role in client.roles.list(tenant_id) if role["name"] == "finance"), None)
        if finance is not None:
            client.roles.assign(tenant_id, user["id"], finance["id"])
        group = client.groups.create(name="Accounts payable", description="Approves supplier invoices")
        client.groups.add_member(group["id"], user["id"])

        allowed = client.permissions.check(user_id=user["id"], tenant_id=tenant_id, permission="invoice.approve")
        print(f"{user['email']} may approve invoices: {allowed}")

        for member in client.users.list(status="active", limit=100):
            print(member["email"], member.get("roles", []))


if __name__ == "__main__":
    main()
