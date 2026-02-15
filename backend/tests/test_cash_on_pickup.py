"""
Test Cash on Pickup payment method functionality
- Order creation with 'Cash on Pickup' sets status 'Awaiting Pickup (Cash)'
- Order creation with other methods sets status 'Pending Payment'
- Admin can mark 'Awaiting Pickup (Cash)' orders as 'Paid' and points are awarded
- Admin can mark 'Pending Payment' orders as 'Paid' (regression)
- Cloudz ledger entry created when Cash on Pickup order marked Paid
- No points awarded at order creation time for Cash on Pickup
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

class TestCashOnPickupOrders:
    """Test Cash on Pickup payment method for orders"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed - cannot proceed with tests")
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Create or login test user"""
        # Try to login first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "testcashpickup@test.com",
            "password": "TestPass123!"
        })
        if login_resp.status_code == 200:
            return login_resp.json()["access_token"], login_resp.json()["user"]["id"]
        
        # Register new user
        register_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "testcashpickup@test.com",
            "password": "TestPass123!",
            "firstName": "CashTest",
            "lastName": "User",
            "dateOfBirth": "2000-01-01"
        })
        if register_resp.status_code != 200:
            pytest.skip("Could not create test user")
        return register_resp.json()["access_token"], register_resp.json()["user"]["id"]
    
    @pytest.fixture(scope="class")
    def test_product_id(self, admin_token):
        """Get or create a test product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        products_resp = requests.get(f"{BASE_URL}/api/products", headers=headers)
        if products_resp.status_code == 200 and len(products_resp.json()) > 0:
            return products_resp.json()[0]["id"]
        pytest.skip("No products available for testing")
    
    def test_cash_on_pickup_order_creates_awaiting_status(self, test_user_token, test_product_id):
        """Test that Cash on Pickup orders get 'Awaiting Pickup (Cash)' status"""
        token, user_id = test_user_token
        headers = {"Authorization": f"Bearer {token}"}
        
        order_data = {
            "items": [{
                "productId": test_product_id,
                "quantity": 1,
                "name": "Test Product",
                "price": 15.00
            }],
            "total": 15.00,
            "pickupTime": "Today - 12:00 PM - 2:00 PM",
            "paymentMethod": "Cash on Pickup"
        }
        
        response = requests.post(f"{BASE_URL}/api/orders", json=order_data, headers=headers)
        assert response.status_code == 200, f"Order creation failed: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain order id"
        assert data["status"] == "Awaiting Pickup (Cash)", f"Status should be 'Awaiting Pickup (Cash)', got '{data['status']}'"
        assert data["paymentMethod"] == "Cash on Pickup"
        assert data["loyaltyPointsEarned"] == 15  # Points calculated but not awarded yet
        
        print(f"✓ Cash on Pickup order created with status: {data['status']}")
        return data["id"]
    
    def test_zelle_order_creates_pending_status(self, test_user_token, test_product_id):
        """Regression: Zelle orders still get 'Pending Payment' status"""
        token, user_id = test_user_token
        headers = {"Authorization": f"Bearer {token}"}
        
        order_data = {
            "items": [{
                "productId": test_product_id,
                "quantity": 1,
                "name": "Test Product",
                "price": 20.00
            }],
            "total": 20.00,
            "pickupTime": "Today - 2:00 PM - 4:00 PM",
            "paymentMethod": "Zelle"
        }
        
        response = requests.post(f"{BASE_URL}/api/orders", json=order_data, headers=headers)
        assert response.status_code == 200, f"Order creation failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "Pending Payment", f"Status should be 'Pending Payment', got '{data['status']}'"
        assert data["paymentMethod"] == "Zelle"
        
        print(f"✓ Zelle order created with status: {data['status']}")
        return data["id"]
    
    def test_venmo_order_creates_pending_status(self, test_user_token, test_product_id):
        """Regression: Venmo orders still get 'Pending Payment' status"""
        token, user_id = test_user_token
        headers = {"Authorization": f"Bearer {token}"}
        
        order_data = {
            "items": [{
                "productId": test_product_id,
                "quantity": 1,
                "name": "Test Product",
                "price": 25.00
            }],
            "total": 25.00,
            "pickupTime": "Today - 4:00 PM - 6:00 PM",
            "paymentMethod": "Venmo"
        }
        
        response = requests.post(f"{BASE_URL}/api/orders", json=order_data, headers=headers)
        assert response.status_code == 200, f"Order creation failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "Pending Payment", f"Status should be 'Pending Payment', got '{data['status']}'"
        
        print(f"✓ Venmo order created with status: {data['status']}")


