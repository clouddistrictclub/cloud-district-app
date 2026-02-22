"""
Test Bug Fixes: Brand images on Home and Admin product upload on web
"""
import os
import pytest
import requests
from io import BytesIO
from PIL import Image

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://premium-vape-local.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "jkaatz@gmail.com"
ADMIN_PASSWORD = "Just1n23$"


@pytest.fixture
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("access_token")


class TestBugFix1_BrandImages:
    """Test Bug Fix 1: Brand images rendering on Home"""
    
    def test_brands_endpoint_returns_image_urls(self):
        """Verify brands endpoint returns image URLs for Geek Bar and Pickles"""
        response = requests.get(f"{BASE_URL}/api/brands?active_only=true")
        assert response.status_code == 200, f"Failed to get brands: {response.text}"
        
        brands = response.json()
        assert len(brands) > 0, "No brands returned"
        
        # Find brands with images
        brands_with_images = [b for b in brands if b.get("image")]
        print(f"\nBrands with images: {len(brands_with_images)}")
        for b in brands_with_images:
            print(f"  - {b['name']}: {b['image']}")
        
        # Verify Geek Bar has migrated image URL
        geek_bar = next((b for b in brands if b["name"] == "Geek Bar"), None)
        assert geek_bar is not None, "Geek Bar brand not found"
        assert geek_bar.get("image"), "Geek Bar has no image"
        assert geek_bar["image"].startswith("/api/uploads/products/brand_"), \
            f"Geek Bar image not migrated. Got: {geek_bar['image']}"
        
        # Verify Pickles has migrated image URL
        pickles = next((b for b in brands if b["name"] == "Pickles"), None)
        assert pickles is not None, "Pickles brand not found"
        assert pickles.get("image"), "Pickles has no image"
        assert pickles["image"].startswith("/api/uploads/products/brand_"), \
            f"Pickles image not migrated. Got: {pickles['image']}"
    
    def test_geek_bar_image_serves_correctly(self):
        """Verify Geek Bar brand image is accessible"""
        # Get brand image URL
        response = requests.get(f"{BASE_URL}/api/brands?active_only=true")
        brands = response.json()
        geek_bar = next((b for b in brands if b["name"] == "Geek Bar"), None)
        
        assert geek_bar and geek_bar.get("image"), "Geek Bar image URL not found"
        
        # Fetch the image
        image_url = f"{BASE_URL}{geek_bar['image']}"
        img_response = requests.get(image_url)
        
        assert img_response.status_code == 200, f"Failed to fetch Geek Bar image: {img_response.status_code}"
        assert "image" in img_response.headers.get("content-type", ""), \
            f"Wrong content type: {img_response.headers.get('content-type')}"
        assert len(img_response.content) > 1000, "Image content too small"
        
        print(f"\nGeek Bar image: {image_url}")
        print(f"  - Status: {img_response.status_code}")
        print(f"  - Content-Type: {img_response.headers.get('content-type')}")
        print(f"  - Size: {len(img_response.content)} bytes")
    
    def test_pickles_image_serves_correctly(self):
        """Verify Pickles brand image is accessible"""
        response = requests.get(f"{BASE_URL}/api/brands?active_only=true")
        brands = response.json()
        pickles = next((b for b in brands if b["name"] == "Pickles"), None)
        
        assert pickles and pickles.get("image"), "Pickles image URL not found"
        
        image_url = f"{BASE_URL}{pickles['image']}"
        img_response = requests.get(image_url)
        
        assert img_response.status_code == 200, f"Failed to fetch Pickles image: {img_response.status_code}"
        assert "image" in img_response.headers.get("content-type", ""), \
            f"Wrong content type: {img_response.headers.get('content-type')}"
        
        print(f"\nPickles image: {image_url}")
        print(f"  - Status: {img_response.status_code}")
        print(f"  - Size: {len(img_response.content)} bytes")
    
    def test_brands_without_images_return_null(self):
        """Verify brands without images return null (for fallback icon)"""
        response = requests.get(f"{BASE_URL}/api/brands?active_only=true")
        brands = response.json()
        
        # These brands should NOT have images
        no_image_brands = ["Lost Mary", "RAZ", "Meloso", "Digiflavor"]
        
        for name in no_image_brands:
            brand = next((b for b in brands if b["name"] == name), None)
            if brand:
                # Should be null or empty string
                assert not brand.get("image") or brand["image"] == "", \
                    f"{name} should not have image, but has: {brand.get('image')}"
                print(f"{name}: image={brand.get('image')} (correctly shows fallback)")


