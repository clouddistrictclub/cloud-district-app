#!/usr/bin/env python3
"""
Admin Setup and Testing for Cloud District Club
Creates an admin user and tests admin endpoints
"""

import requests
import json
import sys
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from passlib.context import CryptContext

# Backend URL
BASE_URL = "https://vape-local-pickup.preview.emergentagent.com/api"

# MongoDB connection (from backend .env)
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin_user():
    """Create an admin user directly in MongoDB"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Check if admin already exists
        admin_email = "admin@test.com"
        existing_admin = await db.users.find_one({"email": admin_email})
        
        if existing_admin:
            print(f"Admin user {admin_email} already exists")
            # Update to ensure isAdmin is true
            await db.users.update_one(
                {"email": admin_email},
                {"$set": {"isAdmin": True}}
            )
            return admin_email
        
        # Create new admin user
        admin_data = {
            "email": admin_email,
            "password": pwd_context.hash("Admin123!"),
            "firstName": "Admin",
            "lastName": "User",
            "dateOfBirth": "1985-01-01",
            "isAdmin": True,
            "loyaltyPoints": 0,
            "createdAt": datetime.utcnow()
        }
        
        result = await db.users.insert_one(admin_data)
        print(f"Created admin user: {admin_email} with ID: {result.inserted_id}")
        return admin_email
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return None
    finally:
        client.close()

def test_admin_endpoints():
    """Test admin endpoints with admin credentials"""
    print("\n🔐 Testing Admin Endpoints")
    
    # Login as admin
    admin_credentials = {
        "email": "admin@test.com",
        "password": "Admin123!"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", 
                               json=admin_credentials,
                               headers={"Content-Type": "application/json"})
        
        if response.status_code != 200:
            print(f"❌ Admin login failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        admin_token = data["access_token"]
        is_admin = data["user"].get("isAdmin", False)
        
        print(f"✅ Admin login successful. isAdmin: {is_admin}")
        
        if not is_admin:
            print("❌ User is not marked as admin in response")
            return False
        
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        # Test 1: Create Product
        test_product = {
            "name": "Admin Test Vape",
            "brand": "Geek Bar",
            "category": "geek-bar",
            "image": "data:image/png;base64,admintest",
            "puffCount": 6000,
            "flavor": "Mint",
            "nicotinePercent": 3.0,
            "price": 24.99,
            "stock": 15
        }
        
        response = requests.post(f"{BASE_URL}/products", 
                               json=test_product,
                               headers=headers)
        
        if response.status_code == 200:
            product_data = response.json()
            product_id = product_data["id"]
            print(f"✅ Admin created product successfully. ID: {product_id}")
        else:
            print(f"❌ Admin product creation failed: {response.status_code} - {response.text}")
            return False
        
        # Test 2: Get All Orders
        response = requests.get(f"{BASE_URL}/admin/orders", headers=headers)
        
        if response.status_code == 200:
            orders = response.json()
            print(f"✅ Admin retrieved {len(orders)} orders")
        else:
            print(f"❌ Admin get all orders failed: {response.status_code} - {response.text}")
            return False
        
        # Test 3: Update Order Status (if there are orders)
        if orders:
            order_id = orders[0]["id"]
            status_update = {"status": "Paid"}
            
            response = requests.patch(f"{BASE_URL}/admin/orders/{order_id}/status", 
                                    json=status_update,
                                    headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Admin updated order status successfully")
            else:
                print(f"❌ Admin update order status failed: {response.status_code} - {response.text}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Admin endpoint testing failed: {e}")
        return False

async def main():
    print("🔧 Setting up Admin User and Testing Admin Endpoints")
    
    # Create admin user
    admin_email = await create_admin_user()
    
    if admin_email:
        # Test admin endpoints
        success = test_admin_endpoints()
        
        if success:
            print("\n✅ All admin tests passed!")
            return True
        else:
            print("\n❌ Some admin tests failed")
            return False
    else:
        print("\n❌ Failed to create admin user")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)