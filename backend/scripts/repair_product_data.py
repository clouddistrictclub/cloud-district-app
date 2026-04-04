"""
One-time production data repair script.
Run AFTER deploying the ProductUpdate schema fix (model_config = ConfigDict(extra='allow')).

Usage:
    python3 /app/backend/scripts/repair_product_data.py

Rules:
- Only touches products where model OR productType is null/missing
- Parses model + productType from the product name field
- Never overwrites valid existing data
- Skips safely if parsing fails
"""

import requests

BASE = "https://api.clouddistrict.club"

# --- Inference rules ---
# Ordered: most-specific first
MODEL_RULES = [
    # (substring_in_name,              model_value,              productType)
    ("Nera Fullview 70K POD",          "Nera Fullview 70K POD",  "pod"),
    ("Nera Fullview 70K Kit",          "Nera Fullview 70K Kit",  "kit"),
    ("CLR 50K",                        "CLR 50K",                "disposable"),
    ("CLIO Platinum 50K",              "CLIO Platinum 50K",      "pod"),
    ("VUE 50K",                        "VUE 50K",                "pod"),
    ("RIA NV30K",                      "RIA NV30K",              "disposable"),
    ("Pulse 15000",                    "Pulse 15000",            "disposable"),
    ("Pulse X 25K",                    "Pulse X 25K",            "disposable"),
    ("Pulse X",                        "Pulse X 25K",            "disposable"),
    ("Pulse",                          "Pulse",                  "disposable"),
    ("MT35000",                        "MT35000 Turbo",          "disposable"),
    ("Meloso Mini",                    "Meloso Mini",            "pod"),
    ("Meloso Max",                     "Meloso Max",             "pod"),
    ("Meloso",                         "Meloso",                 "pod"),
    ("CA6000",                         "CA6000",                 "disposable"),
    ("RX50K",                          "RX50K",                  "disposable"),
    ("TN9000",                         "TN9000",                 "disposable"),
    ("RYL 35K",                        "RYL 35K",                "disposable"),
    ("Nera Fullview 70K",              "Nera Fullview 70K POD",  "pod"),  # fallback
]


def infer_model_and_type(name: str) -> tuple:
    """Returns (model, productType) or (None, None) if no match."""
    name_lower = name.lower()
    for substring, model_val, prod_type in MODEL_RULES:
        if substring.lower() in name_lower:
            return model_val, prod_type
    # Last resort: extract from "X - flavor" pattern
    if " - " in name:
        inferred_model = name.split(" - ")[0].strip()
        if inferred_model:
            return inferred_model, "disposable"
    return None, None


def main():
    print("=== PRODUCT DATA REPAIR ===")
    print(f"Target: {BASE}")
    print()

    # Login
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"identifier": "jkaatz@gmail.com", "password": "Just1n23$"})
    token = r.json().get("access_token")
    if not token:
        print(f"LOGIN FAILED: {r.text}")
        return
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Login OK")

    # Get all products
    prods = requests.get(f"{BASE}/api/products").json()
    prods = prods if isinstance(prods, list) else prods.get("products", [])
    print(f"Total products: {len(prods)}")

    # Find ones that need repair
    to_repair = [
        p for p in prods
        if not p.get("model") or not p.get("productType")
    ]
    print(f"Need repair (null model or productType): {len(to_repair)}")
    print()

    updated = 0
    skipped_no_match = 0
    skipped_valid = 0
    samples = []

    for p in to_repair:
        pid   = p["id"]
        name  = (p.get("name") or "").strip()
        cur_model = p.get("model")
        cur_type  = p.get("productType")

        # Infer from name
        inferred_model, inferred_type = infer_model_and_type(name)

        if not inferred_model and not inferred_type:
            skipped_no_match += 1
            print(f"  SKIP (no match): '{name}'")
            continue

        patch_body = {}
        # Only set fields that are currently null
        if not cur_model and inferred_model:
            patch_body["model"] = inferred_model
        if not cur_type and inferred_type:
            patch_body["productType"] = inferred_type

        if not patch_body:
            skipped_valid += 1
            continue

        # Need at least one valid API field to avoid "No fields to update" error
        # model and productType are in updated schema — they will be saved
        resp = requests.patch(f"{BASE}/api/products/{pid}",
                              json=patch_body, headers=headers)

        if resp.status_code == 200:
            result = resp.json()
            updated += 1
            if len(samples) < 5:
                samples.append({
                    "name": name,
                    "model": result.get("model"),
                    "productType": result.get("productType"),
                    "brand": result.get("brandName"),
                })
        else:
            print(f"  PATCH FAILED {resp.status_code}: {name} | {resp.text[:120]}")

    print(f"\n=== RESULTS ===")
    print(f"  Updated:               {updated}")
    print(f"  Skipped (no name match): {skipped_no_match}")
    print(f"  Skipped (already valid): {skipped_valid}")

    print(f"\n=== SAMPLE (5 corrected) ===")
    for s in samples:
        print(f"  [{s['brand']}] {s['name']}")
        print(f"    model={s['model']} | productType={s['productType']}")

    # Final verification
    prods2 = requests.get(f"{BASE}/api/products").json()
    prods2 = prods2 if isinstance(prods2, list) else prods2.get("products", [])
    still_null_model = [p for p in prods2 if not p.get("model")]
    still_null_type  = [p for p in prods2 if not p.get("productType")]

    print(f"\n=== VERIFICATION ===")
    print(f"  Products still with null model:       {len(still_null_model)}")
    print(f"  Products still with null productType: {len(still_null_type)}")
    print()
    if not still_null_model and not still_null_type:
        print("PRODUCT DATA REPAIRED SAFELY")
    else:
        print("⚠️  Some products still need attention:")
        for p in (still_null_model + still_null_type)[:5]:
            print(f"  {p.get('brandName','')} | model={p.get('model')} | type={p.get('productType')} | name={p.get('name','')[:40]}")


if __name__ == "__main__":
    main()
