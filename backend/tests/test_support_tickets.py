"""
Support Tickets API Tests
- POST /api/support/tickets - Create ticket (authenticated user)
- GET /api/admin/support/tickets - Admin list tickets
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://premium-vape-local.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@clouddistrictclub.com"
ADMIN_PASSWORD = "Admin123!"

# Regular user for testing
TEST_USER_EMAIL = f"support_test_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}@test.com"
TEST_USER_PASSWORD = "TestPass123!"

class TestAuthHelpers:
    """Helper methods for authentication"""
    
    @staticmethod
    def get_admin_token() -> str:
        """Login as admin and return token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    @staticmethod
    def register_test_user() -> tuple:
        """Register a test user and return (token, user_id)"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "firstName": "Support",
            "lastName": "Tester",
            "dateOfBirth": "1990-01-15"
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token"), data.get("user", {}).get("id")
        return None, None


class TestSupportTicketCreation:
    """Tests for POST /api/support/tickets"""
    
    def test_create_ticket_without_auth(self):
        """POST /api/support/tickets without auth returns 401/403"""
        response = requests.post(f"{BASE_URL}/api/support/tickets", json={
            "subject": "Test Subject",
            "message": "Test message content"
        })
        print(f"No auth response: {response.status_code}")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: POST /api/support/tickets without auth returns 401/403")
    
    def test_create_ticket_with_valid_auth(self):
        """POST /api/support/tickets with valid subject+message returns 200"""
        admin_token = TestAuthHelpers.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        response = requests.post(
            f"{BASE_URL}/api/support/tickets",
            json={
                "subject": "TEST_Support Request",
                "message": "TEST_This is a test support ticket message"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Create ticket response: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "id" in data, "Response should contain 'id'"
        assert "message" in data, "Response should contain 'message'"
        print("PASS: POST /api/support/tickets creates ticket successfully")
    
    def test_create_ticket_missing_subject(self):
        """POST /api/support/tickets without subject returns 422"""
        admin_token = TestAuthHelpers.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        response = requests.post(
            f"{BASE_URL}/api/support/tickets",
            json={
                "message": "Test message without subject"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Missing subject response: {response.status_code}")
        assert response.status_code == 422, f"Expected 422 for validation error, got {response.status_code}"
        print("PASS: POST /api/support/tickets without subject returns 422")
    
    def test_create_ticket_missing_message(self):
        """POST /api/support/tickets without message returns 422"""
        admin_token = TestAuthHelpers.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        response = requests.post(
            f"{BASE_URL}/api/support/tickets",
            json={
                "subject": "Test subject without message"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Missing message response: {response.status_code}")
        assert response.status_code == 422, f"Expected 422 for validation error, got {response.status_code}"
        print("PASS: POST /api/support/tickets without message returns 422")
    
    def test_create_ticket_invalid_token(self):
        """POST /api/support/tickets with invalid token returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/support/tickets",
            json={
                "subject": "Test Subject",
                "message": "Test message"
            },
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        print(f"Invalid token response: {response.status_code}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/support/tickets with invalid token returns 401")


class TestAdminSupportTickets:
    """Tests for GET /api/admin/support/tickets"""
    
    def test_get_tickets_without_auth(self):
        """GET /api/admin/support/tickets without auth returns 401/403"""
        response = requests.get(f"{BASE_URL}/api/admin/support/tickets")
        print(f"No auth response: {response.status_code}")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: GET /api/admin/support/tickets without auth returns 401/403")
    
    def test_get_tickets_non_admin_user(self):
        """GET /api/admin/support/tickets with non-admin user returns 403"""
        # Register a non-admin user
        token, user_id = TestAuthHelpers.register_test_user()
        if not token:
            # If registration failed (user exists), try logging in
            print("Registration failed, skipping non-admin test")
            pytest.skip("Could not create test user")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/support/tickets",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Non-admin response: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: GET /api/admin/support/tickets with non-admin returns 403")
    
    def test_get_tickets_admin_success(self):
        """GET /api/admin/support/tickets as admin returns paginated list"""
        admin_token = TestAuthHelpers.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/admin/support/tickets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Admin get tickets response: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        print(f"Response data: {data}")
        
        # Verify response structure
        assert "tickets" in data, "Response should contain 'tickets' field"
        assert "total" in data, "Response should contain 'total' field"
        assert isinstance(data["tickets"], list), "tickets should be a list"
        assert isinstance(data["total"], int), "total should be an integer"
        print(f"PASS: Found {data['total']} total tickets")
    
    def test_get_tickets_filter_by_status_open(self):
        """GET /api/admin/support/tickets?status=open filters correctly"""
        admin_token = TestAuthHelpers.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/admin/support/tickets?status=open",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Filter status=open response: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify all returned tickets have status=open
        for ticket in data["tickets"]:
            assert ticket.get("status") == "open", f"Expected status='open', got '{ticket.get('status')}'"
        print(f"PASS: Filtered {len(data['tickets'])} tickets with status=open")
    
    def test_get_tickets_filter_by_status_closed(self):
        """GET /api/admin/support/tickets?status=closed filters correctly"""
        admin_token = TestAuthHelpers.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/admin/support/tickets?status=closed",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Filter status=closed response: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify all returned tickets have status=closed
        for ticket in data["tickets"]:
            assert ticket.get("status") == "closed", f"Expected status='closed', got '{ticket.get('status')}'"
        print(f"PASS: Filtered {len(data['tickets'])} tickets with status=closed")
    
    def test_get_tickets_pagination(self):
        """GET /api/admin/support/tickets supports skip/limit pagination"""
        admin_token = TestAuthHelpers.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/admin/support/tickets?skip=0&limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Pagination response: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert len(data["tickets"]) <= 5, "Should return at most 5 tickets"
        print(f"PASS: Pagination works - returned {len(data['tickets'])} tickets (limit=5)")


class TestRegressionOrdersAndStreak:
    """Regression tests for existing endpoints"""
    
    def test_orders_endpoint(self):
        """GET /api/orders still works (regression)"""
        admin_token = TestAuthHelpers.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/orders",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Orders endpoint response: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: GET /api/orders still works")
    
    def test_streak_endpoint(self):
        """GET /api/loyalty/streak still works (regression)"""
        admin_token = TestAuthHelpers.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/loyalty/streak",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Streak endpoint response: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "streak" in data, "Response should contain 'streak'"
        print(f"PASS: GET /api/loyalty/streak still works (streak={data['streak']})")
    
    def test_push_register_endpoint(self):
        """POST /api/push/register endpoint exists (regression)"""
        admin_token = TestAuthHelpers.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        # Try registering an invalid token (should return 400 for invalid format)
        response = requests.post(
            f"{BASE_URL}/api/push/register",
            json={"token": "invalid_token"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Push register endpoint response: {response.status_code}")
        # Should be 400 for invalid token format, not 404 (endpoint exists)
        assert response.status_code != 404, "Push register endpoint should exist"
        print("PASS: POST /api/push/register endpoint exists")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
