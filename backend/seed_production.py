#!/usr/bin/env python3
"""Seed script for Cloud District Club production API."""
import requests
import json
import sys

API = "https://api.clouddistrict.club"

# ── 1. Register admin user ──
print("=== Step 1: Register admin user ===")
reg = requests.post(f"{API}/api/auth/register", json={
    "email": "jkaatz@gmail.com",
    "password": "Just1n23$",
    "firstName": "Jake",
    "lastName": "Kaatz",
    "dateOfBirth": "1990-01-15",
})
if reg.status_code == 200:
    data = reg.json()
    TOKEN = data["access_token"]
    print(f"  Registered: {data['user']['email']} (id: {data['user']['id']})")
elif reg.status_code == 400 and "already registered" in reg.text:
    print("  User already exists, logging in...")
    login = requests.post(f"{API}/api/auth/login", json={
        "email": "jkaatz@gmail.com",
        "password": "Just1n23$",
    })
    if login.status_code != 200:
        print(f"  Login failed: {login.text}")
        sys.exit(1)
    data = login.json()
    TOKEN = data["access_token"]
    print(f"  Logged in: {data['user']['email']}")
else:
    print(f"  Registration failed ({reg.status_code}): {reg.text}")
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# ── 2. Promote to admin (directly via MongoDB if endpoint exists, or check) ──
# The register endpoint sets isAdmin=False. We need to promote via the DB.
# Since we can't directly access production MongoDB from here, we'll use
# the local backend's promote pattern. Let's check if there's an admin promote endpoint.
print("\n=== Step 2: Checking admin status ===")
me = requests.get(f"{API}/api/auth/me", headers=HEADERS).json()
if me.get("isAdmin"):
    print(f"  Already admin: {me['email']}")
else:
    print(f"  User is NOT admin yet. Will need manual MongoDB promotion.")
    print(f"  Run in production MongoDB: db.users.updateOne({{email: 'jkaatz@gmail.com'}}, {{$set: {{isAdmin: true}}}})")
    print(f"  Continuing with non-admin seeding (brands/products require admin)...")
    # Try anyway in case it works
    pass

# ── 3. Create brands ──
print("\n=== Step 3: Create brands ===")
BRANDS = [
    {"name": "Geek Bar", "isActive": True, "displayOrder": 1},
    {"name": "Lost Mary", "isActive": True, "displayOrder": 2},
    {"name": "RAZ", "isActive": True, "displayOrder": 3},
    {"name": "Elf Bar", "isActive": True, "displayOrder": 4},
    {"name": "Flum", "isActive": True, "displayOrder": 5},
]

brand_ids = {}
for b in BRANDS:
    r = requests.post(f"{API}/api/brands", json=b, headers=HEADERS)
    if r.status_code == 200:
        brand_data = r.json()
        brand_ids[b["name"]] = brand_data.get("id", "")
        print(f"  Created brand: {b['name']} (id: {brand_ids[b['name']]})")
    else:
        print(f"  Brand '{b['name']}' failed ({r.status_code}): {r.text[:100]}")

if not brand_ids:
    print("\n  No brands created. Admin promotion may be required first.")
    print("  Exiting. Promote user to admin and re-run.")
    sys.exit(1)

