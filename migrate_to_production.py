#!/usr/bin/env python3
"""
Cloud District Club — One-Time Data Migration Script
=====================================================
Exports all data from the PREVIEW backend and imports it into PRODUCTION.
- Preserves all _id values
- Skips duplicates by _id (and by email for users)
- Does NOT trigger any business logic
- Safe to re-run (idempotent)
"""

import json
import sys
import requests
from datetime import datetime

PREVIEW_URL = "https://cloudz-loyalty-hub.preview.emergentagent.com"
PRODUCTION_URL = "https://api.clouddistrict.club"
ADMIN_EMAIL = "jkaatz@gmail.com"
ADMIN_PASSWORD = "Just1n23$"

COLLECTIONS = [
    "brands",
    "products",
    "users",
    "orders",
    "cloudz_ledger",
    "loyalty_rewards",
    "reviews",
    "chat_messages",
    "chat_sessions",
    "push_tokens",
    "support_tickets",
    "inventory_logs",
    "leaderboard_snapshots",
]

# Max documents per import request (to avoid payload size limits)
CHUNK_SIZE = 50


def get_admin_token(base_url):
    """Login as admin and return the JWT token."""
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "access_token" not in data:
        print(f"  ERROR: Login failed at {base_url}: {data}")
        sys.exit(1)
    return data["access_token"]


def export_collection(base_url, token, collection_name):
    """Export all documents from a collection via the export endpoint."""
    resp = requests.get(
        f"{base_url}/api/admin/migrate/export/{collection_name}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("documents", [])


def import_collection(base_url, token, collection_name, documents):
    """Import documents into a collection via the import endpoint, in chunks."""
    total_inserted = 0
    total_skipped = 0
    total_errors = []

    for i in range(0, len(documents), CHUNK_SIZE):
        chunk = documents[i:i + CHUNK_SIZE]
        resp = requests.post(
            f"{base_url}/api/admin/migrate/import",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"collection": collection_name, "documents": chunk},
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()
        total_inserted += result.get("inserted", 0)
        total_skipped += result.get("skipped", 0)
        total_errors.extend(result.get("errors", []))

    return total_inserted, total_skipped, total_errors


def main():
    print("=" * 60)
    print("Cloud District Club — Data Migration")
    print(f"Source:  {PREVIEW_URL}")
    print(f"Target:  {PRODUCTION_URL}")
    print(f"Started: {datetime.utcnow().isoformat()}Z")
    print("=" * 60)

    # Step 1: Get admin tokens
    print("\n[1/4] Authenticating...")
    preview_token = get_admin_token(PREVIEW_URL)
    print(f"  Preview:    OK")
    production_token = get_admin_token(PRODUCTION_URL)
    print(f"  Production: OK")

    # Step 2: Export all collections from preview
    print("\n[2/4] Exporting from preview...")
    all_data = {}
    for coll in COLLECTIONS:
        docs = export_collection(PREVIEW_URL, preview_token, coll)
        all_data[coll] = docs
        print(f"  {coll:30s} {len(docs):>6} docs exported")

    total_exported = sum(len(v) for v in all_data.values())
    print(f"  {'TOTAL':30s} {total_exported:>6} docs")

    # Step 3: Save export to file (backup)
    backup_path = "/app/migration_export.json"
    with open(backup_path, "w") as f:
        json.dump(all_data, f, default=str)
    print(f"\n  Backup saved to {backup_path}")

    # Step 4: Import to production
    print("\n[3/4] Importing to production...")
    migration_report = []
    for coll in COLLECTIONS:
        docs = all_data[coll]
        if not docs:
            print(f"  {coll:30s}   (empty, skipped)")
            migration_report.append({
                "collection": coll, "exported": 0,
                "inserted": 0, "skipped": 0, "errors": [],
            })
            continue

        inserted, skipped, errors = import_collection(
            PRODUCTION_URL, production_token, coll, docs
        )
        status = "OK" if not errors else f"WARN ({len(errors)} errors)"
        print(f"  {coll:30s} +{inserted:>4} inserted, {skipped:>4} skipped  [{status}]")
        if errors:
            for e in errors[:3]:
                print(f"    ERROR: {e}")

        migration_report.append({
            "collection": coll, "exported": len(docs),
            "inserted": inserted, "skipped": skipped, "errors": errors,
        })

    # Step 5: Verification
    print("\n[4/4] Verifying production counts...")
    for coll in COLLECTIONS:
        prod_docs = export_collection(PRODUCTION_URL, production_token, coll)
        preview_count = len(all_data[coll])
        prod_count = len(prod_docs)
        match = "MATCH" if prod_count >= preview_count else "MISMATCH"
        print(f"  {coll:30s} preview={preview_count:>4}  prod={prod_count:>4}  [{match}]")

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    total_inserted = sum(r["inserted"] for r in migration_report)
    total_skipped = sum(r["skipped"] for r in migration_report)
    total_errors = sum(len(r["errors"]) for r in migration_report)
    print(f"  Total exported:  {total_exported}")
    print(f"  Total inserted:  {total_inserted}")
    print(f"  Total skipped:   {total_skipped}")
    print(f"  Total errors:    {total_errors}")
    print(f"  Finished:        {datetime.utcnow().isoformat()}Z")

    # Save report
    report_path = "/app/migration_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "source": PREVIEW_URL,
            "target": PRODUCTION_URL,
            "timestamp": datetime.utcnow().isoformat(),
            "collections": migration_report,
            "totals": {
                "exported": total_exported,
                "inserted": total_inserted,
                "skipped": total_skipped,
                "errors": total_errors,
            },
        }, f, indent=2, default=str)
    print(f"\n  Full report saved to {report_path}")


if __name__ == "__main__":
    main()
