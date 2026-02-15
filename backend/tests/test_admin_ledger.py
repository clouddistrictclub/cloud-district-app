"""
Test suite for Admin Cloudz Ledger API endpoint.
Tests: GET /api/admin/ledger with pagination, type/userId filters, and auth protection.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAdminLedgerAuth:
    """Admin ledger authentication and authorization tests"""

    def get_admin_token(self):
        """Login as admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]

    def get_non_admin_token(self):
        """Login as non-admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonadmin_ledger_test@test.com",
            "password": "Test123!"
        })
        assert response.status_code == 200, f"Non-admin login failed: {response.text}"
        return response.json()["access_token"]

    def test_admin_ledger_requires_auth(self):
        """Unauthenticated requests return 401 or 403"""
        response = requests.get(f"{BASE_URL}/api/admin/ledger")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_admin_ledger_blocks_non_admin(self):
        """Non-admin users get 403 Forbidden"""
        token = self.get_non_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/admin/ledger",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "Admin access required" in response.text

    def test_admin_ledger_allows_admin(self):
        """Admin users can access ledger"""
        token = self.get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/admin/ledger",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"


class TestAdminLedgerPagination:
    """Admin ledger pagination tests"""

    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        return response.json()["access_token"]

    def test_admin_ledger_returns_paginated_response(self, admin_token):
        """Response contains entries array plus pagination metadata"""
        response = requests.get(
            f"{BASE_URL}/api/admin/ledger",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify paginated response structure
        assert "entries" in data, "Missing 'entries' field"
        assert "total" in data, "Missing 'total' field"
        assert "skip" in data, "Missing 'skip' field"
        assert "limit" in data, "Missing 'limit' field"
        assert isinstance(data["entries"], list)
        assert isinstance(data["total"], int)

    def test_admin_ledger_pagination_limit(self, admin_token):
        """Limit parameter returns correct number of entries"""
        response = requests.get(
            f"{BASE_URL}/api/admin/ledger?skip=0&limit=2",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["entries"]) <= 2, f"Expected max 2 entries, got {len(data['entries'])}"
        assert data["limit"] == 2
        assert data["skip"] == 0

    def test_admin_ledger_pagination_skip(self, admin_token):
        """Skip parameter offsets results correctly"""
        # Get first page
        response1 = requests.get(
            f"{BASE_URL}/api/admin/ledger?skip=0&limit=2",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data1 = response1.json()
        
        # Get second page
        response2 = requests.get(
            f"{BASE_URL}/api/admin/ledger?skip=2&limit=2",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data2 = response2.json()
        
        assert response2.status_code == 200
        assert data2["skip"] == 2
        
        # Entries should be different (if total > 2)
        if data1["total"] > 2 and len(data2["entries"]) > 0:
            first_ids = [e["userId"] + e["createdAt"] for e in data1["entries"]]
            second_ids = [e["userId"] + e["createdAt"] for e in data2["entries"]]
            # At least one entry should differ
            assert first_ids != second_ids or len(data2["entries"]) == 0


class TestAdminLedgerFilters:
    """Admin ledger filter tests"""

    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        return response.json()["access_token"]

    def test_admin_ledger_type_filter(self, admin_token):
        """Type filter returns only entries of that type"""
        response = requests.get(
            f"{BASE_URL}/api/admin/ledger?type=admin_adjustment",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All entries should be admin_adjustment type
        for entry in data["entries"]:
            assert entry["type"] == "admin_adjustment", f"Expected type admin_adjustment, got {entry['type']}"

    def test_admin_ledger_user_id_filter(self, admin_token):
        """userId filter returns only entries for that user"""
        admin_user_id = "698f8bb6f3e9a3d6ac40fb66"
        response = requests.get(
            f"{BASE_URL}/api/admin/ledger?userId={admin_user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All entries should be for admin user
        for entry in data["entries"]:
            assert entry["userId"] == admin_user_id, f"Expected userId {admin_user_id}, got {entry['userId']}"

    def test_admin_ledger_combined_filters(self, admin_token):
        """Both type and userId filters can be combined"""
        admin_user_id = "698f8bb6f3e9a3d6ac40fb66"
        response = requests.get(
            f"{BASE_URL}/api/admin/ledger?userId={admin_user_id}&type=admin_adjustment",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All entries should match both filters
        for entry in data["entries"]:
            assert entry["userId"] == admin_user_id
            assert entry["type"] == "admin_adjustment"


class TestAdminLedgerEntryFields:
    """Admin ledger entry field validation tests"""

    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        return response.json()["access_token"]

    def test_admin_ledger_entries_include_user_email(self, admin_token):
        """Each entry includes userEmail resolved from users collection"""
        response = requests.get(
            f"{BASE_URL}/api/admin/ledger?limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for entry in data["entries"]:
            assert "userEmail" in entry, "Missing userEmail field"
            assert entry["userEmail"] != "unknown", f"userEmail should be resolved, not 'unknown'"
            assert "@" in entry["userEmail"], f"userEmail should be valid email format"

    def test_admin_ledger_entries_have_required_fields(self, admin_token):
        """Each entry has all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/ledger?limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["userId", "userEmail", "type", "amount", "balanceAfter", "createdAt"]
        for entry in data["entries"]:
            for field in required_fields:
                assert field in entry, f"Missing required field: {field}"


class TestUserLedgerUnchanged:
    """Verify existing user ledger endpoint unchanged"""

    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@clouddistrictclub.com",
            "password": "Admin123!"
        })
        return response.json()["access_token"]

    def test_user_ledger_returns_flat_array(self, admin_token):
        """GET /api/loyalty/ledger returns flat array, not paginated"""
        response = requests.get(
            f"{BASE_URL}/api/loyalty/ledger",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should be a flat array, not an object with pagination
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        
        # Entries should have standard fields (no userEmail for user endpoint)
        if len(data) > 0:
            assert "type" in data[0]
            assert "amount" in data[0]
            assert "balanceAfter" in data[0]
