"""
Tests for P1 - Product Image Upload System
- POST /api/upload/product-image endpoint
- Static file serving from /api/uploads/products/
- Migration verification (base64 to file)
"""
import pytest
import requests
import os
from pathlib import Path
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cloudz-local-pickup.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')

# Admin credentials
ADMIN_EMAIL = "jkaatz@gmail.com"
ADMIN_PASSWORD = "Just1n23$"


@pytest.fixture(scope="session")
def admin_token():
    """Login as admin and get access token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, f"Response missing access_token: {data}"
    return data["access_token"]


@pytest.fixture
def api_client():
    """Standard requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def admin_client(admin_token):
    """Authenticated admin session"""
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {admin_token}"})
    return session


class TestImageUploadEndpoint:
    """POST /api/upload/product-image tests"""

    def test_upload_requires_admin_auth(self, api_client):
        """Upload endpoint should require admin authentication"""
        # Create a small test image
        image_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100  # Minimal PNG-like bytes
        files = {'file': ('test.png', io.BytesIO(image_data), 'image/png')}
        
        # No auth header
        response = requests.post(f"{BASE_URL}/api/upload/product-image", files=files)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"PASS: Upload without auth returns {response.status_code}")

    def test_upload_with_admin_token_jpg(self, admin_client):
        """Upload JPEG image should work with admin token"""
        # Create a simple 1x1 pixel JPEG (minimal valid JPEG)
        jpeg_data = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
            0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
            0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
            0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
            0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
            0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
            0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
            0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
            0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
            0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
            0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
            0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
            0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
            0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
            0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD2, 0x8A, 0x28, 0x03, 0xFF, 0xD9
        ])
        
        files = {'file': ('test_upload.jpg', io.BytesIO(jpeg_data), 'image/jpeg')}
        response = admin_client.post(f"{BASE_URL}/api/upload/product-image", files=files)
        
        assert response.status_code == 200, f"Upload failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "url" in data, f"Response missing url: {data}"
        assert data["url"].startswith("/api/uploads/products/"), f"Invalid URL format: {data['url']}"
        assert data["url"].endswith(".jpg"), f"URL should end with .jpg: {data['url']}"
        print(f"PASS: Upload returned URL: {data['url']}")
        
        # Verify the uploaded file is accessible
        file_url = f"{BASE_URL}{data['url']}"
        file_response = requests.get(file_url)
        assert file_response.status_code == 200, f"Cannot access uploaded file: {file_url}"
        print(f"PASS: Uploaded file accessible at {file_url}")

    def test_upload_rejects_invalid_extension(self, admin_client):
        """Upload should reject non-image extensions"""
        text_data = b"This is not an image"
        files = {'file': ('test.txt', io.BytesIO(text_data), 'text/plain')}
        
        response = admin_client.post(f"{BASE_URL}/api/upload/product-image", files=files)
        assert response.status_code == 400, f"Expected 400 for invalid file type, got {response.status_code}"
        print(f"PASS: Invalid file type rejected with 400")


class TestStaticFileServing:
    """Test /api/uploads/products/ static file serving"""

    def test_migrated_image_accessible(self):
        """Verify migrated image (Onions product) is accessible"""
        # Get products to find migrated image URL
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        # Find product with migrated URL
        migrated_product = None
        for p in products:
            if p.get("image", "").startswith("/api/uploads/products/"):
                migrated_product = p
                break
        
        assert migrated_product is not None, "No product found with migrated image URL"
        print(f"Found migrated product: {migrated_product['name']}")
        
        # Verify image is accessible
        image_url = f"{BASE_URL}{migrated_product['image']}"
        image_response = requests.get(image_url)
        assert image_response.status_code == 200, f"Migrated image not accessible: {image_url}"
        assert len(image_response.content) > 0, "Image response is empty"
        print(f"PASS: Migrated image accessible: {image_url}")

    def test_static_file_content_type(self):
        """Verify static files return correct content type"""
        # Get any product with migrated image
        response = requests.get(f"{BASE_URL}/api/products")
        products = response.json()
        
        for p in products:
            if p.get("image", "").startswith("/api/uploads/products/") and p["image"].endswith(".jpg"):
                image_url = f"{BASE_URL}{p['image']}"
                image_response = requests.get(image_url)
                content_type = image_response.headers.get("content-type", "")
                assert "image" in content_type.lower(), f"Expected image content-type, got: {content_type}"
                print(f"PASS: Content-Type is {content_type}")
                return
        
        pytest.skip("No JPEG migrated images found")


class TestMigrationVerification:
    """Verify base64 to file migration ran correctly"""

    def test_onions_product_migrated(self):
        """Verify 'Onions' product has URL path instead of base64"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        onions = None
        for p in products:
            if "onion" in p["name"].lower():
                onions = p
                break
        
        if onions is None:
            pytest.skip("Onions product not found in database")
        
        image = onions.get("image", "")
        assert not image.startswith("data:image"), f"Onions image not migrated - still base64: {image[:50]}..."
        assert image.startswith("/api/uploads/products/"), f"Onions image should be URL path: {image}"
        print(f"PASS: Onions product migrated to URL: {image}")

    def test_invalid_base64_skipped(self):
        """Verify product with invalid base64 was skipped (not corrupted)"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        # Find 'Admin Test Vape 2' which had invalid base64 'admintest'
        admin_test = None
        for p in products:
            if "admin test" in p["name"].lower():
                admin_test = p
                break
        
        if admin_test is None:
            pytest.skip("Admin Test Vape 2 not found")
        
        # It should still have the original invalid base64 (migration skipped it)
        image = admin_test.get("image", "")
        print(f"Admin Test Vape 2 image: {image}")
        # Migration should have skipped it - it still has base64 prefix or original value
        assert "admintest" in image or image.startswith("data:image"), \
            f"Unexpected image value after migration skip: {image}"
        print(f"PASS: Invalid base64 product correctly skipped during migration")


class TestProductAPIWithUploadedImages:
    """Test product CRUD with uploaded images"""

    def test_product_returns_url_path(self):
        """GET /api/products should return URL paths for migrated products"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        url_count = 0
        for p in products:
            image = p.get("image", "")
            if image.startswith("/api/uploads/products/"):
                url_count += 1
                print(f"  {p['name']}: {image}")
        
        print(f"PASS: Found {url_count} products with URL image paths")
        assert url_count >= 1, "Expected at least 1 product with URL image path"

    def test_single_product_returns_url_path(self):
        """GET /api/products/{id} should return URL path for migrated product"""
        # First get list to find a migrated product
        response = requests.get(f"{BASE_URL}/api/products")
        products = response.json()
        
        migrated_id = None
        for p in products:
            if p.get("image", "").startswith("/api/uploads/products/"):
                migrated_id = p["id"]
                break
        
        if not migrated_id:
            pytest.skip("No migrated products found")
        
        # Get single product
        response = requests.get(f"{BASE_URL}/api/products/{migrated_id}")
        assert response.status_code == 200
        product = response.json()
        assert product["image"].startswith("/api/uploads/products/"), \
            f"Single product API should return URL path: {product['image']}"
        print(f"PASS: Single product returns URL path: {product['image']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
