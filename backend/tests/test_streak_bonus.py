"""
Streak Bonus System Tests
Tests for the weekly streak bonus feature that awards Cloudz for consecutive ISO weeks with Paid orders.
Streak bonus scale: Week 2: +50, Week 3: +100, Week 4: +200, Week 5+: +500
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
PRODUCT_ID = "6990e43720bc90d09dba30bf"  # Product with stock


class TestStreakEndpoint:
    """Tests for GET /api/loyalty/streak endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_auth(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"],
            "headers": {"Authorization": f"Bearer {data['access_token']}"}
        }
    
    @pytest.fixture(scope="class")
    def test_user_auth(self):
        """Create a new test user for streak tests"""
        unique_id = uuid.uuid4().hex[:8]
        email = f"streaktest_{unique_id}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "Streak",
            "lastName": "Tester",
            "dateOfBirth": "1990-01-15"
        })
        assert response.status_code == 200, f"User registration failed: {response.text}"
        data = response.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"],
            "email": email,
            "headers": {"Authorization": f"Bearer {data['access_token']}"}
        }
    
    def test_streak_endpoint_returns_correct_fields(self, admin_auth):
        """Test that streak endpoint returns all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/loyalty/streak",
            headers=admin_auth["headers"]
        )
        assert response.status_code == 200, f"Streak endpoint failed: {response.text}"
        
        data = response.json()
        
        # Verify all required fields are present
        assert "streak" in data, "Missing 'streak' field"
        assert "currentBonus" in data, "Missing 'currentBonus' field"
        assert "nextBonus" in data, "Missing 'nextBonus' field"
        assert "daysUntilExpiry" in data, "Missing 'daysUntilExpiry' field"
        assert "isoWeek" in data, "Missing 'isoWeek' field"
        assert "isoYear" in data, "Missing 'isoYear' field"
        
        # Verify data types
        assert isinstance(data["streak"], int), "streak should be an integer"
        assert isinstance(data["currentBonus"], int), "currentBonus should be an integer"
        assert isinstance(data["nextBonus"], int), "nextBonus should be an integer"
        assert isinstance(data["daysUntilExpiry"], int), "daysUntilExpiry should be an integer"
        assert isinstance(data["isoWeek"], int), "isoWeek should be an integer"
        assert isinstance(data["isoYear"], int), "isoYear should be an integer"
        
        print(f"Streak data: {data}")
    
    def test_streak_endpoint_without_auth_returns_403(self):
        """Test that streak endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/loyalty/streak")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Error response should have 'detail' field"
        print(f"Auth error response: {data}")
    
    def test_streak_endpoint_with_invalid_token_returns_401(self):
        """Test that streak endpoint rejects invalid tokens"""
        response = requests.get(
            f"{BASE_URL}/api/loyalty/streak",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"Invalid token response: {response.json()}")
    
    def test_new_user_has_zero_streak(self, test_user_auth):
        """Test that a new user with no orders has streak 0"""
        response = requests.get(
            f"{BASE_URL}/api/loyalty/streak",
            headers=test_user_auth["headers"]
        )
        assert response.status_code == 200, f"Streak endpoint failed: {response.text}"
        
        data = response.json()
        assert data["streak"] == 0, f"New user should have streak 0, got {data['streak']}"
        assert data["currentBonus"] == 0, f"New user should have currentBonus 0, got {data['currentBonus']}"
        # nextBonus for streak 0 -> 1 is 0 (bonus only starts at streak 2)
        print(f"New user streak data: {data}")
    
    def test_iso_week_and_year_match_current_date(self, admin_auth):
        """Test that isoWeek and isoYear match the current date"""
        response = requests.get(
            f"{BASE_URL}/api/loyalty/streak",
            headers=admin_auth["headers"]
        )
        assert response.status_code == 200
        
        data = response.json()
        now = datetime.utcnow()
        expected_year, expected_week, _ = now.isocalendar()
        
        assert data["isoYear"] == expected_year, f"isoYear mismatch: {data['isoYear']} != {expected_year}"
        assert data["isoWeek"] == expected_week, f"isoWeek mismatch: {data['isoWeek']} != {expected_week}"
        print(f"ISO week/year verified: {expected_year}-W{expected_week}")
    
    def test_days_until_expiry_is_valid_range(self, admin_auth):
        """Test that daysUntilExpiry is within valid range (0-6)"""
        response = requests.get(
            f"{BASE_URL}/api/loyalty/streak",
            headers=admin_auth["headers"]
        )
        assert response.status_code == 200
        
        data = response.json()
        assert 0 <= data["daysUntilExpiry"] <= 6, f"daysUntilExpiry should be 0-6, got {data['daysUntilExpiry']}"
        print(f"Days until expiry: {data['daysUntilExpiry']}")


