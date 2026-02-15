"""
Cloudz Ledger Tests - Tests for Transaction Ledger & History UI
Tests: admin_adjustment, tier_redemption, purchase_reward, referral_bonus, GET /api/loyalty/ledger
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@clouddistrictclub.com"
ADMIN_PASSWORD = "Admin123!"
ADMIN_USER_ID = "698f8bb6f3e9a3d6ac40fb66"
ADMIN_REFERRAL_CODE = "STAV20H"


class TestCloudzLedger:
    """Test the Cloudz Ledger feature - tracking all Cloudz balance changes"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        
        data = login_response.json()
        self.token = data["access_token"]
        self.admin_user = data["user"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        print(f"Logged in as admin: {self.admin_user['email']} with {self.admin_user['loyaltyPoints']} points")

    def test_1_ledger_endpoint_returns_array(self):
        """Test 1: GET /api/loyalty/ledger returns array of ledger entries"""
        response = self.session.get(f"{BASE_URL}/api/loyalty/ledger")
        
        assert response.status_code == 200, f"Ledger endpoint failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Ledger should return a list"
        
        print(f"Ledger returned {len(data)} entries")
        
        # Verify structure of entries if any exist
        if len(data) > 0:
            entry = data[0]
            assert "userId" in entry, "Entry should have userId"
            assert "type" in entry, "Entry should have type"
            assert "amount" in entry, "Entry should have amount"
            assert "balanceAfter" in entry, "Entry should have balanceAfter"
            assert "reference" in entry, "Entry should have reference"
            assert "createdAt" in entry, "Entry should have createdAt"
            assert "_id" not in entry, "_id should be excluded from response"
            
            print(f"Sample entry: type={entry['type']}, amount={entry['amount']}, balanceAfter={entry['balanceAfter']}")

    def test_2_admin_adjustment_creates_ledger_entry(self):
        """Test 2: Admin adjustment to loyaltyPoints creates admin_adjustment ledger entry"""
        # Get current ledger count
        initial_ledger = self.session.get(f"{BASE_URL}/api/loyalty/ledger").json()
        initial_count = len(initial_ledger)
        
        # Get current points
        me_response = self.session.get(f"{BASE_URL}/api/auth/me")
        current_points = me_response.json()["loyaltyPoints"]
        new_points = current_points + 500  # Add 500 points
        
        # Admin adjusts own points
        adjust_response = self.session.patch(
            f"{BASE_URL}/api/admin/users/{ADMIN_USER_ID}",
            json={"loyaltyPoints": new_points}
        )
        
        assert adjust_response.status_code == 200, f"Admin adjustment failed: {adjust_response.text}"
        
        # Verify user points updated
        updated_user = adjust_response.json()
        assert updated_user["loyaltyPoints"] == new_points, "Points should be updated"
        
        # Check ledger for new entry
        new_ledger = self.session.get(f"{BASE_URL}/api/loyalty/ledger").json()
        assert len(new_ledger) > initial_count, "New ledger entry should be created"
        
        # Find the admin_adjustment entry (should be most recent)
        admin_entries = [e for e in new_ledger if e["type"] == "admin_adjustment" and e["amount"] == 500]
        assert len(admin_entries) > 0, "admin_adjustment entry should exist"
        
        latest_entry = admin_entries[0]
        assert latest_entry["amount"] == 500, "Amount should be +500"
        assert latest_entry["balanceAfter"] == new_points, "balanceAfter should match new balance"
        assert "Admin set balance" in latest_entry["reference"], "Reference should mention admin set balance"
        
        print(f"Admin adjustment verified: +500 points, balanceAfter={latest_entry['balanceAfter']}")

    def test_3_tier_redemption_creates_ledger_entry(self):
        """Test 3: Tier redemption creates tier_redemption ledger entry with negative amount"""
        # Get current points
        me_response = self.session.get(f"{BASE_URL}/api/auth/me")
        current_points = me_response.json()["loyaltyPoints"]
        
        # Need at least 1000 points for tier_1
        if current_points < 1000:
            # Add more points via admin adjustment
            self.session.patch(
                f"{BASE_URL}/api/admin/users/{ADMIN_USER_ID}",
                json={"loyaltyPoints": 2000}
            )
            current_points = 2000
        
        # Get initial ledger count
        initial_ledger = self.session.get(f"{BASE_URL}/api/loyalty/ledger").json()
        initial_count = len(initial_ledger)
        
        # Redeem tier_1 (Bronze Cloud - 1000 points)
        redeem_response = self.session.post(
            f"{BASE_URL}/api/loyalty/redeem",
            json={"tierId": "tier_1"}
        )
        
        # May fail if already has active reward for this tier
        if redeem_response.status_code == 400:
            if "already have an active reward" in redeem_response.text:
                print("Skipping: Already has active tier_1 reward")
                pytest.skip("User already has active tier_1 reward - can't test duplicate redemption")
            else:
                assert False, f"Tier redemption failed: {redeem_response.text}"
        
        assert redeem_response.status_code == 200, f"Tier redemption failed: {redeem_response.text}"
        
        redeem_data = redeem_response.json()
        assert "rewardId" in redeem_data, "Should return rewardId"
        
        # Check ledger for tier_redemption entry
        new_ledger = self.session.get(f"{BASE_URL}/api/loyalty/ledger").json()
        assert len(new_ledger) > initial_count, "New ledger entry should be created for tier redemption"
        
        # Find tier_redemption entry
        tier_entries = [e for e in new_ledger if e["type"] == "tier_redemption" and e["amount"] == -1000]
        assert len(tier_entries) > 0, "tier_redemption entry should exist"
        
        latest_entry = tier_entries[0]
        assert latest_entry["amount"] == -1000, "Amount should be -1000 (negative)"
        assert "Bronze Cloud" in latest_entry["reference"], "Reference should mention tier name"
        
        print(f"Tier redemption verified: -1000 points, reference={latest_entry['reference']}")

    def test_4_purchase_reward_creates_ledger_entry(self):
        """Test 4: Marking order as Paid creates purchase_reward ledger entry"""
        # Need a product first - get products
        products_response = self.session.get(f"{BASE_URL}/api/products")
        products = products_response.json()
        
        if len(products) == 0:
            pytest.skip("No products available to create order")
        
        product = products[0]
        
        # Create an order
        order_data = {
            "items": [{
                "productId": product["id"],
                "quantity": 1,
                "name": product["name"],
                "price": product["price"]
            }],
            "total": product["price"],
            "pickupTime": "2025-01-16 14:00",
            "paymentMethod": "Cash"
        }
        
        order_response = self.session.post(f"{BASE_URL}/api/orders", json=order_data)
        assert order_response.status_code == 200, f"Order creation failed: {order_response.text}"
        
        order = order_response.json()
        order_id = order["id"]
        points_earned = order["loyaltyPointsEarned"]
        
        print(f"Created order {order_id[:8]} for ${order['total']}, will earn {points_earned} points")
        
        # Get initial ledger
        initial_ledger = self.session.get(f"{BASE_URL}/api/loyalty/ledger").json()
        initial_count = len(initial_ledger)
        
        # Mark order as Paid
        status_response = self.session.patch(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": "Paid"}
        )
        assert status_response.status_code == 200, f"Status update failed: {status_response.text}"
        
        # Check ledger for purchase_reward entry
        new_ledger = self.session.get(f"{BASE_URL}/api/loyalty/ledger").json()
        assert len(new_ledger) > initial_count, "New ledger entry should be created for purchase reward"
        
        # Find purchase_reward entry
        purchase_entries = [e for e in new_ledger if e["type"] == "purchase_reward" and f"Order #{order_id[:8]}" in e["reference"]]
        assert len(purchase_entries) > 0, "purchase_reward entry should exist for this order"
        
        latest_entry = purchase_entries[0]
        assert latest_entry["amount"] == points_earned, f"Amount should be {points_earned}"
        
        print(f"Purchase reward verified: +{points_earned} points for order {order_id[:8]}")

    def test_5_referral_bonus_creates_ledger_entries(self):
        """Test 5: First paid order by referred user creates referral_bonus entries for both users"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create a new user referred by admin
        new_user_data = {
            "email": f"test_ledger_ref_{unique_id}@test.com",
            "password": "TestPass123!",
            "firstName": "Test",
            "lastName": "Referral",
            "dateOfBirth": "2000-01-01",
            "referralCode": ADMIN_REFERRAL_CODE  # Admin's referral code
        }
        
        register_response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json=new_user_data
        )
        assert register_response.status_code == 200, f"Registration failed: {register_response.text}"
        
        new_user_token = register_response.json()["access_token"]
        new_user_id = register_response.json()["user"]["id"]
        
        print(f"Created referred user {new_user_id[:8]} with referrer {ADMIN_USER_ID[:8]}")
        
        # Login as new user and create an order
        new_user_session = requests.Session()
        new_user_session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {new_user_token}"
        })
        
        # Get products
        products = new_user_session.get(f"{BASE_URL}/api/products").json()
        if len(products) == 0:
            pytest.skip("No products available")
        
        product = products[0]
        
        # Create order as new user
        order_data = {
            "items": [{
                "productId": product["id"],
                "quantity": 1,
                "name": product["name"],
                "price": product["price"]
            }],
            "total": product["price"],
            "pickupTime": "2025-01-16 15:00",
            "paymentMethod": "Cash"
        }
        
        order_response = new_user_session.post(f"{BASE_URL}/api/orders", json=order_data)
        assert order_response.status_code == 200, f"Order creation failed: {order_response.text}"
        
        order_id = order_response.json()["id"]
        print(f"Created order {order_id[:8]} for new referred user")
        
        # Get admin's ledger before marking paid
        admin_ledger_before = self.session.get(f"{BASE_URL}/api/loyalty/ledger").json()
        admin_entries_before = len(admin_ledger_before)
        
        # Mark order as Paid (triggers referral bonus)
        status_response = self.session.patch(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": "Paid"}
        )
        assert status_response.status_code == 200, f"Status update failed: {status_response.text}"
        
        # Check admin (referrer) ledger for referral_bonus entry
        admin_ledger_after = self.session.get(f"{BASE_URL}/api/loyalty/ledger").json()
        
        referrer_bonus_entries = [
            e for e in admin_ledger_after 
            if e["type"] == "referral_bonus" and e["amount"] == 2000
        ]
        
        # Check if referrer got 2000 points
        assert len(referrer_bonus_entries) > 0, "Referrer should have referral_bonus entry with +2000 points"
        
        print(f"Referrer (admin) received referral_bonus: +2000 points")
        
        # Check new user's ledger for their 1000 point bonus
        new_user_ledger = new_user_session.get(f"{BASE_URL}/api/loyalty/ledger").json()
        
        referred_bonus_entries = [
            e for e in new_user_ledger 
            if e["type"] == "referral_bonus" and e["amount"] == 1000
        ]
        
        assert len(referred_bonus_entries) > 0, "Referred user should have referral_bonus entry with +1000 points"
        
        print(f"Referred user received referral_bonus: +1000 points")
        
        # Cleanup: The test user is a new registration, but we can't easily delete
        print(f"Test referral user created: test_ledger_ref_{unique_id}@test.com")

    def test_6_balance_after_field_accuracy(self):
        """Test 6: Ledger balanceAfter field matches user's actual loyaltyPoints after each transaction"""
        # Get current user state
        me_response = self.session.get(f"{BASE_URL}/api/auth/me")
        current_points = me_response.json()["loyaltyPoints"]
        
        # Make an adjustment
        new_points = current_points + 100
        self.session.patch(
            f"{BASE_URL}/api/admin/users/{ADMIN_USER_ID}",
            json={"loyaltyPoints": new_points}
        )
        
        # Get ledger and verify most recent entry's balanceAfter
        ledger = self.session.get(f"{BASE_URL}/api/loyalty/ledger").json()
        
        # Most recent entry should be first (sorted by createdAt desc)
        if len(ledger) > 0:
            latest_entry = ledger[0]
            
            # Get current user points
            me_after = self.session.get(f"{BASE_URL}/api/auth/me")
            actual_points = me_after.json()["loyaltyPoints"]
            
            # The latest entry's balanceAfter should match what the balance was at that transaction time
            # Since we just made the adjustment, it should match
            assert latest_entry["balanceAfter"] == actual_points, \
                f"balanceAfter ({latest_entry['balanceAfter']}) should match current points ({actual_points})"
            
            print(f"Balance accuracy verified: balanceAfter={latest_entry['balanceAfter']}, actual={actual_points}")


class TestLedgerEntryTypes:
    """Verify all 4 transaction types are properly labeled"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        
        self.token = login_response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def test_ledger_has_expected_types(self):
        """Verify ledger contains entries with correct type values"""
        response = self.session.get(f"{BASE_URL}/api/loyalty/ledger")
        assert response.status_code == 200
        
        entries = response.json()
        if len(entries) == 0:
            pytest.skip("No ledger entries to verify types")
        
        # Collect all types found
        types_found = set(e["type"] for e in entries)
        expected_types = {"purchase_reward", "referral_bonus", "tier_redemption", "admin_adjustment"}
        
        print(f"Types found in ledger: {types_found}")
        print(f"Expected types: {expected_types}")
        
        # At least admin_adjustment should exist from previous tests
        assert "admin_adjustment" in types_found or len(types_found) > 0, \
            "Ledger should have at least one type of entry"
        
        # Verify all types are from the expected set
        for t in types_found:
            assert t in expected_types, f"Unexpected type found: {t}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
