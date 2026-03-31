"""
Regression tests for loyalty & referral system.
Run with: pytest backend/tests/test_loyalty_referral.py -v
"""
import pytest
import httpx
import math

BASE = "https://cloud-district-1.preview.emergentagent.com"
ADMIN_EMAIL = "jkaatz@gmail.com"
ADMIN_PASS = "Just1n23$"


@pytest.fixture(scope="module")
def admin_token():
    r = httpx.post(f"{BASE}/api/auth/login", json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def test_accounts(admin_token):
    """Register referrer + referred user, yield ids/tokens, cleanup after."""
    import random, string
    suffix = "".join(random.choices(string.digits, k=6))

    # Register referrer
    ref = httpx.post(f"{BASE}/api/auth/register", json={
        "email": f"testref_ref_{suffix}@test.com",
        "password": "Test1234!",
        "firstName": "Ref", "lastName": "Er",
        "dateOfBirth": "1990-01-01",
        "username": f"testref_{suffix}",
    })
    assert ref.status_code == 200
    referrer = ref.json()

    # Register new user with referral code
    new = httpx.post(f"{BASE}/api/auth/register", json={
        "email": f"testref_new_{suffix}@test.com",
        "password": "Test1234!",
        "firstName": "New", "lastName": "User",
        "dateOfBirth": "1990-01-01",
        "username": f"testnew_{suffix}",
        "referralCode": f"testref_{suffix}",
    })
    assert new.status_code == 200
    new_user = new.json()

    yield {
        "referrer_id": referrer["user"]["id"],
        "referrer_token": referrer["access_token"],
        "new_user_id": new_user["user"]["id"],
        "new_user_token": new_user["access_token"],
        "new_user_points_on_signup": new_user["user"]["loyaltyPoints"],
    }

    # Cleanup
    headers = {"Authorization": f"Bearer {admin_token}"}
    httpx.delete(f"{BASE}/api/admin/users/{referrer['user']['id']}", headers=headers)
    httpx.delete(f"{BASE}/api/admin/users/{new_user['user']['id']}", headers=headers)


def test_issue3_new_user_gets_1000_cloudz(test_accounts):
    """New user with referral should start with 1000 Cloudz (500 base + 500 bonus)."""
    assert test_accounts["new_user_points_on_signup"] == 1000


def test_issue4_referrer_gets_pending_not_balance(test_accounts, admin_token):
    """Referrer should have referral_pending in ledger, balance unchanged at 500."""
    ref_id = test_accounts["referrer_id"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Check ledger
    ledger = httpx.get(f"{BASE}/api/admin/users/{ref_id}/cloudz-ledger", headers=headers).json()
    pending = [e for e in ledger if e.get("type") == "referral_pending"]
    assert len(pending) == 1
    assert pending[0]["amount"] == 1500
    assert pending[0]["status"] == "pending"

    # Balance should still be 500 (no change from pending)
    users = httpx.get(f"{BASE}/api/admin/users", headers=headers).json()
    referrer = next(u for u in users if u["id"] == ref_id)
    assert referrer["loyaltyPoints"] == 500


def test_issue1_bulk_discount_no_cloudz_deduction(test_accounts, admin_token):
    """Bulk discount (10+ items) must not create any negative Cloudz ledger entry."""
    new_user_id = test_accounts["new_user_id"]
    new_user_token = test_accounts["new_user_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get a product
    products = httpx.get(f"{BASE}/api/products").json()
    product = next(p for p in products if p.get("isActive") and p.get("stock", 0) >= 10)

    order = httpx.post(f"{BASE}/api/orders",
        headers={"Authorization": f"Bearer {new_user_token}"},
        json={
            "items": [{"productId": product["id"], "quantity": 10, "name": product["name"], "price": product["price"]}],
            "total": product["price"] * 10,
            "pickupTime": "ASAP",
            "paymentMethod": "Venmo",
        }).json()

    assert order.get("discountApplied", 0) > 0, "Discount should be applied for 10+ items"
    order_id = order["id"]

    # Check no bulk_discount ledger entry was created
    ledger = httpx.get(f"{BASE}/api/admin/users/{new_user_id}/cloudz-ledger", headers=headers).json()
    bulk_entries = [e for e in ledger if e.get("type") == "bulk_discount"]
    assert len(bulk_entries) == 0, f"No bulk_discount ledger entries expected, found: {bulk_entries}"

    # Cancel the order to restore stock
    httpx.post(f"{BASE}/api/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {new_user_token}"})


def test_issue2_purchase_reward_on_paid(test_accounts, admin_token):
    """Marking order Paid should award floor(total * 3) Cloudz to buyer."""
    new_user_id = test_accounts["new_user_id"]
    new_user_token = test_accounts["new_user_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    products = httpx.get(f"{BASE}/api/products").json()
    product = next(p for p in products if p.get("isActive") and p.get("stock", 0) > 0)

    order_total = 100.0
    order = httpx.post(f"{BASE}/api/orders",
        headers={"Authorization": f"Bearer {new_user_token}"},
        json={
            "items": [{"productId": product["id"], "quantity": 1, "name": product["name"], "price": order_total}],
            "total": order_total,
            "pickupTime": "ASAP",
            "paymentMethod": "Venmo",
        }).json()
    order_id = order["id"]
    expected_points = int(order_total) * 3  # 300

    # Mark Paid
    httpx.patch(f"{BASE}/api/admin/orders/{order_id}/status",
        headers=headers, json={"status": "Paid"})

    # Check new user ledger for purchase_reward
    ledger = httpx.get(f"{BASE}/api/admin/users/{new_user_id}/cloudz-ledger", headers=headers).json()
    rewards = [e for e in ledger if e.get("type") == "purchase_reward" and e.get("orderId") == order_id]
    assert len(rewards) == 1, f"Expected 1 purchase_reward, got {len(rewards)}"
    assert rewards[0]["amount"] == expected_points, f"Expected {expected_points}, got {rewards[0]['amount']}"

    return order_id  # Not usable as a return val in pytest, but leaving for context


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])
