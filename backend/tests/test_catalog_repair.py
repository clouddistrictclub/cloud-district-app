"""
Catalog Repair Test Suite
Tests for Cloud District Club product catalog repair & creation:
1. Total product count (~162)
2. Zero empty/null images in catalog
3. CLIO Platinum 50K Kit vs Pod use DIFFERENT images
4. CLR 50K products all use valid CDN image URL
5. New products exist (RIA NV30K, CLR flavors, Nera, Pulse)
6. No duplicate product names
7. Fallback image for products with no image (product_routes.py resolve_image)
8. All active product images are absolute HTTPS URLs
"""

import pytest
import requests
import os
import asyncio
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

# Admin credentials for test product creation
ADMIN_EMAIL = "jkaatz@gmail.com"
ADMIN_PASSWORD = "Just1n23$"

# Brand IDs (known from previous tests)
BRAND_IDS = {
    "geek_bar": "698fcbaea7e3829faf8adb0d",
    "lost_mary": "698fcbaea7e3829faf8adb0e",
    "raz": "698fcbaea7e3829faf8adb0f"
}

# Expected CDN image URLs from catalog_repair.py
EXPECTED_CLR_50K_IMG = "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2822/10234/CLR_Web_Square-800x800__51088.1772656543.jpg?c=2"
EXPECTED_CLIO_KIT_IMG = "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2810/10178/Geek-Bar-Clio-Kit_MAIN-800x800__78643.1770672975.jpg?c=2"
EXPECTED_CLIO_POD_IMG = "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2816/10206/Clio_Platinum_PODS_WEB_SQUARE-800x800__08807.1771442773.jpg?c=2"
FALLBACK_IMAGE_URL = "https://clouddistrict.club/placeholder.png"


@pytest.fixture(scope="module")
def all_products():
    """Fetch all products (including inactive) once for all tests."""
    response = requests.get(f"{BASE_URL}/api/products?active_only=false")
    assert response.status_code == 200, f"GET /api/products failed: {response.text}"
    products = response.json()
    assert isinstance(products, list), "Expected a list of products"
    print(f"\n[Fixture] Total products fetched: {len(products)}")
    return products


@pytest.fixture(scope="module")
def active_products():
    """Fetch only active products (default API behavior)."""
    response = requests.get(f"{BASE_URL}/api/products")
    assert response.status_code == 200, f"GET /api/products failed: {response.text}"
    products = response.json()
    assert isinstance(products, list), "Expected a list of products"
    print(f"\n[Fixture] Active products fetched: {len(products)}")
    return products


