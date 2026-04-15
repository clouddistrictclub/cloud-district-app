"""
Test payment methods and processing fees for orders:
- Apple Pay: 1.75% fee, status=Pending Payment
- Cash App: 1.75% fee, status=Pending Payment
- Chime: 1.75% fee, status=Pending Payment
- Zelle: 0% fee, status=Pending Payment
- Cash on Pickup: 0% fee, status=Awaiting Pickup (Cash)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')


@pytest.fixture(scope="module")
def user_token():
    """Login as existing user or register a new test user"""
    # Try to login with existing test user
    login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "identifier": "test_payment_fees@test.com",
        "password": "TestPass123!"
    })
    if login_resp.status_code == 200:
        data = login_resp.json()
        return data["access_token"]

    # Register a new test user
    register_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": "test_payment_fees@test.com",
        "password": "TestPass123!",
        "username": "fee_tester",
        "firstName": "FeeTest",
        "lastName": "User",
        "dateOfBirth": "2000-01-01"
    })
    if register_resp.status_code not in (200, 201):
        pytest.skip(f"Could not create test user: {register_resp.text}")

    login2 = requests.post(f"{BASE_URL}/api/auth/login", json={
        "identifier": "test_payment_fees@test.com",
        "password": "TestPass123!"
    })
    if login2.status_code != 200:
        pytest.skip("Could not login test user")
    return login2.json()["access_token"]


@pytest.fixture(scope="module")
def sample_product(user_token):
    """Get the first available product for test orders"""
    resp = requests.get(
        f"{BASE_URL}/api/products",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert resp.status_code == 200, f"Failed to get products: {resp.text}"
    products = resp.json()
    assert len(products) > 0, "No products available for testing"
    # Find a product with stock
    for p in products:
        if p.get("stock", 0) > 0:
            return p
    pytest.skip("No products with stock available")


def create_test_order(user_token, sample_product, payment_method: str, amount: float = 20.0):
    """Helper to create a test order with a given payment method"""
    order_data = {
        "items": [
            {
                "productId": sample_product["id"],
                "quantity": 1,
                "name": sample_product["name"],
                "price": amount,
            }
        ],
        "total": amount,
        "pickupTime": "Tomorrow - 12:00 PM - 2:00 PM",
        "paymentMethod": payment_method,
        "rewardId": None,
        "couponApplied": False,
        "storeCreditApplied": 0.0,
    }
    resp = requests.post(
        f"{BASE_URL}/api/orders",
        json=order_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    return resp


class TestPaymentMethodFees:
    """Verify processing fees and statuses for all payment methods"""

    def test_apple_pay_fee_and_status(self, user_token, sample_product):
        """Apple Pay: processingFee=1.75% of total, status=Pending Payment"""
        amount = 20.0
        resp = create_test_order(user_token, sample_product, "Apple Pay", amount)
        assert resp.status_code == 200, f"Apple Pay order failed: {resp.text}"
        data = resp.json()
        expected_fee = round(amount * 0.0175, 2)  # 0.35
        assert data["processingFee"] == expected_fee, (
            f"Expected processingFee={expected_fee}, got {data['processingFee']}"
        )
        assert data["status"] == "Pending Payment", (
            f"Expected status='Pending Payment', got '{data['status']}'"
        )
        print(f"PASS Apple Pay: fee={data['processingFee']}, status={data['status']}")

    def test_cashapp_fee_and_status(self, user_token, sample_product):
        """Cash App: processingFee=1.75% of total, status=Pending Payment"""
        amount = 20.0
        resp = create_test_order(user_token, sample_product, "Cash App", amount)
        assert resp.status_code == 200, f"Cash App order failed: {resp.text}"
        data = resp.json()
        expected_fee = round(amount * 0.0175, 2)  # 0.35
        assert data["processingFee"] == expected_fee, (
            f"Expected processingFee={expected_fee}, got {data['processingFee']}"
        )
        assert data["status"] == "Pending Payment", (
            f"Expected status='Pending Payment', got '{data['status']}'"
        )
        print(f"PASS Cash App: fee={data['processingFee']}, status={data['status']}")

    def test_chime_fee_and_status(self, user_token, sample_product):
        """Chime: processingFee=1.75% of total, status=Pending Payment"""
        amount = 20.0
        resp = create_test_order(user_token, sample_product, "Chime", amount)
        assert resp.status_code == 200, f"Chime order failed: {resp.text}"
        data = resp.json()
        expected_fee = round(amount * 0.0175, 2)  # 0.35
        assert data["processingFee"] == expected_fee, (
            f"Expected processingFee={expected_fee}, got {data['processingFee']}"
        )
        assert data["status"] == "Pending Payment", (
            f"Expected status='Pending Payment', got '{data['status']}'"
        )
        print(f"PASS Chime: fee={data['processingFee']}, status={data['status']}")

    def test_zelle_no_fee(self, user_token, sample_product):
        """Zelle: processingFee=0.0, status=Pending Payment"""
        amount = 20.0
        resp = create_test_order(user_token, sample_product, "Zelle", amount)
        assert resp.status_code == 200, f"Zelle order failed: {resp.text}"
        data = resp.json()
        assert data["processingFee"] == 0.0, (
            f"Expected processingFee=0.0 for Zelle, got {data['processingFee']}"
        )
        assert data["status"] == "Pending Payment", (
            f"Expected status='Pending Payment', got '{data['status']}'"
        )
        print(f"PASS Zelle: fee={data['processingFee']}, status={data['status']}")

    def test_cash_on_pickup_no_fee_awaiting_status(self, user_token, sample_product):
        """Cash on Pickup: processingFee=0.0, status=Awaiting Pickup (Cash)"""
        amount = 20.0
        resp = create_test_order(user_token, sample_product, "Cash on Pickup", amount)
        assert resp.status_code == 200, f"Cash on Pickup order failed: {resp.text}"
        data = resp.json()
        assert data["processingFee"] == 0.0, (
            f"Expected processingFee=0.0 for Cash on Pickup, got {data['processingFee']}"
        )
        assert data["status"] == "Awaiting Pickup (Cash)", (
            f"Expected status='Awaiting Pickup (Cash)', got '{data['status']}'"
        )
        print(f"PASS Cash on Pickup: fee={data['processingFee']}, status={data['status']}")

    def test_apple_pay_fee_precision(self, user_token, sample_product):
        """Apple Pay fee should be exactly round(total * 0.0175, 2) — test with odd amount"""
        amount = 37.50
        resp = create_test_order(user_token, sample_product, "Apple Pay", amount)
        assert resp.status_code == 200, f"Apple Pay order failed: {resp.text}"
        data = resp.json()
        expected_fee = round(amount * 0.0175, 2)  # 0.66
        assert data["processingFee"] == expected_fee, (
            f"Expected processingFee={expected_fee}, got {data['processingFee']}"
        )
        print(f"PASS Apple Pay precision: amount={amount}, fee={data['processingFee']}, expected={expected_fee}")

    def test_order_total_includes_fee_for_apple_pay(self, user_token, sample_product):
        """Final order total should be original amount + processing fee for Apple Pay"""
        amount = 20.0
        resp = create_test_order(user_token, sample_product, "Apple Pay", amount)
        assert resp.status_code == 200, f"Apple Pay order failed: {resp.text}"
        data = resp.json()
        expected_fee = round(amount * 0.0175, 2)
        expected_total = round(amount + expected_fee, 2)
        assert data["total"] == expected_total, (
            f"Expected total={expected_total} (amount + fee), got total={data['total']}"
        )
        print(f"PASS Apple Pay total: {data['total']} = {amount} + {expected_fee}")

    def test_payment_method_name_preserved(self, user_token, sample_product):
        """Order should store the correct paymentMethod name"""
        resp = create_test_order(user_token, sample_product, "Apple Pay")
        assert resp.status_code == 200, f"Order failed: {resp.text}"
        data = resp.json()
        assert data["paymentMethod"] == "Apple Pay", (
            f"Expected paymentMethod='Apple Pay', got '{data['paymentMethod']}'"
        )
        print(f"PASS payment method name: {data['paymentMethod']}")
