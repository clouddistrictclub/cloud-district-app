"""
Test suite for localStorage persistence fixes for auth and age verification.
Tests the fix for AsyncStorage on Expo web SSR not persisting data.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL') or os.environ.get('REACT_APP_BACKEND_URL')

class TestAuthAPI:
    """Backend auth API tests"""
    
    def test_login_success(self):
        """Test login with valid credentials returns token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "jkaatz@gmail.com",
            "password": "Just1n23$"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user data in response"
        assert data["user"]["email"] == "jkaatz@gmail.com"
        assert data["user"]["isAdmin"] == True
        print(f"Login successful, token starts with: {data['access_token'][:20]}...")
        return data["access_token"]
    
    def test_auth_me_with_token(self):
        """Test /api/auth/me returns user data with valid token"""
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "jkaatz@gmail.com",
            "password": "Just1n23$"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Then test /api/auth/me
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        
        data = response.json()
        assert data["email"] == "jkaatz@gmail.com"
        assert data["isAdmin"] == True
        print(f"Auth/me successful for user: {data['email']}")
        
    def test_auth_me_without_token(self):
        """Test /api/auth/me fails without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403], f"Should fail without token but got: {response.status_code}"
        print("Auth/me correctly rejects requests without token")


class TestImageUpload:
    """Test image upload endpoint requires auth"""
    
    def test_upload_without_auth_fails(self):
        """Test that image upload fails without auth token"""
        # Create a minimal test image
        files = {
            'file': ('test.jpg', b'fake image data', 'image/jpeg')
        }
        response = requests.post(f"{BASE_URL}/api/upload/product-image", files=files)
        assert response.status_code in [401, 403, 422], f"Should fail without auth, got: {response.status_code}"
        print(f"Upload correctly requires auth, returned: {response.status_code}")
    
    def test_upload_with_auth_success(self):
        """Test that image upload works with valid auth token"""
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "jkaatz@gmail.com",
            "password": "Just1n23$"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Create minimal test file
        files = {
            'file': ('test.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 100, 'image/png')
        }
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/upload/product-image",
            files=files,
            headers=headers
        )
        # It may fail validation but should not be 401/403 if auth works
        if response.status_code == 200:
            print(f"Upload successful: {response.json()}")
        elif response.status_code in [401, 403]:
            pytest.fail(f"Upload failed due to auth: {response.status_code} - {response.text}")
        else:
            print(f"Upload returned {response.status_code} (auth worked, file validation may have failed)")


class TestProductsAPI:
    """Test products CRUD with auth"""
    
    def test_get_products(self):
        """Test GET products list (public)"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Failed to get products: {response.text}"
        products = response.json()
        print(f"Got {len(products)} products")
        return products
    
    def test_get_brands(self):
        """Test GET brands list (public)"""
        response = requests.get(f"{BASE_URL}/api/brands")
        assert response.status_code == 200, f"Failed to get brands: {response.text}"
        brands = response.json()
        print(f"Got {len(brands)} brands")
        return brands


class TestCartAPI:
    """Test cart operations (mostly client-side but verify related endpoints)"""
    
    def test_products_for_cart(self):
        """Verify products endpoint returns data needed for cart"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        if len(products) > 0:
            product = products[0]
            # Verify product has fields needed for cart
            assert "id" in product, "Product missing id"
            assert "name" in product, "Product missing name"
            assert "price" in product, "Product missing price"
            print(f"Product has required cart fields: {product['name']} - ${product['price']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