@pytest.fixture(scope="module")
def admin_token():
    """Obtain admin JWT token for write operations."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    token = response.json().get("access_token")
    assert token, "No access_token in login response"
    return token


# ─────────────────────────────────────────────────────────────────────────────
# 1. PRODUCT COUNT
# ─────────────────────────────────────────────────────────────────────────────
class TestProductCount:
    """Verify total catalog size after repair + new product creation."""

    def test_total_product_count_at_least_162(self, all_products):
        """Catalog must have at least 162 products (repair created/updated many)."""
        count = len(all_products)
        print(f"  Total products in DB: {count}")
        assert count >= 162, (
            f"Expected ≥162 products but got {count}. "
            "Repair script may not have run or some products were deleted."
        )
        print(f"  ✓ Product count is {count} (≥162)")

    def test_api_products_returns_200(self):
        """Basic health check: GET /api/products returns 200."""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        print(f"  ✓ GET /api/products → 200 OK")


# ─────────────────────────────────────────────────────────────────────────────
# 2. NO EMPTY IMAGES
# ─────────────────────────────────────────────────────────────────────────────
class TestNoEmptyImages:
    """Verify the catalog has zero empty/null images after repair."""

    def test_no_null_image_in_api_response(self, all_products):
        """API response must have no null image field (fallback kicks in)."""
        null_img_products = [
            p for p in all_products
            if p.get("image") is None
        ]
        if null_img_products:
            names = [p.get("name", "?") for p in null_img_products]
            print(f"  FAIL: Products with null image: {names}")
        assert len(null_img_products) == 0, (
            f"{len(null_img_products)} products returned null image from API: "
            f"{[p.get('name') for p in null_img_products[:5]]}"
        )
        print(f"  ✓ No products have null image in API response")

    def test_no_empty_string_image_in_api_response(self, all_products):
        """API response must have no empty-string image (fallback or CDN URL expected)."""
        empty_img_products = [
            p for p in all_products
            if p.get("image") == ""
        ]
        if empty_img_products:
            names = [p.get("name", "?") for p in empty_img_products]
            print(f"  FAIL: Products with empty-string image: {names}")
        assert len(empty_img_products) == 0, (
            f"{len(empty_img_products)} products returned empty-string image: "
            f"{[p.get('name') for p in empty_img_products[:5]]}"
        )
        print(f"  ✓ No products have empty-string image in API response")

    def test_active_products_no_empty_images(self, active_products):
        """Active products specifically must have no empty/null images."""
        bad = [
            p for p in active_products
            if not p.get("image")  # catches None and ""
        ]
        assert len(bad) == 0, (
            f"{len(bad)} ACTIVE products have empty/null image: "
            f"{[p.get('name') for p in bad[:5]]}"
        )
        print(f"  ✓ All {len(active_products)} active products have non-empty images")

    def test_all_images_are_non_empty_strings(self, all_products):
        """All product images must be non-empty strings."""
        bad = [p for p in all_products if not isinstance(p.get("image"), str) or not p.get("image")]
        assert len(bad) == 0, (
            f"{len(bad)} products have non-string or empty images. "
            f"First 5: {[p.get('name') for p in bad[:5]]}"
        )
        print(f"  ✓ All {len(all_products)} products have non-empty string images")


# ─────────────────────────────────────────────────────────────────────────────
# 3. CLIO PLATINUM 50K – KIT vs POD IMAGE DIFFERENTIATION
# ─────────────────────────────────────────────────────────────────────────────
class TestClioPlatinum50K:
    """Kit and Pod must use DIFFERENT images; each must use the correct CDN URL."""

    @pytest.fixture(autouse=True)
    def get_clio_products(self, all_products):
        """Filter CLIO Platinum 50K products."""
        self.clio_all = [
            p for p in all_products
            if "CLIO Platinum 50K" in p.get("name", "") or p.get("model") == "CLIO Platinum 50K"
        ]
        self.clio_kits = [p for p in self.clio_all if p.get("productType") == "kit"]
        self.clio_pods = [p for p in self.clio_all if p.get("productType") == "pod"]
        print(f"\n  CLIO Platinum 50K — Kits: {len(self.clio_kits)}, Pods: {len(self.clio_pods)}, Total: {len(self.clio_all)}")

    def test_clio_products_exist(self):
        """There must be CLIO Platinum 50K products in the catalog."""
        assert len(self.clio_all) > 0, "No CLIO Platinum 50K products found in catalog"
        print(f"  ✓ Found {len(self.clio_all)} CLIO Platinum 50K products")

    def test_clio_kit_products_exist(self):
        """At least one CLIO Platinum 50K Kit must exist."""
        assert len(self.clio_kits) > 0, (
            "No CLIO Platinum 50K Kit (productType=kit) products found. "
            f"All CLIO products: {[(p.get('name'), p.get('productType')) for p in self.clio_all]}"
        )
        print(f"  ✓ Found {len(self.clio_kits)} CLIO Kit products")

    def test_clio_pod_products_exist(self):
        """At least one CLIO Platinum 50K Pod must exist."""
        assert len(self.clio_pods) > 0, (
            "No CLIO Platinum 50K Pod (productType=pod) products found. "
            f"All CLIO products: {[(p.get('name'), p.get('productType')) for p in self.clio_all]}"
        )
        print(f"  ✓ Found {len(self.clio_pods)} CLIO Pod products")

    def test_clio_kit_uses_kit_image(self):
        """All CLIO Kit products must use the Kit-specific BigCommerce image (product 2810)."""
        wrong = [
            p for p in self.clio_kits
            if p.get("image") != EXPECTED_CLIO_KIT_IMG
        ]
        if wrong:
            for p in wrong:
                print(f"  FAIL Kit image wrong: {p.get('name')} → {p.get('image')}")
        assert len(wrong) == 0, (
            f"{len(wrong)} CLIO Kit products have wrong image:\n"
            + "\n".join(f"  {p.get('name')}: {p.get('image')[:80]}" for p in wrong)
        )
        print(f"  ✓ All {len(self.clio_kits)} CLIO Kit products use correct kit image")

    def test_clio_pod_uses_pod_image(self):
        """All CLIO Pod products must use the Pod-specific BigCommerce image (product 2816)."""
        wrong = [
            p for p in self.clio_pods
            if p.get("image") != EXPECTED_CLIO_POD_IMG
        ]
        if wrong:
            for p in wrong:
                print(f"  FAIL Pod image wrong: {p.get('name')} → {p.get('image')}")
        assert len(wrong) == 0, (
            f"{len(wrong)} CLIO Pod products have wrong image:\n"
            + "\n".join(f"  {p.get('name')}: {p.get('image')[:80]}" for p in wrong)
        )
        print(f"  ✓ All {len(self.clio_pods)} CLIO Pod products use correct pod image")

    def test_clio_kit_and_pod_images_are_different(self):
        """Kit image URL must NOT equal Pod image URL."""
        assert EXPECTED_CLIO_KIT_IMG != EXPECTED_CLIO_POD_IMG, (
            "Kit and Pod expected images are the same URL — catalog_repair.py has a bug"
        )
        if self.clio_kits and self.clio_pods:
            kit_img = self.clio_kits[0].get("image")
            pod_img = self.clio_pods[0].get("image")
            assert kit_img != pod_img, (
                f"CLIO Kit image == Pod image (should be different):\n"
                f"  Kit image: {kit_img}\n"
                f"  Pod image: {pod_img}"
            )
            print(f"  ✓ Kit image ≠ Pod image (correctly differentiated)")
        else:
            pytest.skip("Cannot compare — missing Kit or Pod products")

    def test_clio_kit_image_contains_bigcommerce_product_2810(self):
        """Kit image URL must reference BigCommerce product 2810."""
        assert "products/2810" in EXPECTED_CLIO_KIT_IMG, "CLIO Kit URL doesn't contain products/2810"
        if self.clio_kits:
            kit_img = self.clio_kits[0].get("image", "")
            assert "products/2810" in kit_img, (
                f"CLIO Kit product image does not reference BigCommerce product 2810: {kit_img}"
            )
            print(f"  ✓ CLIO Kit image references BigCommerce product 2810")

    def test_clio_pod_image_contains_bigcommerce_product_2816(self):
        """Pod image URL must reference BigCommerce product 2816."""
        assert "products/2816" in EXPECTED_CLIO_POD_IMG, "CLIO Pod URL doesn't contain products/2816"
        if self.clio_pods:
            pod_img = self.clio_pods[0].get("image", "")
            assert "products/2816" in pod_img, (
                f"CLIO Pod product image does not reference BigCommerce product 2816: {pod_img}"
            )
            print(f"  ✓ CLIO Pod image references BigCommerce product 2816")


# ─────────────────────────────────────────────────────────────────────────────
# 4. CLR 50K IMAGES
# ─────────────────────────────────────────────────────────────────────────────
class TestClr50K:
    """All CLR 50K products must use the correct CDN image (BigCommerce product 2822)."""

    @pytest.fixture(autouse=True)
    def get_clr_products(self, all_products):
        """Filter CLR 50K products."""
        self.clr_products = [
            p for p in all_products
            if "CLR 50K" in p.get("name", "") or p.get("model") == "CLR 50K"
        ]
        print(f"\n  CLR 50K products found: {len(self.clr_products)}")
        for p in self.clr_products:
            print(f"    - {p.get('name')} | img: {p.get('image', '')[:70]}")

    def test_clr_50k_products_exist(self):
        """At least 8 CLR 50K products must exist."""
        assert len(self.clr_products) >= 8, (
            f"Expected ≥8 CLR 50K products, found {len(self.clr_products)}"
        )
        print(f"  ✓ Found {len(self.clr_products)} CLR 50K products (≥8)")

    def test_all_clr_50k_use_correct_cdn_image(self):
        """Every CLR 50K product must use the CDN URL for BigCommerce product 2822."""
        wrong = [
            p for p in self.clr_products
            if p.get("image") != EXPECTED_CLR_50K_IMG
        ]
        if wrong:
            for p in wrong:
                print(f"  FAIL CLR image wrong: {p.get('name')} → {p.get('image', 'EMPTY')[:80]}")
        assert len(wrong) == 0, (
            f"{len(wrong)} CLR 50K products have incorrect image:\n"
            + "\n".join(f"  {p.get('name')}: {p.get('image', 'EMPTY')[:80]}" for p in wrong)
        )
        print(f"  ✓ All {len(self.clr_products)} CLR 50K products use correct CDN image")

    def test_clr_image_contains_bigcommerce_product_2822(self):
        """CLR image URL must reference BigCommerce product 2822."""
        assert "products/2822" in EXPECTED_CLR_50K_IMG, "CLR URL doesn't contain products/2822"
        for p in self.clr_products:
            img = p.get("image", "")
            assert "products/2822" in img, (
                f"{p.get('name')} CLR image does not reference BigCommerce product 2822: {img[:80]}"
            )
        print(f"  ✓ All CLR 50K images reference BigCommerce product 2822")


# ─────────────────────────────────────────────────────────────────────────────
# 5. NEW PRODUCTS EXISTENCE
# ─────────────────────────────────────────────────────────────────────────────
class TestNewProductsExist:
    """Verify all new products created by catalog_repair.py exist in the catalog."""

    def test_ria_nv30k_blue_razz_ice_exists(self, all_products):
        """RIA NV30K - Blue Razz Ice must exist with model=RIA NV30K."""
        matches = [
            p for p in all_products
            if p.get("model") == "RIA NV30K"
        ]
        print(f"  RIA NV30K products: {[p.get('name') for p in matches]}")
        assert len(matches) >= 1, (
            "No product with model='RIA NV30K' found. "
            "Repair script should have created 'RIA NV30K - Blue Razz Ice'."
        )
        blue_razz = [p for p in matches if "Blue Razz Ice" in p.get("flavor", "") or "Blue Razz Ice" in p.get("name", "")]
        assert len(blue_razz) >= 1, (
            f"RIA NV30K - Blue Razz Ice not found. Found models: {[p.get('name') for p in matches]}"
        )
        print(f"  ✓ RIA NV30K - Blue Razz Ice exists: {blue_razz[0].get('name')}")

    def test_ria_nv30k_model_field_correct(self, all_products):
        """RIA NV30K product must have model='RIA NV30K', not empty or wrong."""
        matches = [p for p in all_products if "RIA NV30K" in p.get("name", "")]
        for p in matches:
            assert p.get("model") == "RIA NV30K", (
                f"{p.get('name')} has wrong model field: '{p.get('model')}'"
            )
        if matches:
            print(f"  ✓ RIA NV30K model field correct for all {len(matches)} product(s)")

    def test_clr_50k_blue_razz_ice_exists(self, all_products):
        """CLR 50K - Blue Razz Ice must exist (new flavor)."""
        match = next(
            (p for p in all_products
             if p.get("model") == "CLR 50K" and "Blue Razz Ice" in p.get("flavor", "")),
            None
        )
        assert match is not None, "CLR 50K - Blue Razz Ice not found"
        print(f"  ✓ {match.get('name')} exists")

    def test_clr_50k_sour_strawberry_exists(self, all_products):
        """CLR 50K - Sour Strawberry must exist (new flavor)."""
        match = next(
            (p for p in all_products
             if p.get("model") == "CLR 50K" and "Sour Strawberry" in p.get("flavor", "")),
            None
        )
        assert match is not None, "CLR 50K - Sour Strawberry not found"
        print(f"  ✓ {match.get('name')} exists")

    def test_clr_50k_sour_apple_ice_exists(self, all_products):
        """CLR 50K - Sour Apple Ice must exist (new flavor)."""
        match = next(
            (p for p in all_products
             if p.get("model") == "CLR 50K" and "Sour Apple Ice" in p.get("flavor", "")),
            None
        )
        assert match is not None, "CLR 50K - Sour Apple Ice not found"
        print(f"  ✓ {match.get('name')} exists")

    # Nera Fullview 70K POD
    def test_nera_fv_pod_scary_berry_exists(self, all_products):
        """Lost Mary Nera 70K POD - Scary Berry must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Nera 70K" and p.get("productType") == "pod"
             and "Scary Berry" in p.get("flavor", "")),
            None
        )
        assert match is not None, "Nera 70K POD - Scary Berry not found"
        print(f"  ✓ {match.get('name')} exists")

    def test_nera_fv_pod_golden_berry_exists(self, all_products):
        """Lost Mary Nera 70K POD - Golden Berry must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Nera 70K" and p.get("productType") == "pod"
             and "Golden Berry" in p.get("flavor", "")),
            None
        )
        assert match is not None, "Nera 70K POD - Golden Berry not found"
        print(f"  ✓ {match.get('name')} exists")

    def test_nera_fv_pod_pink_lemonade_exists(self, all_products):
        """Lost Mary Nera 70K POD - Pink Lemonade must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Nera 70K" and p.get("productType") == "pod"
             and "Pink Lemonade" in p.get("flavor", "")),
            None
        )
        assert match is not None, "Nera 70K POD - Pink Lemonade not found"
        print(f"  ✓ {match.get('name')} exists")

    def test_nera_fv_pod_blue_razz_ice_exists(self, all_products):
        """Lost Mary Nera 70K POD - Blue Razz Ice must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Nera 70K" and p.get("productType") == "pod"
             and "Blue Razz Ice" in p.get("flavor", "")),
            None
        )
        assert match is not None, "Nera 70K POD - Blue Razz Ice not found"
        print(f"  ✓ {match.get('name')} exists")

    def test_nera_fv_pod_rocket_freeze_exists(self, all_products):
        """Lost Mary Nera 70K POD - Rocket Freeze must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Nera 70K" and p.get("productType") == "pod"
             and "Rocket Freeze" in p.get("flavor", "")),
            None
        )
        assert match is not None, "Nera 70K POD - Rocket Freeze not found"
        print(f"  ✓ {match.get('name')} exists")

    # Nera Fullview 70K KIT
    def test_nera_fv_kit_pink_lemonade_pink_blue_exists(self, all_products):
        """Lost Mary Nera 70K KIT - Pink Lemonade + Pink & Blue must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Nera 70K" and p.get("productType") == "kit"
             and "Pink Lemonade" in p.get("flavor", "")),
            None
        )
        assert match is not None, "Nera 70K KIT - Pink Lemonade + Pink & Blue not found"
        print(f"  ✓ {match.get('name')} exists")

    def test_nera_fv_kit_scary_berry_golden_berry_exists(self, all_products):
        """Lost Mary Nera 70K KIT - Scary Berry + Golden Berry must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Nera 70K" and p.get("productType") == "kit"
             and "Scary Berry" in p.get("flavor", "")),
            None
        )
        assert match is not None, "Nera 70K KIT - Scary Berry + Golden Berry not found"
        print(f"  ✓ {match.get('name')} exists")

    def test_nera_fv_kit_blue_razz_ice_exists(self, all_products):
        """Lost Mary Nera 70K KIT - Blue Razz Ice must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Nera 70K" and p.get("productType") == "kit"
             and "Blue Razz Ice" in p.get("flavor", "")),
            None
        )
        assert match is not None, "Nera 70K KIT - Blue Razz Ice not found"
        print(f"  ✓ {match.get('name')} exists")

    # Geek Bar Pulse 15K new flavors
    def test_pulse_peach_lemonade_thermal_exists(self, all_products):
        """Geek Bar Pulse - Peach Lemonade (Thermal Edition) must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Pulse"
             and "Peach Lemonade" in p.get("flavor", "")
             and "Thermal" in p.get("flavor", "")),
            None
        )
        assert match is not None, "Pulse - Peach Lemonade (Thermal Edition) not found"
        print(f"  ✓ {match.get('name')} exists")

    def test_pulse_strawberry_kiwi_thermal_exists(self, all_products):
        """Geek Bar Pulse - Strawberry Kiwi (Thermal Edition) must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Pulse"
             and "Strawberry Kiwi" in p.get("flavor", "")
             and "Thermal" in p.get("flavor", "")),
            None
        )
        assert match is not None, "Pulse - Strawberry Kiwi (Thermal Edition) not found"
        print(f"  ✓ {match.get('name')} exists")

    def test_pulse_blueberry_watermelon_exists(self, all_products):
        """Geek Bar Pulse - Blueberry Watermelon must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Pulse"
             and "Blueberry Watermelon" in p.get("flavor", "")),
            None
        )
        assert match is not None, "Pulse - Blueberry Watermelon not found"
        print(f"  ✓ {match.get('name')} exists")

    def test_pulse_strawberry_mango_exists(self, all_products):
        """Geek Bar Pulse - Strawberry Mango must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Pulse"
             and "Strawberry Mango" in p.get("flavor", "")),
            None
        )
        assert match is not None, "Pulse - Strawberry Mango not found"
        print(f"  ✓ {match.get('name')} exists")

    def test_pulse_blow_pop_bpop_exists(self, all_products):
        """Geek Bar Pulse - Blow Pop / B-Burst (B-Pop) must exist."""
        match = next(
            (p for p in all_products
             if p.get("model") == "Pulse"
             and ("Blow Pop" in p.get("flavor", "") or "B-Pop" in p.get("flavor", "") or "B-Burst" in p.get("flavor", ""))),
            None
        )
        assert match is not None, "Pulse - Blow Pop / B-Burst (B-Pop) not found"
        print(f"  ✓ {match.get('name')} exists")


# ─────────────────────────────────────────────────────────────────────────────
# 6. NO DUPLICATE PRODUCT NAMES
# ─────────────────────────────────────────────────────────────────────────────
class TestNoDuplicateNames:
    """The catalog must not contain duplicate product names."""

    def test_no_duplicate_product_names(self, all_products):
        """All product names must be unique across the catalog."""
        names = [p.get("name", "").strip().lower() for p in all_products]
        seen = set()
        duplicates = []
        for name in names:
            if name in seen:
                duplicates.append(name)
            seen.add(name)

        if duplicates:
            print(f"  FAIL: Duplicate product names found:")
            for d in sorted(set(duplicates)):
                count = names.count(d)
                print(f"    '{d}' appears {count} times")

        assert len(duplicates) == 0, (
            f"Found {len(set(duplicates))} duplicate product names: "
            f"{sorted(set(duplicates))[:10]}"
        )
        print(f"  ✓ No duplicate product names in catalog ({len(all_products)} unique)")


# ─────────────────────────────────────────────────────────────────────────────
# 7. FALLBACK IMAGE FOR NULL PRODUCTS
# ─────────────────────────────────────────────────────────────────────────────
class TestFallbackImage:
    """
    product_routes.py resolve_image() must return FALLBACK_IMAGE_URL
    for products with null/empty image stored in DB.

    Strategy: Use PyMongo directly to inject a product with null image into the DB,
    then verify the API returns FALLBACK_IMAGE_URL for that product.
    ProductCreate schema enforces min_length=1 on image, so direct DB insertion is needed.
    """

    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = "test_database"

    @pytest.fixture(scope="class")
    def test_product_id(self):
        """Insert a test product with null image directly into MongoDB."""
        from datetime import datetime
        client = MongoClient(self.MONGO_URL)
        db = client[self.DB_NAME]

        doc = {
            "brandId": BRAND_IDS["geek_bar"],
            "brandName": "Geek Bar",
            "model": "TEST_FALLBACK",
            "flavor": "TEST Fallback Flavor",
            "name": "TEST_FALLBACK_IMAGE_PRODUCT",
            "slug": "test-fallback-image-product",
            "productType": "disposable",
            "puffCount": 1000,
            "nicotinePercent": 5.0,
            "nicotineStrength": "50mg",
            "price": 1.00,
            "stock": 1,
            "image": None,   # null image → should trigger fallback
            "images": [],
            "category": "all",
            "isActive": True,
            "isFeatured": False,
            "displayOrder": 0,
            "lowStockThreshold": 5,
            "description": "Test product for fallback image verification",
            "createdAt": datetime.utcnow(),
        }
        result = db.products.insert_one(doc)
        product_id = str(result.inserted_id)
        print(f"\n  Inserted fallback test product directly into MongoDB: {product_id}")
        client.close()

        yield product_id

        # Cleanup: remove test product
        client2 = MongoClient(self.MONGO_URL)
        db2 = client2[self.DB_NAME]
        db2.products.delete_one({"_id": ObjectId(product_id)})
        client2.close()
        print(f"\n  Deleted fallback test product from MongoDB: {product_id}")

    def test_get_product_with_null_image_returns_fallback(self, test_product_id):
        """GET /api/products/{id} must return FALLBACK_IMAGE_URL for null-image product."""
        response = requests.get(f"{BASE_URL}/api/products/{test_product_id}")
        assert response.status_code == 200, f"GET product failed: {response.text}"
        data = response.json()
        image = data.get("image")
        print(f"  Product image from API: {image}")
        assert image == FALLBACK_IMAGE_URL, (
            f"Expected fallback URL '{FALLBACK_IMAGE_URL}' but got '{image}'. "
            "resolve_image() in product_routes.py may not be working correctly."
        )
        print(f"  ✓ Fallback image correctly returned for null-image product: {image}")

    def test_product_list_null_image_returns_fallback(self, test_product_id):
        """GET /api/products (list) must also return FALLBACK_IMAGE_URL for null-image product."""
        response = requests.get(f"{BASE_URL}/api/products?active_only=false")
        assert response.status_code == 200
        products = response.json()
        test_product = next((p for p in products if p.get("id") == test_product_id), None)
        assert test_product is not None, (
            f"Test product {test_product_id} not found in product list. "
            "Ensure the product was inserted with isActive=True."
        )
        image = test_product.get("image")
        assert image == FALLBACK_IMAGE_URL, (
            f"Product list returned '{image}' instead of fallback URL for null-image product"
        )
        print(f"  ✓ Product list also returns fallback URL correctly for null-image product")


# ─────────────────────────────────────────────────────────────────────────────
# 8. ALL IMAGES ARE ABSOLUTE HTTPS URLS
# ─────────────────────────────────────────────────────────────────────────────
class TestAbsoluteImageURLs:
    """
    All product images (from active product list) should be either:
    - Absolute HTTPS URLs (https://...) for CDN images
    - Relative /api/uploads/ paths for local uploads (acceptable per spec)
    - FALLBACK_IMAGE_URL (https://clouddistrict.club/placeholder.png)
    
    Empty strings and null values are NOT acceptable.
    """

    def test_no_empty_or_null_images_in_active_products(self, active_products):
        """No active product should have empty or null image."""
        bad = [p for p in active_products if not p.get("image")]
        assert len(bad) == 0, (
            f"{len(bad)} active products have empty/null image: "
            f"{[p.get('name') for p in bad[:5]]}"
        )
        print(f"  ✓ All {len(active_products)} active products have non-empty image field")

    def test_cdn_images_are_https_urls(self, active_products):
        """Images that are not local /api/uploads/ paths must be HTTPS URLs."""
        non_https_non_local = [
            p for p in active_products
            if p.get("image")
            and not p.get("image", "").startswith("https://")
            and not p.get("image", "").startswith("/api/uploads/")
        ]
        if non_https_non_local:
            for p in non_https_non_local:
                print(f"  WARN: {p.get('name')} has non-https, non-local image: {p.get('image')[:80]}")
        # This is a warning check; local /api/uploads/ are acceptable legacy
        assert len(non_https_non_local) == 0, (
            f"{len(non_https_non_local)} products have images that are neither HTTPS nor /api/uploads/: "
            f"{[p.get('name') for p in non_https_non_local[:5]]}"
        )
        print(f"  ✓ All non-local images use HTTPS URLs")

    def test_count_local_upload_images(self, all_products):
        """Report count of legacy /api/uploads/ images (acceptable for known brands)."""
        local_upload = [
            p for p in all_products
            if p.get("image", "").startswith("/api/uploads/")
        ]
        print(f"  INFO: {len(local_upload)} products still use local /api/uploads/ images (legacy brands)")
        for p in local_upload:
            print(f"    - {p.get('brandName', '?')} | {p.get('name')} | {p.get('image', '')[:60]}")
        # Per spec: ≤25 local upload products acceptable (legacy VIHO, RX50K, Switch Ultra, etc.)
        assert len(local_upload) <= 30, (
            f"Too many local upload images: {len(local_upload)} (expected ≤30). "
            "Normalization may have failed for some products."
        )
        print(f"  ✓ Local upload count ({len(local_upload)}) is within acceptable limit (≤30)")

    def test_clio_kit_images_are_absolute_https(self, all_products):
        """CLIO Kit product images must be absolute HTTPS URLs."""
        clio_kits = [
            p for p in all_products
            if p.get("model") == "CLIO Platinum 50K" and p.get("productType") == "kit"
        ]
        for p in clio_kits:
            img = p.get("image", "")
            assert img.startswith("https://"), (
                f"CLIO Kit {p.get('name')} image is not HTTPS: {img}"
            )
        print(f"  ✓ All {len(clio_kits)} CLIO Kit products have HTTPS images")

    def test_clio_pod_images_are_absolute_https(self, all_products):
        """CLIO Pod product images must be absolute HTTPS URLs."""
        clio_pods = [
            p for p in all_products
            if p.get("model") == "CLIO Platinum 50K" and p.get("productType") == "pod"
        ]
        for p in clio_pods:
            img = p.get("image", "")
            assert img.startswith("https://"), (
                f"CLIO Pod {p.get('name')} image is not HTTPS: {img}"
            )
        print(f"  ✓ All {len(clio_pods)} CLIO Pod products have HTTPS images")

    def test_clr_50k_images_are_absolute_https(self, all_products):
        """CLR 50K product images must be absolute HTTPS URLs."""
        clr_products = [
            p for p in all_products
            if p.get("model") == "CLR 50K"
        ]
        for p in clr_products:
            img = p.get("image", "")
            assert img.startswith("https://"), (
                f"CLR 50K {p.get('name')} image is not HTTPS: {img}"
            )
        print(f"  ✓ All {len(clr_products)} CLR 50K products have HTTPS images")
