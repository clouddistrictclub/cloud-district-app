#!/usr/bin/env python3
"""
Cloud District Club — Controlled User Migration
=================================================
Migrates ONLY the 13 specified users + their orders, ledger, and rewards.
Handles ID remapping for users that already exist in production.
"""

import asyncio
import json
import requests
from copy import deepcopy
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

PRODUCTION_URL = "https://api.clouddistrict.club"
ADMIN_EMAIL = "jkaatz@gmail.com"
ADMIN_PASSWORD = "Just1n23$"

TARGET_EMAILS = [
    "jkaatz@gmail.com",
    "jraymasangkay@gmail.com",
    "tccaldwell2013@gmail.com",
    "briannamchase@gmail.com",
    "sophiamylife27@gmail.com",
    "babypufferfish69@yahoo.com",
    "krystle.jischkowsky@outlook.com",
    "sobermenace17@gmail.com",
    "jennifer.schoninger@gmail.com",
    "ambersays6862@gmail.com",
    "ewingtrevorfreedom25@gmail.com",
    "kippyruth@gmail.com",
    "kaleenamw@gmail.com",
]


def serialize_doc(doc):
    """Convert a MongoDB document to JSON-safe dict."""
    result = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = serialize_doc(v)
        elif isinstance(v, list):
            result[k] = [serialize_doc(i) if isinstance(i, dict) else (str(i) if isinstance(i, ObjectId) else i) for i in v]
        else:
            result[k] = v
    return result


def remap_user_id(doc, id_map, fields):
    """Remap user ID fields in a document using the ID mapping."""
    d = deepcopy(doc)
    for field in fields:
        if field in d and d[field] in id_map:
            d[field] = id_map[d[field]]
    return d


def get_prod_token():
    resp = requests.post(
        f"{PRODUCTION_URL}/api/auth/login",
        json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"]


def import_to_prod(token, collection, documents):
    """Import documents to production via API. Returns (inserted, skipped, errors)."""
    if not documents:
        return 0, 0, []
    total_ins, total_skip, total_err = 0, 0, []
    CHUNK = 25
    for i in range(0, len(documents), CHUNK):
        chunk = documents[i:i+CHUNK]
        resp = requests.post(
            f"{PRODUCTION_URL}/api/admin/migrate/import",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"collection": collection, "documents": chunk},
            timeout=120,
        )
        resp.raise_for_status()
        r = resp.json()
        total_ins += r.get("inserted", 0)
        total_skip += r.get("skipped", 0)
        total_err.extend(r.get("errors", []))
    return total_ins, total_skip, total_err


def update_prod_user(token, user_id, update_fields):
    """Update an existing production user's fields."""
    resp = requests.patch(
        f"{PRODUCTION_URL}/api/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=update_fields,
        timeout=30,
    )
    return resp.status_code, resp.json()


