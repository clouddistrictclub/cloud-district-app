"""
Test Cloudz earn rate at 3x multiplier (3 Cloudz per $1 spent)
Verifies the backend earn rate change from 1x to 3x per $1 spent
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCloudzEarnRate:
    """Test the 3x Cloudz earn rate on orders"""
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Create/login test user and return token"""
        unique_email = f"test_earn_rate_{int(time.time())}@test.com"
        
        # Register new user
        register_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "firstName": "Test",
            "lastName": "EarnRate",
            "dateOfBirth": "1990-01-01",
            "phone": "555-0001"
        })
        
        if register_resp.status_code == 200:
            data = register_resp.json()
            return data.get("access_token"), data.get("user", {}).get("id"), unique_email
        
        # If register fails (user exists), try login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": unique_email,
            "password": "TestPass123!"
        })
        
        if login_resp.status_code == 200:
            data = login_resp.json()
            return data.get("access_token"), data.get("user", {}).get("id"), unique_email
        
        pytest.skip(f"Could not create/login test user: {register_resp.text}")
    
    @pytest.fixture(scope="class")
    def product_id(self):
        """Get first available product ID"""
        resp = requests.get(f"{BASE_URL}/api/products")
        assert resp.status_code == 200, f"Failed to get products: {resp.text}"
        products = resp.json()
        assert len(products) > 0, "No products available for testing"
        return products[0]["id"], products[0]["name"], products[0]["price"]
    
    def test_order_creation_returns_3x_points(self, test_user_token, product_id):
        """Test that order creation returns loyalty points at 3x rate"""
        token, user_id, email = test_user_token
        prod_id, prod_name, prod_price = product_id
        
        # Create order with a specific total
        order_total = 20.00  # $20 order should earn 60 Cloudz (20 * 3)
        
        headers = {"Authorization": f"Bearer {token}"}
        order_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "items": [{
                "productId": prod_id,
                "quantity": 1,
                "name": prod_name,
                "price": prod_price
            }],
            "total": order_total,
            "pickupTime": "2:00 PM - 3:00 PM",
            "paymentMethod": "Cash on Pickup",
            "loyaltyPointsUsed": 0
        }, headers=headers)
        
        assert order_resp.status_code == 200, f"Order creation failed: {order_resp.text}"
        order_data = order_resp.json()
        
        # Verify the earn rate is 3x
        expected_points = int(order_total) * 3  # 20 * 3 = 60
        actual_points = order_data.get("loyaltyPointsEarned", 0)
        
        print(f"Order Total: ${order_total}")
        print(f"Expected Points (3x): {expected_points}")
        print(f"Actual Points Earned: {actual_points}")
        
        assert actual_points == expected_points, \
            f"Earn rate incorrect! Expected {expected_points} (3x), got {actual_points}"
    
    def test_various_order_amounts_3x_rate(self, test_user_token, product_id):
        """Test 3x earn rate with various order amounts"""
        token, user_id, email = test_user_token
        prod_id, prod_name, prod_price = product_id
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test cases: (order_total, expected_points)
        test_cases = [
            (10.00, 30),   # $10 * 3 = 30
            (25.50, 75),   # int(25.50) * 3 = 25 * 3 = 75
            (50.00, 150),  # $50 * 3 = 150
            (100.00, 300), # $100 * 3 = 300
        ]
        
        for order_total, expected_points in test_cases:
            order_resp = requests.post(f"{BASE_URL}/api/orders", json={
                "items": [{
                    "productId": prod_id,
                    "quantity": 1,
                    "name": prod_name,
                    "price": prod_price
                }],
                "total": order_total,
                "pickupTime": "3:00 PM - 4:00 PM",
                "paymentMethod": "Cash on Pickup",
                "loyaltyPointsUsed": 0
            }, headers=headers)
            
            assert order_resp.status_code == 200, f"Order creation failed for ${order_total}: {order_resp.text}"
            order_data = order_resp.json()
            
            actual_points = order_data.get("loyaltyPointsEarned", 0)
            
            print(f"  ${order_total} -> Expected: {expected_points}, Actual: {actual_points}")
            
            assert actual_points == expected_points, \
                f"Earn rate incorrect for ${order_total}! Expected {expected_points}, got {actual_points}"
        
        print("All 3x earn rate tests passed!")


class TestAdminUserCloudzBalance:
    """Test admin user's Cloudz balance"""
    
    def test_admin_user_balance_30000(self):
        """Verify admin user jkaatz@gmail.com has 30,000 Cloudz"""
        # Login as admin
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "jkaatz@gmail.com",
            "password": "Just1n23$"
        })
        
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        data = login_resp.json()
        
        user = data.get("user", {})
        loyalty_points = user.get("loyaltyPoints", 0)
        
        print(f"Admin user Cloudz balance: {loyalty_points}")
        
        # Admin should have 30,000 Cloudz
        assert loyalty_points == 30000, \
            f"Admin Cloudz balance incorrect! Expected 30000, got {loyalty_points}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
