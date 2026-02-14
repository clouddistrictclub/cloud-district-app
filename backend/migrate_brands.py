#!/usr/bin/env python3
"""
Database migration and seeding script
- Creates brands
- Updates existing products with brandId and brandName
- Removes hardcoded data
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'cloud_district_club')

# Brands to create
BRANDS = [
    {"name": "Geek Bar", "isActive": True, "displayOrder": 1},
    {"name": "Lost Mary", "isActive": True, "displayOrder": 2},
    {"name": "RAZ", "isActive": True, "displayOrder": 3},
    {"name": "Meloso", "isActive": True, "displayOrder": 4},
    {"name": "Digiflavor", "isActive": True, "displayOrder": 5},
]

async def migrate():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("=" * 60)
    print("Cloud District Club - Database Migration")
    print("=" * 60)
    
    # Step 1: Create brands
    print("\n1. Creating brands...")
    brand_map = {}
    
    for brand_data in BRANDS:
        existing = await db.brands.find_one({"name": brand_data["name"]})
        if existing:
            print(f"   ✓ Brand '{brand_data['name']}' already exists")
            brand_map[brand_data["name"]] = str(existing["_id"])
        else:
            brand_data["createdAt"] = datetime.utcnow()
            result = await db.brands.insert_one(brand_data)
            brand_map[brand_data["name"]] = str(result.inserted_id)
            print(f"   ✓ Created brand '{brand_data['name']}'")
    
    # Step 2: Update existing products
    print("\n2. Updating existing products...")
    products = await db.products.find().to_list(1000)
    
    for product in products:
        # Check if product has brandId and brandName
        if "brandId" not in product or "brandName" not in product:
            # Try to infer brand from product data
            brand_name = product.get("brand", "Geek Bar")  # Default to Geek Bar
            
            if brand_name in brand_map:
                brand_id = brand_map[brand_name]
            else:
                # If brand doesn't exist, use first brand
                brand_id = brand_map["Geek Bar"]
                brand_name = "Geek Bar"
            
            update_data = {
                "brandId": brand_id,
                "brandName": brand_name
            }
            
            # Add missing fields with defaults
            if "lowStockThreshold" not in product:
                update_data["lowStockThreshold"] = 5
            if "isActive" not in product:
                update_data["isActive"] = True
            if "isFeatured" not in product:
                update_data["isFeatured"] = False
            if "displayOrder" not in product:
                update_data["displayOrder"] = 0
            if "images" not in product:
                update_data["images"] = []
            
            await db.products.update_one(
                {"_id": product["_id"]},
                {"$set": update_data}
            )
            print(f"   ✓ Updated product '{product.get('name', 'Unknown')}' → {brand_name}")
    
    # Step 3: Summary
    print("\n3. Database Status:")
    brand_count = await db.brands.count_documents({})
    product_count = await db.products.count_documents({})
    user_count = await db.users.count_documents({})
    order_count = await db.orders.count_documents({})
    
    print(f"   Brands: {brand_count}")
    print(f"   Products: {product_count}")
    print(f"   Users: {user_count}")
    print(f"   Orders: {order_count}")
    
    print("\n✅ Migration complete!")
    print("\nNext steps:")
    print("1. Restart backend: sudo supervisorctl restart backend")
    print("2. Brands will now appear in Admin → Brands")
    print("3. Products will be selectable by brand")
    print("4. Home screen will pull brands dynamically")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
