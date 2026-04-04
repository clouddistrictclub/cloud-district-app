"""
READ-ONLY diagnostic — called via GET /api/admin/identify-invalid-brand-ids.
Returns all products with a missing or invalid brandId.
Does NOT modify any data.
"""

from database import db


async def identify_invalid_brand_ids():
    # Load all valid brand ids
    all_brands = await db.brands.find({}, {"_id": 1}).to_list(1000)
    valid_ids: set[str] = {str(b["_id"]) for b in all_brands}

    # Scan every product
    all_products = await db.products.find(
        {},
        {"_id": 1, "name": 1, "brandName": 1, "model": 1, "productType": 1, "brandId": 1}
    ).to_list(5000)

    invalid = []
    for p in all_products:
        bid = (p.get("brandId") or "").strip()
        if not bid or bid not in valid_ids:
            invalid.append({
                "_id":         str(p["_id"]),
                "name":        p.get("name"),
                "brandName":   p.get("brandName"),
                "model":       p.get("model"),
                "productType": p.get("productType"),
                "brandId":     p.get("brandId"),
            })

    return {"count": len(invalid), "products": invalid}
