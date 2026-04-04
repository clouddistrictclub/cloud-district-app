"""
One-time async data repair — called via POST /api/admin/repair-brand-ids.
Ensures every product has a valid brandId that matches the brands collection.

Rules:
- Loads all brands and builds a case-insensitive name → id string map.
- Skips products whose brandId is already valid (idempotent).
- Matches invalid/missing brandId using product.brandName (case-insensitive).
- Falls back to inferring brand from product.name if brandName is missing.
- Never overwrites a valid brandId.
- Never creates duplicate brands.
- Never touches model or productType.
"""

from database import db
from bson import ObjectId

# Fallback: substring in product name → canonical brand name in DB
NAME_FALLBACKS = [
    ("Lost Mary",  "Lost Mary"),
    ("Geek Bar",   "Geek Bar"),
    ("RAZ",        "RAZ"),
    ("Elf Bar",    "Elf Bar"),
    ("Flum",       "Flum"),
]


def _infer_brand_name(product_name: str) -> str | None:
    nl = product_name.lower()
    for substr, brand_name in NAME_FALLBACKS:
        if substr.lower() in nl:
            return brand_name
    return None


async def run_brand_id_repair():
    # ── Step 1: load all brands, build maps ─────────────────────────────────
    all_brands = await db.brands.find({}, {"_id": 1, "name": 1}).to_list(1000)

    # { normalised_name: brand_id_string }
    name_to_id: dict[str, str] = {
        b["name"].strip().lower(): str(b["_id"]) for b in all_brands
    }
    # set of valid brand id strings for O(1) lookup
    valid_ids: set[str] = set(name_to_id.values())

    # ── Step 2: find products with missing / invalid brandId ─────────────────
    all_products = await db.products.find(
        {},
        {"_id": 1, "name": 1, "brandName": 1, "brandId": 1}
    ).to_list(5000)

    updated = 0
    skipped_no_match = 0
    samples: list[dict] = []

    for p in all_products:
        current_brand_id = p.get("brandId") or ""

        # Already valid — skip
        if current_brand_id and current_brand_id in valid_ids:
            continue

        product_name  = (p.get("name")      or "").strip()
        brand_name_raw = (p.get("brandName") or "").strip()

        # Try to resolve via brandName first
        resolved_id   = name_to_id.get(brand_name_raw.lower()) if brand_name_raw else None
        resolved_name = brand_name_raw if resolved_id else None

        # Fallback: infer brand from product name
        if not resolved_id and product_name:
            inferred = _infer_brand_name(product_name)
            if inferred:
                resolved_id   = name_to_id.get(inferred.lower())
                resolved_name = inferred if resolved_id else None

        if not resolved_id:
            skipped_no_match += 1
            continue

        patch: dict = {"brandId": resolved_id}
        # Also fix brandName if it was missing or mismatched
        if not brand_name_raw or brand_name_raw.lower() != resolved_name.lower():
            patch["brandName"] = resolved_name

        await db.products.update_one({"_id": p["_id"]}, {"$set": patch})
        updated += 1

        if len(samples) < 5:
            samples.append({
                "name":          product_name,
                "old_brandId":   current_brand_id or None,
                "new_brandId":   resolved_id,
                "brandName":     resolved_name,
            })

    # ── Step 3: count remaining invalids ────────────────────────────────────
    remaining = 0
    check_products = await db.products.find({}, {"_id": 1, "brandId": 1}).to_list(5000)
    for p in check_products:
        bid = p.get("brandId") or ""
        if not bid or bid not in valid_ids:
            remaining += 1

    status = "BRAND IDs FULLY REPAIRED" if remaining == 0 else f"PARTIAL — {remaining} products still have invalid brandId"

    return {
        "brands_loaded":          len(all_brands),
        "products_scanned":       len(all_products),
        "updated":                updated,
        "skipped_no_match":       skipped_no_match,
        "remaining_invalid":      remaining,
        "sample":                 samples,
        "status":                 status,
    }
