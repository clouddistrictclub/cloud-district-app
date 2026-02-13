#!/usr/bin/env python3
"""
Helper script to create admin user and seed sample products
Run this after registering your first user in the app
"""
import os
import sys
from pymongo import MongoClient
from datetime import datetime
import asyncio

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'cloud_district_club')

# Sample placeholder image (1x1 transparent PNG in base64)
PLACEHOLDER_IMAGE = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='

SAMPLE_PRODUCTS = [
    {
        "name": "Geek Bar Pulse X",
        "brand": "Geek Bar",
        "category": "geek-bar",
        "image": PLACEHOLDER_IMAGE,
        "puffCount": 25000,
        "flavor": "Watermelon Ice",
        "nicotinePercent": 5.0,
        "price": 24.99,
        "stock": 15
    },
    {
        "name": "Lost Mary OS5000",
        "brand": "Lost Mary",
        "category": "lost-mary",
        "image": PLACEHOLDER_IMAGE,
        "puffCount": 5000,
        "flavor": "Blue Razz Ice",
        "nicotinePercent": 5.0,
        "price": 19.99,
        "stock": 20
    },
    {
        "name": "RAZ TN9000",
        "brand": "RAZ",
        "category": "raz",
        "image": PLACEHOLDER_IMAGE,
        "puffCount": 9000,
        "flavor": "Strawberry Kiwi",
        "nicotinePercent": 5.0,
        "price": 21.99,
        "stock": 12
    },
    {
        "name": "Meloso Ultra",
        "brand": "Meloso",
        "category": "meloso",
        "image": PLACEHOLDER_IMAGE,
        "puffCount": 10000,
        "flavor": "Peach Mango",
        "nicotinePercent": 5.0,
        "price": 22.99,
        "stock": 8
    },
    {
        "name": "Digiflavor DROP",
        "brand": "Digiflavor",
        "category": "digiflavor",
        "image": PLACEHOLDER_IMAGE,
        "puffCount": 7000,
        "flavor": "Mint Ice",
        "nicotinePercent": 5.0,
        "price": 20.99,
        "stock": 10
    },
    {
        "name": "Geek Bar B5000",
        "brand": "Geek Bar",
        "category": "best-sellers",
        "image": PLACEHOLDER_IMAGE,
        "puffCount": 5000,
        "flavor": "Grape Ice",
        "nicotinePercent": 5.0,
        "price": 18.99,
        "stock": 25
    },
    {
        "name": "Lost Mary BM5000",
        "brand": "Lost Mary",
        "category": "new-arrivals",
        "image": PLACEHOLDER_IMAGE,
        "puffCount": 5000,
        "flavor": "Tropical Rainbow",
        "nicotinePercent": 5.0,
        "price": 19.99,
        "stock": 30
    }
]

def main():
    print("=" * 60)
    print("Cloud District Club - Database Setup")
    print("=" * 60)
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Step 1: Make first user admin
        print("\n1. Setting up admin user...")
        email = input("Enter the email of the user to make admin (default: admin@clouddistrictclub.com): ").strip()
        if not email:
            email = "admin@clouddistrictclub.com"
        
        result = db.users.update_one(
            {"email": email},
            {"$set": {"isAdmin": True}}
        )
        
        if result.matched_count > 0:
            print(f"✅ User {email} is now an admin")
        else:
            print(f"❌ User {email} not found. Please register in the app first.")
            sys.exit(1)
        
        # Step 2: Add sample products
        print("\n2. Adding sample products...")
        
        # Clear existing products
        clear = input("Clear existing products? (y/N): ").strip().lower()
        if clear == 'y':
            db.products.delete_many({})
            print("✅ Cleared existing products")
        
        # Insert products
        added = 0
        for product in SAMPLE_PRODUCTS:
            # Check if product already exists
            existing = db.products.find_one({"name": product["name"]})
            if not existing:
                db.products.insert_one(product)
                print(f"✅ Added: {product['name']}")
                added += 1
            else:
                print(f"⏭️  Skipped (exists): {product['name']}")
        
        print(f"\n✅ Setup complete! Added {added} new products")
        print("\nAdmin Login Credentials:")
        print(f"Email: {email}")
        print("Password: (the password you registered with)")
        print("\nYou can now login to the app and access the admin dashboard!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()
