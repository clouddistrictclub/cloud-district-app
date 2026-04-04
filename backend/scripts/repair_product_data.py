"""
One-time async data repair — called via POST /api/admin/repair-products.
Uses the database directly (no HTTP round-trips).
"""

from database import db

MODEL_RULES = [
    ("Nera Fullview 70K POD", "Nera Fullview 70K POD", "pod"),
    ("Nera Fullview 70K Kit", "Nera Fullview 70K Kit", "kit"),
    ("CLR 50K",               "CLR 50K",               "disposable"),
    ("CLIO Platinum 50K",     "CLIO Platinum 50K",      "pod"),
    ("VUE 50K",               "VUE 50K",                "pod"),
    ("RIA NV30K",             "RIA NV30K",              "disposable"),
    ("Pulse X 25K",           "Pulse X 25K",            "disposable"),
    ("Pulse X",               "Pulse X 25K",            "disposable"),
    ("Pulse 15000",           "Pulse 15000",            "disposable"),
    ("Pulse",                 "Pulse",                  "disposable"),
    ("MT35000",               "MT35000 Turbo",          "disposable"),
    ("Meloso Mini",           "Meloso Mini",            "pod"),
    ("Meloso Max",            "Meloso Max",             "pod"),
    ("Meloso",                "Meloso",                 "pod"),
    ("CA6000",                "CA6000",                 "disposable"),
    ("RX50K",                 "RX50K",                  "disposable"),
    ("TN9000",                "TN9000",                 "disposable"),
    ("RYL 35K",               "RYL 35K",                "disposable"),
    ("Nera Fullview 70K",     "Nera Fullview 70K POD",  "pod"),
]


def _infer(name: str):
    nl = name.lower()
    for substr, model_val, prod_type in MODEL_RULES:
        if substr.lower() in nl:
            return model_val, prod_type
    if " - " in name:
        return name.split(" - ")[0].strip(), "disposable"
    return None, None


async def run_repair():
    to_fix = await db.products.find(
        {"$or": [
            {"model": None}, {"model": ""}, {"model": {"$exists": False}},
            {"productType": None}, {"productType": ""}, {"productType": {"$exists": False}},
        ]},
        {"_id": 1, "name": 1, "brandName": 1, "model": 1, "productType": 1}
    ).to_list(1000)

    updated = 0
    samples = []

    for p in to_fix:
        name = (p.get("name") or "").strip()
        cur_model = p.get("model")
        cur_type  = p.get("productType")

        inferred_model, inferred_type = _infer(name)
        if not inferred_model and not inferred_type:
            continue

        patch = {}
        if not cur_model and inferred_model:
            patch["model"] = inferred_model
        if not cur_type and inferred_type:
            patch["productType"] = inferred_type

        if not patch:
            continue

        await db.products.update_one({"_id": p["_id"]}, {"$set": patch})
        updated += 1

        if len(samples) < 5:
            samples.append({
                "brand":       p.get("brandName", ""),
                "name":        name,
                "model":       patch.get("model", cur_model),
                "productType": patch.get("productType", cur_type),
            })

    remaining_model = await db.products.count_documents(
        {"$or": [{"model": None}, {"model": ""}, {"model": {"$exists": False}}]}
    )
    remaining_type = await db.products.count_documents(
        {"$or": [{"productType": None}, {"productType": ""}, {"productType": {"$exists": False}}]}
    )

    return {
        "updated":                  updated,
        "remaining_null_model":     remaining_model,
        "remaining_null_productType": remaining_type,
        "sample":                   samples,
        "status":                   "PRODUCT DATA REPAIRED SAFELY" if remaining_model == 0 and remaining_type == 0 else "PARTIAL — some products still need review",
    }
