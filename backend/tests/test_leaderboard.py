"""
Leaderboard API Tests
Tests for GET /api/leaderboard endpoint with byPoints and byReferrals rankings
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cloudz-local-pickup.preview.emergentagent.com').rstrip('/')

# Admin credentials
ADMIN_EMAIL = "admin@clouddistrictclub.com"
ADMIN_PASSWORD = "Admin123!"


@pytest.fixture(scope="module")
def admin_token():
    """Login as admin and get token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip(f"Admin login failed: {response.text}")


@pytest.fixture(scope="module")
def admin_user_id():
    """Get admin user id"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["user"]["id"]
    pytest.skip("Could not get admin user id")


class TestLeaderboardAuthentication:
    """Tests for leaderboard authentication requirements"""

    def test_unauthenticated_request_returns_error(self):
        """Unauthenticated request to /api/leaderboard should return 401 or 403"""
        response = requests.get(f"{BASE_URL}/api/leaderboard")
        # FastAPI HTTPBearer returns 403 for missing token
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        data = response.json()
        assert "detail" in data

    def test_invalid_token_returns_401(self):
        """Invalid token should return 401"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestLeaderboardResponseStructure:
    """Tests for leaderboard response structure"""

    def test_leaderboard_returns_200(self, admin_token):
        """Authenticated request returns 200 status"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_response_has_bypoints_and_byreferrals(self, admin_token):
        """Response contains byPoints and byReferrals arrays"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        assert "byPoints" in data, "Response missing 'byPoints' array"
        assert "byReferrals" in data, "Response missing 'byReferrals' array"
        assert isinstance(data["byPoints"], list), "byPoints should be a list"
        assert isinstance(data["byReferrals"], list), "byReferrals should be a list"

    def test_entry_has_required_fields_only(self, admin_token):
        """Each entry has only the required fields: rank, displayName, points, referralCount, tier, tierColor, isCurrentUser"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        required_fields = {"rank", "displayName", "points", "referralCount", "tier", "tierColor", "isCurrentUser"}
        forbidden_fields = {"email", "password", "_id", "id", "firstName", "lastName"}
        
        for entry in data["byPoints"][:5]:  # Check first 5 entries
            entry_keys = set(entry.keys())
            # Check all required fields exist
            assert entry_keys == required_fields, f"Entry has wrong fields. Expected: {required_fields}, Got: {entry_keys}"
            # Check no forbidden fields
            for field in forbidden_fields:
                assert field not in entry_keys, f"Entry should not contain '{field}'"

        for entry in data["byReferrals"][:5]:
            entry_keys = set(entry.keys())
            assert entry_keys == required_fields, f"Entry has wrong fields. Expected: {required_fields}, Got: {entry_keys}"

    def test_no_sensitive_data_exposed(self, admin_token):
        """Response should not expose email, password, or MongoDB _id"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        for entry in data["byPoints"]:
            assert "email" not in entry, "Email should not be exposed"
            assert "password" not in entry, "Password should not be exposed"
            assert "_id" not in entry, "MongoDB _id should not be exposed"
        
        for entry in data["byReferrals"]:
            assert "email" not in entry
            assert "password" not in entry
            assert "_id" not in entry


class TestLeaderboardSorting:
    """Tests for leaderboard sorting order"""

    def test_bypoints_sorted_descending(self, admin_token):
        """byPoints array is sorted by points in descending order"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        points_list = [entry["points"] for entry in data["byPoints"]]
        assert points_list == sorted(points_list, reverse=True), "byPoints should be sorted in descending order"

    def test_byreferrals_sorted_descending(self, admin_token):
        """byReferrals array is sorted by referralCount in descending order"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        referral_list = [entry["referralCount"] for entry in data["byReferrals"]]
        assert referral_list == sorted(referral_list, reverse=True), "byReferrals should be sorted in descending order"

    def test_ranks_are_sequential(self, admin_token):
        """Ranks should be sequential starting from 1"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        for i, entry in enumerate(data["byPoints"]):
            expected_rank = i + 1
            assert entry["rank"] == expected_rank, f"Expected rank {expected_rank}, got {entry['rank']}"
        
        for i, entry in enumerate(data["byReferrals"]):
            expected_rank = i + 1
            assert entry["rank"] == expected_rank, f"Expected rank {expected_rank}, got {entry['rank']}"


class TestLeaderboardCurrentUser:
    """Tests for isCurrentUser flag"""

    def test_iscurrentuser_true_for_requesting_user(self, admin_token, admin_user_id):
        """isCurrentUser should be true only for the requesting user's entry"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        # Find admin user (Admin P.) in the lists
        current_user_count_points = sum(1 for e in data["byPoints"] if e["isCurrentUser"])
        current_user_count_refs = sum(1 for e in data["byReferrals"] if e["isCurrentUser"])
        
        # Should have exactly 1 current user in each list (or 0 if not in top 20)
        assert current_user_count_points <= 1, "Should have at most 1 isCurrentUser=true in byPoints"
        assert current_user_count_refs <= 1, "Should have at most 1 isCurrentUser=true in byReferrals"
        
        # Admin user should be marked as current user
        current_users = [e for e in data["byPoints"] if e["isCurrentUser"]]
        if current_users:
            assert current_users[0]["displayName"] == "Admin P.", f"Current user should be Admin P., got {current_users[0]['displayName']}"