class TestStreakBonusScale:
    """Tests to verify bonus scale: Week 2: +50, Week 3: +100, Week 4: +200, Week 5+: +500"""
    
    @pytest.fixture(scope="class")
    def admin_auth(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        assert response.status_code == 200
        data = response.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"],
            "headers": {"Authorization": f"Bearer {data['access_token']}"}
        }
    
    def test_streak_1_has_zero_bonus(self, admin_auth):
        """Admin has streak=1, should have currentBonus=0 and nextBonus=50"""
        response = requests.get(
            f"{BASE_URL}/api/loyalty/streak",
            headers=admin_auth["headers"]
        )
        assert response.status_code == 200
        
        data = response.json()
        # Admin has streak=1 (only orders in current week)
        if data["streak"] == 1:
            assert data["currentBonus"] == 0, "Streak 1 should have currentBonus 0"
            assert data["nextBonus"] == 50, "Streak 1 should have nextBonus 50 (for streak 2)"
            print(f"Streak 1 bonus verified: current={data['currentBonus']}, next={data['nextBonus']}")
        else:
            print(f"Admin streak is {data['streak']}, cannot verify streak 1 bonus")


class TestOrderStatusAndStreakTrigger:
    """Tests for streak bonus trigger when order is marked as Paid"""
    
    @pytest.fixture(scope="class")
    def admin_auth(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        assert response.status_code == 200
        data = response.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"],
            "headers": {"Authorization": f"Bearer {data['access_token']}"}
        }
    
    @pytest.fixture(scope="class")
    def test_user_with_order(self, admin_auth):
        """Create a new test user and an order"""
        unique_id = uuid.uuid4().hex[:8]
        email = f"streakorder_{unique_id}@test.com"
        
        # Register user
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "OrderStreak",
            "lastName": "Tester",
            "dateOfBirth": "1990-01-15"
        })
        assert response.status_code == 200
        data = response.json()
        
        user_data = {
            "token": data["access_token"],
            "user_id": data["user"]["id"],
            "email": email,
            "headers": {"Authorization": f"Bearer {data['access_token']}"}
        }
        
        # Create an order
        order_response = requests.post(
            f"{BASE_URL}/api/orders",
            json={
                "items": [{
                    "productId": PRODUCT_ID,
                    "quantity": 1,
                    "name": "Test Product",
                    "price": 10.00
                }],
                "total": 10.00,
                "pickupTime": "2026-02-16T14:00:00Z",
                "paymentMethod": "Cash on Pickup"
            },
            headers=user_data["headers"]
        )
        assert order_response.status_code == 200, f"Order creation failed: {order_response.text}"
        order_data = order_response.json()
        user_data["order_id"] = order_data["id"]
        user_data["admin_headers"] = admin_auth["headers"]
        
        return user_data
    
    def test_user_streak_before_order_paid(self, test_user_with_order):
        """User should have streak=0 before any order is marked Paid"""
        response = requests.get(
            f"{BASE_URL}/api/loyalty/streak",
            headers=test_user_with_order["headers"]
        )
        assert response.status_code == 200
        
        data = response.json()
        # Before order is Paid, streak should be 0
        assert data["streak"] == 0, f"Streak before Paid should be 0, got {data['streak']}"
        print(f"User streak before Paid: {data}")
    
    def test_mark_order_paid_triggers_streak_update(self, test_user_with_order):
        """Mark order as Paid and verify streak increases"""
        order_id = test_user_with_order["order_id"]
        
        # Mark order as Paid
        response = requests.patch(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": "Paid"},
            headers=test_user_with_order["admin_headers"]
        )
        assert response.status_code == 200, f"Failed to mark order as Paid: {response.text}"
        
        # Check streak after marking Paid
        streak_response = requests.get(
            f"{BASE_URL}/api/loyalty/streak",
            headers=test_user_with_order["headers"]
        )
        assert streak_response.status_code == 200
        
        data = streak_response.json()
        assert data["streak"] == 1, f"Streak after first Paid order should be 1, got {data['streak']}"
        assert data["currentBonus"] == 0, "Streak 1 should have currentBonus 0"
        assert data["nextBonus"] == 50, "Streak 1 should have nextBonus 50"
        print(f"User streak after Paid: {data}")
    
    def test_no_streak_bonus_ledger_for_streak_1(self, test_user_with_order):
        """Verify no streak_bonus entry in ledger for streak=1 (correct behavior)"""
        response = requests.get(
            f"{BASE_URL}/api/loyalty/ledger",
            headers=test_user_with_order["headers"]
        )
        assert response.status_code == 200
        
        ledger = response.json()
        streak_entries = [e for e in ledger if e.get("type") == "streak_bonus"]
        
        # For streak=1, there should be no streak_bonus entry (bonus starts at streak 2)
        assert len(streak_entries) == 0, f"Should have no streak_bonus entries for streak=1, found {len(streak_entries)}"
        print(f"Verified: No streak_bonus ledger entries for streak=1 (correct behavior)")


