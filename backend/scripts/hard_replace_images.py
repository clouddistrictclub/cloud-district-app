"""
Hard-replace product images with verified URLs supplied by the owner.
- CLIO Platinum 50K: flavor-specific (same image for Kit + Pod of same flavor)
- CLR 50K:           flavor-specific

Rules:
  * ONLY update existing records (no inserts)
  * Verify every URL returns HTTP 200 before writing
  * Report skipped URLs and products not found in DB
"""

import asyncio
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME   = os.environ.get("DB_NAME", "clouddistrict")

# ── EXACT URLs PROVIDED BY OWNER ─────────────────────────────────────────────

CLIO_IMAGES = {
    "Code Red":             "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-code-red.webp",
    "Cool Mint":            "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-cool-mint.webp",
    "White Peach Raspberry":"https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-white-peach-raspberry.webp",
    "Dragonfruit Lemonade": "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-dragonfruit-lemonade.webp",
    "Fcuking Fab":          "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-fcuking-fab.webp",
    "Peach Slush":          "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-peach-slush.webp",
    "Sour Watermelon Drop": "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-sour-watermelon-drop.webp",
    "Strawberry B-Burst":   "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-strawberry-bburst.webp",
}

CLR_IMAGES = {
    "Sour Apple Ice":   "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Sour-Apple-Ice.jpg",
    "Sour Gush":        "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Sour-Gush.jpg",
    "Sour Strawberry":  "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Sour-Strawberry.jpg",
    "Amazon Lemonade":  "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Amazon-Lemonade.jpg",
    "Banana Ice":       "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Banana-Ice.jpg",
    "Strazz":           "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Strazz.jpg",
    "Triple Berry Ice": "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Triple-Berry-Ice.jpg",
    "Watermelon Ice":   "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Watermelon-Ice.jpg",
    "White Gummy":      "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-White-Gummy.jpg",
    "Blue Rancher":     "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Blue-Rancher.jpg",
    "Blue Razz Ice":    "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Blue-Razz-Ice.jpg",
    "Cool Mint":        "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Cool-Mint.jpg",
    "Miami Mint":       "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Mint-Mint.jpg",
    "Peach Berry":      "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Peach-Berry.jpg",
    "Pineapple Savers": "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Pineapple-Savers.jpg",
}