class TestBugFix2_AdminProductUpload:
    """Test Bug Fix 2: Admin product image upload on web"""
    
    def test_upload_endpoint_requires_auth(self):
        """Verify upload endpoint requires admin authentication"""
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'file': ('test.jpg', img_bytes, 'image/jpeg')}
        
        # Without auth should fail
        response = requests.post(f"{BASE_URL}/api/upload/product-image", files=files)
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_upload_with_admin_token(self, admin_token):
        """Verify admin can upload product images"""
        # Create a test image
        img = Image.new('RGB', (200, 200), color='blue')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'file': ('test_upload.jpg', img_bytes, 'image/jpeg')}
        headers = {'Authorization': f'Bearer {admin_token}'}
        
        response = requests.post(
            f"{BASE_URL}/api/upload/product-image",
            files=files,
            headers=headers
        )
        
        print(f"\nUpload response status: {response.status_code}")
        print(f"Upload response: {response.text}")
        
        # Should return 200 with URL (not 422 which was the bug)
        assert response.status_code == 200, \
            f"Upload failed with {response.status_code}: {response.text}"
        
        data = response.json()
        assert "url" in data, "Response missing 'url' field"
        assert data["url"].startswith("/api/uploads/products/"), \
            f"Invalid URL format: {data['url']}"
        
        # Verify the uploaded file is accessible
        uploaded_url = f"{BASE_URL}{data['url']}"
        verify_response = requests.get(uploaded_url)
        assert verify_response.status_code == 200, \
            f"Uploaded file not accessible: {verify_response.status_code}"
        
        print(f"Uploaded file URL: {uploaded_url}")
        print(f"Verification status: {verify_response.status_code}")
    
    def test_upload_with_png(self, admin_token):
        """Verify PNG upload works"""
        img = Image.new('RGBA', (150, 150), color='green')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        files = {'file': ('test_upload.png', img_bytes, 'image/png')}
        headers = {'Authorization': f'Bearer {admin_token}'}
        
        response = requests.post(
            f"{BASE_URL}/api/upload/product-image",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 200, f"PNG upload failed: {response.text}"
        print(f"\nPNG upload successful: {response.json().get('url')}")
    
    def test_upload_rejects_invalid_extension(self, admin_token):
        """Verify upload rejects non-image files"""
        files = {'file': ('test.txt', BytesIO(b'not an image'), 'text/plain')}
        headers = {'Authorization': f'Bearer {admin_token}'}
        
        response = requests.post(
            f"{BASE_URL}/api/upload/product-image",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 400, \
            f"Expected 400 for invalid file type, got {response.status_code}"
        print(f"\nInvalid extension correctly rejected: {response.json()}")


class TestBrandImageMigration:
    """Test brand image migration from base64 to files"""
    
    def test_migration_completed(self):
        """Verify brand images were migrated from base64 to file URLs"""
        response = requests.get(f"{BASE_URL}/api/brands?active_only=false")
        brands = response.json()
        
        # Count brands with migrated URLs vs base64
        migrated = 0
        base64 = 0
        no_image = 0
        
        for brand in brands:
            img = brand.get("image")
            if not img or img == "":
                no_image += 1
            elif img.startswith("/api/uploads/"):
                migrated += 1
            elif img.startswith("data:image"):
                base64 += 1
        
        print(f"\nBrand image status:")
        print(f"  - Migrated to files: {migrated}")
        print(f"  - Still base64: {base64}")
        print(f"  - No image: {no_image}")
        
        # Verify at least 2 brands migrated (Geek Bar, Pickles)
        assert migrated >= 2, f"Expected at least 2 migrated brands, got {migrated}"
        # Verify no base64 images remain
        assert base64 == 0, f"Found {base64} brands still using base64"


class TestRegression:
    """Test regressions - existing functionality still works"""
    
    def test_products_endpoint(self):
        """Verify products endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Products endpoint failed: {response.text}"
        products = response.json()
        assert isinstance(products, list), "Products should return a list"
        print(f"\nProducts: {len(products)} items")
    
    def test_product_images_load(self):
        """Verify product images are accessible"""
        response = requests.get(f"{BASE_URL}/api/products")
        products = response.json()
        
        for product in products[:3]:  # Test first 3 products
            img = product.get("image", "")
            if img and img.startswith("/api/uploads/"):
                img_url = f"{BASE_URL}{img}"
                img_response = requests.get(img_url)
                assert img_response.status_code == 200, \
                    f"Product {product['name']} image failed: {img_response.status_code}"
                print(f"Product '{product['name']}' image OK: {img_url}")
    
    def test_login_flow(self):
        """Verify login flow works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert data["user"]["isAdmin"] == True, "User should be admin"
        print(f"\nLogin successful for admin user")
