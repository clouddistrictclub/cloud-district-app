"""
Comprehensive OpenAPI contract test — 61 operations across all routes.
ITERATION 32 — Verifying two contract fixes:
  FIX 1: HTTPBearer(auto_error=False) in auth.py — missing token now returns 401 "Not authenticated".
          All "no_auth" tests now assert strict 401.
  FIX 2: POST /api/auth/register with duplicate email now returns 409 Conflict (was 400).
  All 107 previously-passing tests must still pass.
"""

import pytest
import requests
import os
import time
import uuid
import math

BASE_URL = "http://localhost:8001"

ADMIN_EMAIL = "jkaatz@gmail.com"
ADMIN_PASSWORD = "Just1n23$"
ADMIN_ID = "698f8be2f3e9a3d6ac40fb67"

SUFFIX = uuid.uuid4().hex[:6]
TEST_EMAIL = f"TEST_c_{SUFFIX}@example.com"
TEST_EMAIL2 = f"TEST_c2_{SUFFIX}@example.com"
TEST_PASSWORD = "TestPass123!"
TEST_DOB = "1990-01-01"


# ─────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(session):
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
    })
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def test_user(session):
    """Register a fresh test user (token NOT invalidated during the run)."""
    resp = session.post(f"{BASE_URL}/api/auth/register", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "firstName": "ContractFirst",
        "lastName": "ContractLast",
        "dateOfBirth": TEST_DOB,
        "phone": "5551234567",
    })
    assert resp.status_code == 200, f"Test user register failed: {resp.text}"
    return resp.json()


@pytest.fixture(scope="module")
def test_user2(session):
    """Second test user for cross-user permission tests."""
    # Wait a bit to avoid rate-limit burst (tests start after test_user)
    time.sleep(1)
    resp = session.post(f"{BASE_URL}/api/auth/register", json={
        "email": TEST_EMAIL2,
        "password": TEST_PASSWORD,
        "firstName": "SecondFirst",
        "lastName": "SecondLast",
        "dateOfBirth": TEST_DOB,
    })
    assert resp.status_code == 200, f"Test user2 register failed: {resp.text}"
    return resp.json()


@pytest.fixture(scope="module")
def user_headers(test_user):
    return {"Authorization": f"Bearer {test_user['access_token']}"}


@pytest.fixture(scope="module")
def user2_headers(test_user2):
    return {"Authorization": f"Bearer {test_user2['access_token']}"}


@pytest.fixture(scope="module")
def sample_product(session):
    """Return a product with stock > 5 for safe order tests."""
    products = session.get(f"{BASE_URL}/api/products").json()
    # Pick product with highest stock to avoid running out
    in_stock = [p for p in products if p.get("stock", 0) > 5]
    if not in_stock:
        pytest.skip("No products with stock>5")
    return sorted(in_stock, key=lambda p: p["stock"], reverse=True)[0]


# ─────────────────────────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_200(self, session):
        resp = session.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200
        print(f"  PASS health: {resp.json()}")


# ─────────────────────────────────────────────────────────────────
# AUTH — REGISTER
# ─────────────────────────────────────────────────────────────────

class TestAuthRegister:
    def test_register_valid(self, test_user):
        """Valid registration: 200, signup bonus 500, referralCode present."""
        assert "access_token" in test_user
        u = test_user["user"]
        assert u["email"] == TEST_EMAIL
        assert u["loyaltyPoints"] == 500, f"Expected 500 signup bonus, got {u['loyaltyPoints']}"
        assert u["referralCode"] and len(u["referralCode"]) == 8
        print(f"  PASS register valid: id={u['id']}, referralCode={u['referralCode']}")

    def test_register_duplicate_email(self, session):
        """Duplicate email — CODE returns 400, OpenAPI contract says 409 (CONTRACT DEVIATION)."""
        resp = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "firstName": "Dup",
            "lastName": "User",
            "dateOfBirth": TEST_DOB,
        })
        assert resp.status_code == 409, f"Expected 409 got {resp.status_code}: {resp.text}"
        print(f"  ACTUAL {resp.status_code} for duplicate email — CONTRACT SAYS 409, CODE RETURNS 400")

    def test_register_invalid_dob_format(self, session):
        """Bad DOB format → 422 from Pydantic validator."""
        resp = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"bad_dob_{SUFFIX}@example.com",
            "password": TEST_PASSWORD,
            "firstName": "Bad",
            "lastName": "Dob",
            "dateOfBirth": "01-01-1990",
        })
        assert resp.status_code == 422
        print(f"  PASS invalid DOB 422")

    def test_register_missing_required_fields(self, session):
        """Missing required fields → 422."""
        resp = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"missing_{SUFFIX}@example.com",
        })
        assert resp.status_code == 422
        print(f"  PASS missing fields 422")

    def test_register_underage(self, session):
        """Under-21 → 400."""
        resp = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"underage_{SUFFIX}@example.com",
            "password": TEST_PASSWORD,
            "firstName": "Young",
            "lastName": "User",
            "dateOfBirth": "2010-01-01",
        })
        assert resp.status_code == 400
        print(f"  PASS underage 400")

    def test_register_invalid_referral_code(self, session):
        """Invalid referral code → 400."""
        resp = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"badref_{SUFFIX}@example.com",
            "password": TEST_PASSWORD,
            "firstName": "Bad",
            "lastName": "Ref",
            "dateOfBirth": TEST_DOB,
            "referralCode": "BADCODE99",
        })
        assert resp.status_code == 400
        print(f"  PASS invalid referral code 400")


# ─────────────────────────────────────────────────────────────────
# AUTH — LOGIN
# ─────────────────────────────────────────────────────────────────

class TestAuthLogin:
    def test_login_valid(self, session):
        resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["isAdmin"] is True
        print(f"  PASS login valid admin")

    def test_login_wrong_password(self, session):
        resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": "WrongPass!99",
        })
        assert resp.status_code == 401
        print(f"  PASS wrong password 401")

    def test_login_nonexistent_user(self, session):
        resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nobody@nowherenull.com", "password": "SomePass123!",
        })
        assert resp.status_code == 401
        print(f"  PASS nonexistent user 401")

    def test_login_missing_fields(self, session):
        resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL})
        assert resp.status_code == 422
        print(f"  PASS login missing fields 422")


# ─────────────────────────────────────────────────────────────────
# AUTH — GET /api/auth/me
# ─────────────────────────────────────────────────────────────────