# ── 4. Create products ──
print("\n=== Step 4: Create products ===")
PRODUCTS = [
    {
        "name": "Geek Bar Pulse 15000",
        "brand": "Geek Bar",
        "category": "Disposable",
        "puffCount": 15000,
        "flavor": "Watermelon Ice",
        "nicotinePercent": 5.0,
        "price": 19.99,
        "stock": 50,
        "description": "15000 puffs, rechargeable, dual mesh coil for bold watermelon ice flavor.",
        "isFeatured": True,
        "displayOrder": 1,
    },
    {
        "name": "Geek Bar Skyview 25000",
        "brand": "Geek Bar",
        "category": "Disposable",
        "puffCount": 25000,
        "flavor": "Blue Razz Ice",
        "nicotinePercent": 5.0,
        "price": 24.99,
        "stock": 40,
        "description": "25000 puffs with smart display screen. Icy blue raspberry blast.",
        "isFeatured": True,
        "displayOrder": 2,
    },
    {
        "name": "Lost Mary MO5000",
        "brand": "Lost Mary",
        "category": "Disposable",
        "puffCount": 5000,
        "flavor": "Strawberry Mango",
        "nicotinePercent": 5.0,
        "price": 14.99,
        "stock": 60,
        "description": "Compact and flavorful. Tropical strawberry mango blend.",
        "isFeatured": False,
        "displayOrder": 3,
    },
    {
        "name": "Lost Mary MT15000 Turbo",
        "brand": "Lost Mary",
        "category": "Disposable",
        "puffCount": 15000,
        "flavor": "Triple Berry Ice",
        "nicotinePercent": 5.0,
        "price": 21.99,
        "stock": 35,
        "description": "Turbo mode for extra vapor. Triple berry with cooling menthol.",
        "isFeatured": True,
        "displayOrder": 4,
    },
    {
        "name": "RAZ TN9000",
        "brand": "RAZ",
        "category": "Disposable",
        "puffCount": 9000,
        "flavor": "Grape Ice",
        "nicotinePercent": 5.0,
        "price": 16.99,
        "stock": 45,
        "description": "Smooth grape ice with adjustable airflow control.",
        "isFeatured": False,
        "displayOrder": 5,
    },
    {
        "name": "RAZ DC25000",
        "brand": "RAZ",
        "category": "Disposable",
        "puffCount": 25000,
        "flavor": "Peach Mango",
        "nicotinePercent": 5.0,
        "price": 26.99,
        "stock": 30,
        "description": "Dual-core technology, 25000 puffs. Sweet peach mango fusion.",
        "isFeatured": True,
        "displayOrder": 6,
    },
    {
        "name": "Elf Bar BC5000",
        "brand": "Elf Bar",
        "category": "Disposable",
        "puffCount": 5000,
        "flavor": "Miami Mint",
        "nicotinePercent": 5.0,
        "price": 13.99,
        "stock": 70,
        "description": "Classic Elf Bar form factor. Cool Miami mint flavor.",
        "isFeatured": False,
        "displayOrder": 7,
    },
    {
        "name": "Elf Bar Ultra 50000",
        "brand": "Elf Bar",
        "category": "Disposable",
        "puffCount": 50000,
        "flavor": "Blueberry Watermelon",
        "nicotinePercent": 5.0,
        "price": 29.99,
        "stock": 25,
        "description": "Ultra capacity 50000 puffs. Premium blueberry watermelon mix.",
        "isFeatured": True,
        "displayOrder": 8,
    },
    {
        "name": "Flum Float 3000",
        "brand": "Flum",
        "category": "Disposable",
        "puffCount": 3000,
        "flavor": "Aloe Grape",
        "nicotinePercent": 5.0,
        "price": 11.99,
        "stock": 55,
        "description": "Lightweight and portable. Refreshing aloe grape flavor.",
        "isFeatured": False,
        "displayOrder": 9,
    },
    {
        "name": "Flum Pebble 6000",
        "brand": "Flum",
        "category": "Disposable",
        "puffCount": 6000,
        "flavor": "Lush Ice",
        "nicotinePercent": 5.0,
        "price": 15.99,
        "stock": 40,
        "description": "Pebble-shaped design. Watermelon with icy menthol finish.",
        "isFeatured": False,
        "displayOrder": 10,
    },
]

for p in PRODUCTS:
    brand_name = p.pop("brand")
    bid = brand_ids.get(brand_name, "")
    if not bid:
        print(f"  Skipping {p['name']} — brand '{brand_name}' not found")
        continue
    p["brandId"] = bid
    p["image"] = ""  # Placeholder — add images via admin dashboard later
    r = requests.post(f"{API}/api/products", json=p, headers=HEADERS)
    if r.status_code == 200:
        pid = r.json().get("id", "")
        print(f"  Created product: {p['name']} ({p['flavor']}) — ${p['price']} (id: {pid})")
    else:
        print(f"  Product '{p['name']}' failed ({r.status_code}): {r.text[:100]}")

# ── 5. Verify ──
print("\n=== Step 5: Verify seeded data ===")
brands = requests.get(f"{API}/api/brands", headers=HEADERS).json()
products = requests.get(f"{API}/api/products", headers=HEADERS).json()
print(f"  Brands: {len(brands)}")
print(f"  Products: {len(products)}")
for b in brands:
    print(f"    - {b['name']} (active: {b.get('isActive', True)})")
for p in products:
    print(f"    - {p['name']} | {p.get('flavor','')} | ${p.get('price',0)} | stock: {p.get('stock',0)}")

print("\n=== Seeding complete! ===")