# ── URL VERIFICATION ─────────────────────────────────────────────────────────
def verify_url(url: str) -> tuple[bool, int]:
    """Return (ok, status_code). Tries HEAD then GET."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; CDCImageVerifier/1.0)"
        )
    }
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status < 400, r.status
        except urllib.error.HTTPError as e:
            if method == "GET":
                return False, e.code
        except Exception:
            pass
    return False, 0


def verify_all(label: str, mapping: dict) -> dict:
    """Return only URLs that pass HTTP 200 check."""
    print(f"\n─── Verifying {label} URLs ───")
    verified = {}
    for flavor, url in mapping.items():
        ok, code = verify_url(url)
        status = f"HTTP {code}" if code else "TIMEOUT/ERROR"
        mark   = "✓" if ok else "✗"
        print(f"  [{mark}] {flavor:30s} {status}  {url[:70]}")
        if ok:
            verified[flavor] = url
        else:
            print(f"       !! SKIPPING — URL did not return 200")
    return verified


# ── MAIN ─────────────────────────────────────────────────────────────────────
async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db     = client[DB_NAME]
    print(f"Connected → DB: {DB_NAME}")

    # ── Step 1: verify all supplied URLs ─────────────────────────────────────
    verified_clio = verify_all("CLIO Platinum 50K", CLIO_IMAGES)
    verified_clr  = verify_all("CLR 50K",           CLR_IMAGES)

    total_updated = 0
    not_found     = []
    sample        = []       # up to 5 updated records

    # ── Step 2: update CLIO Platinum 50K ─────────────────────────────────────
    print("\n═══ Updating CLIO Platinum 50K ═══")
    for flavor, new_img in verified_clio.items():
        # Kit and Pod share the same image for the same flavor
        result = await db.products.update_many(
            {
                "brandName": "Geek Bar",
                "model":     "CLIO Platinum 50K",
                "flavor":    flavor,
            },
            {"$set": {"image": new_img}},
        )
        mc = result.modified_count
        total_updated += mc
        if mc:
            print(f"  ✓  [{flavor}] → updated {mc} record(s)")
            if len(sample) < 5:
                sample.append({"model": "CLIO Platinum 50K", "flavor": flavor, "image": new_img, "updated": mc})
        else:
            print(f"  –  [{flavor}] → no matching product in DB (skipped)")
            not_found.append(f"CLIO – {flavor}")

    # ── Step 3: update CLR 50K ────────────────────────────────────────────────
    print("\n═══ Updating CLR 50K ═══")
    for flavor, new_img in verified_clr.items():
        result = await db.products.update_many(
            {
                "brandName": "Geek Bar",
                "model":     "CLR 50K",
                "flavor":    flavor,
            },
            {"$set": {"image": new_img}},
        )
        mc = result.modified_count
        total_updated += mc
        if mc:
            print(f"  ✓  [{flavor}] → updated {mc} record(s)")
            if len(sample) < 5:
                sample.append({"model": "CLR 50K", "flavor": flavor, "image": new_img, "updated": mc})
        else:
            print(f"  –  [{flavor}] → no matching product in DB (skipped — may not exist)")
            not_found.append(f"CLR – {flavor}")

    # ── Step 4: final validation ──────────────────────────────────────────────
    print("\n═══ Validation Pass ═══")

    clio_prods = await db.products.find(
        {"brandName": "Geek Bar", "model": "CLIO Platinum 50K"}
    ).to_list(50)

    clr_prods = await db.products.find(
        {"brandName": "Geek Bar", "model": "CLR 50K"}
    ).to_list(50)

    def count_broken(prods):
        return [p for p in prods if not p.get("image") or "placeholder" in p.get("image", "")]

    broken_clio = count_broken(clio_prods)
    broken_clr  = count_broken(clr_prods)

    # Check CLIO flavor uniqueness
    clio_flavor_imgs = {p.get("flavor"): p.get("image") for p in clio_prods}
    clio_img_values  = list(clio_flavor_imgs.values())
    duplicates_clio  = len(clio_img_values) != len(set(v for v in clio_img_values if v))

    print(f"\n  CLIO products total:      {len(clio_prods)}")
    print(f"  CLIO broken/placeholder:  {len(broken_clio)} (must be 0)")
    print(f"  CLIO duplicate images:    {duplicates_clio} (should be False for unique per flavor)")

    print(f"\n  CLR products total:       {len(clr_prods)}")
    print(f"  CLR broken/placeholder:   {len(broken_clr)} (must be 0)")

    print(f"\n  Total records updated:    {total_updated}")
    print(f"  URLs skipped (not in DB): {len(not_found)}")
    if not_found:
        for nf in not_found:
            print(f"    – {nf}")

    # ── Step 5: sample of 5 updated records ──────────────────────────────────
    print("\n═══ Sample of Updated Records ═══")
    for i, rec in enumerate(sample[:5], 1):
        print(f"  {i}. [{rec['model']}] {rec['flavor']} ({rec['updated']} updated)")
        print(f"     → {rec['image']}")

    # ── Print full CLIO state ─────────────────────────────────────────────────
    print("\n═══ Full CLIO 50K State ═══")
    for p in sorted(clio_prods, key=lambda x: (x.get("flavor",""), x.get("productType",""))):
        img = p.get("image","")
        src = "bigmos" if "bigmos" in img else ("bigcom" if "bigcommerce" in img else "OTHER")
        print(f"  {p.get('flavor'):30s} {p.get('productType'):5s} [{src}] {img[:60]}")

    # ── Print full CLR state ──────────────────────────────────────────────────
    print("\n═══ Full CLR 50K State ═══")
    for p in sorted(clr_prods, key=lambda x: x.get("flavor","")):
        img = p.get("image","")
        src = "ebcreate" if "ebcreate" in img else ("bigcom" if "bigcommerce" in img else "OTHER")
        print(f"  {p.get('flavor'):30s} [{src}] {img[:70]}")

    client.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
