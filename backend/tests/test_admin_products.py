"""
Backend tests for Admin Product Management (CRUD and Image Upload)
Tests the bug fixes for:
1. Image upload - Authorization header and multipart boundary
2. Product creation - With uploaded image path
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "jkaatz@gmail.com"
ADMIN_PASSWORD = "Just1n23$"

# Brand IDs
BRAND_IDS = {
    "geek_bar": "698fcbaea7e3829faf8adb0d",
    "lost_mary": "698fcbaea7e3829faf8adb0e",
    "raz": "698fcbaea7e3829faf8adb0f"
}


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    assert data.get("user", {}).get("isAdmin") == True, "User is not admin"
    return data["access_token"]


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestAdminAuth:
    """Test admin authentication"""
    
    def test_admin_login_success(self, api_client):
        """Test admin login returns valid token and user data"""
        response = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["isAdmin"] == True
        print(f"✓ Admin login successful, isAdmin={data['user']['isAdmin']}")

    def test_admin_me_endpoint(self, api_client, admin_token):
        """Test /auth/me returns admin user info"""
        response = api_client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["isAdmin"] == True
        print(f"✓ /auth/me returns admin user: {data['email']}")


class TestImageUpload:
    """Test the image upload endpoint - key bug fix area"""
    
    def test_upload_without_auth_fails(self, api_client):
        """Upload without auth token should fail with 403"""
        # Create a simple test image in memory
        image_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100  # Minimal PNG header
        files = {'file': ('test.png', io.BytesIO(image_content), 'image/png')}
        
        response = requests.post(
            f"{BASE_URL}/api/upload/product-image",
            files=files
        )
        # Should fail without auth - 403 Forbidden or 401 Unauthorized
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Upload without auth correctly returns {response.status_code}")

    def test_upload_with_auth_succeeds(self, admin_token):
        """Upload with correct Authorization header should succeed"""
        # Create a simple valid JPEG image
        # Minimal JPEG header
        jpeg_content = bytes([
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
            0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xDB, 0x20, 0xF8, 0xD3, 0x4F, 0x80,
            0xFF, 0xD9
        ])
        
        files = {'file': ('test_upload.jpg', io.BytesIO(jpeg_content), 'image/jpeg')}
        
        # IMPORTANT: Do NOT set Content-Type header - let requests set it with boundary
        response = requests.post(
            f"{BASE_URL}/api/upload/product-image",
            files=files,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Upload failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "url" in data, f"Response missing 'url' field: {data}"
        assert data["url"].startswith("/api/uploads/products/"), f"Invalid URL format: {data['url']}"
        print(f"✓ Image upload successful: {data['url']}")
        return data["url"]


class TestProductCRUD:
    """Test product Create, Read, Update, Delete operations"""
    
    @pytest.fixture(scope="class")
    def uploaded_image_url(self, admin_token):
        """Upload a test image and return its URL"""
        jpeg_content = bytes([
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
            0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
            0x00, 0xFB, 0xD5, 0xDB, 0x20, 0xF8, 0xD3, 0x4F, 0x80, 0xFF, 0xD9
        ])
        
        files = {'file': ('product_test.jpg', io.BytesIO(jpeg_content), 'image/jpeg')}
        response = requests.post(
            f"{BASE_URL}/api/upload/product-image",
            files=files,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Upload failed: {response.text}"
        return response.json()["url"]
    
    def test_list_products(self, api_client):
        """Test fetching product list"""
        response = api_client.get(f"{BASE_URL}/api/products?active_only=false")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Expected array of products"
        print(f"✓ Products list returned {len(data)} products")
        return data

    def test_list_brands(self, api_client):
        """Test fetching brands list"""
        response = api_client.get(f"{BASE_URL}/api/brands?active_only=false")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Expected array of brands"
        assert len(data) >= 3, f"Expected at least 3 brands, got {len(data)}"
        print(f"✓ Brands list returned {len(data)} brands")
        for brand in data:
            print(f"  - {brand['name']} (id: {brand['id']})")

    def test_create_product_with_image(self, admin_token, uploaded_image_url):
        """Test creating a new product with uploaded image"""
        product_data = {
            "name": "TEST_Admin_Created_Product",
            "brandId": BRAND_IDS["geek_bar"],
            "category": "best-sellers",
            "image": uploaded_image_url,
            "puffCount": 5000,
            "flavor": "Test Berry Blast",
            "nicotinePercent": 5.0,
            "price": 24.99,
            "stock": 50,
            "lowStockThreshold": 10,
            "isActive": True,
            "isFeatured": False,
            "loyaltyEarnRate": 0,
            "displayOrder": 0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/products",
            json=product_data,
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 200, f"Create failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data["name"] == product_data["name"]
        assert data["image"] == uploaded_image_url
        assert data["brandName"] == "Geek Bar"
        assert "id" in data
        print(f"✓ Product created: {data['name']} (id: {data['id']})")
        return data["id"]

    def test_get_product_by_id(self, api_client, admin_token):
        """Test getting a single product by ID"""
        # First get the list to find a product
        response = api_client.get(f"{BASE_URL}/api/products?active_only=false")
        products = response.json()
        if not products:
            pytest.skip("No products to test")
        
        product_id = products[0]["id"]
        response = api_client.get(f"{BASE_URL}/api/products/{product_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == product_id
        print(f"✓ Got product by ID: {data['name']}")

    def test_update_product(self, admin_token):
        """Test updating an existing product"""
        # First create a test product
        product_data = {
            "name": "TEST_Update_Product",
            "brandId": BRAND_IDS["lost_mary"],
            "category": "new-arrivals",
            "image": "/api/uploads/products/test.jpg",
            "puffCount": 3000,
            "flavor": "Original Flavor",
            "nicotinePercent": 3.0,
            "price": 19.99,
            "stock": 25,
            "lowStockThreshold": 5,
            "isActive": True,
            "isFeatured": False,
            "loyaltyEarnRate": 0,
            "displayOrder": 0
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/products",
            json=product_data,
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            }
        )
        assert create_response.status_code == 200
        product_id = create_response.json()["id"]
        
        # Now update
        update_data = {
            "name": "TEST_Updated_Product_Name",
            "flavor": "Updated Flavor",
            "price": 29.99
        }
        
        update_response = requests.patch(
            f"{BASE_URL}/api/products/{product_id}",
            json=update_data,
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            }
        )
        
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "TEST_Updated_Product_Name"
        assert data["flavor"] == "Updated Flavor"
        assert data["price"] == 29.99
        print(f"✓ Product updated successfully: {data['name']}")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/products/{product_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    def test_delete_product(self, admin_token):
        """Test deleting a product"""
        # Create a product to delete
        product_data = {
            "name": "TEST_Delete_Product",
            "brandId": BRAND_IDS["raz"],
            "category": "best-sellers",
            "image": "/api/uploads/products/test.jpg",
            "puffCount": 4000,
            "flavor": "Delete Me",
            "nicotinePercent": 4.0,
            "price": 15.99,
            "stock": 10,
            "lowStockThreshold": 2,
            "isActive": True,
            "isFeatured": False,
            "loyaltyEarnRate": 0,
            "displayOrder": 0
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/products",
            json=product_data,
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            }
        )
        assert create_response.status_code == 200
        product_id = create_response.json()["id"]
        
        # Delete
        delete_response = requests.delete(
            f"{BASE_URL}/api/products/{product_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert delete_response.status_code == 200
        print(f"✓ Product deleted successfully")
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/products/{product_id}")
        assert get_response.status_code == 404


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_products(self, admin_token):
        """Remove all TEST_ prefixed products"""
        response = requests.get(f"{BASE_URL}/api/products?active_only=false")
        products = response.json()
        
        cleaned = 0
        for product in products:
            if product["name"].startswith("TEST_"):
                del_response = requests.delete(
                    f"{BASE_URL}/api/products/{product['id']}",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                if del_response.status_code == 200:
                    cleaned += 1
        
        print(f"✓ Cleaned up {cleaned} test products")
