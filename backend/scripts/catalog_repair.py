"""
Cloud District Club – Comprehensive Product Catalog Repair + Creation Script
Runs against the LOCAL MongoDB instance (preview environment).

WHAT THIS DOES:
 PART 1  – Fix 43 products with empty/null images
 PART 2  – Replace ALL CLIO Platinum 50K images (Kit ≠ Pod)
 PART 3  – Replace ALL CLR 50K images (currently all blank)
 PART 4  – Create 23 new products (skip exact duplicates)
 PART 5  – Normalize: existing Nera Fullview / VUE 50K / MT35000 local-upload
           products are upgraded to absolute HTTPS CDN URLs
 PART 6  – product_routes.py fallback is handled separately
"""

import asyncio
import sys
import os
import re
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME   = os.environ.get("DB_NAME", "clouddistrict")

# ─── VERIFIED CDN IMAGE URLS ─────────────────────────────────────────────────
# All tested; these are the master image URLs to use in the DB
IMG = {
    # Geek Bar CLR 50K  (same device image for all flavors)
    "CLR_50K":
        "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2822/10234/CLR_Web_Square-800x800__51088.1772656543.jpg?c=2",

    # Geek Bar CLIO Platinum 50K – KIT (full device)
    "CLIO_KIT":
        "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2810/10178/Geek-Bar-Clio-Kit_MAIN-800x800__78643.1770672975.jpg?c=2",

    # Geek Bar CLIO Platinum 50K – POD (pod cartridge only)
    "CLIO_POD":
        "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2816/10206/Clio_Platinum_PODS_WEB_SQUARE-800x800__08807.1771442773.jpg?c=2",

    # RAZ VUE 50K – KIT (full kit box)
    "VUE_KIT":
        "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2807/10165/RAZ-VUE-50K-Full-Kit_00-800x800__68447.1769025029.jpg?c=2",

    # RAZ VUE 50K – POD (pods square)
    "VUE_POD":
        "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2808/10169/VUE_Pods_Web_Square-800x800__45772.1769025312.jpg?c=2",

    # Lost Mary Nera Fullview 70K – POD
    "NERA_FV_POD":
        "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2768/10013/___77235.1760038255.png?c=2",

    # Lost Mary Nera Fullview 70K – KIT
    "NERA_FV_KIT":
        "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2767/10010/___71173.1760037985.png?c=2",

    # Lost Mary MT35000 Turbo (same for all flavors)
    "MT35000":
        "https://d31ixytk8zua6i.cloudfront.net/products/mt35000/p3_product_2x.png",

    # Geek Bar Pulse 15000
    "PULSE_15K":
        "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2490/8990/geek-bar-geek-bar-pulse-15000__33880.1717506396.jpg?c=2",

    # Geek Bar RIA NV30K – Blue Razz Ice (flavor-specific from manufacturer)
    "RIA_NV30K":
        "https://nexussmoke.com/wp-content/uploads/2025/05/Blue_Razz_Ice_1026ad81-7e67-4d83-b8ad-77498b350d37.png",
}

# Fallback image (used in product_routes.py separately)
FALLBACK_IMG = "https://clouddistrict.club/placeholder.png"


# ─── URL VERIFICATION ────────────────────────────────────────────────────────
def verify_url(url: str) -> bool:
    """Return True if the URL responds with HTTP 2xx or 3xx."""
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "CDCBot/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status < 400
    except Exception:
        # Try GET as fallback (some CDNs reject HEAD)
        try:
            req2 = urllib.request.Request(url,
                                          headers={"User-Agent": "CDCBot/1.0"})
            with urllib.request.urlopen(req2, timeout=8) as resp2:
                return resp2.status < 400
        except Exception:
            return False