async def main():
    print("=" * 60)
    print("CONTROLLED MIGRATION — 13 Users")
    print(f"Target: {PRODUCTION_URL}")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # ---- Connect to preview MongoDB ----
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["test_database"]

    # ---- Step 1: Get production admin token ----
    print("\n[1/6] Authenticating with production...")
    prod_token = get_prod_token()
    print("  OK")

    # ---- Step 2: Get production existing users ----
    print("\n[2/6] Checking production for existing users...")
    prod_users_resp = requests.get(
        f"{PRODUCTION_URL}/api/admin/users",
        headers={"Authorization": f"Bearer {prod_token}"},
        timeout=30,
    )
    prod_users = prod_users_resp.json()
    prod_email_to_id = {u["email"]: u["id"] for u in prod_users}
    print(f"  Production has {len(prod_users)} existing users")
    for email, pid in prod_email_to_id.items():
        if email in TARGET_EMAILS:
            print(f"  EXISTING: {email} → prod_id={pid}")

    # ---- Step 3: Export preview users ----
    print("\n[3/6] Exporting preview data for 13 users...")
    preview_users = []
    preview_user_ids = []
    id_map = {}  # preview_id → production_id (for remapping)

    for email in TARGET_EMAILS:
        user = await db.users.find_one({"email": email})
        if not user:
            print(f"  SKIP (not in preview): {email}")
            continue
        preview_id = str(user["_id"])
        preview_users.append(serialize_doc(user))
        preview_user_ids.append(preview_id)

        # Check if this user already exists in production
        if email in prod_email_to_id:
            prod_id = prod_email_to_id[email]
            id_map[preview_id] = prod_id
            print(f"  REMAP: {email}  preview={preview_id} → prod={prod_id}")
        else:
            print(f"  NEW:   {email}  _id={preview_id}")

    # Export orders for these users
    orders_cursor = db.orders.find({"userId": {"$in": preview_user_ids}})
    preview_orders = [serialize_doc(o) async for o in orders_cursor]
    print(f"  Orders: {len(preview_orders)}")

    # Export ledger for these users
    ledger_cursor = db.cloudz_ledger.find({"userId": {"$in": preview_user_ids}})
    preview_ledger = [serialize_doc(e) async for e in ledger_cursor]
    print(f"  Ledger entries: {len(preview_ledger)}")

    # Export loyalty rewards for these users
    rewards_cursor = db.loyalty_rewards.find({"userId": {"$in": preview_user_ids}})
    preview_rewards = [serialize_doc(r) async for r in rewards_cursor]
    print(f"  Loyalty rewards: {len(preview_rewards)}")

    # Also get ledger entries where referredUserId is one of our users
    extra_ledger_cursor = db.cloudz_ledger.find({
        "referredUserId": {"$in": preview_user_ids},
        "userId": {"$nin": preview_user_ids},
    })
    extra_ledger = [serialize_doc(e) async for e in extra_ledger_cursor]
    if extra_ledger:
        print(f"  Extra referral ledger (referrer outside scope): {len(extra_ledger)} — skipping these")

    # ---- Step 4: Apply ID remapping ----
    print("\n[4/6] Applying ID remapping...")
    remapped_count = 0

    # Users: skip those that already exist, import the rest
    users_to_import = []
    users_to_update = []
    for u in preview_users:
        preview_id = u["_id"]
        if preview_id in id_map:
            # User exists in production — update their data instead
            users_to_update.append((id_map[preview_id], u))
        else:
            users_to_import.append(u)

    # Orders: remap userId
    orders_to_import = []
    for o in preview_orders:
        remapped = remap_user_id(o, id_map, ["userId"])
        if remapped["userId"] != o["userId"]:
            remapped_count += 1
        orders_to_import.append(remapped)

    # Ledger: remap userId and referredUserId
    ledger_to_import = []
    for e in preview_ledger:
        remapped = remap_user_id(e, id_map, ["userId", "referredUserId"])
        if remapped["userId"] != e["userId"]:
            remapped_count += 1
        ledger_to_import.append(remapped)

    # Rewards: remap userId
    rewards_to_import = []
    for r in preview_rewards:
        remapped = remap_user_id(r, id_map, ["userId"])
        rewards_to_import.append(remapped)

    # Also remap referredBy on user docs (may contain ObjectId strings)
    for u in users_to_import:
        if u.get("referredBy") and u["referredBy"] in id_map:
            u["referredBy"] = id_map[u["referredBy"]]

    print(f"  Remapped {remapped_count} userId references")
    print(f"  Users to import: {len(users_to_import)}")
    print(f"  Users to update: {len(users_to_update)}")
    print(f"  Orders to import: {len(orders_to_import)}")
    print(f"  Ledger to import: {len(ledger_to_import)}")
    print(f"  Rewards to import: {len(rewards_to_import)}")

    # ---- Step 5: Import to production ----
    print("\n[5/6] Importing to production...")

    # 5a: Import new users
    ins, skip, errs = import_to_prod(prod_token, "users", users_to_import)
    print(f"  users:          +{ins} inserted, {skip} skipped, {len(errs)} errors")
    for e in errs:
        print(f"    ERROR: {e}")

    # 5b: Update existing users
    for prod_id, user_data in users_to_update:
        update_fields = {
            "loyaltyPoints": user_data.get("loyaltyPoints", 0),
            "firstName": user_data.get("firstName"),
            "lastName": user_data.get("lastName"),
            "phone": user_data.get("phone"),
            "username": user_data.get("username"),
            "profilePhoto": user_data.get("profilePhoto"),
        }
        # Remove None values
        update_fields = {k: v for k, v in update_fields.items() if v is not None}
        status, resp = update_prod_user(prod_token, prod_id, update_fields)
        print(f"  user UPDATE {user_data['email']}: status={status}")

    # 5c: Import orders
    ins, skip, errs = import_to_prod(prod_token, "orders", orders_to_import)
    print(f"  orders:         +{ins} inserted, {skip} skipped, {len(errs)} errors")
    for e in errs:
        print(f"    ERROR: {e}")

    # 5d: Import ledger
    ins, skip, errs = import_to_prod(prod_token, "cloudz_ledger", ledger_to_import)
    print(f"  cloudz_ledger:  +{ins} inserted, {skip} skipped, {len(errs)} errors")
    for e in errs:
        print(f"    ERROR: {e}")

    # 5e: Import loyalty rewards
    ins, skip, errs = import_to_prod(prod_token, "loyalty_rewards", rewards_to_import)
    print(f"  loyalty_rewards:+{ins} inserted, {skip} skipped, {len(errs)} errors")
    for e in errs:
        print(f"    ERROR: {e}")

    # ---- Step 6: Verify ----
    print("\n[6/6] Verifying production...")

    # Re-login to refresh token
    prod_token = get_prod_token()

    prod_users_resp = requests.get(
        f"{PRODUCTION_URL}/api/admin/users",
        headers={"Authorization": f"Bearer {prod_token}"},
        timeout=30,
    )
    prod_users_after = prod_users_resp.json()
    target_emails_in_prod = [u for u in prod_users_after if u["email"] in TARGET_EMAILS]

    print(f"  Production users total: {len(prod_users_after)}")
    print(f"  Target users in prod:   {len(target_emails_in_prod)}")
    for u in target_emails_in_prod:
        print(f"    {u['email']:42s} pts={u.get('loyaltyPoints',0):>6}  id={u['id']}")

    # Check admin user specifically
    admin_in_prod = next((u for u in prod_users_after if u["email"] == "jkaatz@gmail.com"), None)
    if admin_in_prod:
        # Verify orders attached
        orders_resp = requests.get(
            f"{PRODUCTION_URL}/api/admin/users/{admin_in_prod['id']}/profile",
            headers={"Authorization": f"Bearer {prod_token}"},
            timeout=30,
        )
        profile = orders_resp.json()
        order_count = len(profile.get("orders", []))
        ledger_resp = requests.get(
            f"{PRODUCTION_URL}/api/admin/users/{admin_in_prod['id']}/cloudz-ledger",
            headers={"Authorization": f"Bearer {prod_token}"},
            timeout=30,
        )
        ledger_entries = ledger_resp.json()
        print(f"\n  SAMPLE VERIFICATION — {ADMIN_EMAIL}:")
        print(f"    Cloudz balance: {admin_in_prod.get('loyaltyPoints', 0)}")
        print(f"    Orders: {order_count}")
        print(f"    Ledger entries: {len(ledger_entries)}")

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