class TestLeaderboardDisplayName:
    """Tests for displayName format"""

    def test_displayname_format(self, admin_token):
        """displayName format should be 'FirstName L.' (first name + last initial with period)"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        for entry in data["byPoints"]:
            display_name = entry["displayName"]
            # Should end with a period (for last initial)
            # Format: "FirstName L."
            parts = display_name.rsplit(" ", 1)
            if len(parts) == 2:
                first_name, last_initial = parts
                assert len(last_initial) == 2, f"Last initial should be 1 char + period, got '{last_initial}'"
                assert last_initial.endswith("."), f"Last initial should end with period, got '{last_initial}'"


class TestLeaderboardTiers:
    """Tests for tier information"""

    def test_tier_fields_present(self, admin_token):
        """Each entry should have tier and tierColor fields"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        for entry in data["byPoints"]:
            assert "tier" in entry, "Entry missing 'tier' field"
            assert "tierColor" in entry, "Entry missing 'tierColor' field"
            # tier can be null, tierColor should always be a string
            assert isinstance(entry["tierColor"], str), "tierColor should be a string"

    def test_tier_color_format(self, admin_token):
        """tierColor should be a valid hex color string"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        for entry in data["byPoints"]:
            tier_color = entry["tierColor"]
            # Should start with # and be a valid hex color
            assert tier_color.startswith("#"), f"tierColor should start with #, got '{tier_color}'"
            assert len(tier_color) in [4, 7], f"tierColor should be 4 or 7 chars (#RGB or #RRGGBB), got '{tier_color}'"


class TestLeaderboardLimit:
    """Tests for leaderboard size limit"""

    def test_bypoints_max_20_entries(self, admin_token):
        """byPoints should return at most 20 entries"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        assert len(data["byPoints"]) <= 20, f"byPoints should have at most 20 entries, got {len(data['byPoints'])}"

    def test_byreferrals_max_20_entries(self, admin_token):
        """byReferrals should return at most 20 entries"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        assert len(data["byReferrals"]) <= 20, f"byReferrals should have at most 20 entries, got {len(data['byReferrals'])}"


class TestLeaderboardDataValues:
    """Tests for data value correctness"""

    def test_points_are_non_negative(self, admin_token):
        """Points should be non-negative integers"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        for entry in data["byPoints"]:
            assert isinstance(entry["points"], int), f"Points should be int, got {type(entry['points'])}"
            assert entry["points"] >= 0, f"Points should be non-negative, got {entry['points']}"

    def test_referral_count_are_non_negative(self, admin_token):
        """Referral counts should be non-negative integers"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        for entry in data["byReferrals"]:
            assert isinstance(entry["referralCount"], int), f"referralCount should be int"
            assert entry["referralCount"] >= 0, f"referralCount should be non-negative"

    def test_admin_user_in_leaderboard(self, admin_token):
        """Admin user (Admin P.) should appear in leaderboard with correct data"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        # Find admin in byReferrals (should be #1)
        admin_by_refs = [e for e in data["byReferrals"] if e["displayName"] == "Admin P."]
        assert len(admin_by_refs) == 1, "Admin P. should appear in byReferrals"
        assert admin_by_refs[0]["rank"] == 1, f"Admin P. should be #1 in referrals, got rank {admin_by_refs[0]['rank']}"
        assert admin_by_refs[0]["referralCount"] == 4, f"Admin should have 4 referrals, got {admin_by_refs[0]['referralCount']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