def verify_all_images():
    print("\n=== Verifying CDN image URLs ===")
    bad = []
    for key, url in IMG.items():
        ok = verify_url(url)
        status = "OK  ✓" if ok else "FAIL ✗"
        print(f"  [{status}] {key}: {url[:90]}")
        if not ok:
            bad.append(key)
    if bad:
        print(f"\n  WARN: {len(bad)} URLs failed verification: {bad}")
        print("  These will NOT be written to DB.\n")
    else:
        print("  All URLs verified.\n")
    return bad


# ─── SLUG GENERATOR ──────────────────────────────────────────────────────────
def make_slug(brand: str, model: str, flavor: str) -> str:
    raw = f"{brand}-{model}-{flavor}"
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return slug[:100]


# ─── MAIN ────────────────────────────────────────────────────────────────────
async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    print(f"Connected to DB: {DB_NAME}\n")

    # ── Verify URLs first ────────────────────────────────────────────────────
    bad_keys = verify_all_images()
    verified_img = {k: v for k, v in IMG.items() if k not in bad_keys}

    # ── Fetch brand IDs ──────────────────────────────────────────────────────
    brands = await db.brands.find({}).to_list(50)
    brand_map = {b["name"]: str(b["_id"]) for b in brands}
    print("Brand IDs:", brand_map)

    geek_bar_id = brand_map.get("Geek Bar")
    lost_mary_id = brand_map.get("Lost Mary")
    raz_id = brand_map.get("RAZ")

    counters = {"fixed_image": 0, "updated_stock": 0, "created": 0, "skipped": 0, "failed_image": 0}

    # ═══════════════════════════════════════════════════════════════════════
    # PART 2 – Replace ALL CLIO Platinum 50K images (Kit vs Pod)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n=== PART 2: CLIO Platinum 50K – Kit vs Pod image fix ===")
    if "CLIO_KIT" in verified_img and "CLIO_POD" in verified_img:
        clio_products = await db.products.find(
            {"brandName": "Geek Bar", "model": "CLIO Platinum 50K"}
        ).to_list(50)
        for p in clio_products:
            pid = p["_id"]
            pt = p.get("productType", "")
            new_img = verified_img["CLIO_KIT"] if pt == "kit" else verified_img["CLIO_POD"]
            await db.products.update_one({"_id": pid}, {"$set": {"image": new_img}})
            print(f"  [{pt.upper()}] {p.get('name')} → updated")
            counters["fixed_image"] += 1
    else:
        print("  SKIPPED – CLIO image URLs failed verification")

    # ═══════════════════════════════════════════════════════════════════════
    # PART 3 – CLR 50K: fix all (currently all blank)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n=== PART 3: CLR 50K image fix ===")
    if "CLR_50K" in verified_img:
        clr = await db.products.find(
            {"brandName": "Geek Bar", "model": "CLR 50K"}
        ).to_list(20)
        for p in clr:
            await db.products.update_one(
                {"_id": p["_id"]}, {"$set": {"image": verified_img["CLR_50K"]}}
            )
            print(f"  {p.get('name')} → CLR_50K image set")
            counters["fixed_image"] += 1
    else:
        print("  SKIPPED – CLR_50K URL failed verification")

    # ═══════════════════════════════════════════════════════════════════════
    # PART 1 + 5 – Fix remaining empty images + normalize Nera Fullview /
    #              VUE 50K / MT35000 from local uploads → CDN
    # ═══════════════════════════════════════════════════════════════════════
    print("\n=== PART 1+5: Fix remaining empty images & normalize ===")

    # Model → image key mapping
    MODEL_IMG_MAP = {
        # (brandName, model, productType) → IMG key
        ("Geek Bar", "Meloso Mini",      None):        None,   # use same-model fallback
        ("Geek Bar", "Pulse",            None):        None,
        ("Geek Bar", "Pulse X",          None):        None,
        ("RAZ",      "CA6000",           None):        None,
        ("RAZ",      "TN9000",           None):        None,
        ("RAZ",      "RYL 35K",          None):        None,
        ("Lost Mary","MT35000 Turbo",    None):        "MT35000",
        ("RAZ",      "VUE 50K",          "kit"):       "VUE_KIT",
        ("RAZ",      "VUE 50K",          "pod"):       "VUE_POD",
        ("Lost Mary","Nera 70K",         "pod"):       "NERA_FV_POD",
        ("Lost Mary","Nera 70K",         "kit"):       "NERA_FV_KIT",
    }

    # For models where we use a same-model fallback, find an existing image
    same_model_fallback = {}
    for (brand, model, pt), key in MODEL_IMG_MAP.items():
        if key is None:
            query = {"brandName": brand, "model": model, "image": {"$nin": ["", None]}}
            if pt:
                query["productType"] = pt
            sample = await db.products.find_one(query)
            if sample:
                same_model_fallback[(brand, model, pt)] = sample["image"]
                print(f"  Fallback for ({brand},{model},{pt}): {sample['image'][:70]}")

    all_products = await db.products.find({}).to_list(500)
    for p in all_products:
        img = p.get("image", "")
        if img:
            # Also normalize: if local upload path → skip (handled differently)
            continue  # has image, skip for now

        # Product has empty image
        brand = p.get("brandName", "")
        model = p.get("model", "")
        pt    = p.get("productType")
        name  = p.get("name", "")

        # Skip CLIO (handled in PART 2) and CLR (handled in PART 3)
        if model in ("CLIO Platinum 50K", "CLR 50K"):
            continue

        # Determine best image
        new_img = None

        # Try exact match
        key_exact = (brand, model, pt)
        key_notype = (brand, model, None)
        img_key = MODEL_IMG_MAP.get(key_exact) or MODEL_IMG_MAP.get(key_notype)

        if img_key and img_key in verified_img:
            new_img = verified_img[img_key]
        elif key_exact in same_model_fallback:
            new_img = same_model_fallback[key_exact]
        elif key_notype in same_model_fallback:
            new_img = same_model_fallback[key_notype]

        if new_img:
            await db.products.update_one(
                {"_id": p["_id"]}, {"$set": {"image": new_img}}
            )
            print(f"  FIXED [{brand}] {name} → {new_img[:70]}")
            counters["fixed_image"] += 1
        else:
            print(f"  WARN: no image found for {name}")
            counters["failed_image"] += 1

    # ═══════════════════════════════════════════════════════════════════════
    # NORMALIZE: Upgrade Nera Fullview / VUE / MT35000 local upload → CDN
    # ═══════════════════════════════════════════════════════════════════════
    print("\n=== PART 5: Normalize local-upload → CDN for known models ===")
    normalize_rules = [
        # (brandName, model, productType) → IMG key
        ("Lost Mary", "Nera 70K", "pod",  "NERA_FV_POD"),
        ("Lost Mary", "Nera 70K", "kit",  "NERA_FV_KIT"),
        ("Lost Mary", "MT35000 Turbo", None, "MT35000"),
        ("RAZ",       "VUE 50K", "kit",   "VUE_KIT"),
        ("RAZ",       "VUE 50K", "pod",   "VUE_POD"),
    ]
    for rule in normalize_rules:
        if len(rule) == 4:
            brand, model, pt, img_key = rule
        else:
            continue
        if img_key not in verified_img:
            print(f"  SKIPPED (unverified) {brand} {model} {pt}")
            continue
        q = {"brandName": brand, "model": model}
        if pt:
            q["productType"] = pt
        prods = await db.products.find(q).to_list(50)
        cdn_url = verified_img[img_key]
        for p in prods:
            cur = p.get("image", "")
            if cur.startswith("/api/uploads/") or cur == "":
                await db.products.update_one({"_id": p["_id"]}, {"$set": {"image": cdn_url}})
                print(f"  NORMALIZED [{brand}] {p.get('name')} → CDN")
                counters["fixed_image"] += 1

    # ═══════════════════════════════════════════════════════════════════════
    # PART 4 – Create / update new products
    # ═══════════════════════════════════════════════════════════════════════
    print("\n=== PART 4: Create new products ===")

    now = datetime.utcnow()

    # Helper: check duplicate by brandId + model + flavor + productType
    async def exists(brand_id, model, flavor, product_type):
        doc = await db.products.find_one({
            "brandId": brand_id,
            "model": model,
            "flavor": flavor,
            "productType": product_type,
        })
        return doc

    # Helper: create product
    async def create_or_update(brand_id, brand_name, model, flavor,
                                product_type, puff_count, nicotine_pct,
                                price, stock, description, image,
                                category="all", is_active=True, is_featured=False):
        existing = await exists(brand_id, model, flavor, product_type)
        if existing:
            # Update missing fields (image, stock, description)
            updates = {}
            if not existing.get("image"):
                updates["image"] = image
            # Always update stock if product exists (add to existing stock)
            # Per user: "DO NOT duplicate – Instead update missing fields"
            if updates:
                await db.products.update_one({"_id": existing["_id"]}, {"$set": updates})
                print(f"  UPDATED [{brand_name}] {model} – {flavor} ({product_type})")
                counters["fixed_image"] += 1
            else:
                # Update stock to provided value
                await db.products.update_one({"_id": existing["_id"]}, {"$set": {"stock": stock}})
                print(f"  STOCK_UPDATE [{brand_name}] {model} – {flavor} → stock={stock}")
                counters["updated_stock"] += 1
            return

        name = f"{model} - {flavor}"
        slug = make_slug(brand_name, model, flavor)
        doc = {
            "brandId":         brand_id,
            "brandName":       brand_name,
            "model":           model,
            "flavor":          flavor,
            "name":            name,
            "slug":            slug,
            "productType":     product_type,
            "puffCount":       puff_count,
            "nicotinePercent": nicotine_pct,
            "nicotineStrength": f"{int(nicotine_pct * 10)}mg",
            "price":           price,
            "stock":           stock,
            "image":           image,
            "images":          [],
            "category":        category,
            "isActive":        is_active,
            "isFeatured":      is_featured,
            "displayOrder":    0,
            "lowStockThreshold": 5,
            "description":     description,
            "createdAt":       now,
        }
        result = await db.products.insert_one(doc)
        print(f"  CREATED [{brand_name}] {name} (id={result.inserted_id})")
        counters["created"] += 1

    # ─── NEW PRODUCT LIST ────────────────────────────────────────────────
    # 1) Lost Mary Nera Fullview 70K POD – Scary Berry
    await create_or_update(
        lost_mary_id, "Lost Mary", "Nera 70K", "Scary Berry", "pod",
        70000, 5.0, 20.0, 1,
        "Lost Mary Nera Fullview 70K POD – ~70,000 puffs | 5% (50mg) | 800mAh USB-C | Dual modes",
        verified_img.get("NERA_FV_POD", FALLBACK_IMG)
    )

    # 2) Geek Bar CLR 50K – Amazon Lemonade  (exists, update stock/image)
    await create_or_update(
        geek_bar_id, "Geek Bar", "CLR 50K", "Amazon Lemonade", "disposable",
        50000, 5.0, 30.0, 2,
        "Geek Bar CLR 50K – ~50,000 puffs (Regular) | 5% (50mg) | 900mAh USB-C | VPU technology",
        verified_img.get("CLR_50K", FALLBACK_IMG)
    )

    # 3) Geek Bar CLR 50K – Blue Razz Ice  (NEW)
    await create_or_update(
        geek_bar_id, "Geek Bar", "CLR 50K", "Blue Razz Ice", "disposable",
        50000, 5.0, 30.0, 3,
        "Geek Bar CLR 50K – ~50,000 puffs (Regular) | 5% (50mg) | 900mAh USB-C | VPU technology",
        verified_img.get("CLR_50K", FALLBACK_IMG)
    )

    # 4) Geek Bar CLR 50K – Sour Strawberry  (NEW)
    await create_or_update(
        geek_bar_id, "Geek Bar", "CLR 50K", "Sour Strawberry", "disposable",
        50000, 5.0, 30.0, 2,
        "Geek Bar CLR 50K – ~50,000 puffs (Regular) | 5% (50mg) | 900mAh USB-C | VPU technology",
        verified_img.get("CLR_50K", FALLBACK_IMG)
    )

    # 5) Geek Bar CLR 50K – Sour Apple Ice  (NEW)
    await create_or_update(
        geek_bar_id, "Geek Bar", "CLR 50K", "Sour Apple Ice", "disposable",
        50000, 5.0, 30.0, 2,
        "Geek Bar CLR 50K – ~50,000 puffs (Regular) | 5% (50mg) | 900mAh USB-C | VPU technology",
        verified_img.get("CLR_50K", FALLBACK_IMG)
    )

    # 6) Geek Bar CLIO Platinum 50K POD – Dragonfruit Lemonade  (exists)
    await create_or_update(
        geek_bar_id, "Geek Bar", "CLIO Platinum 50K", "Dragonfruit Lemonade", "pod",
        50000, 5.0, 25.0, 3,
        "Geek Bar CLIO Platinum 50K POD – ~50,000 puffs | 5% (50mg) | 500mAh Pod battery | Transparent e-liquid pod",
        verified_img.get("CLIO_POD", FALLBACK_IMG)
    )

    # 7) Geek Bar CLIO Platinum 50K POD – Blue Razz Ice  (exists, missing image)
    await create_or_update(
        geek_bar_id, "Geek Bar", "CLIO Platinum 50K", "Blue Razz Ice", "pod",
        50000, 5.0, 25.0, 2,
        "Geek Bar CLIO Platinum 50K POD – ~50,000 puffs | 5% (50mg) | 500mAh Pod battery | Transparent e-liquid pod",
        verified_img.get("CLIO_POD", FALLBACK_IMG)
    )

    # 8) RAZ VUE 50K Kit – Hawaiian Punch  (exists, missing image)
    await create_or_update(
        raz_id, "RAZ", "VUE 50K", "Hawaiian Punch", "kit",
        50000, 5.0, 30.0, 2,
        "RAZ VUE 50K Full Kit – ~50,000 puffs | 5% (50mg) | Normal & Boost modes | USB-C charging",
        verified_img.get("VUE_KIT", FALLBACK_IMG)
    )

    # 9) RAZ VUE 50K Kit – Blue Razz Ice  (exists, missing image)
    await create_or_update(
        raz_id, "RAZ", "VUE 50K", "Blue Razz Ice", "kit",
        50000, 5.0, 30.0, 2,
        "RAZ VUE 50K Full Kit – ~50,000 puffs | 5% (50mg) | Normal & Boost modes | USB-C charging",
        verified_img.get("VUE_KIT", FALLBACK_IMG)
    )

    # 10) Lost Mary Nera Fullview 70K POD – Blue Razz Ice  (NEW)
    await create_or_update(
        lost_mary_id, "Lost Mary", "Nera 70K", "Blue Razz Ice", "pod",
        70000, 5.0, 25.0, 1,
        "Lost Mary Nera Fullview 70K POD – ~70,000 puffs | 5% (50mg) | 800mAh USB-C | Dual modes",
        verified_img.get("NERA_FV_POD", FALLBACK_IMG)
    )

    # 11) Lost Mary Nera Fullview 70K POD – Golden Berry  (NEW)
    await create_or_update(
        lost_mary_id, "Lost Mary", "Nera 70K", "Golden Berry", "pod",
        70000, 5.0, 25.0, 1,
        "Lost Mary Nera Fullview 70K POD – ~70,000 puffs | 5% (50mg) | 800mAh USB-C | Dual modes",
        verified_img.get("NERA_FV_POD", FALLBACK_IMG)
    )

    # 12) Lost Mary Nera Fullview 70K POD – Pink Lemonade  (NEW)
    await create_or_update(
        lost_mary_id, "Lost Mary", "Nera 70K", "Pink Lemonade", "pod",
        70000, 5.0, 25.0, 2,
        "Lost Mary Nera Fullview 70K POD – ~70,000 puffs | 5% (50mg) | 800mAh USB-C | Dual modes",
        verified_img.get("NERA_FV_POD", FALLBACK_IMG)
    )

    # 13) Geek Bar Pulse 15000 – Peach Lemonade (Thermal Edition)  (NEW)
    await create_or_update(
        geek_bar_id, "Geek Bar", "Pulse", "Peach Lemonade (Thermal Edition)", "disposable",
        15000, 5.0, 25.0, 2,
        "Geek Bar Pulse 15000 – ~15,000 puffs (Regular) | 5% (50mg) | 650mAh USB-C | Dual-core heating | Display screen",
        verified_img.get("PULSE_15K", FALLBACK_IMG)
    )

    # 14) Lost Mary Nera Fullview 70K POD – Rocket Freeze  (NEW – Fullview variant)
    await create_or_update(
        lost_mary_id, "Lost Mary", "Nera 70K", "Rocket Freeze", "pod",
        70000, 5.0, 25.0, 3,
        "Lost Mary Nera Fullview 70K POD – ~70,000 puffs | 5% (50mg) | 800mAh USB-C | Dual modes",
        verified_img.get("NERA_FV_POD", FALLBACK_IMG)
    )

    # 15) Lost Mary Nera Fullview 70K KIT – Pink Lemonade + Pink & Blue  (NEW)
    await create_or_update(
        lost_mary_id, "Lost Mary", "Nera 70K", "Pink Lemonade + Pink & Blue", "kit",
        70000, 5.0, 30.0, 1,
        "Lost Mary Nera Fullview 70K KIT – Device + 2 pods | ~70,000 puffs | 5% (50mg) | 800mAh USB-C | Normal & Turbo modes",
        verified_img.get("NERA_FV_KIT", FALLBACK_IMG)
    )

    # 16) Lost Mary Nera Fullview 70K KIT – Scary Berry + Golden Berry  (NEW)
    await create_or_update(
        lost_mary_id, "Lost Mary", "Nera 70K", "Scary Berry + Golden Berry", "kit",
        70000, 5.0, 30.0, 1,
        "Lost Mary Nera Fullview 70K KIT – Device + 2 pods | ~70,000 puffs | 5% (50mg) | 800mAh USB-C | Normal & Turbo modes",
        verified_img.get("NERA_FV_KIT", FALLBACK_IMG)
    )

    # 17) Lost Mary Nera Fullview 70K KIT – Blue Razz Ice  (NEW)
    await create_or_update(
        lost_mary_id, "Lost Mary", "Nera 70K", "Blue Razz Ice", "kit",
        70000, 5.0, 30.0, 1,
        "Lost Mary Nera Fullview 70K KIT – Device + 2 pods | ~70,000 puffs | 5% (50mg) | 800mAh USB-C | Normal & Turbo modes",
        verified_img.get("NERA_FV_KIT", FALLBACK_IMG)
    )

    # 18) RIA NV30K – Blue Razz Ice  (NEW model)
    await create_or_update(
        geek_bar_id, "Geek Bar", "RIA NV30K", "Blue Razz Ice", "disposable",
        30000, 5.0, 30.0, 2,
        "Geek Bar RIA NV30K – ~30,000 puffs (Regular) | 5% (50mg) | 1000mAh USB-C | Dual mesh coil | 3D curved display | Leather grip",
        verified_img.get("RIA_NV30K", FALLBACK_IMG)
    )

    # 19) Geek Bar Pulse 15000 – Strawberry Kiwi (Thermal Edition)  (NEW variant)
    await create_or_update(
        geek_bar_id, "Geek Bar", "Pulse", "Strawberry Kiwi (Thermal Edition)", "disposable",
        15000, 5.0, 25.0, 3,
        "Geek Bar Pulse 15000 – ~15,000 puffs (Regular) | 5% (50mg) | 650mAh USB-C | Dual-core heating | Display screen",
        verified_img.get("PULSE_15K", FALLBACK_IMG)
    )

    # 20) Geek Bar Pulse 15000 – Blueberry Watermelon  (NEW)
    await create_or_update(
        geek_bar_id, "Geek Bar", "Pulse", "Blueberry Watermelon", "disposable",
        15000, 5.0, 25.0, 2,
        "Geek Bar Pulse 15000 – ~15,000 puffs (Regular) | 5% (50mg) | 650mAh USB-C | Dual-core heating | Display screen",
        verified_img.get("PULSE_15K", FALLBACK_IMG)
    )

    # 21) Geek Bar Pulse 15000 – Black Cherry  (EXISTS already - update stock only)
    await create_or_update(
        geek_bar_id, "Geek Bar", "Pulse", "Black Cherry", "disposable",
        15000, 5.0, 25.0, 2,
        "Geek Bar Pulse 15000 – ~15,000 puffs (Regular) | 5% (50mg) | 650mAh USB-C | Dual-core heating | Display screen",
        verified_img.get("PULSE_15K", FALLBACK_IMG)
    )

    # 22) Geek Bar Pulse 15000 – Strawberry Mango  (NEW)
    await create_or_update(
        geek_bar_id, "Geek Bar", "Pulse", "Strawberry Mango", "disposable",
        15000, 5.0, 25.0, 5,
        "Geek Bar Pulse 15000 – ~15,000 puffs (Regular) | 5% (50mg) | 650mAh USB-C | Dual-core heating | Display screen",
        verified_img.get("PULSE_15K", FALLBACK_IMG)
    )

    # 23) Geek Bar Pulse 15000 – Blow Pop / B-Burst (B-Pop)  (NEW)
    await create_or_update(
        geek_bar_id, "Geek Bar", "Pulse", "Blow Pop / B-Burst (B-Pop)", "disposable",
        15000, 5.0, 25.0, 5,
        "Geek Bar Pulse 15000 – ~15,000 puffs (Regular) | 5% (50mg) | 650mAh USB-C | Dual-core heating | Display screen",
        verified_img.get("PULSE_15K", FALLBACK_IMG)
    )

    # ═══════════════════════════════════════════════════════════════════════
    # PART 7 – Final validation pass
    # ═══════════════════════════════════════════════════════════════════════
    print("\n=== PART 7: Final validation ===")
    all_prods = await db.products.find({}).to_list(500)
    total = len(all_prods)
    missing_img = [p for p in all_prods if not p.get("image")]
    empty_img   = [p for p in all_prods if p.get("image") == ""]
    local_upload = [p for p in all_prods if p.get("image","").startswith("/api/uploads/")]

    print(f"  Total products:          {total}")
    print(f"  Missing images (null):   {len(missing_img)}")
    print(f"  Empty string images:     {len(empty_img)}")
    print(f"  Local upload /api/uploads: {len(local_upload)}")
    if empty_img or missing_img:
        print("  STILL MISSING:")
        for p in (empty_img + missing_img):
            print(f"    [{p.get('brandName')}] {p.get('name')}")

    # ─── SUMMARY ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Images fixed/updated:   {counters['fixed_image']}")
    print(f"  Stock updated:          {counters['updated_stock']}")
    print(f"  New products created:   {counters['created']}")
    print(f"  Skipped (no-op):        {counters['skipped']}")
    print(f"  Failed image (no URL):  {counters['failed_image']}")
    print(f"  Still missing images:   {len(empty_img) + len(missing_img)}")
    print("=" * 60)

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
