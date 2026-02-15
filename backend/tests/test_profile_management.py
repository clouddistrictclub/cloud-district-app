"""
Test suite for Cloud District Club Profile Management
Tests PATCH /api/profile endpoint and profile fields (phone, firstName, lastName, email, profilePhoto)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials
ADMIN_EMAIL = "admin@clouddistrictclub.com"
ADMIN_PASSWORD = "Admin123!"
ADMIN_PHONE = "555-123-4567"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_auth(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    return {
        "token": data["access_token"],
        "user": data["user"]
    }


@pytest.fixture(scope="module")
def admin_headers(admin_auth):
    """Headers with admin auth token"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_auth['token']}"
    }


@pytest.fixture(scope="module")
def test_user(api_client):
    """Create a test user for profile testing"""
    unique_id = str(uuid.uuid4())[:8]
    email = f"TEST_profile_{unique_id}@test.com"
    response = api_client.post(f"{BASE_URL}/api/auth/register", json={
        "email": email,
        "password": "TestPass123!",
        "firstName": "ProfileTest",
        "lastName": "User",
        "dateOfBirth": "1990-01-01",
        "phone": None
    })
    assert response.status_code == 200, f"Test user registration failed: {response.text}"
    data = response.json()
    return {
        "token": data["access_token"],
        "user": data["user"],
        "email": email,
        "password": "TestPass123!"
    }


@pytest.fixture(scope="module")
def test_user_headers(test_user):
    """Headers with test user auth token"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {test_user['token']}"
    }


class TestHealthCheck:
    """Health and basic connectivity tests"""
    
    def test_api_accessible(self, api_client):
        """Test that API is accessible"""
        response = api_client.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200


class TestProfileEndpoint:
    """Tests for PATCH /api/profile endpoint"""
    
    def test_profile_requires_auth(self, api_client):
        """Test that profile endpoint requires authentication"""
        response = api_client.patch(f"{BASE_URL}/api/profile", json={
            "firstName": "Test"
        })
        assert response.status_code in [401, 403]
    
    def test_update_first_name(self, api_client, test_user_headers, test_user):
        """Test updating first name"""
        new_first_name = f"Updated_{uuid.uuid4().hex[:4]}"
        response = api_client.patch(
            f"{BASE_URL}/api/profile",
            json={"firstName": new_first_name},
            headers=test_user_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["firstName"] == new_first_name
        
        # Verify persistence via GET /api/auth/me
        me_response = api_client.get(f"{BASE_URL}/api/auth/me", headers=test_user_headers)
        assert me_response.status_code == 200
        assert me_response.json()["firstName"] == new_first_name
    
    def test_update_last_name(self, api_client, test_user_headers):
        """Test updating last name"""
        new_last_name = f"UpdatedLast_{uuid.uuid4().hex[:4]}"
        response = api_client.patch(
            f"{BASE_URL}/api/profile",
            json={"lastName": new_last_name},
            headers=test_user_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["lastName"] == new_last_name
    
    def test_update_phone(self, api_client, test_user_headers):
        """Test updating phone number"""
        new_phone = "555-999-8888"
        response = api_client.patch(
            f"{BASE_URL}/api/profile",
            json={"phone": new_phone},
            headers=test_user_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["phone"] == new_phone
        
        # Verify persistence via GET /api/auth/me
        me_response = api_client.get(f"{BASE_URL}/api/auth/me", headers=test_user_headers)
        assert me_response.status_code == 200
        assert me_response.json()["phone"] == new_phone
    
    def test_update_email(self, api_client, test_user_headers):
        """Test updating email"""
        unique_id = uuid.uuid4().hex[:8]
        new_email = f"TEST_newemail_{unique_id}@test.com"
        response = api_client.patch(
            f"{BASE_URL}/api/profile",
            json={"email": new_email},
            headers=test_user_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["email"] == new_email
    
    def test_update_multiple_fields(self, api_client, test_user_headers):
        """Test updating multiple fields at once"""
        unique_id = uuid.uuid4().hex[:4]
        update_data = {
            "firstName": f"Multi_{unique_id}",
            "lastName": f"Update_{unique_id}",
            "phone": "555-111-2222"
        }
        response = api_client.patch(
            f"{BASE_URL}/api/profile",
            json=update_data,
            headers=test_user_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["firstName"] == update_data["firstName"]
        assert data["lastName"] == update_data["lastName"]
        assert data["phone"] == update_data["phone"]
    
    def test_update_profile_photo_base64(self, api_client, test_user_headers):
        """Test updating profile photo with base64 data"""
        # Simple 1x1 red pixel PNG in base64
        base64_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        
        response = api_client.patch(
            f"{BASE_URL}/api/profile",
            json={"profilePhoto": base64_image},
            headers=test_user_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["profilePhoto"] == base64_image
        
        # Verify persistence
        me_response = api_client.get(f"{BASE_URL}/api/auth/me", headers=test_user_headers)
        assert me_response.status_code == 200
        assert me_response.json()["profilePhoto"] == base64_image
    
    def test_update_empty_body_returns_current_user(self, api_client, test_user_headers):
        """Test that empty update body returns current user without error"""
        response = api_client.patch(
            f"{BASE_URL}/api/profile",
            json={},
            headers=test_user_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert "email" in data


class TestAdminUserPhone:
    """Test that admin user phone is stored and returned correctly"""
    
    def test_admin_user_has_phone_field(self, api_client, admin_headers):
        """Test that admin user has phone field in response"""
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        # Phone field should exist (may be None or have a value)
        assert "phone" in data
    
    def test_admin_update_phone(self, api_client, admin_headers):
        """Test admin updating their own phone number"""
        response = api_client.patch(
            f"{BASE_URL}/api/profile",
            json={"phone": ADMIN_PHONE},
            headers=admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["phone"] == ADMIN_PHONE


class TestUserResponse:
    """Test UserResponse model includes all profile fields"""
    
    def test_auth_me_includes_profile_fields(self, api_client, admin_headers):
        """Test /api/auth/me returns all profile fields"""
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Required fields
        assert "id" in data
        assert "email" in data
        assert "firstName" in data
        assert "lastName" in data
        assert "dateOfBirth" in data
        assert "isAdmin" in data
        assert "loyaltyPoints" in data
        
        # Optional profile fields
        assert "phone" in data  # Should exist even if None
        assert "profilePhoto" in data  # Should exist even if None
    
    def test_login_returns_profile_fields(self, api_client):
        """Test /api/auth/login returns all profile fields in user object"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        
        data = response.json()
        user = data["user"]
        
        # Check profile fields in login response
        assert "phone" in user
        assert "profilePhoto" in user


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
