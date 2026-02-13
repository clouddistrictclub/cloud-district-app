#!/usr/bin/env python3
"""
Loyalty Points and Complete Integration Test
Tests the full order flow including loyalty points calculation
"""

import requests
import json
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

# Backend URL
BASE_URL = "https://quick-cloud-1.preview.emergentagent.com/api"

# MongoDB connection
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

async def test_loyalty_points_flow():
    """Test complete loyalty points flow"""
    print("🎯 Testing Loyalty Points Flow")
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # 1. Login as regular user
        login_data = {
            "email": "test@test.com",
            "password": "Test123!"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", 
                               json=login_data,
                               headers={"Content-Type": "application/json"})
        
        if response.status_code != 200:
            print(f"❌ User login failed: {response.status_code}")
            return False
            
        user_data = response.json()
        user_token = user_data["access_token"]
        user_id = user_data["user"]["id"]
        initial_points = user_data["user"]["loyaltyPoints"]
        
        print(f"✅ User logged in. Initial loyalty points: {initial_points}")
        
        headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }
        
        # 2. Create an order worth $50 (should earn 50 points)
        order_data = {
            "items": [
                {
                    "productId": "test-product-id",
                    "quantity": 1,
                    "name": "Premium Vape Product",
                    "price": 50.00
                }
            ],
            "total": 50.00,
            "pickupTime": "2024-12-20T10:00:00Z",
            "paymentMethod": "Credit Card",
            "loyaltyPointsUsed": 0
        }
        
        response = requests.post(f"{BASE_URL}/orders", 
                               json=order_data,
                               headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Order creation failed: {response.status_code} - {response.text}")
            return False
            
        order = response.json()
        order_id = order["id"]
        points_to_earn = order["loyaltyPointsEarned"]
        
        print(f"✅ Order created. Points to earn: {points_to_earn}")
        
        # 3. Login as admin and mark order as paid
        admin_login = {
            "email": "admin@test.com",
            "password": "Admin123!"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", 
                               json=admin_login,
                               headers={"Content-Type": "application/json"})
        
        if response.status_code != 200:
            print(f"❌ Admin login failed: {response.status_code}")
            return False
            
        admin_data = response.json()
        admin_token = admin_data["access_token"]
        
        admin_headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        # 4. Mark order as paid (this should add loyalty points)
        status_update = {"status": "Paid"}
        
        response = requests.patch(f"{BASE_URL}/admin/orders/{order_id}/status", 
                                json=status_update,
                                headers=admin_headers)
        
        if response.status_code != 200:
            print(f"❌ Order status update failed: {response.status_code} - {response.text}")
            return False
            
        print("✅ Order marked as paid")
        
        # 5. Check user's loyalty points after payment
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Failed to get updated user profile: {response.status_code}")
            return False
            
        updated_user = response.json()
        final_points = updated_user["loyaltyPoints"]
        
        expected_points = initial_points + points_to_earn
        
        print(f"Initial points: {initial_points}")
        print(f"Points earned: {points_to_earn}")
        print(f"Expected points: {expected_points}")
        print(f"Actual final points: {final_points}")
        
        if final_points == expected_points:
            print("✅ Loyalty points calculated correctly!")
            return True
        else:
            print("❌ Loyalty points calculation incorrect!")
            return False
            
    except Exception as e:
        print(f"❌ Loyalty points test failed: {e}")
        return False
    finally:
        client.close()

async def test_using_loyalty_points():
    """Test using loyalty points to reduce order total"""
    print("\n💰 Testing Using Loyalty Points")
    
    try:
        # Login as user
        login_data = {
            "email": "test@test.com",
            "password": "Test123!"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", 
                               json=login_data,
                               headers={"Content-Type": "application/json"})
        
        user_data = response.json()
        user_token = user_data["access_token"]
        available_points = user_data["user"]["loyaltyPoints"]
        
        print(f"Available loyalty points: {available_points}")
        
        if available_points < 10:
            print("❌ Insufficient loyalty points for test")
            return False
            
        headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }
        
        # Create order using 10 loyalty points
        points_to_use = min(10, available_points)
        
        order_data = {
            "items": [
                {
                    "productId": "test-product-id-2",
                    "quantity": 1,
                    "name": "Budget Vape Product",
                    "price": 25.00
                }
            ],
            "total": 25.00 - points_to_use,  # Reduced by loyalty points
            "pickupTime": "2024-12-20T11:00:00Z",
            "paymentMethod": "Credit Card",
            "loyaltyPointsUsed": points_to_use
        }
        
        response = requests.post(f"{BASE_URL}/orders", 
                               json=order_data,
                               headers=headers)
        
        if response.status_code == 200:
            order = response.json()
            print(f"✅ Order with loyalty points created. Used {points_to_use} points")
            
            # Check if points were deducted
            response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
            updated_user = response.json()
            new_points = updated_user["loyaltyPoints"]
            
            expected_points = available_points - points_to_use
            
            if new_points == expected_points:
                print(f"✅ Loyalty points deducted correctly: {available_points} -> {new_points}")
                return True
            else:
                print(f"❌ Loyalty points deduction incorrect: expected {expected_points}, got {new_points}")
                return False
        else:
            print(f"❌ Order with loyalty points failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Using loyalty points test failed: {e}")
        return False

async def main():
    print("🏪 Running Complete Integration Tests\n")
    
    # Test loyalty points earning
    loyalty_success = await test_loyalty_points_flow()
    
    # Test loyalty points usage
    usage_success = await test_using_loyalty_points()
    
    print(f"\n📊 Integration Test Results:")
    print(f"{'✅' if loyalty_success else '❌'} Loyalty Points Earning")
    print(f"{'✅' if usage_success else '❌'} Loyalty Points Usage")
    
    overall_success = loyalty_success and usage_success
    print(f"\n{'✅ All integration tests passed!' if overall_success else '❌ Some integration tests failed'}")
    
    return overall_success

if __name__ == "__main__":
    result = asyncio.run(main())
    import sys
    sys.exit(0 if result else 1)