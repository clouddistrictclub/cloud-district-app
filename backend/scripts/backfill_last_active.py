"""
ONE-TIME MIGRATION: Backfill lastActiveAt for users where it is null.

Sources checked (most recent wins):
  - orders.createdAt       (userId == str(user._id))
  - cloudz_ledger.createdAt (userId == str(user._id))

Run:
  cd /app/backend && python scripts/backfill_last_active.py
"""

import asyncio
import os
import sys
from datetime import datetime

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME   = os.environ["DB_NAME"]


async def run() -> None:
    client = AsyncIOMotorClient(MONGO_URL)
    db     = client[DB_NAME]

    # Only process users with no lastActiveAt
    users = await db.users.find(
        {"lastActiveAt": None},
        {"_id": 1, "email": 1},
    ).to_list(10_000)

    print(f"Users to backfill: {len(users)}")

    updated = 0
    skipped = 0

    for user in users:
        uid_str = str(user["_id"])

        # Most recent order for this user
        order_doc = await db.orders.find_one(
            {"userId": uid_str},
            {"createdAt": 1},
            sort=[("createdAt", -1)],
        )

        # Most recent cloudz ledger entry for this user
        ledger_doc = await db.cloudz_ledger.find_one(
            {"userId": uid_str},
            {"createdAt": 1},
            sort=[("createdAt", -1)],
        )

        # Collect candidate timestamps
        candidates: list[datetime] = []
        if order_doc  and order_doc.get("createdAt"):
            candidates.append(order_doc["createdAt"])
        if ledger_doc and ledger_doc.get("createdAt"):
            candidates.append(ledger_doc["createdAt"])

        if not candidates:
            skipped += 1
            continue

        most_recent = max(candidates)

        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"lastActiveAt": most_recent}},
        )
        updated += 1
        print(f"  {user.get('email', uid_str):<40}  lastActiveAt = {most_recent.isoformat()}")

    print(f"\nDone. Updated: {updated}  |  No activity found (left null): {skipped}")
    client.close()


if __name__ == "__main__":
    asyncio.run(run())
