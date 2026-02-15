"""
Test suite for Cloud District Club Referral Program - Phase 1
Tests the referral system features:
- Register without referral code: auto-generates referralCode
- Register with valid referral code: stores referredBy
- Register with invalid referral code: returns 400
- Login/Me endpoints return referralCode, referralCount, referralRewardsEarned
- Referral reward triggers on first paid order (referrer +2000, referred +1000)
- Referral reward does NOT re-trigger on second paid order
- referralRewardIssued flag prevents double rewards
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials (referrer for testing)
ADMIN_EMAIL = "admin@clouddistrictclub.com"
ADMIN_PASSWORD = "Admin123!"
ADMIN_REFERRAL_CODE = "STAV20H"

# Test user prefix
TEST_USER_PREFIX = "TEST_referral_"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_auth(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    return {
        "token": data["access_token"],
        "user": data["user"]
    }


@pytest.fixture(scope="module")
def admin_headers(admin_auth):
    """Headers with admin auth token"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_auth['token']}"
    }


class TestRegisterWithoutReferralCode:
    """Test registration without referral code - should auto-generate referralCode"""
    
    def test_register_without_referral_code_success(self, api_client):
        """Test registering without referral code succeeds and auto-generates referralCode"""
        unique_id = str(uuid.uuid4())[:8]
        email = f"{TEST_USER_PREFIX}noref_{unique_id}@test.com"
        
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "NoRef",
            "lastName": "User",
            "dateOfBirth": "1990-01-01"
        })
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "user" in data
        
        user = data["user"]
        assert user["email"] == email
        
        # CRITICAL: Verify referralCode was auto-generated
        assert "referralCode" in user, "referralCode should be in user response"
        assert user["referralCode"] is not None, "referralCode should not be None"
        assert len(user["referralCode"]) == 7, f"referralCode should be 7 chars, got {len(user['referralCode'])}"
        assert user["referralCode"].isalnum(), "referralCode should be alphanumeric"
        
        # Verify referral stats are initialized
        assert user.get("referralCount", 0) == 0
        assert user.get("referralRewardsEarned", 0) == 0
        
        print(f"[PASS] User registered without referral code. Auto-generated code: {user['referralCode']}")


class TestRegisterWithValidReferralCode:
    """Test registration with valid referral code - should store referredBy"""
    
    def test_register_with_admin_referral_code_success(self, api_client, admin_auth):
        """Test registering with admin's referral code succeeds"""
        unique_id = str(uuid.uuid4())[:8]
        email = f"{TEST_USER_PREFIX}withref_{unique_id}@test.com"
        
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "WithRef",
            "lastName": "User",
            "dateOfBirth": "1990-01-01",
            "referralCode": ADMIN_REFERRAL_CODE
        })
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        
        user = data["user"]
        assert user["email"] == email
        
        # User should have their own referral code (not the one they used)
        assert "referralCode" in user
        assert user["referralCode"] is not None
        assert user["referralCode"] != ADMIN_REFERRAL_CODE, "User's referralCode should be different from referrer's"
        
        print(f"[PASS] User registered with referral code {ADMIN_REFERRAL_CODE}. User's own code: {user['referralCode']}")
        
        return {
            "token": data["access_token"],
            "user": user,
            "email": email
        }
    
    def test_register_with_lowercase_referral_code(self, api_client):
        """Test that referral code matching is case-insensitive"""
        unique_id = str(uuid.uuid4())[:8]
        email = f"{TEST_USER_PREFIX}lowercase_{unique_id}@test.com"
        
        # Try with lowercase version of admin's code
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "Lower",
            "lastName": "Case",
            "dateOfBirth": "1990-01-01",
            "referralCode": ADMIN_REFERRAL_CODE.lower()
        })
        
        assert response.status_code == 200, f"Registration with lowercase code failed: {response.text}"
        print("[PASS] Referral code matching is case-insensitive")


class TestRegisterWithInvalidReferralCode:
    """Test registration with invalid referral code - should return 400"""
    
    def test_register_with_invalid_referral_code_fails(self, api_client):
        """Test registering with invalid referral code returns 400"""
        unique_id = str(uuid.uuid4())[:8]
        email = f"{TEST_USER_PREFIX}invalid_{unique_id}@test.com"
        
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "Invalid",
            "lastName": "Code",
            "dateOfBirth": "1990-01-01",
            "referralCode": "INVALID123"  # Non-existent code
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "Invalid referral code" in data.get("detail", ""), f"Expected 'Invalid referral code' error, got: {data}"
        
        print("[PASS] Invalid referral code returns 400 'Invalid referral code'")
    
    def test_register_with_random_string_referral_code(self, api_client):
        """Test registering with random string referral code returns 400"""
        unique_id = str(uuid.uuid4())[:8]
        email = f"{TEST_USER_PREFIX}random_{unique_id}@test.com"
        
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "Random",
            "lastName": "String",
            "dateOfBirth": "1990-01-01",
            "referralCode": "ZZZZZZZ"
        })
        
        assert response.status_code == 400
        print("[PASS] Random referral code returns 400")