class TestAuthMe:
    def test_me_valid_jwt(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/auth/me", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == TEST_EMAIL
        assert "referralCode" in data and data["referralCode"]
        assert data["loyaltyPoints"] >= 500
        print(f"  PASS me valid JWT: referralCode={data['referralCode']}")

    def test_me_no_token(self, session):
        """CONTRACT DEVIATION: returns 403 instead of 401 for missing token."""
        resp = session.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} for no-token (contract says 401, FastAPI HTTPBearer returns 403)")

    def test_me_invalid_token(self, session):
        resp = session.get(f"{BASE_URL}/api/auth/me",
                           headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401
        print(f"  PASS invalid token 401")


# ─────────────────────────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────────────────────────

class TestProfile:
    def test_update_profile_valid(self, session, user_headers):
        resp = session.patch(f"{BASE_URL}/api/profile", headers=user_headers, json={
            "firstName": "UpdatedFirst",
            "lastName": "UpdatedLast",
            "phone": "5559876543",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["firstName"] == "UpdatedFirst"
        print(f"  PASS profile update valid")

    def test_update_profile_no_token(self, session):
        """CONTRACT DEVIATION: 403 instead of 401 for missing token."""
        resp = session.patch(f"{BASE_URL}/api/profile", json={"firstName": "X"})
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")


class TestUsername:
    def test_set_valid_username(self, session, user_headers):
        username = f"testuser_{SUFFIX}"
        resp = session.patch(f"{BASE_URL}/api/me/username", headers=user_headers, json={
            "username": username
        })
        assert resp.status_code == 200
        assert resp.json()["username"] == username
        print(f"  PASS set username: {username}")

    def test_reserved_username(self, session, user_headers):
        resp = session.patch(f"{BASE_URL}/api/me/username", headers=user_headers, json={
            "username": "admin"
        })
        assert resp.status_code == 400
        print(f"  PASS reserved username 400")

    def test_username_too_short(self, session, user_headers):
        resp = session.patch(f"{BASE_URL}/api/me/username", headers=user_headers, json={
            "username": "ab"
        })
        assert resp.status_code == 400
        print(f"  PASS username too short 400")

    def test_username_no_token(self, session):
        """CONTRACT DEVIATION: 403 instead of 401 for missing token."""
        resp = session.patch(f"{BASE_URL}/api/me/username", json={"username": "valid123"})
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")

    def test_username_duplicate(self, session, user_headers, test_user2):
        """Duplicate username → 400."""
        # First set a username for user2
        u2_username = f"u2usr_{SUFFIX}"
        session.patch(f"{BASE_URL}/api/me/username",
                      headers={"Authorization": f"Bearer {test_user2['access_token']}"},
                      json={"username": u2_username})
        # Now try to set same username as user1
        resp = session.patch(f"{BASE_URL}/api/me/username", headers=user_headers, json={
            "username": u2_username
        })
        assert resp.status_code == 400
        print(f"  PASS duplicate username 400")


# ─────────────────────────────────────────────────────────────────
# PROFILE UTILITY ENDPOINTS
# ─────────────────────────────────────────────────────────────────

class TestProfileUtils:
    def test_get_referral_earnings(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/me/referral-earnings", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "totalReferralCloudz" in data
        assert "referralOrderCount" in data
        print(f"  PASS referral earnings: {data}")

    def test_get_cloudz_ledger(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/me/cloudz-ledger", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        types = [e.get("type") for e in data]
        assert "signup_bonus" in types, f"Expected signup_bonus in ledger, found: {types}"
        print(f"  PASS cloudz ledger: {len(data)} entries, has signup_bonus")

    def test_get_coupon(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/me/coupon", headers=user_headers)
        assert resp.status_code == 200
        assert "coupon" in resp.json()
        print(f"  PASS coupon: {resp.json()}")

    def test_referral_earnings_no_token(self, session):
        """CONTRACT DEVIATION: 403 instead of 401."""
        resp = session.get(f"{BASE_URL}/api/me/referral-earnings")
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")

    def test_cloudz_ledger_no_token(self, session):
        """CONTRACT DEVIATION: 403 instead of 401."""
        resp = session.get(f"{BASE_URL}/api/me/cloudz-ledger")
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")


# ─────────────────────────────────────────────────────────────────
# PRODUCTS
# ─────────────────────────────────────────────────────────────────

class TestProducts:
    def test_list_products_public(self, session):
        resp = session.get(f"{BASE_URL}/api/products")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"  PASS list products: {len(resp.json())} products")

    def test_get_product_valid(self, session, sample_product):
        pid = sample_product["id"]
        resp = session.get(f"{BASE_URL}/api/products/{pid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == pid
        assert "name" in data and "price" in data and "stock" in data
        print(f"  PASS get product: {data['name']}")

    def test_get_product_invalid_id(self, session):
        resp = session.get(f"{BASE_URL}/api/products/000000000000000000000000")
        assert resp.status_code == 404
        print(f"  PASS product 404")

    def test_create_product_non_admin_403(self, session, user_headers):
        brands = session.get(f"{BASE_URL}/api/brands").json()
        bid = brands[0]["id"] if brands else "000000000000000000000000"
        resp = session.post(f"{BASE_URL}/api/products", headers=user_headers, json={
            "name": "UnauthorizedProduct",
            "brandId": bid,
            "category": "test",
            "image": "https://example.com/img.jpg",
            "puffCount": 500,
            "flavor": "mint",
            "nicotinePercent": 5.0,
            "price": 10.0,
            "stock": 10,
        })
        assert resp.status_code == 403
        print(f"  PASS create product non-admin 403")

    def test_create_product_no_auth(self, session):
        """CONTRACT DEVIATION: 403 instead of 401 for missing token."""
        resp = session.post(f"{BASE_URL}/api/products", json={
            "name": "NoAuth", "brandId": "x", "category": "t",
            "image": "x", "puffCount": 500, "flavor": "m",
            "nicotinePercent": 5.0, "price": 10.0, "stock": 10,
        })
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")

    def test_patch_product_non_admin_403(self, session, user_headers, sample_product):
        resp = session.patch(f"{BASE_URL}/api/products/{sample_product['id']}",
                             headers=user_headers, json={"price": 99.0})
        assert resp.status_code == 403
        print(f"  PASS patch product non-admin 403")

    def test_delete_product_non_admin_403(self, session, user_headers, sample_product):
        resp = session.delete(f"{BASE_URL}/api/products/{sample_product['id']}",
                              headers=user_headers)
        assert resp.status_code == 403
        print(f"  PASS delete product non-admin 403")

    def test_admin_create_update_delete_product(self, session, admin_headers):
        brands = session.get(f"{BASE_URL}/api/brands").json()
        if not brands:
            pytest.skip("No brands")
        bid = brands[0]["id"]

        # CREATE
        create = session.post(f"{BASE_URL}/api/products", headers=admin_headers, json={
            "name": f"TEST_P_{SUFFIX}",
            "brandId": bid, "category": "test",
            "image": "https://example.com/img.jpg",
            "puffCount": 500, "flavor": "mint",
            "nicotinePercent": 5.0, "price": 10.0, "stock": 50,
        })
        assert create.status_code == 200, f"Create product failed: {create.text}"
        pid = create.json()["id"]
        assert create.json()["name"] == f"TEST_P_{SUFFIX}"
        print(f"  PASS admin create product: {pid}")

        # UPDATE
        upd = session.patch(f"{BASE_URL}/api/products/{pid}", headers=admin_headers, json={"price": 15.0})
        assert upd.status_code == 200
        assert upd.json()["price"] == 15.0
        print(f"  PASS admin update product")

        # STOCK ADJUST
        stock = session.patch(f"{BASE_URL}/api/products/{pid}/stock", headers=admin_headers, json={
            "adjustment": 10, "reason": "restock"
        })
        assert stock.status_code == 200
        assert stock.json()["newStock"] == 60
        print(f"  PASS admin stock adjust: +10 → 60")

        # DELETE
        del_resp = session.delete(f"{BASE_URL}/api/products/{pid}", headers=admin_headers)
        assert del_resp.status_code == 200
        assert session.get(f"{BASE_URL}/api/products/{pid}").status_code == 404
        print(f"  PASS admin delete product then 404")

    def test_stock_adjust_non_admin_403(self, session, user_headers, sample_product):
        resp = session.patch(f"{BASE_URL}/api/products/{sample_product['id']}/stock",
                             headers=user_headers, json={"adjustment": 1})
        assert resp.status_code == 403
        print(f"  PASS stock adjust non-admin 403")

    def test_upload_image_non_admin_403(self, session, user_headers):
        import io
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
            b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        files = {"file": ("test.png", io.BytesIO(png_bytes), "image/png")}
        headers = {"Authorization": user_headers["Authorization"]}
        resp = session.post(f"{BASE_URL}/api/upload/product-image", headers=headers, files=files)
        assert resp.status_code == 403
        print(f"  PASS upload image non-admin 403")


# ─────────────────────────────────────────────────────────────────
# BRANDS
# ─────────────────────────────────────────────────────────────────

class TestBrands:
    def test_get_brands_public(self, session):
        resp = session.get(f"{BASE_URL}/api/brands")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"  PASS get brands: {len(resp.json())} brands")

    def test_create_brand_non_admin_403(self, session, user_headers):
        resp = session.post(f"{BASE_URL}/api/brands", headers=user_headers, json={"name": "Unauth"})
        assert resp.status_code == 403
        print(f"  PASS create brand non-admin 403")

    def test_update_brand_non_admin_403(self, session, user_headers):
        brands = session.get(f"{BASE_URL}/api/brands").json()
        if not brands:
            pytest.skip("No brands")
        resp = session.patch(f"{BASE_URL}/api/brands/{brands[0]['id']}",
                             headers=user_headers, json={"name": "x"})
        assert resp.status_code == 403
        print(f"  PASS update brand non-admin 403")

    def test_delete_brand_non_admin_403(self, session, user_headers):
        brands = session.get(f"{BASE_URL}/api/brands").json()
        if not brands:
            pytest.skip("No brands")
        resp = session.delete(f"{BASE_URL}/api/brands/{brands[0]['id']}", headers=user_headers)
        assert resp.status_code == 403
        print(f"  PASS delete brand non-admin 403")

    def test_admin_brand_crud(self, session, admin_headers):
        # CREATE
        cr = session.post(f"{BASE_URL}/api/brands", headers=admin_headers, json={
            "name": f"TEST_Brand_{SUFFIX}", "isActive": True,
        })
        assert cr.status_code == 200, f"Create brand: {cr.text}"
        bid = cr.json()["id"]

        # UPDATE
        upd = session.patch(f"{BASE_URL}/api/brands/{bid}", headers=admin_headers, json={
            "name": f"TEST_Brand_U_{SUFFIX}"
        })
        assert upd.status_code == 200

        # DELETE
        del_r = session.delete(f"{BASE_URL}/api/brands/{bid}", headers=admin_headers)
        assert del_r.status_code == 200
        print(f"  PASS admin brand CRUD")


# ─────────────────────────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────────────────────────

class TestCategories:
    def test_get_categories_public(self, session):
        resp = session.get(f"{BASE_URL}/api/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list) and len(data) > 0
        print(f"  PASS categories: {data}")


# ─────────────────────────────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────────────────────────────

# module-level state for order IDs
_order_state = {}


class TestOrders:
    def test_create_order_valid(self, session, user_headers, sample_product):
        resp = session.post(f"{BASE_URL}/api/orders", headers=user_headers, json={
            "items": [{"productId": sample_product["id"], "quantity": 1,
                       "name": sample_product["name"], "price": sample_product["price"]}],
            "total": sample_product["price"],
            "pickupTime": "Tomorrow 2PM",
            "paymentMethod": "Zelle",
        })
        assert resp.status_code == 200, f"Create order: {resp.text}"
        order = resp.json()
        assert order["status"] == "Pending Payment"
        assert order["storeCreditApplied"] == 0.0
        _order_state["user_pending_id"] = order["id"]
        print(f"  PASS create order valid: {order['id']}")

    def test_list_orders_own(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/orders", headers=user_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"  PASS list orders: {len(resp.json())}")

    def test_list_orders_no_auth(self, session):
        """CONTRACT DEVIATION: 403 instead of 401 for missing token."""
        resp = session.get(f"{BASE_URL}/api/orders")
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")

    def test_get_order_own(self, session, user_headers):
        oid = _order_state.get("user_pending_id")
        if not oid:
            pytest.skip("No order created")
        resp = session.get(f"{BASE_URL}/api/orders/{oid}", headers=user_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == oid
        print(f"  PASS get own order 200")

    def test_get_order_other_user_403(self, session, user2_headers):
        oid = _order_state.get("user_pending_id")
        if not oid:
            pytest.skip("No order created")
        resp = session.get(f"{BASE_URL}/api/orders/{oid}", headers=user2_headers)
        assert resp.status_code == 403
        print(f"  PASS get other user's order 403")

    def test_cancel_order_pending(self, session, user_headers):
        oid = _order_state.get("user_pending_id")
        if not oid:
            pytest.skip("No order created")
        resp = session.post(f"{BASE_URL}/api/orders/{oid}/cancel", headers=user_headers)
        assert resp.status_code == 200
        print(f"  PASS cancel pending order 200")

    def test_cancel_already_cancelled_400(self, session, user_headers):
        oid = _order_state.get("user_pending_id")
        if not oid:
            pytest.skip("No order created")
        resp = session.post(f"{BASE_URL}/api/orders/{oid}/cancel", headers=user_headers)
        assert resp.status_code == 400
        print(f"  PASS cancel already-cancelled 400")

    def test_create_order_missing_fields(self, session, user_headers):
        """Missing required fields → 422."""
        resp = session.post(f"{BASE_URL}/api/orders", headers=user_headers, json={
            "items": [],  # min_items=1 will fail
        })
        assert resp.status_code == 422
        print(f"  PASS missing order fields 422")

    def test_create_order_no_auth(self, session):
        """CONTRACT DEVIATION: 403 instead of 401 for missing token."""
        resp = session.post(f"{BASE_URL}/api/orders", json={
            "items": [{"productId": "x", "quantity": 1, "name": "x", "price": 1.0}],
            "total": 1.0, "pickupTime": "Soon", "paymentMethod": "Zelle",
        })
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")

    def test_create_order_out_of_stock(self, session, user_headers):
        """Non-existent product → 404."""
        resp = session.post(f"{BASE_URL}/api/orders", headers=user_headers, json={
            "items": [{"productId": "000000000000000000000000", "quantity": 1,
                       "name": "Ghost", "price": 10.0}],
            "total": 10.0, "pickupTime": "Now", "paymentMethod": "Zelle",
        })
        # 404 for non-existent; 409 for actual out-of-stock
        assert resp.status_code in (404, 409)
        print(f"  PASS nonexistent product: {resp.status_code}")

    def test_create_order_store_credit_capped(self, session, admin_headers, sample_product):
        """storeCreditApplied capped at available balance."""
        me = session.get(f"{BASE_URL}/api/auth/me", headers=admin_headers).json()
        available = float(me.get("creditBalance", 0.0))
        request_credit = available + 100.0

        resp = session.post(f"{BASE_URL}/api/orders", headers=admin_headers, json={
            "items": [{"productId": sample_product["id"], "quantity": 1,
                       "name": sample_product["name"], "price": sample_product["price"]}],
            "total": max(sample_product["price"], 1.0),
            "pickupTime": "CreditTest",
            "paymentMethod": "Zelle",
            "storeCreditApplied": request_credit,
        })
        assert resp.status_code == 200, f"store credit order: {resp.text}"
        order = resp.json()
        assert order["storeCreditApplied"] <= available, (
            f"Not capped: applied={order['storeCreditApplied']} > balance={available}"
        )
        _order_state["admin_credit_order_id"] = order["id"]
        print(f"  PASS store credit capped: applied={order['storeCreditApplied']}, requested={request_credit}")


# ─────────────────────────────────────────────────────────────────
# LOYALTY
# ─────────────────────────────────────────────────────────────────

class TestLoyalty:
    def test_get_tiers(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/loyalty/tiers", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "userPoints" in data
        assert "tiers" in data and len(data["tiers"]) == 5
        print(f"  PASS tiers: userPoints={data['userPoints']}")

    def test_get_tiers_no_auth(self, session):
        """CONTRACT DEVIATION: 403 instead of 401."""
        resp = session.get(f"{BASE_URL}/api/loyalty/tiers")
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")

    def test_get_rewards(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/loyalty/rewards", headers=user_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"  PASS rewards: {len(resp.json())}")

    def test_get_history(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/loyalty/history", headers=user_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"  PASS loyalty history")

    def test_get_ledger(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/loyalty/ledger", headers=user_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"  PASS loyalty ledger")

    def test_get_streak(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/loyalty/streak", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "streak" in data and "currentBonus" in data
        print(f"  PASS streak: {data}")

    def test_redeem_insufficient_points_400(self, session, user_headers):
        """New user (500 pts) tries tier_2 (5000 pts) → 400."""
        resp = session.post(f"{BASE_URL}/api/loyalty/redeem", headers=user_headers, json={
            "tierId": "tier_2"
        })
        assert resp.status_code == 400
        print(f"  PASS redeem insufficient 400")

    def test_redeem_valid_tier(self, session, admin_headers):
        """Admin should have >= 1000 pts for tier_1."""
        me = session.get(f"{BASE_URL}/api/auth/me", headers=admin_headers).json()
        if me.get("loyaltyPoints", 0) < 1000:
            # Give admin enough points
            session.post(f"{BASE_URL}/api/admin/users/{ADMIN_ID}/cloudz-adjust",
                         headers=admin_headers, json={"amount": 2000, "description": "test top-up"})

        resp = session.post(f"{BASE_URL}/api/loyalty/redeem", headers=admin_headers, json={
            "tierId": "tier_1"
        })
        if resp.status_code == 400 and "already have an active reward" in resp.text:
            print(f"  NOTE already-active tier_1 reward (idempotent check passed)")
        else:
            assert resp.status_code == 200, f"Redeem failed: {resp.text}"
            data = resp.json()
            assert "rewardId" in data
            assert data["rewardAmount"] == 5.0
            print(f"  PASS redeem tier_1: amount={data['rewardAmount']}")

    def test_redeem_already_active_400(self, session, admin_headers):
        """Second redeem of same tier (while active) → 400."""
        me = session.get(f"{BASE_URL}/api/auth/me", headers=admin_headers).json()
        if me.get("loyaltyPoints", 0) < 1000:
            session.post(f"{BASE_URL}/api/admin/users/{ADMIN_ID}/cloudz-adjust",
                         headers=admin_headers, json={"amount": 2000, "description": "top-up"})

        # First redeem (may succeed or 400 if active)
        r1 = session.post(f"{BASE_URL}/api/loyalty/redeem", headers=admin_headers, json={"tierId": "tier_1"})
        if r1.status_code == 200:
            # Now try again — must be 400
            r2 = session.post(f"{BASE_URL}/api/loyalty/redeem", headers=admin_headers, json={"tierId": "tier_1"})
            assert r2.status_code == 400
            print(f"  PASS redeem already-active 400")
        else:
            # Already active from test_redeem_valid_tier or earlier
            assert r1.status_code == 400
            print(f"  PASS already-active 400 confirmed: {r1.json()}")


# ─────────────────────────────────────────────────────────────────
# LEADERBOARD
# ─────────────────────────────────────────────────────────────────

class TestLeaderboard:
    def test_leaderboard_has_movement_field(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/leaderboard", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "byPoints" in data and "byReferrals" in data
        if data["byPoints"]:
            entry = data["byPoints"][0]
            assert "movement" in entry, f"movement missing: {entry}"
        print(f"  PASS leaderboard: movement field present, {len(data['byPoints'])} entries")

    def test_leaderboard_no_auth(self, session):
        """CONTRACT DEVIATION: 403 instead of 401."""
        resp = session.get(f"{BASE_URL}/api/leaderboard")
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")


# ─────────────────────────────────────────────────────────────────
# ADMIN — USER MANAGEMENT
# ─────────────────────────────────────────────────────────────────

class TestAdminUsers:
    def test_get_all_users_admin(self, session, admin_headers):
        resp = session.get(f"{BASE_URL}/api/admin/users", headers=admin_headers)
        assert resp.status_code == 200
        users = resp.json()
        assert isinstance(users, list) and len(users) >= 1
        print(f"  PASS admin get users: {len(users)}")

    def test_get_all_users_non_admin_403(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/admin/users", headers=user_headers)
        assert resp.status_code == 403
        print(f"  PASS admin users non-admin 403")

    def test_get_all_users_no_auth(self, session):
        """CONTRACT DEVIATION: 403 instead of 401."""
        resp = session.get(f"{BASE_URL}/api/admin/users")
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")

    def test_get_user_profile_admin(self, session, admin_headers, test_user):
        uid = test_user["user"]["id"]
        resp = session.get(f"{BASE_URL}/api/admin/users/{uid}/profile", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data and "orders" in data and "totalSpent" in data
        print(f"  PASS admin user profile: orders={len(data['orders'])}")

    def test_admin_update_user(self, session, admin_headers, test_user):
        uid = test_user["user"]["id"]
        resp = session.patch(f"{BASE_URL}/api/admin/users/{uid}", headers=admin_headers, json={
            "firstName": "AdminUpdated"
        })
        assert resp.status_code == 200
        assert resp.json()["firstName"] == "AdminUpdated"
        print(f"  PASS admin update user")

    def test_admin_cloudz_adjust_positive(self, session, admin_headers, test_user):
        uid = test_user["user"]["id"]
        resp = session.post(f"{BASE_URL}/api/admin/users/{uid}/cloudz-adjust", headers=admin_headers, json={
            "amount": 100, "description": "Test +adjustment"
        })
        assert resp.status_code == 200
        assert "newBalance" in resp.json()
        print(f"  PASS cloudz adjust +100: newBalance={resp.json()['newBalance']}")

    def test_admin_cloudz_adjust_negative(self, session, admin_headers, test_user):
        uid = test_user["user"]["id"]
        resp = session.post(f"{BASE_URL}/api/admin/users/{uid}/cloudz-adjust", headers=admin_headers, json={
            "amount": -50, "description": "Test -adjustment"
        })
        assert resp.status_code == 200
        print(f"  PASS cloudz adjust -50: newBalance={resp.json()['newBalance']}")

    def test_admin_get_cloudz_ledger(self, session, admin_headers, test_user):
        uid = test_user["user"]["id"]
        resp = session.get(f"{BASE_URL}/api/admin/users/{uid}/cloudz-ledger", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"  PASS admin cloudz ledger: {len(resp.json())} entries")

    def test_admin_credit_add(self, session, admin_headers, test_user):
        uid = test_user["user"]["id"]
        resp = session.post(f"{BASE_URL}/api/admin/users/{uid}/credit", headers=admin_headers, json={
            "amount": 10.0, "description": "Test add credit"
        })
        assert resp.status_code == 200
        assert "newCreditBalance" in resp.json()
        print(f"  PASS admin credit add: {resp.json()['newCreditBalance']}")

    def test_admin_credit_deduct(self, session, admin_headers, test_user):
        uid = test_user["user"]["id"]
        profile = session.get(f"{BASE_URL}/api/admin/users/{uid}/profile", headers=admin_headers).json()
        credit = profile["user"].get("creditBalance", 0)
        if credit < 5:
            pytest.skip(f"Insufficient credit ({credit})")
        resp = session.post(f"{BASE_URL}/api/admin/users/{uid}/credit", headers=admin_headers, json={
            "amount": -5.0, "description": "Test deduct credit"
        })
        assert resp.status_code == 200
        print(f"  PASS admin credit deduct")

    def test_admin_set_password_valid(self, session, admin_headers, test_user):
        uid = test_user["user"]["id"]
        resp = session.post(f"{BASE_URL}/api/admin/users/{uid}/set-password", headers=admin_headers, json={
            "newPassword": "NewSecurePass123!"
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        print(f"  PASS admin set password valid")

    def test_admin_set_password_too_short_400(self, session, admin_headers, test_user):
        uid = test_user["user"]["id"]
        resp = session.post(f"{BASE_URL}/api/admin/users/{uid}/set-password", headers=admin_headers, json={
            "newPassword": "short"
        })
        assert resp.status_code == 400
        print(f"  PASS admin set password too-short 400")

    def test_admin_update_notes(self, session, admin_headers, test_user):
        uid = test_user["user"]["id"]
        resp = session.patch(f"{BASE_URL}/api/admin/users/{uid}/notes", headers=admin_headers, json={
            "notes": "Test admin notes"
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        print(f"  PASS admin update notes")

    def test_admin_set_username(self, session, admin_headers, test_user):
        uid = test_user["user"]["id"]
        new_uname = f"adminset_{SUFFIX}"
        resp = session.patch(f"{BASE_URL}/api/admin/users/{uid}/username", headers=admin_headers, json={
            "username": new_uname
        })
        assert resp.status_code == 200
        assert resp.json()["username"] == new_uname
        print(f"  PASS admin set username: {new_uname}")

    def test_admin_set_referrer(self, session, admin_headers, test_user, test_user2):
        uid = test_user["user"]["id"]
        ref_code = test_user2["user"]["referralCode"]
        resp = session.patch(f"{BASE_URL}/api/admin/users/{uid}/referrer", headers=admin_headers, json={
            "referrerIdentifier": ref_code
        })
        assert resp.status_code == 200
        print(f"  PASS admin set referrer")

    def test_admin_force_logout_disposable_user(self, session, admin_headers):
        """Force-logout a DISPOSABLE user (not the test_user) to preserve test_user token."""
        # Register a disposable user
        suf2 = uuid.uuid4().hex[:6]
        time.sleep(2)  # avoid rate limit
        reg = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"TEST_dispose_{suf2}@example.com",
            "password": TEST_PASSWORD,
            "firstName": "Dispose",
            "lastName": "User",
            "dateOfBirth": TEST_DOB,
        })
        if reg.status_code == 429:
            pytest.skip("Rate limit — cannot register disposable user for force-logout test")
        assert reg.status_code == 200
        dispose_id = reg.json()["user"]["id"]

        resp = session.post(f"{BASE_URL}/api/admin/users/{dispose_id}/force-logout",
                            headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        print(f"  PASS admin force logout on disposable user")

        # Cleanup
        session.delete(f"{BASE_URL}/api/admin/users/{dispose_id}", headers=admin_headers)

    def test_admin_merge_users(self, session, admin_headers):
        """Merge two fresh disposable users."""
        suf2 = uuid.uuid4().hex[:6]
        time.sleep(2)  # Rate limit buffer

        r1 = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"TEST_ms_{suf2}@example.com",
            "password": TEST_PASSWORD,
            "firstName": "MrgSrc",
            "lastName": "U",
            "dateOfBirth": TEST_DOB,
        })
        if r1.status_code == 429:
            pytest.skip("Rate limit for merge test")
        assert r1.status_code == 200
        src_id = r1.json()["user"]["id"]

        time.sleep(1)
        r2 = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"TEST_mt_{suf2}@example.com",
            "password": TEST_PASSWORD,
            "firstName": "MrgTgt",
            "lastName": "U",
            "dateOfBirth": TEST_DOB,
        })
        if r2.status_code == 429:
            session.delete(f"{BASE_URL}/api/admin/users/{src_id}", headers=admin_headers)
            pytest.skip("Rate limit for merge target")
        assert r2.status_code == 200
        tgt_id = r2.json()["user"]["id"]

        merge = session.post(f"{BASE_URL}/api/admin/users/merge", headers=admin_headers, json={
            "sourceUserId": src_id, "targetUserId": tgt_id,
        })
        assert merge.status_code == 200
        assert merge.json()["success"] is True
        print(f"  PASS admin merge users")

        session.delete(f"{BASE_URL}/api/admin/users/{src_id}", headers=admin_headers)
        session.delete(f"{BASE_URL}/api/admin/users/{tgt_id}", headers=admin_headers)

    def test_admin_delete_user_nonexistent_404(self, session, admin_headers):
        """Delete non-existent user → 404."""
        resp = session.delete(f"{BASE_URL}/api/admin/users/000000000000000000000000",
                              headers=admin_headers)
        assert resp.status_code == 404
        print(f"  PASS admin delete nonexistent 404")


# ─────────────────────────────────────────────────────────────────
# ADMIN — ORDERS
# ─────────────────────────────────────────────────────────────────

_admin_order_state = {}


class TestAdminOrders:
    def test_get_all_orders_admin(self, session, admin_headers):
        resp = session.get(f"{BASE_URL}/api/admin/orders", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"  PASS admin get all orders: {len(resp.json())}")

    def test_get_all_orders_non_admin_403(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/admin/orders", headers=user_headers)
        assert resp.status_code == 403
        print(f"  PASS admin orders non-admin 403")

    def test_admin_update_order_status_to_paid(self, session, admin_headers, user_headers, sample_product):
        """Create order, mark Paid → loyalty points earned."""
        # Check user's points before
        me_before = session.get(f"{BASE_URL}/api/auth/me", headers=user_headers).json()
        pts_before = me_before["loyaltyPoints"]

        # Create order
        resp = session.post(f"{BASE_URL}/api/orders", headers=user_headers, json={
            "items": [{"productId": sample_product["id"], "quantity": 1,
                       "name": sample_product["name"], "price": sample_product["price"]}],
            "total": sample_product["price"],
            "pickupTime": "Status test",
            "paymentMethod": "Zelle",
        })
        assert resp.status_code == 200, f"Create order for status test: {resp.text}"
        oid = resp.json()["id"]
        order_total = resp.json()["total"]

        # Mark as Paid
        paid = session.patch(f"{BASE_URL}/api/admin/orders/{oid}/status",
                             headers=admin_headers, json={"status": "Paid"})
        assert paid.status_code == 200, f"Status → Paid: {paid.text}"
        _admin_order_state["paid_order_id"] = oid
        _admin_order_state["pts_before"] = pts_before
        _admin_order_state["order_total"] = order_total
        print(f"  PASS admin order → Paid: order_total={order_total}")

    def test_loyalty_points_earned_on_paid(self, session, user_headers):
        """User earns total*3 points when order is marked Paid."""
        if "pts_before" not in _admin_order_state:
            pytest.skip("No prior order state")
        me_after = session.get(f"{BASE_URL}/api/auth/me", headers=user_headers).json()
        pts_after = me_after["loyaltyPoints"]
        expected = int(_admin_order_state["order_total"]) * 3
        actual = pts_after - _admin_order_state["pts_before"]
        assert actual == expected, f"Expected +{expected} pts, got +{actual}"
        print(f"  PASS loyalty on Paid: +{actual} pts (total*3={expected})")

    def test_admin_order_edit(self, session, admin_headers, sample_product):
        oid = _admin_order_state.get("paid_order_id")
        if not oid:
            pytest.skip("No paid order")
        resp = session.patch(f"{BASE_URL}/api/admin/orders/{oid}/edit",
                             headers=admin_headers, json={
            "items": [{"productId": sample_product["id"], "quantity": 1,
                       "name": sample_product["name"], "price": sample_product["price"]}],
            "total": sample_product["price"],
            "adminNotes": "Edited by test",
        })
        assert resp.status_code == 200
        print(f"  PASS admin order edit")


# ─────────────────────────────────────────────────────────────────
# ADMIN — ANALYTICS, LEDGER, CHATS, SUPPORT
# ─────────────────────────────────────────────────────────────────

class TestAdminAnalytics:
    def test_get_analytics_admin(self, session, admin_headers):
        resp = session.get(f"{BASE_URL}/api/admin/analytics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        for field in ["totalOrders", "totalRevenue", "avgOrderValue",
                      "repeatPurchaseRate", "revenueByPayment", "topProducts",
                      "topCustomers", "lowInventory"]:
            assert field in data, f"Missing field: {field}"
        assert isinstance(data["repeatPurchaseRate"], (int, float))
        print(f"  PASS analytics: repeatPurchaseRate={data['repeatPurchaseRate']}")

    def test_analytics_non_admin_403(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/admin/analytics", headers=user_headers)
        assert resp.status_code == 403
        print(f"  PASS analytics non-admin 403")

    def test_get_admin_ledger(self, session, admin_headers):
        resp = session.get(f"{BASE_URL}/api/admin/ledger", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data and "total" in data
        print(f"  PASS admin ledger: {data['total']} total entries")

    def test_admin_ledger_non_admin_403(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/admin/ledger", headers=user_headers)
        assert resp.status_code == 403
        print(f"  PASS ledger non-admin 403")

    def test_get_admin_chats(self, session, admin_headers):
        resp = session.get(f"{BASE_URL}/api/admin/chats", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"  PASS admin chats: {len(resp.json())} sessions")

    def test_get_support_tickets_admin(self, session, admin_headers):
        resp = session.get(f"{BASE_URL}/api/admin/support/tickets", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tickets" in data and "total" in data
        print(f"  PASS admin support tickets: {data['total']} total")


# ─────────────────────────────────────────────────────────────────
# ADMIN — REVIEWS
# ─────────────────────────────────────────────────────────────────

_review_state = {}


class TestAdminReviews:
    def test_get_all_reviews_admin(self, session, admin_headers):
        resp = session.get(f"{BASE_URL}/api/admin/reviews", headers=admin_headers)
        assert resp.status_code == 200
        reviews = resp.json()
        assert isinstance(reviews, list)
        _review_state["reviews"] = reviews
        print(f"  PASS admin get reviews: {len(reviews)}")

    def test_admin_update_review(self, session, admin_headers):
        reviews = _review_state.get("reviews", [])
        if not reviews:
            pytest.skip("No reviews")
        rid = reviews[0]["id"]
        resp = session.patch(f"{BASE_URL}/api/admin/reviews/{rid}", headers=admin_headers, json={
            "isHidden": True
        })
        assert resp.status_code == 200
        # Reset
        session.patch(f"{BASE_URL}/api/admin/reviews/{rid}", headers=admin_headers, json={"isHidden": False})
        print(f"  PASS admin update review")

    def test_admin_delete_nonexistent_review_404(self, session, admin_headers):
        resp = session.delete(f"{BASE_URL}/api/admin/reviews/000000000000000000000000",
                              headers=admin_headers)
        assert resp.status_code == 404
        print(f"  PASS admin delete nonexistent review 404")

    def test_admin_reviews_non_admin_403(self, session, user_headers):
        resp = session.get(f"{BASE_URL}/api/admin/reviews", headers=user_headers)
        assert resp.status_code == 403
        print(f"  PASS admin reviews non-admin 403")


# ─────────────────────────────────────────────────────────────────
# REVIEWS — Public + user endpoints
# ─────────────────────────────────────────────────────────────────

class TestReviews:
    def test_get_product_reviews_public(self, session, sample_product):
        resp = session.get(f"{BASE_URL}/api/reviews/product/{sample_product['id']}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"  PASS product reviews public: {len(resp.json())}")

    def test_check_can_review(self, session, user_headers, sample_product):
        resp = session.get(f"{BASE_URL}/api/reviews/check/{sample_product['id']}",
                           headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "canReview" in data and "hasReviewed" in data
        print(f"  PASS check can review: {data}")

    def test_post_review_requires_purchase_403(self, session, user_headers, sample_product):
        """Review without qualifying purchase → 403."""
        resp = session.post(f"{BASE_URL}/api/reviews", headers=user_headers, json={
            "productId": sample_product["id"],
            "orderId": "000000000000000000000000",
            "rating": 5,
            "comment": "Test"
        })
        # 403 = no qualifying purchase; 400 = already reviewed
        assert resp.status_code in (400, 403), f"Expected 403/400 got {resp.status_code}: {resp.text}"
        print(f"  PASS review requires purchase: {resp.status_code}")

    def test_post_review_no_auth(self, session, sample_product):
        """CONTRACT DEVIATION: 403 instead of 401 for missing token."""
        resp = session.post(f"{BASE_URL}/api/reviews", json={
            "productId": sample_product["id"],
            "orderId": "000000000000000000000000",
            "rating": 5,
        })
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")


# ─────────────────────────────────────────────────────────────────
# PUSH & SUPPORT
# ─────────────────────────────────────────────────────────────────

class TestPushAndSupport:
    def test_register_push_token_invalid_400(self, session, user_headers):
        resp = session.post(f"{BASE_URL}/api/push/register", headers=user_headers, json={
            "token": "InvalidToken123"
        })
        assert resp.status_code == 400
        print(f"  PASS push invalid token 400")

    def test_register_push_token_valid(self, session, user_headers):
        resp = session.post(f"{BASE_URL}/api/push/register", headers=user_headers, json={
            "token": "ExponentPushToken[test1234567890]"
        })
        assert resp.status_code == 200
        print(f"  PASS push valid token 200")

    def test_push_no_auth(self, session):
        """CONTRACT DEVIATION: 403 instead of 401 for missing token."""
        resp = session.post(f"{BASE_URL}/api/push/register", json={"token": "ExponentPushToken[x]"})
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")

    def test_create_support_ticket(self, session, user_headers):
        resp = session.post(f"{BASE_URL}/api/support/tickets", headers=user_headers, json={
            "subject": "Test Support",
            "message": "Contract test ticket."
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        print(f"  PASS create ticket: {data['id']}")

    def test_create_ticket_no_auth(self, session):
        """CONTRACT DEVIATION: 403 instead of 401 for missing token."""
        resp = session.post(f"{BASE_URL}/api/support/tickets", json={
            "subject": "x", "message": "x"
        })
        assert resp.status_code == 401
        print(f"  ACTUAL {resp.status_code} (contract says 401)")


# ─────────────────────────────────────────────────────────────────
# FLOW 1 — register → login → /api/auth/me → verify referralCode
# ─────────────────────────────────────────────────────────────────

class TestFlow1UserRegistration:
    def test_flow1(self, session, admin_headers):
        suf = uuid.uuid4().hex[:6]
        email = f"TEST_flow1_{suf}@example.com"
        time.sleep(2)  # rate limit buffer

        reg = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": TEST_PASSWORD,
            "firstName": "FlowOne",
            "lastName": "User",
            "dateOfBirth": "1988-06-15",
        })
        if reg.status_code == 429:
            pytest.skip("Rate limited — try again later")
        assert reg.status_code == 200, f"Register failed: {reg.text}"
        ref_code = reg.json()["user"]["referralCode"]
        assert reg.json()["user"]["loyaltyPoints"] == 500

        login = session.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": TEST_PASSWORD})
        assert login.status_code == 200
        token = login.json()["access_token"]

        me = session.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        assert me["email"] == email
        assert me["referralCode"] == ref_code
        assert me["loyaltyPoints"] == 500

        print(f"  PASS FLOW 1: register→login→me verified, referralCode={ref_code}")

        user_id = me["id"]
        session.delete(f"{BASE_URL}/api/admin/users/{user_id}", headers=admin_headers)


# ─────────────────────────────────────────────────────────────────
# FLOW 2 — order with storeCreditApplied → credit deducted → cancel → credit restored
# ─────────────────────────────────────────────────────────────────

class TestFlow2Shopping:
    def test_flow2(self, session, admin_headers, sample_product):
        # Get or set admin credit
        me = session.get(f"{BASE_URL}/api/auth/me", headers=admin_headers).json()
        credit_before = float(me.get("creditBalance", 0.0))
        if credit_before < 5:
            session.post(f"{BASE_URL}/api/admin/users/{ADMIN_ID}/credit", headers=admin_headers, json={
                "amount": 20.0, "description": "Flow2 test credit top-up"
            })
            credit_before += 20.0

        credit_to_apply = 5.0

        # Create order with store credit
        products = session.get(f"{BASE_URL}/api/products").json()
        stocked = [p for p in products if p.get("stock", 0) > 1]
        if not stocked:
            pytest.skip("No stocked products")
        prod = sorted(stocked, key=lambda p: p["stock"], reverse=True)[0]

        resp = session.post(f"{BASE_URL}/api/orders", headers=admin_headers, json={
            "items": [{"productId": prod["id"], "quantity": 1,
                       "name": prod["name"], "price": prod["price"]}],
            "total": max(prod["price"], credit_to_apply + 0.01),
            "pickupTime": "Flow2 test",
            "paymentMethod": "Zelle",
            "storeCreditApplied": credit_to_apply,
        })
        assert resp.status_code == 200, f"Flow2 order failed: {resp.text}"
        order = resp.json()
        applied = order["storeCreditApplied"]
        oid = order["id"]

        me2 = session.get(f"{BASE_URL}/api/auth/me", headers=admin_headers).json()
        credit_after_order = float(me2["creditBalance"])
        assert abs(credit_after_order - (credit_before - applied)) < 0.01, (
            f"Credit deduction wrong: {credit_before} - {applied} != {credit_after_order}"
        )
        print(f"  PASS FLOW 2 credit deducted: {credit_before} → {credit_after_order}")

        # Cancel → credit restored
        cancel = session.post(f"{BASE_URL}/api/orders/{oid}/cancel", headers=admin_headers)
        assert cancel.status_code == 200

        me3 = session.get(f"{BASE_URL}/api/auth/me", headers=admin_headers).json()
        credit_restored = float(me3["creditBalance"])
        assert abs(credit_restored - credit_before) < 0.01, (
            f"Credit not restored: before={credit_before}, after_cancel={credit_restored}"
        )
        print(f"  PASS FLOW 2 complete: credit restored={credit_restored}")


# ─────────────────────────────────────────────────────────────────
# FLOW 3 — earn Cloudz → redeem tier → verify reward
# ─────────────────────────────────────────────────────────────────

class TestFlow3Loyalty:
    def test_flow3(self, session, admin_headers, sample_product):
        me = session.get(f"{BASE_URL}/api/auth/me", headers=admin_headers).json()
        pts = me["loyaltyPoints"]
        if pts < 1000:
            session.post(f"{BASE_URL}/api/admin/users/{ADMIN_ID}/cloudz-adjust",
                         headers=admin_headers, json={
                "amount": 1500 - pts, "description": "Flow3 top-up"
            })

        redeem = session.post(f"{BASE_URL}/api/loyalty/redeem", headers=admin_headers, json={
            "tierId": "tier_1"
        })
        if redeem.status_code == 400 and "already have an active reward" in redeem.text:
            print(f"  NOTE already has active tier_1 reward")
        else:
            assert redeem.status_code == 200, f"Redeem failed: {redeem.text}"
            assert "rewardId" in redeem.json()

        rewards = session.get(f"{BASE_URL}/api/loyalty/rewards", headers=admin_headers).json()
        assert len(rewards) >= 1, f"Expected rewards, got: {rewards}"
        print(f"  PASS FLOW 3: {len(rewards)} active reward(s)")


# ─────────────────────────────────────────────────────────────────
# FLOW 4 — Referral: register with code → both get 500 → order Paid → referrer gets reward
# ─────────────────────────────────────────────────────────────────

class TestFlow4Referral:
    def test_flow4(self, session, admin_headers, sample_product):
        suf = uuid.uuid4().hex[:6]
        time.sleep(3)  # rate limit buffer

        # Register referrer
        r1 = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"TEST_ref_{suf}@example.com",
            "password": TEST_PASSWORD,
            "firstName": "Referrer",
            "lastName": "User",
            "dateOfBirth": "1985-03-20",
        })
        if r1.status_code == 429:
            pytest.skip("Rate limit — cannot run Flow4")
        assert r1.status_code == 200
        referrer_id = r1.json()["user"]["id"]
        referrer_code = r1.json()["user"]["referralCode"]
        referrer_token = r1.json()["access_token"]
        referrer_pts_0 = r1.json()["user"]["loyaltyPoints"]  # 500
        assert referrer_pts_0 == 500

        time.sleep(1)
        # Register new user with referral code
        r2 = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"TEST_referd_{suf}@example.com",
            "password": TEST_PASSWORD,
            "firstName": "Referred",
            "lastName": "User",
            "dateOfBirth": "1992-07-10",
            "referralCode": referrer_code,
        })
        if r2.status_code == 429:
            session.delete(f"{BASE_URL}/api/admin/users/{referrer_id}", headers=admin_headers)
            pytest.skip("Rate limit for referred user")
        assert r2.status_code == 200
        new_user_id = r2.json()["user"]["id"]
        new_user_pts_0 = r2.json()["user"]["loyaltyPoints"]
        new_user_token = r2.json()["access_token"]
        assert new_user_pts_0 == 500, f"New user should have 500 pts, got {new_user_pts_0}"

        # Verify referrer got +500
        referrer_me = session.get(f"{BASE_URL}/api/auth/me",
                                   headers={"Authorization": f"Bearer {referrer_token}"}).json()
        assert referrer_me["loyaltyPoints"] == 1000, (
            f"Referrer should have 1000 pts (500+500), got {referrer_me['loyaltyPoints']}"
        )
        print(f"  PASS FLOW 4 signup bonuses: new_user=500, referrer=1000")

        # Create order as referred user
        prod = sample_product
        order = session.post(f"{BASE_URL}/api/orders",
                             headers={"Authorization": f"Bearer {new_user_token}"},
                             json={
            "items": [{"productId": prod["id"], "quantity": 1,
                       "name": prod["name"], "price": prod["price"]}],
            "total": prod["price"],
            "pickupTime": "Flow4",
            "paymentMethod": "Zelle",
        })
        assert order.status_code == 200, f"Referred user order: {order.text}"
        oid = order.json()["id"]
        total = float(order.json()["total"])

        # Mark Paid
        paid = session.patch(f"{BASE_URL}/api/admin/orders/{oid}/status",
                             headers=admin_headers, json={"status": "Paid"})
        assert paid.status_code == 200

        # Verify referrer gets math.floor(total*0.5) Cloudz
        expected_reward = math.floor(total * 0.5)
        referrer_after = session.get(f"{BASE_URL}/api/auth/me",
                                      headers={"Authorization": f"Bearer {referrer_token}"}).json()
        pts_gained = referrer_after["loyaltyPoints"] - referrer_me["loyaltyPoints"]
        assert pts_gained == expected_reward, (
            f"Expected referrer +{expected_reward} (floor({total}*0.5)), got +{pts_gained}"
        )
        print(f"  PASS FLOW 4 referral reward: +{pts_gained} pts (total={total})")

        # Cleanup
        session.delete(f"{BASE_URL}/api/admin/users/{referrer_id}", headers=admin_headers)
        session.delete(f"{BASE_URL}/api/admin/users/{new_user_id}", headers=admin_headers)


# ─────────────────────────────────────────────────────────────────
# FLOW 5 — Admin: login → users → cloudz-adjust → order status → analytics
# ─────────────────────────────────────────────────────────────────

class TestFlow5Admin:
    def test_flow5(self, session, admin_headers, user_headers, sample_product, test_user):
        # GET users
        users = session.get(f"{BASE_URL}/api/admin/users", headers=admin_headers)
        assert users.status_code == 200
        assert len(users.json()) >= 1
        print(f"  PASS FLOW 5 users: {len(users.json())}")

        # POST cloudz-adjust
        uid = test_user["user"]["id"]
        adj = session.post(f"{BASE_URL}/api/admin/users/{uid}/cloudz-adjust",
                            headers=admin_headers, json={"amount": 25, "description": "Flow5"})
        assert adj.status_code == 200
        print(f"  PASS FLOW 5 cloudz-adjust: newBalance={adj.json()['newBalance']}")

        # Create order, mark Paid
        order = session.post(f"{BASE_URL}/api/orders", headers=user_headers, json={
            "items": [{"productId": sample_product["id"], "quantity": 1,
                       "name": sample_product["name"], "price": sample_product["price"]}],
            "total": sample_product["price"],
            "pickupTime": "Flow5",
            "paymentMethod": "Zelle",
        })
        assert order.status_code == 200, f"Flow5 order: {order.text}"
        oid = order.json()["id"]

        status = session.patch(f"{BASE_URL}/api/admin/orders/{oid}/status",
                                headers=admin_headers, json={"status": "Paid"})
        assert status.status_code == 200
        print(f"  PASS FLOW 5 order → Paid")

        # GET analytics
        analytics = session.get(f"{BASE_URL}/api/admin/analytics", headers=admin_headers)
        assert analytics.status_code == 200
        data = analytics.json()
        assert "repeatPurchaseRate" in data and "totalOrders" in data
        print(f"  PASS FLOW 5 analytics: totalOrders={data['totalOrders']}, repeatPurchaseRate={data['repeatPurchaseRate']}")


# ─────────────────────────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────────────────────────

class TestCleanup:
    def test_cleanup_test_users(self, session, admin_headers):
        users = session.get(f"{BASE_URL}/api/admin/users", headers=admin_headers).json()
        cleaned = 0
        for u in users:
            if u.get("email", "").startswith("TEST_"):
                r = session.delete(f"{BASE_URL}/api/admin/users/{u['id']}", headers=admin_headers)
                if r.status_code == 200:
                    cleaned += 1
        print(f"  PASS cleanup: {cleaned} TEST_ users removed")
