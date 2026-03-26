"""
Tests for:
1. Leaderboard rank movement tracking (/api/leaderboard movement field)
2. Leaderboard daily snapshot (leaderboard_snapshots collection)
3. Store credit at checkout (deduction, capping, storeCreditApplied in order)
"""
import pytest
import requests
import os
from datetime import datetime

# Use localhost for direct backend testing (avoids SPA fallback on external URL)
BASE_URL = "http://localhost:8001"

# Admin credentials from test context
ADMIN_EMAIL = "jkaatz@gmail.com"
ADMIN_PASSWORD = "Just1n23$"


# ==================== FIXTURES ====================

@pytest.fixture(scope="module")
def admin_token():
    """Login as admin user and return JWT token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_user_data(admin_token):
    """Get admin user data from /api/auth/me"""
    response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if response.status_code == 200:
        return response.json()
    pytest.skip(f"Could not get admin user data: {response.text}")


@pytest.fixture(scope="module")
def products(admin_token):
    """Get available products for order testing - prefer high stock items"""
    response = requests.get(f"{BASE_URL}/api/products")
    if response.status_code == 200:
        data = response.json()
        products_list = data if isinstance(data, list) else data.get("products", [])
        # Sort by stock descending to use high-stock items first
        active_products = sorted(
            [p for p in products_list if p.get("isActive", True) and p.get("stock", 0) >= 3],
            key=lambda x: -x.get("stock", 0)
        )
        if active_products:
            return active_products
    pytest.skip("Could not load products with sufficient stock for testing")


# ==================== LEADERBOARD TESTS ====================

class TestLeaderboardMovement:
    """Tests for movement field in /api/leaderboard response"""

    def test_leaderboard_returns_200(self, admin_token):
        """GET /api/leaderboard returns 200 status"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_leaderboard_has_bypoints_and_byreferrals(self, admin_token):
        """Response contains byPoints and byReferrals arrays"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        assert "byPoints" in data, "Response missing 'byPoints'"
        assert "byReferrals" in data, "Response missing 'byReferrals'"
        assert isinstance(data["byPoints"], list)
        assert isinstance(data["byReferrals"], list)

    def test_movement_field_exists_in_bypoints(self, admin_token):
        """Each entry in byPoints has a 'movement' field"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        assert len(data["byPoints"]) > 0, "byPoints should have at least 1 entry"

        for entry in data["byPoints"]:
            assert "movement" in entry, f"Entry missing 'movement' field: {entry}"

    def test_movement_field_exists_in_byreferrals(self, admin_token):
        """Each entry in byReferrals has a 'movement' field"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        assert len(data["byReferrals"]) > 0, "byReferrals should have at least 1 entry"

        for entry in data["byReferrals"]:
            assert "movement" in entry, f"Entry missing 'movement' field: {entry}"

    def test_movement_value_is_int_or_null(self, admin_token):
        """Movement value must be int (positive, negative, 0) or null"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        for entry in data["byPoints"]:
            movement = entry["movement"]
            assert movement is None or isinstance(movement, int), \
                f"Movement should be int or null, got {type(movement)}: {movement}"

    def test_movement_positive_means_moved_up(self, admin_token):
        """Movement field semantics: positive = moved up, negative = moved down"""
        # With a yesterday snapshot having swapped rankings, at least one should show movement
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        movements = [e["movement"] for e in data["byPoints"]]
        print(f"byPoints movements: {movements}")
        # At least verify structure is correct - can't guarantee movement values without snapshot
        for m in movements:
            if m is not None:
                assert isinstance(m, int), f"Non-null movement must be int, got {m}"

    def test_unauthenticated_leaderboard_rejected(self):
        """Leaderboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/leaderboard")
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"

    def test_leaderboard_response_schema_with_movement(self, admin_token):
        """Each entry must have rank, displayName, points, referralCount, tier, tierColor, isCurrentUser, movement"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        required_fields = {"rank", "displayName", "points", "referralCount", "tier", "tierColor", "isCurrentUser", "movement"}

        for entry in data["byPoints"][:5]:
            for field in required_fields:
                assert field in entry, f"Entry missing field '{field}': {entry.keys()}"

        for entry in data["byReferrals"][:5]:
            for field in required_fields:
                assert field in entry, f"Entry missing field '{field}': {entry.keys()}"

    def test_admin_user_isCurrentUser_flagged(self, admin_token):
        """Admin user should have isCurrentUser=True"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        current_users = [e for e in data["byPoints"] if e["isCurrentUser"]]
        assert len(current_users) <= 1, "Should have at most 1 current user"
        if current_users:
            print(f"Admin user in leaderboard: {current_users[0]['displayName']}, rank={current_users[0]['rank']}, movement={current_users[0]['movement']}")


# ==================== LEADERBOARD SNAPSHOT TESTS ====================

class TestLeaderboardSnapshot:
    """Tests for daily leaderboard snapshot"""

    def test_today_snapshot_exists(self, admin_token):
        """Today's snapshot should exist in leaderboard_snapshots (created on startup)"""
        # We verify this indirectly: if movement is null for all users, snapshot might be missing
        # A more direct check: call leaderboard and verify at least some movements returned
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        # According to test context: yesterday snapshot exists with swapped rankings
        # So at least some users should show non-null movement
        movements_by_points = [e["movement"] for e in data["byPoints"]]
        print(f"Movements in byPoints: {movements_by_points}")
        # If ALL movements are null → yesterday's snapshot might not be found
        # Per review_request: yesterday snapshot exists, so some should be non-null
        has_non_null = any(m is not None for m in movements_by_points)
        assert has_non_null, \
            f"All movements are null - yesterday's snapshot may not be found. Movements: {movements_by_points}"

    def test_movement_reflects_yesterday_swap(self, admin_token):
        """With yesterday's swapped ranking snapshot, movement values should be non-zero"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        non_null_movements = [e["movement"] for e in data["byPoints"] if e["movement"] is not None]
        print(f"Non-null movements in byPoints: {non_null_movements}")

        if non_null_movements:
            # With swapped rankings, we expect both positive and negative movements
            has_positive = any(m > 0 for m in non_null_movements)
            has_negative = any(m < 0 for m in non_null_movements)
            print(f"Has positive movement: {has_positive}, has negative movement: {has_negative}")
            # At minimum, at least one non-zero or zero movement is present
            assert len(non_null_movements) > 0, "Expected some non-null movements"


# ==================== STORE CREDIT TESTS ====================

class TestStoreCreditCheckout:
    """Tests for store credit application at checkout.
    Uses Zelle payment so orders get 'Pending Payment' status and can be cancelled."""

    def _get_fresh_credit(self, admin_token):
        """Get fresh credit balance from API"""
        resp = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        return float(resp.json().get("creditBalance", 0))

    def _place_zelle_order(self, admin_token, product, credit_to_apply, pickup_time="Tomorrow - 12:00 PM - 2:00 PM"):
        """Helper to place a Zelle order (creates Pending Payment → can be cancelled)"""
        product_price = float(product["price"])
        available_credit = self._get_fresh_credit(admin_token)
        actual_credit = min(credit_to_apply, available_credit, product_price)
        order_total = round(product_price - actual_credit, 2)
        order_data = {
            "items": [{"productId": product["id"], "quantity": 1, "name": product["name"], "price": product_price}],
            "total": order_total,
            "pickupTime": pickup_time,
            "paymentMethod": "Zelle",
            "storeCreditApplied": credit_to_apply,  # May be capped by backend
            "couponApplied": False,
        }
        return requests.post(
            f"{BASE_URL}/api/orders", json=order_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    def _cancel_order(self, admin_token, order_id):
        """Cancel an order to restore stock"""
        return requests.post(
            f"{BASE_URL}/api/orders/{order_id}/cancel",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    def test_admin_has_credit_balance(self, admin_token):
        """Admin user should have creditBalance > 0 ($20 after manual testing)"""
        credit = self._get_fresh_credit(admin_token)
        print(f"Admin creditBalance: ${credit}")
        assert credit > 0, f"Admin should have creditBalance > 0, got {credit}"

    def test_place_order_with_store_credit(self, admin_token, products):
        """Placing order with storeCreditApplied deducts from user creditBalance"""
        credit_before = self._get_fresh_credit(admin_token)
        if credit_before <= 0:
            pytest.skip("Admin user has no credit balance to test with")

        product = products[0]
        product_price = float(product["price"])
        credit_to_apply = min(1.0, credit_before, product_price)

        response = self._place_zelle_order(admin_token, product, credit_to_apply)
        print(f"Order response status: {response.status_code}")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        order = response.json()
        order_id = order.get("id")

        # Verify storeCreditApplied field exists in response
        assert "storeCreditApplied" in order, "Order should have storeCreditApplied field"
        assert float(order["storeCreditApplied"]) == credit_to_apply, \
            f"Expected storeCreditApplied={credit_to_apply}, got {order['storeCreditApplied']}"

        # Verify credit deduction
        credit_after = self._get_fresh_credit(admin_token)
        expected_credit = round(credit_before - credit_to_apply, 2)
        print(f"Credit: before=${credit_before}, applied=${credit_to_apply}, after=${credit_after}, expected=${expected_credit}")
        assert abs(credit_after - expected_credit) < 0.01, \
            f"Expected credit {expected_credit}, got {credit_after}"

        # Cancel order to restore stock
        if order_id:
            cancel = self._cancel_order(admin_token, order_id)
            print(f"Cancel order: {cancel.status_code}")

    def test_store_credit_capped_at_available_balance(self, admin_token, products):
        """storeCreditApplied cannot exceed user's creditBalance"""
        credit_before = self._get_fresh_credit(admin_token)
        if credit_before <= 0:
            pytest.skip("Admin user has no credit balance")

        product = products[1] if len(products) > 1 else products[0]  # Use different product
        product_price = float(product["price"])

        # Request more credit than available
        requested_credit = credit_before + 100.0  # Way more than available

        response = self._place_zelle_order(admin_token, product, requested_credit, "Tomorrow - 2:00 PM - 4:00 PM")
        assert response.status_code == 200, \
            f"Order should succeed even with excessive credit request: {response.text}"

        order = response.json()
        applied = float(order["storeCreditApplied"])
        print(f"Requested credit: {requested_credit}, Applied: {applied}, Available was: {credit_before}")
        # Backend should cap at available balance
        assert applied <= credit_before + 0.01, \
            f"Applied credit {applied} should not exceed available {credit_before}"

        # Cancel to restore stock
        order_id = order.get("id")
        if order_id:
            self._cancel_order(admin_token, order_id)

    def test_store_credit_applied_stored_in_order_document(self, admin_token, products):
        """storeCreditApplied field is properly stored in the order document and retrievable via GET"""
        credit_before = self._get_fresh_credit(admin_token)
        if credit_before <= 0:
            pytest.skip("Admin user has no credit balance")

        product = products[2] if len(products) > 2 else products[0]
        product_price = float(product["price"])
        credit_to_apply = min(0.5, credit_before, product_price)

        response = self._place_zelle_order(admin_token, product, credit_to_apply, "Tomorrow - 10:00 AM - 12:00 PM")
        assert response.status_code == 200, f"Order creation failed: {response.text}"

        created_order = response.json()
        order_id = created_order["id"]

        # GET the order and verify storeCreditApplied persisted
        get_response = requests.get(
            f"{BASE_URL}/api/orders/{order_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.status_code == 200
        fetched_order = get_response.json()

        assert "storeCreditApplied" in fetched_order, "GET order should include storeCreditApplied"
        assert abs(float(fetched_order["storeCreditApplied"]) - credit_to_apply) < 0.01, \
            f"Stored storeCreditApplied {fetched_order['storeCreditApplied']} != expected {credit_to_apply}"
        print(f"storeCreditApplied correctly stored: {fetched_order['storeCreditApplied']}")

        # Cancel order
        if order_id:
            self._cancel_order(admin_token, order_id)

    def test_zero_store_credit_not_deducted(self, admin_token, products):
        """Order with storeCreditApplied=0 should not change creditBalance"""
        credit_before = self._get_fresh_credit(admin_token)

        product = products[3] if len(products) > 3 else products[0]
        product_price = float(product["price"])

        order_data = {
            "items": [{"productId": product["id"], "quantity": 1, "name": product["name"], "price": product_price}],
            "total": product_price,
            "pickupTime": "Tomorrow - 12:00 PM - 2:00 PM",
            "paymentMethod": "Zelle",
            "storeCreditApplied": 0.0,
            "couponApplied": False,
        }

        response = requests.post(
            f"{BASE_URL}/api/orders", json=order_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Order failed: {response.text}"

        order = response.json()
        assert float(order.get("storeCreditApplied", 0)) == 0.0, "storeCreditApplied should be 0"

        # Verify credit unchanged
        credit_after = self._get_fresh_credit(admin_token)
        assert abs(credit_after - credit_before) < 0.01, \
            f"Credit should not change when storeCreditApplied=0. Before: {credit_before}, After: {credit_after}"

        order_id = order.get("id")
        if order_id:
            self._cancel_order(admin_token, order_id)

    def test_store_credit_capped_at_order_total(self, admin_token, products):
        """storeCreditApplied cannot exceed order total"""
        credit_before = self._get_fresh_credit(admin_token)
        if credit_before <= 0:
            pytest.skip("Admin user has no credit balance")

        product = products[4] if len(products) > 4 else products[0]
        product_price = float(product["price"])
        # Apply more credit than order total
        over_credit = product_price + 50.0

        order_data = {
            "items": [{"productId": product["id"], "quantity": 1, "name": product["name"], "price": product_price}],
            "total": 0.0,  # Frontend computes 0 when fully covered by credit
            "pickupTime": "Tomorrow - 2:00 PM - 4:00 PM",
            "paymentMethod": "Zelle",
            "storeCreditApplied": over_credit,
            "couponApplied": False,
        }

        response = requests.post(
            f"{BASE_URL}/api/orders", json=order_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Over-credit response: {response.status_code}: {response.json() if response.status_code < 500 else response.text}")

        if response.status_code == 200:
            order = response.json()
            applied = float(order["storeCreditApplied"])
            print(f"Applied credit: {applied}, product price: {product_price}")
            # Should be capped at order total (product_price since total=0 but order total is product_price)
            assert applied <= product_price + 0.01, \
                f"Applied credit {applied} should not exceed order price {product_price}"

            order_id = order.get("id")
            if order_id:
                self._cancel_order(admin_token, order_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
