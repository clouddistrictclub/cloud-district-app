"""
Test suite for Cloud District Club Loyalty Tier System
Tests the new Cloudz tier-based redemption system with 5 tiers:
- Bronze Cloud (1000pts/$5), Silver Storm (5000pts/$30), Gold Thunder (10000pts/$75)
- Platinum Haze (20000pts/$175), Diamond Sky (30000pts/$300)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials
ADMIN_EMAIL = "admin@clouddistrictclub.com"
ADMIN_PASSWORD = "Admin123!"

# Test user credentials (will be created)
TEST_USER_PREFIX = "TEST_loyalty_"


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


@pytest.fixture(scope="module")
def test_user(api_client):
    """Create a test user with sufficient points for testing"""
    unique_id = str(uuid.uuid4())[:8]
    email = f"{TEST_USER_PREFIX}{unique_id}@test.com"
    response = api_client.post(f"{BASE_URL}/api/auth/register", json={
        "email": email,
        "password": "TestPass123!",
        "firstName": "Test",
        "lastName": "User",
        "dateOfBirth": "1990-01-01",
        "phone": None
    })
    assert response.status_code == 200, f"Test user registration failed: {response.text}"
    data = response.json()
    return {
        "token": data["access_token"],
        "user": data["user"],
        "email": email,
        "password": "TestPass123!"
    }


@pytest.fixture(scope="module")
def test_user_headers(test_user):
    """Headers with test user auth token"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {test_user['token']}"
    }


class TestHealthCheck:
    """Health and basic connectivity tests"""
    
    def test_api_accessible(self, api_client):
        """Test that API is accessible"""
        response = api_client.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200


