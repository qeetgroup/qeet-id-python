"""Print the last week's deletions from the audit log, with the asynchronous client and machine credentials.

QEET_ID_CLIENT_ID=… QEET_ID_CLIENT_SECRET=… QEET_ID_TENANT_ID=… python examples/async_audit_report.py
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta

from qeet_id import AsyncQeetID


async def main() -> None:
    """Walk every page of the week's user deletions."""
    tenant_id = os.environ["QEET_ID_TENANT_ID"]
    since = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    async with AsyncQeetID(
        client_id=os.environ["QEET_ID_CLIENT_ID"], client_secret=os.environ["QEET_ID_CLIENT_SECRET"]
    ) as client:
        async for entry in client.audit_logs.list(tenant_id, action="user.deleted", from_=since):
            print(entry["created_at"], entry["actor_user_id"], entry["resource_id"])
        chain = await client.audit_logs.verify(tenant_id)
        print("chain intact" if chain["ok"] else f"chain broken at {chain.get('broken_at_id')}")


if __name__ == "__main__":
    asyncio.run(main())
