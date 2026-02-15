"""
Backend tests for Phase 2: Referral Deep Linking
Tests the registration API with referralCode parameter
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestReferralDeepLinking:
    """Tests for referral code handling in registration"""
    
    def test_register_with_valid_referral_code(self):
        """Test registration with admin's referral code STAV20H"""
        unique_email = f"TEST_deeplink_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "firstName": "DeepLink",
            "lastName": "TestUser",
            "dateOfBirth": "2000-01-01",
            "referralCode": "STAV20H"  # Admin's referral code
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == unique_email
        assert data["user"]["firstName"] == "DeepLink"
        assert data["user"]["lastName"] == "TestUser"
        # New user should have their own referral code
        assert data["user"]["referralCode"] is not None
        assert len(data["user"]["referralCode"]) == 7
        
        print(f"✅ Registered user with referral code: {data['user']['referralCode']}")
    
    def test_register_with_lowercase_referral_code(self):
        """Test registration with lowercase referral code - should be case-insensitive"""
        unique_email = f"TEST_deeplink_lower_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "firstName": "LowerCase",
            "lastName": "TestUser",
            "dateOfBirth": "2000-01-01",
            "referralCode": "stav20h"  # Lowercase version
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user" in data
        assert data["user"]["referralCode"] is not None
        
        print("✅ Registration with lowercase referral code succeeded")
    
    def test_register_with_invalid_referral_code(self):
        """Test registration with invalid referral code - should fail"""
        unique_email = f"TEST_deeplink_invalid_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "firstName": "Invalid",
            "lastName": "TestUser",
            "dateOfBirth": "2000-01-01",
            "referralCode": "INVALID123"  # Non-existent code
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data
        assert "invalid" in data["detail"].lower() or "referral" in data["detail"].lower()
        
        print(f"✅ Invalid referral code correctly rejected: {data['detail']}")
    
    def test_register_without_referral_code(self):
        """Test registration without referral code - should succeed"""
        unique_email = f"TEST_deeplink_nocode_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "firstName": "NoCode",
            "lastName": "TestUser",
            "dateOfBirth": "2000-01-01"
            # No referralCode provided
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user" in data
        # User should still get their own referral code
        assert data["user"]["referralCode"] is not None
        assert len(data["user"]["referralCode"]) == 7
        
        print(f"✅ User registered without referral code, got own code: {data['user']['referralCode']}")
    
    def test_register_with_empty_referral_code(self):
        """Test registration with empty string referral code - should succeed"""
        unique_email = f"TEST_deeplink_empty_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "firstName": "EmptyCode",
            "lastName": "TestUser",
            "dateOfBirth": "2000-01-01",
            "referralCode": ""  # Empty string
        })
        
        # Empty string should be treated as no referral code
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user" in data
        assert data["user"]["referralCode"] is not None
        
        print("✅ Empty referral code treated as no referral code")
    
    def test_login_returns_referral_fields(self):
        """Test that login response includes referral-related fields"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        user = data["user"]
        
        # Verify all referral fields are present
        assert "referralCode" in user, "referralCode field missing"
        assert "referralCount" in user, "referralCount field missing"
        assert "referralRewardsEarned" in user, "referralRewardsEarned field missing"
        
        # Verify admin's referral code
        assert user["referralCode"] == "STAV20H", f"Expected STAV20H, got {user['referralCode']}"
        
        print(f"✅ Login returns referral fields: code={user['referralCode']}, count={user['referralCount']}, earned={user['referralRewardsEarned']}")
    
    def test_auth_me_returns_referral_fields(self):
        """Test that /api/auth/me returns referral-related fields"""
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Then get user info
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        user = response.json()
        
        # Verify all referral fields are present
        assert "referralCode" in user, "referralCode field missing"
        assert "referralCount" in user, "referralCount field missing"
        assert "referralRewardsEarned" in user, "referralRewardsEarned field missing"
        
        assert user["referralCode"] == "STAV20H"
        
        print(f"✅ /api/auth/me returns referral fields correctly")


class TestRegistrationValidation:
    """Tests for registration validation"""
    
    def test_registration_age_validation(self):
        """Test that registration validates age 21+"""
        unique_email = f"TEST_deeplink_underage_{uuid.uuid4().hex[:8]}@test.com"
        
        # User born in 2010 (would be under 21 in 2025)
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "firstName": "Young",
            "lastName": "User",
            "dateOfBirth": "2010-01-01"  # Under 21
        })
        
        assert response.status_code == 400, f"Expected 400 for underage, got {response.status_code}"
        
        data = response.json()
        assert "21" in data["detail"] or "older" in data["detail"].lower()
        
        print(f"✅ Age validation working: {data['detail']}")
    
    def test_registration_duplicate_email(self):
        """Test that duplicate email is rejected"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "admin@clouddistrictclub.com",  # Existing admin email
            "password": "Test123!",
            "firstName": "Duplicate",
            "lastName": "User",
            "dateOfBirth": "2000-01-01"
        })
        
        assert response.status_code == 400, f"Expected 400 for duplicate email, got {response.status_code}"
        
        data = response.json()
        assert "email" in data["detail"].lower() or "registered" in data["detail"].lower()
        
        print(f"✅ Duplicate email rejected: {data['detail']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