class TestLoyaltyTiersEndpoint:
    """Tests for GET /api/loyalty/tiers endpoint"""
    
    def test_get_tiers_authenticated(self, api_client, admin_headers, admin_auth):
        """Test getting tiers returns all 5 tiers with correct data"""
        response = api_client.get(f"{BASE_URL}/api/loyalty/tiers", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "userPoints" in data
        assert "tiers" in data
        
        # Verify 5 tiers
        tiers = data["tiers"]
        assert len(tiers) == 5, f"Expected 5 tiers, got {len(tiers)}"
        
        # Verify tier structure
        expected_tiers = [
            {"id": "tier_1", "name": "Bronze Cloud", "pointsRequired": 1000, "reward": 5.00},
            {"id": "tier_2", "name": "Silver Storm", "pointsRequired": 5000, "reward": 30.00},
            {"id": "tier_3", "name": "Gold Thunder", "pointsRequired": 10000, "reward": 75.00},
            {"id": "tier_4", "name": "Platinum Haze", "pointsRequired": 20000, "reward": 175.00},
            {"id": "tier_5", "name": "Diamond Sky", "pointsRequired": 30000, "reward": 300.00},
        ]
        
        for i, tier in enumerate(tiers):
            assert tier["id"] == expected_tiers[i]["id"]
            assert tier["name"] == expected_tiers[i]["name"]
            assert tier["pointsRequired"] == expected_tiers[i]["pointsRequired"]
            assert tier["reward"] == expected_tiers[i]["reward"]
            assert "unlocked" in tier
            assert "pointsNeeded" in tier
    
    def test_tiers_unlock_status_based_on_points(self, api_client, admin_headers, admin_auth):
        """Test that tiers show correct unlock status based on user points"""
        response = api_client.get(f"{BASE_URL}/api/loyalty/tiers", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        user_points = data["userPoints"]
        
        # Admin has 6500 points - Bronze (1000) and Silver (5000) should be unlocked
        for tier in data["tiers"]:
            if tier["pointsRequired"] <= user_points:
                assert tier["unlocked"] is True, f"{tier['name']} should be unlocked with {user_points} points"
                assert tier["pointsNeeded"] == 0
            else:
                assert tier["unlocked"] is False, f"{tier['name']} should be locked with {user_points} points"
                assert tier["pointsNeeded"] == tier["pointsRequired"] - user_points
    
    def test_tiers_requires_auth(self, api_client):
        """Test that tiers endpoint requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/loyalty/tiers")
        assert response.status_code in [401, 403]


class TestLoyaltyRedeemEndpoint:
    """Tests for POST /api/loyalty/redeem endpoint"""
    
    def test_redeem_invalid_tier(self, api_client, admin_headers):
        """Test redeeming an invalid tier ID returns error"""
        response = api_client.post(f"{BASE_URL}/api/loyalty/redeem", 
                                   json={"tierId": "invalid_tier"},
                                   headers=admin_headers)
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()
    
    def test_redeem_insufficient_points(self, api_client, test_user_headers):
        """Test redeeming tier with insufficient points fails"""
        # Test user has 0 points, try to redeem Bronze Cloud (1000 pts)
        response = api_client.post(f"{BASE_URL}/api/loyalty/redeem",
                                   json={"tierId": "tier_1"},
                                   headers=test_user_headers)
        assert response.status_code == 400
        assert "not enough points" in response.json().get("detail", "").lower()
    
    def test_redeem_requires_auth(self, api_client):
        """Test that redeem endpoint requires authentication"""
        response = api_client.post(f"{BASE_URL}/api/loyalty/redeem",
                                   json={"tierId": "tier_1"})
        assert response.status_code in [401, 403]


class TestLoyaltyRewardsEndpoint:
    """Tests for GET /api/loyalty/rewards endpoint"""
    
    def test_get_active_rewards(self, api_client, admin_headers):
        """Test getting active (unused) rewards"""
        response = api_client.get(f"{BASE_URL}/api/loyalty/rewards", headers=admin_headers)
        assert response.status_code == 200
        
        rewards = response.json()
        assert isinstance(rewards, list)
        
        # Verify reward structure if any rewards exist
        if len(rewards) > 0:
            reward = rewards[0]
            assert "id" in reward
            assert "tierId" in reward
            assert "tierName" in reward
            assert "rewardAmount" in reward
            assert "pointsSpent" in reward
    
    def test_rewards_requires_auth(self, api_client):
        """Test that rewards endpoint requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/loyalty/rewards")
        assert response.status_code in [401, 403]


class TestLoyaltyHistoryEndpoint:
    """Tests for GET /api/loyalty/history endpoint"""
    
    def test_get_redemption_history(self, api_client, admin_headers):
        """Test getting redemption history"""
        response = api_client.get(f"{BASE_URL}/api/loyalty/history", headers=admin_headers)
        assert response.status_code == 200
        
        history = response.json()
        assert isinstance(history, list)
        
        # Verify history item structure if any exists
        if len(history) > 0:
            item = history[0]
            assert "id" in item
            assert "tierId" in item
            assert "tierName" in item
            assert "rewardAmount" in item
            assert "pointsSpent" in item
            assert "used" in item
            assert "createdAt" in item
    
    def test_history_requires_auth(self, api_client):
        """Test that history endpoint requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/loyalty/history")
        assert response.status_code in [401, 403]


class TestOrderWithReward:
    """Tests for POST /api/orders with rewardId integration"""
    
    def test_order_endpoint_accepts_reward_id(self, api_client, admin_headers):
        """Test that order endpoint accepts rewardId parameter"""
        # First check if there are any products
        products_response = api_client.get(f"{BASE_URL}/api/products", headers=admin_headers)
        if products_response.status_code != 200 or len(products_response.json()) == 0:
            pytest.skip("No products available for order testing")
        
        products = products_response.json()
        product = products[0]
        
        # Get active rewards
        rewards_response = api_client.get(f"{BASE_URL}/api/loyalty/rewards", headers=admin_headers)
        assert rewards_response.status_code == 200
        rewards = rewards_response.json()
        
        reward_id = rewards[0]["id"] if len(rewards) > 0 else None
        
        # Test order creation with rewardId (may fail due to other validation)
        order_data = {
            "items": [{
                "productId": product["id"],
                "quantity": 1,
                "name": product["name"],
                "price": product["price"]
            }],
            "total": product["price"],
            "pickupTime": "Today - 12:00 PM - 2:00 PM",
            "paymentMethod": "Zelle",
            "rewardId": reward_id
        }
        
        response = api_client.post(f"{BASE_URL}/api/orders", json=order_data, headers=admin_headers)
        # Should either succeed or fail with inventory/validation error, not schema error
        assert response.status_code in [200, 201, 400, 404], f"Unexpected status: {response.status_code}"


class TestRedeemAndVerifyFlow:
    """End-to-end test of redeeming a tier and verifying points deduction"""
    
    def test_admin_redeem_silver_storm_if_possible(self, api_client, admin_headers, admin_auth):
        """Test full redemption flow for admin user"""
        # Get current points
        tiers_response = api_client.get(f"{BASE_URL}/api/loyalty/tiers", headers=admin_headers)
        assert tiers_response.status_code == 200
        
        initial_points = tiers_response.json()["userPoints"]
        
        # Admin has 6500 points - can redeem Silver Storm (5000 pts) or Bronze Cloud (1000 pts)
        # First check if already has an active reward
        rewards_response = api_client.get(f"{BASE_URL}/api/loyalty/rewards", headers=admin_headers)
        active_rewards = rewards_response.json()
        
        # Try to redeem Bronze Cloud if not already active
        bronze_active = any(r["tierId"] == "tier_1" for r in active_rewards)
        silver_active = any(r["tierId"] == "tier_2" for r in active_rewards)
        
        if initial_points >= 1000 and not bronze_active:
            # Redeem Bronze Cloud
            redeem_response = api_client.post(f"{BASE_URL}/api/loyalty/redeem",
                                              json={"tierId": "tier_1"},
                                              headers=admin_headers)
            
            if redeem_response.status_code == 200:
                data = redeem_response.json()
                assert data["rewardAmount"] == 5.00
                assert data["pointsSpent"] == 1000
                assert data["remainingPoints"] == initial_points - 1000
                
                # Verify reward was created
                rewards_response = api_client.get(f"{BASE_URL}/api/loyalty/rewards", headers=admin_headers)
                rewards = rewards_response.json()
                bronze_reward = next((r for r in rewards if r["tierId"] == "tier_1"), None)
                assert bronze_reward is not None, "Bronze reward should be active"
                
        elif initial_points >= 5000 and not silver_active and not bronze_active:
            # Redeem Silver Storm
            redeem_response = api_client.post(f"{BASE_URL}/api/loyalty/redeem",
                                              json={"tierId": "tier_2"},
                                              headers=admin_headers)
            
            if redeem_response.status_code == 200:
                data = redeem_response.json()
                assert data["rewardAmount"] == 30.00
                assert data["pointsSpent"] == 5000
    
    def test_prevent_duplicate_tier_redemption(self, api_client, admin_headers):
        """Test that user cannot redeem same tier twice if already active"""
        # Get active rewards
        rewards_response = api_client.get(f"{BASE_URL}/api/loyalty/rewards", headers=admin_headers)
        active_rewards = rewards_response.json()
        
        if len(active_rewards) > 0:
            # Try to redeem same tier again
            active_tier_id = active_rewards[0]["tierId"]
            redeem_response = api_client.post(f"{BASE_URL}/api/loyalty/redeem",
                                              json={"tierId": active_tier_id},
                                              headers=admin_headers)
            assert redeem_response.status_code == 400
            assert "already have an active reward" in redeem_response.json().get("detail", "").lower()


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_login_success(self, api_client):
        """Test successful login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["isAdmin"] is True
    
    def test_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@email.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401
    
    def test_get_me_authenticated(self, api_client, admin_headers):
        """Test getting current user info"""
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == ADMIN_EMAIL
        assert "loyaltyPoints" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
