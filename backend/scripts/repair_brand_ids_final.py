"""
One-time targeted repair — called via POST /api/admin/repair-brand-ids-final.
Ensures VIHO, Maskking, ExtreBar brands exist, then patches exactly 12 products.
Does NOT touch any other products or fields.
Idempotent — safe to run multiple times.
"""

from database import db
from bson import ObjectId
from datetime import datetime

# Brands to ensure exist (created if missing, reused if present)
REQUIRED_BRANDS = ["VIHO", "Maskking", "ExtreBar"]

# Exact product _id → brand name mapping
PRODUCT_BRAND_MAP = {
    # VIHO
    "69c32910560d53710b4d1259": "VIHO",
    "69c32910560d53710b4d125a": "VIHO",
    "69c32910560d53710b4d125b": "VIHO",
    "69c32910560d53710b4d125c": "VIHO",
    "69c32910560d53710b4d125e": "VIHO",
    # Maskking
    "69c32910560d53710b4d1271": "Maskking",
    "69c32910560d53710b4d1272": "Maskking",
    "69c32910560d53710b4d1273": "Maskking",
    # ExtreBar
    "69c32910560d53710b4d1274": "ExtreBar",
    "69c32910560d53710b4d1275": "ExtreBar",
    "69c32910560d53710b4d1276": "ExtreBar",
    "69c32910560d53710b4d1277": "ExtreBar",
}


async def run_final_brand_repair():
    # ── Step 1 & 2: ensure brands exist, build name → id map ────────────────
    brand_id_map: dict[str, str] = {}

    for brand_name in REQUIRED_BRANDS:
        existing = await db.brands.find_one(
            {"name": {"$regex": f"^{brand_name}$", "$options": "i"}},
            {"_id": 1, "name": 1}
        )
        if existing:
            brand_id_map[brand_name] = str(existing["_id"])
        else:
            result = await db.brands.insert_one({
                "name":      brand_name,
                "isActive":  True,
                "createdAt": datetime.utcnow(),
            })
            brand_id_map[brand_name] = str(result.inserted_id)

    # ── Step 3: update exactly 12 products ──────────────────────────────────
    updated = 0
    skipped_already_valid = 0
    errors: list[str] = []

    for product_id_str, brand_name in PRODUCT_BRAND_MAP.items():
        correct_brand_id = brand_id_map[brand_name]
        try:
            oid = ObjectId(product_id_str)
        except Exception:
            errors.append(f"Invalid ObjectId: {product_id_str}")
            continue

        product = await db.products.find_one({"_id": oid}, {"_id": 1, "brandId": 1})
        if not product:
            errors.append(f"Product not found: {product_id_str}")
            continue

        if product.get("brandId") == correct_brand_id:
            skipped_already_valid += 1
            continue

        await db.products.update_one(
            {"_id": oid},
            {"$set": {"brandId": correct_brand_id, "brandName": brand_name}}
        )
        updated += 1

    # ── Step 4: verify ───────────────────────────────────────────────────────
    all_valid_ids: set[str] = set()
    all_brands = await db.brands.find({}, {"_id": 1}).to_list(1000)
    all_valid_ids = {str(b["_id"]) for b in all_brands}

    remaining_invalid = 0
    all_products = await db.products.find({}, {"_id": 1, "brandId": 1}).to_list(5000)
    for p in all_products:
        bid = (p.get("brandId") or "").strip()
        if not bid or bid not in all_valid_ids:
            remaining_invalid += 1

    status = "FINAL BRAND REPAIR COMPLETE" if remaining_invalid == 0 else f"PARTIAL — {remaining_invalid} products still invalid"

    return {
        "brands_ensured":         brand_id_map,
        "updated":                updated,
        "skipped_already_valid":  skipped_already_valid,
        "errors":                 errors,
        "remaining_invalid":      remaining_invalid,
        "status":                 status,
    }