class TestAdminOrderStatusTransitions:
    """Test admin marking orders as Paid"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def test_user_setup(self):
        """Create test user and get initial state"""
        # Register new user with unique email
        unique_suffix = int(time.time())
        email = f"testpaiduser{unique_suffix}@test.com"
        
        register_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "PaidTest",
            "lastName": "User",
            "dateOfBirth": "2000-01-01"
        })
        if register_resp.status_code != 200:
            pytest.skip(f"Could not create test user: {register_resp.text}")
        
        data = register_resp.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"],
            "initial_points": data["user"]["loyaltyPoints"]
        }
    
    @pytest.fixture(scope="class")
    def test_product_id(self, admin_token):
        """Get a test product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        products_resp = requests.get(f"{BASE_URL}/api/products", headers=headers)
        if products_resp.status_code == 200 and len(products_resp.json()) > 0:
            return products_resp.json()[0]["id"]
        pytest.skip("No products available")
    
    def test_admin_marks_cash_on_pickup_as_paid_awards_points(self, admin_token, test_user_setup, test_product_id):
        """Test that admin can mark Cash on Pickup order as Paid and points are awarded"""
        user_token = test_user_setup["token"]
        user_id = test_user_setup["user_id"]
        initial_points = test_user_setup["initial_points"]
        
        user_headers = {"Authorization": f"Bearer {user_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create Cash on Pickup order
        order_data = {
            "items": [{
                "productId": test_product_id,
                "quantity": 1,
                "name": "Test Product",
                "price": 30.00
            }],
            "total": 30.00,
            "pickupTime": "Today - 12:00 PM - 2:00 PM",
            "paymentMethod": "Cash on Pickup"
        }
        
        order_resp = requests.post(f"{BASE_URL}/api/orders", json=order_data, headers=user_headers)
        assert order_resp.status_code == 200
        order_id = order_resp.json()["id"]
        expected_points = order_resp.json()["loyaltyPointsEarned"]
        
        # Check user points before admin marks as Paid
        me_before = requests.get(f"{BASE_URL}/api/auth/me", headers=user_headers)
        points_before = me_before.json()["loyaltyPoints"]
        
        # Admin marks as Paid
        status_resp = requests.patch(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": "Paid"},
            headers=admin_headers
        )
        assert status_resp.status_code == 200, f"Admin status update failed: {status_resp.text}"
        
        # Check user points after
        me_after = requests.get(f"{BASE_URL}/api/auth/me", headers=user_headers)
        points_after = me_after.json()["loyaltyPoints"]
        
        assert points_after == points_before + expected_points, \
            f"Points should increase by {expected_points}. Before: {points_before}, After: {points_after}"
        
        print(f"✓ Admin marked Cash on Pickup order as Paid, points awarded: {expected_points}")
        return order_id
    
    def test_admin_marks_pending_payment_as_paid_regression(self, admin_token, test_user_setup, test_product_id):
        """Regression: Admin can still mark 'Pending Payment' orders as Paid"""
        user_token = test_user_setup["token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create Zelle order (Pending Payment status)
        order_data = {
            "items": [{
                "productId": test_product_id,
                "quantity": 1,
                "name": "Test Product",
                "price": 35.00
            }],
            "total": 35.00,
            "pickupTime": "Tomorrow - 10:00 AM - 12:00 PM",
            "paymentMethod": "Zelle"
        }
        
        order_resp = requests.post(f"{BASE_URL}/api/orders", json=order_data, headers=user_headers)
        assert order_resp.status_code == 200
        order_id = order_resp.json()["id"]
        assert order_resp.json()["status"] == "Pending Payment"
        
        # Admin marks as Paid
        status_resp = requests.patch(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": "Paid"},
            headers=admin_headers
        )
        assert status_resp.status_code == 200, f"Admin status update failed: {status_resp.text}"
        
        print(f"✓ Admin marked Pending Payment order as Paid (regression OK)")


class TestCloudzLedger:
    """Test Cloudz ledger entries for Cash on Pickup"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def test_user_for_ledger(self):
        """Create unique test user for ledger test"""
        unique_suffix = int(time.time())
        email = f"testledger{unique_suffix}@test.com"
        
        register_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "LedgerTest",
            "lastName": "User",
            "dateOfBirth": "2000-01-01"
        })
        if register_resp.status_code != 200:
            pytest.skip(f"Could not create ledger test user: {register_resp.text}")
        
        data = register_resp.json()
        return {"token": data["access_token"], "user_id": data["user"]["id"]}
    
    @pytest.fixture(scope="class")
    def test_product_id(self, admin_token):
        """Get a test product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        products_resp = requests.get(f"{BASE_URL}/api/products", headers=headers)
        if products_resp.status_code == 200 and len(products_resp.json()) > 0:
            return products_resp.json()[0]["id"]
        pytest.skip("No products available")
    
    def test_no_ledger_entry_on_order_creation(self, test_user_for_ledger, test_product_id):
        """Test that no ledger entry is created when Cash on Pickup order is placed"""
        token = test_user_for_ledger["token"]
        user_id = test_user_for_ledger["user_id"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get ledger entries before order
        ledger_before = requests.get(f"{BASE_URL}/api/loyalty/ledger", headers=headers)
        entries_before = len(ledger_before.json()) if ledger_before.status_code == 200 else 0
        
        # Create Cash on Pickup order
        order_data = {
            "items": [{
                "productId": test_product_id,
                "quantity": 1,
                "name": "Test Product",
                "price": 40.00
            }],
            "total": 40.00,
            "pickupTime": "Today - 12:00 PM - 2:00 PM",
            "paymentMethod": "Cash on Pickup"
        }
        
        order_resp = requests.post(f"{BASE_URL}/api/orders", json=order_data, headers=headers)
        assert order_resp.status_code == 200
        
        # Get ledger entries after order
        ledger_after = requests.get(f"{BASE_URL}/api/loyalty/ledger", headers=headers)
        entries_after = len(ledger_after.json()) if ledger_after.status_code == 200 else 0
        
        # No new purchase_reward entry should be created at order time
        purchase_entries_after = [e for e in ledger_after.json() if e.get("type") == "purchase_reward"]
        
        assert entries_after == entries_before, \
            f"No ledger entry should be created on order creation. Before: {entries_before}, After: {entries_after}"
        
        print(f"✓ No ledger entry created on Cash on Pickup order creation")
        return order_resp.json()["id"]
    
    def test_ledger_entry_created_when_marked_paid(self, admin_token, test_user_for_ledger, test_product_id):
        """Test that ledger entry is created when Cash on Pickup order is marked Paid"""
        user_token = test_user_for_ledger["token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create Cash on Pickup order
        order_data = {
            "items": [{
                "productId": test_product_id,
                "quantity": 1,
                "name": "Test Product",
                "price": 50.00
            }],
            "total": 50.00,
            "pickupTime": "Tomorrow - 12:00 PM - 2:00 PM",
            "paymentMethod": "Cash on Pickup"
        }
        
        order_resp = requests.post(f"{BASE_URL}/api/orders", json=order_data, headers=user_headers)
        assert order_resp.status_code == 200
        order_id = order_resp.json()["id"]
        expected_points = order_resp.json()["loyaltyPointsEarned"]
        
        # Get ledger before marking paid
        ledger_before = requests.get(f"{BASE_URL}/api/loyalty/ledger", headers=user_headers)
        purchase_entries_before = [e for e in ledger_before.json() if e.get("type") == "purchase_reward"]
        
        # Admin marks as Paid
        status_resp = requests.patch(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": "Paid"},
            headers=admin_headers
        )
        assert status_resp.status_code == 200
        
        # Get ledger after marking paid
        ledger_after = requests.get(f"{BASE_URL}/api/loyalty/ledger", headers=user_headers)
        purchase_entries_after = [e for e in ledger_after.json() if e.get("type") == "purchase_reward"]
        
        # Should have one more purchase_reward entry
        assert len(purchase_entries_after) > len(purchase_entries_before), \
            f"Should have new purchase_reward ledger entry after marking Paid"
        
        # Verify the new entry details
        new_entry = purchase_entries_after[0]  # Most recent first
        assert new_entry["type"] == "purchase_reward"
        assert new_entry["amount"] == expected_points
        assert order_id[:8] in new_entry.get("reference", "")
        
        print(f"✓ Ledger entry 'purchase_reward' created when Cash on Pickup order marked Paid")


class TestNoPointsAtOrderCreation:
    """Test that no points are awarded at order creation for Cash on Pickup"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def fresh_test_user(self):
        """Create fresh user to verify points are not awarded on order creation"""
        unique_suffix = int(time.time())
        email = f"freshuser{unique_suffix}@test.com"
        
        register_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "Fresh",
            "lastName": "User",
            "dateOfBirth": "2000-01-01"
        })
        if register_resp.status_code != 200:
            pytest.skip("Could not create fresh test user")
        
        data = register_resp.json()
        return {"token": data["access_token"], "user_id": data["user"]["id"]}
    
    @pytest.fixture(scope="class")
    def test_product_id(self, admin_token):
        """Get a test product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        products_resp = requests.get(f"{BASE_URL}/api/products", headers=headers)
        if products_resp.status_code == 200 and len(products_resp.json()) > 0:
            return products_resp.json()[0]["id"]
        pytest.skip("No products available")
    
    def test_user_points_unchanged_on_cash_on_pickup_order(self, fresh_test_user, test_product_id):
        """Test that user points are NOT increased when placing Cash on Pickup order"""
        token = fresh_test_user["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get points before order
        me_before = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        points_before = me_before.json()["loyaltyPoints"]
        
        # Create Cash on Pickup order
        order_data = {
            "items": [{
                "productId": test_product_id,
                "quantity": 1,
                "name": "Test Product",
                "price": 100.00
            }],
            "total": 100.00,
            "pickupTime": "Today - 12:00 PM - 2:00 PM",
            "paymentMethod": "Cash on Pickup"
        }
        
        order_resp = requests.post(f"{BASE_URL}/api/orders", json=order_data, headers=headers)
        assert order_resp.status_code == 200
        
        # Verify order has loyaltyPointsEarned calculated
        assert order_resp.json()["loyaltyPointsEarned"] == 100, \
            "Order should have loyaltyPointsEarned calculated"
        
        # Get points after order - should be unchanged
        me_after = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        points_after = me_after.json()["loyaltyPoints"]
        
        assert points_after == points_before, \
            f"Points should NOT increase on order creation. Before: {points_before}, After: {points_after}"
        
        print(f"✓ User points unchanged on Cash on Pickup order creation (points awarded only on Paid)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