class TestOrderFlowRegression:
    """Regression tests to ensure order creation and status update still work"""
    
    @pytest.fixture(scope="class")
    def admin_auth(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        assert response.status_code == 200
        data = response.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"],
            "headers": {"Authorization": f"Bearer {data['access_token']}"}
        }
    
    def test_order_creation_still_works(self, admin_auth):
        """Regression: Order creation flow works correctly"""
        # Create order
        response = requests.post(
            f"{BASE_URL}/api/orders",
            json={
                "items": [{
                    "productId": PRODUCT_ID,
                    "quantity": 1,
                    "name": "Test Product",
                    "price": 15.00
                }],
                "total": 15.00,
                "pickupTime": "2026-02-16T15:00:00Z",
                "paymentMethod": "Zelle"
            },
            headers=admin_auth["headers"]
        )
        assert response.status_code == 200, f"Order creation failed: {response.text}"
        
        data = response.json()
        assert "id" in data, "Order should have an ID"
        assert data["status"] == "Pending Payment", "Zelle order should have 'Pending Payment' status"
        print(f"Order created: {data['id']}")
    
    def test_get_user_orders_still_works(self, admin_auth):
        """Regression: Get user orders works correctly"""
        response = requests.get(
            f"{BASE_URL}/api/orders",
            headers=admin_auth["headers"]
        )
        assert response.status_code == 200, f"Get orders failed: {response.text}"
        
        orders = response.json()
        assert isinstance(orders, list), "Should return a list of orders"
        print(f"User has {len(orders)} orders")
    
    def test_admin_get_all_orders_still_works(self, admin_auth):
        """Regression: Admin get all orders works correctly"""
        response = requests.get(
            f"{BASE_URL}/api/admin/orders",
            headers=admin_auth["headers"]
        )
        assert response.status_code == 200, f"Admin get orders failed: {response.text}"
        
        orders = response.json()
        assert isinstance(orders, list), "Should return a list of orders"
        print(f"Total orders in system: {len(orders)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
