"""
ONE-TIME MIGRATION: Backfill referralCode = username for users where they differ.

Rules:
  - Only updates users who HAVE a username set
  - Sets referralCode = username (lowercase enforced at registration)
  - Skips users with no username (referralCode left as-is)

Run:
  cd /app/backend && python scripts/backfill_referral_codes.py
"""

import asyncio
import os

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME   = os.environ["DB_NAME"]


async def run() -> None:
    client = AsyncIOMotorClient(MONGO_URL)
    db     = client[DB_NAME]

    # Find users who have a username but referralCode is missing or doesn't match
    users = await db.users.find(
        {"username": {"$exists": True, "$ne": None}},
        {"_id": 1, "email": 1, "username": 1, "referralCode": 1},
    ).to_list(10_000)

    print(f"Users with username set: {len(users)}")

    already_correct = 0
    updated         = 0

    for user in users:
        username      = user.get("username", "").strip()
        referral_code = user.get("referralCode", "")

        if not username:
            continue

        if referral_code == username:
            already_correct += 1
            continue

        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"referralCode": username}},
        )
        updated += 1
        print(f"  UPDATED  {user.get('email', str(user['_id'])):<40}  "
              f"referralCode: '{referral_code}' → '{username}'")

    print(f"\nDone. Already correct: {already_correct}  |  Updated: {updated}")
    client.close()


if __name__ == "__main__":
    asyncio.run(run())