class TestLoginReturnsReferralFields:
    """Test that login returns referralCode, referralCount, referralRewardsEarned"""
    
    def test_login_returns_referral_fields(self, api_client):
        """Test login response includes all referral fields"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        assert response.status_code == 200
        data = response.json()
        user = data["user"]
        
        # CRITICAL: Verify all referral fields are present
        assert "referralCode" in user, "referralCode should be in login response"
        assert "referralCount" in user, "referralCount should be in login response"
        assert "referralRewardsEarned" in user, "referralRewardsEarned should be in login response"
        
        # Admin's referral code should be STAV20H
        assert user["referralCode"] == ADMIN_REFERRAL_CODE, f"Expected {ADMIN_REFERRAL_CODE}, got {user['referralCode']}"
        
        # Verify they are correct types
        assert isinstance(user["referralCount"], int)
        assert isinstance(user["referralRewardsEarned"], int)
        
        print(f"[PASS] Login returns referralCode={user['referralCode']}, referralCount={user['referralCount']}, referralRewardsEarned={user['referralRewardsEarned']}")


class TestGetMeReturnsReferralFields:
    """Test that GET /api/auth/me returns referralCode, referralCount, referralRewardsEarned"""
    
    def test_me_returns_referral_fields(self, api_client, admin_headers):
        """Test /api/auth/me response includes all referral fields"""
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        
        assert response.status_code == 200
        user = response.json()
        
        # CRITICAL: Verify all referral fields are present
        assert "referralCode" in user, "referralCode should be in /me response"
        assert "referralCount" in user, "referralCount should be in /me response"
        assert "referralRewardsEarned" in user, "referralRewardsEarned should be in /me response"
        
        print(f"[PASS] GET /me returns referralCode={user['referralCode']}, referralCount={user['referralCount']}, referralRewardsEarned={user['referralRewardsEarned']}")


class TestReferralRewardFlow:
    """Test full referral reward flow: register with code, create order, mark paid, verify rewards"""
    
    def test_full_referral_reward_flow(self, api_client, admin_headers, admin_auth):
        """
        Test complete referral reward flow:
        1. Register new user with admin's referral code
        2. Create order for that user
        3. Admin marks order as Paid
        4. Verify referrer gets +2000 Cloudz and referralCount increases
        5. Verify referred user gets +1000 Cloudz
        """
        # Step 1: Get admin's initial state
        admin_me_before = api_client.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert admin_me_before.status_code == 200
        admin_before = admin_me_before.json()
        admin_initial_points = admin_before["loyaltyPoints"]
        admin_initial_count = admin_before.get("referralCount", 0)
        admin_initial_earned = admin_before.get("referralRewardsEarned", 0)
        
        print(f"Admin initial state: points={admin_initial_points}, referralCount={admin_initial_count}, referralRewardsEarned={admin_initial_earned}")
        
        # Step 2: Register new user with admin's referral code
        unique_id = str(uuid.uuid4())[:8]
        email = f"{TEST_USER_PREFIX}reward_flow_{unique_id}@test.com"
        
        register_response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "RewardFlow",
            "lastName": "User",
            "dateOfBirth": "1990-01-01",
            "referralCode": ADMIN_REFERRAL_CODE
        })
        
        assert register_response.status_code == 200, f"Registration failed: {register_response.text}"
        new_user_data = register_response.json()
        new_user_token = new_user_data["access_token"]
        new_user = new_user_data["user"]
        new_user_id = new_user["id"]
        new_user_initial_points = new_user["loyaltyPoints"]
        new_user_headers = {"Authorization": f"Bearer {new_user_token}", "Content-Type": "application/json"}
        
        print(f"New user registered: id={new_user_id}, points={new_user_initial_points}")
        
        # Step 3: Get a product to create an order
        products_response = api_client.get(f"{BASE_URL}/api/products", headers=admin_headers)
        assert products_response.status_code == 200, "Failed to get products"
        products = products_response.json()
        
        if len(products) == 0:
            pytest.skip("No products available for order testing")
        
        product = products[0]
        
        # Step 4: Create order for new user
        order_data = {
            "items": [{
                "productId": product["id"],
                "quantity": 1,
                "name": product["name"],
                "price": product["price"]
            }],
            "total": product["price"],
            "pickupTime": "Today - 12:00 PM - 2:00 PM",
            "paymentMethod": "Zelle"
        }
        
        order_response = api_client.post(f"{BASE_URL}/api/orders", json=order_data, headers=new_user_headers)
        assert order_response.status_code in [200, 201], f"Order creation failed: {order_response.text}"
        order = order_response.json()
        order_id = order["id"]
        
        print(f"Order created: id={order_id}, status={order['status']}")
        
        # Step 5: Admin marks order as Paid (triggers referral reward)
        status_response = api_client.patch(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": "Paid"},
            headers=admin_headers
        )
        assert status_response.status_code == 200, f"Status update failed: {status_response.text}"
        
        print("Order marked as Paid - referral rewards should trigger")
        
        # Step 6: Verify admin (referrer) got +2000 points and referralCount increased
        admin_me_after = api_client.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert admin_me_after.status_code == 200
        admin_after = admin_me_after.json()
        
        expected_admin_points = admin_initial_points + 2000
        expected_admin_count = admin_initial_count + 1
        expected_admin_earned = admin_initial_earned + 2000
        
        assert admin_after["loyaltyPoints"] == expected_admin_points, \
            f"Admin points: expected {expected_admin_points}, got {admin_after['loyaltyPoints']}"
        assert admin_after["referralCount"] == expected_admin_count, \
            f"Admin referralCount: expected {expected_admin_count}, got {admin_after['referralCount']}"
        assert admin_after["referralRewardsEarned"] == expected_admin_earned, \
            f"Admin referralRewardsEarned: expected {expected_admin_earned}, got {admin_after['referralRewardsEarned']}"
        
        print(f"[PASS] Admin (referrer) got +2000 Cloudz: {admin_initial_points} -> {admin_after['loyaltyPoints']}")
        print(f"[PASS] Admin referralCount increased: {admin_initial_count} -> {admin_after['referralCount']}")
        print(f"[PASS] Admin referralRewardsEarned increased: {admin_initial_earned} -> {admin_after['referralRewardsEarned']}")
        
        # Step 7: Verify new user (referred) got +1000 points + order points
        new_user_me_after = api_client.get(f"{BASE_URL}/api/auth/me", headers=new_user_headers)
        assert new_user_me_after.status_code == 200
        new_user_after = new_user_me_after.json()
        
        # New user gets: order points (int(total)) + 1000 referral bonus
        order_points = int(product["price"])
        expected_new_user_points = new_user_initial_points + order_points + 1000
        
        assert new_user_after["loyaltyPoints"] == expected_new_user_points, \
            f"New user points: expected {expected_new_user_points}, got {new_user_after['loyaltyPoints']}"
        
        print(f"[PASS] New user (referred) got +1000 referral bonus + {order_points} order points: {new_user_initial_points} -> {new_user_after['loyaltyPoints']}")
        
        return {
            "order_id": order_id,
            "new_user_token": new_user_token,
            "new_user_headers": new_user_headers,
            "admin_points_after": admin_after["loyaltyPoints"]
        }


class TestReferralRewardDoesNotRetrigger:
    """Test that referral reward does NOT re-trigger on second paid order"""
    
    def test_second_order_does_not_retrigger_referral_reward(self, api_client, admin_headers, admin_auth):
        """
        Test that referral reward only triggers once per referred user:
        1. Register new user with admin's referral code
        2. Create and pay first order -> rewards trigger
        3. Create and pay second order -> rewards should NOT trigger again
        """
        # Step 1: Get admin's initial state
        admin_me_before = api_client.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        admin_before = admin_me_before.json()
        admin_initial_points = admin_before["loyaltyPoints"]
        admin_initial_count = admin_before.get("referralCount", 0)
        
        # Step 2: Register new user with admin's referral code
        unique_id = str(uuid.uuid4())[:8]
        email = f"{TEST_USER_PREFIX}no_retrigger_{unique_id}@test.com"
        
        register_response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "NoRetrigger",
            "lastName": "User",
            "dateOfBirth": "1990-01-01",
            "referralCode": ADMIN_REFERRAL_CODE
        })
        
        assert register_response.status_code == 200
        new_user_data = register_response.json()
        new_user_token = new_user_data["access_token"]
        new_user_headers = {"Authorization": f"Bearer {new_user_token}", "Content-Type": "application/json"}
        
        # Get products
        products_response = api_client.get(f"{BASE_URL}/api/products", headers=admin_headers)
        products = products_response.json()
        if len(products) == 0:
            pytest.skip("No products available for order testing")
        product = products[0]
        
        # Step 3: Create and pay FIRST order
        order_data = {
            "items": [{
                "productId": product["id"],
                "quantity": 1,
                "name": product["name"],
                "price": product["price"]
            }],
            "total": product["price"],
            "pickupTime": "Today - 12:00 PM - 2:00 PM",
            "paymentMethod": "Zelle"
        }
        
        order1_response = api_client.post(f"{BASE_URL}/api/orders", json=order_data, headers=new_user_headers)
        assert order1_response.status_code in [200, 201]
        order1_id = order1_response.json()["id"]
        
        # Mark first order as Paid
        api_client.patch(
            f"{BASE_URL}/api/admin/orders/{order1_id}/status",
            json={"status": "Paid"},
            headers=admin_headers
        )
        
        # Get admin state after first order
        admin_me_after_first = api_client.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        admin_after_first = admin_me_after_first.json()
        points_after_first = admin_after_first["loyaltyPoints"]
        count_after_first = admin_after_first["referralCount"]
        
        print(f"After first paid order: admin points={points_after_first}, count={count_after_first}")
        
        # Step 4: Create and pay SECOND order
        order2_response = api_client.post(f"{BASE_URL}/api/orders", json=order_data, headers=new_user_headers)
        assert order2_response.status_code in [200, 201]
        order2_id = order2_response.json()["id"]
        
        # Mark second order as Paid
        api_client.patch(
            f"{BASE_URL}/api/admin/orders/{order2_id}/status",
            json={"status": "Paid"},
            headers=admin_headers
        )
        
        # Step 5: Verify admin state did NOT get additional referral rewards
        admin_me_after_second = api_client.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        admin_after_second = admin_me_after_second.json()
        points_after_second = admin_after_second["loyaltyPoints"]
        count_after_second = admin_after_second["referralCount"]
        
        print(f"After second paid order: admin points={points_after_second}, count={count_after_second}")
        
        # CRITICAL: Referral count should NOT have increased again
        assert count_after_second == count_after_first, \
            f"referralCount should not increase on second order: {count_after_first} -> {count_after_second}"
        
        # CRITICAL: Admin should NOT have received another 2000 points
        # (Points should be same as after first order since no referral bonus)
        assert points_after_second == points_after_first, \
            f"Admin should NOT get additional referral bonus: {points_after_first} -> {points_after_second}"
        
        print("[PASS] Referral reward did NOT re-trigger on second paid order")
        print(f"[PASS] referralRewardIssued flag prevented double rewards")


class TestReferralRewardIssuedFlag:
    """Test that referralRewardIssued flag is set after first reward"""
    
    def test_referral_reward_issued_flag_set(self, api_client, admin_headers):
        """Test that referred user has referralRewardIssued=True after reward"""
        # This is an internal check - we can verify via DB or behavior
        # For now, we verify behavior: second order doesn't trigger reward
        
        # Register user with referral code
        unique_id = str(uuid.uuid4())[:8]
        email = f"{TEST_USER_PREFIX}flag_test_{unique_id}@test.com"
        
        register_response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "firstName": "FlagTest",
            "lastName": "User",
            "dateOfBirth": "1990-01-01",
            "referralCode": ADMIN_REFERRAL_CODE
        })
        
        assert register_response.status_code == 200
        new_user_token = register_response.json()["access_token"]
        new_user_headers = {"Authorization": f"Bearer {new_user_token}", "Content-Type": "application/json"}
        
        # Get product
        products = api_client.get(f"{BASE_URL}/api/products", headers=admin_headers).json()
        if not products:
            pytest.skip("No products")
        product = products[0]
        
        # Create first order
        order_data = {
            "items": [{"productId": product["id"], "quantity": 1, "name": product["name"], "price": product["price"]}],
            "total": product["price"],
            "pickupTime": "Today - 12:00 PM - 2:00 PM",
            "paymentMethod": "Zelle"
        }
        
        order1 = api_client.post(f"{BASE_URL}/api/orders", json=order_data, headers=new_user_headers).json()
        
        # Mark first order paid
        api_client.patch(f"{BASE_URL}/api/admin/orders/{order1['id']}/status", json={"status": "Paid"}, headers=admin_headers)
        
        # Get user points after first order
        user_after_first = api_client.get(f"{BASE_URL}/api/auth/me", headers=new_user_headers).json()
        points_after_first = user_after_first["loyaltyPoints"]
        
        # Create second order
        order2 = api_client.post(f"{BASE_URL}/api/orders", json=order_data, headers=new_user_headers).json()
        
        # Mark second order paid
        api_client.patch(f"{BASE_URL}/api/admin/orders/{order2['id']}/status", json={"status": "Paid"}, headers=admin_headers)
        
        # Get user points after second order
        user_after_second = api_client.get(f"{BASE_URL}/api/auth/me", headers=new_user_headers).json()
        points_after_second = user_after_second["loyaltyPoints"]
        
        # User should only get order points on second order (no referral bonus)
        order_points = int(product["price"])
        expected_second = points_after_first + order_points  # Only order points, no +1000
        
        assert points_after_second == expected_second, \
            f"User should not get referral bonus on second order: expected {expected_second}, got {points_after_second}"
        
        print("[PASS] referralRewardIssued flag prevents user from getting multiple referral bonuses")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
