"""
Test suite for Live Chat System
Tests chat REST endpoints and WebSocket functionality
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cloudz-local-pickup.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "jkaatz@gmail.com"
ADMIN_PASSWORD = "Just1n23$"
TEST_USER_EMAIL = "testuser@cloud.club"
TEST_USER_PASSWORD = "Test1234!"


class TestChatAuthentication:
    """Test login for chat users"""
    
    def test_admin_login(self):
        """Admin user login for chat management"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["isAdmin"] == True, "User should be admin"
        print(f"Admin login successful. User ID: {data['user']['id']}")
    
    def test_regular_user_login(self):
        """Regular user login for chat"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Test user login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["isAdmin"] == False, "User should not be admin"
        print(f"Test user login successful. User ID: {data['user']['id']}")


class TestChatMessagesAPI:
    """Test chat messages REST API"""
    
    @pytest.fixture
    def test_user_auth(self):
        """Get test user authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        data = response.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"],
            "chat_id": f"chat_{data['user']['id']}"
        }
    
    @pytest.fixture
    def admin_auth(self):
        """Get admin authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        data = response.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"]
        }
    
    def test_get_chat_messages_authenticated(self, test_user_auth):
        """Test getting chat messages with valid auth"""
        response = requests.get(
            f"{BASE_URL}/api/chat/messages/{test_user_auth['chat_id']}",
            headers={"Authorization": f"Bearer {test_user_auth['token']}"}
        )
        assert response.status_code == 200, f"Failed to get chat messages: {response.text}"
        # Response should be a list (possibly empty)
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Got {len(data)} messages for chat: {test_user_auth['chat_id']}")
    
    def test_get_chat_messages_unauthenticated(self, test_user_auth):
        """Test getting chat messages without auth should fail"""
        response = requests.get(
            f"{BASE_URL}/api/chat/messages/{test_user_auth['chat_id']}"
        )
        assert response.status_code == 403, f"Expected 403 without auth, got: {response.status_code}"


class TestAdminChatsAPI:
    """Test admin chat management REST API"""
    
    @pytest.fixture
    def admin_auth(self):
        """Get admin authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        data = response.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"]
        }
    
    @pytest.fixture
    def test_user_auth(self):
        """Get test user authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        data = response.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"]
        }
    
    def test_admin_get_chats(self, admin_auth):
        """Admin can get all chat sessions"""
        response = requests.get(
            f"{BASE_URL}/api/admin/chats",
            headers={"Authorization": f"Bearer {admin_auth['token']}"}
        )
        assert response.status_code == 200, f"Failed to get admin chats: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Admin found {len(data)} chat sessions")
    
    def test_admin_chats_requires_admin(self, test_user_auth):
        """Regular user cannot access admin chats endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/admin/chats",
            headers={"Authorization": f"Bearer {test_user_auth['token']}"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got: {response.status_code}"
    
    def test_admin_chats_unauthenticated(self):
        """Unauthenticated user cannot access admin chats"""
        response = requests.get(f"{BASE_URL}/api/admin/chats")
        assert response.status_code == 403, f"Expected 403 without auth, got: {response.status_code}"


class TestChatSystemIntegration:
    """Integration tests for chat system"""
    
    @pytest.fixture
    def admin_auth(self):
        """Get admin authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        data = response.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"],
            "is_admin": data["user"]["isAdmin"]
        }
    
    @pytest.fixture
    def test_user_auth(self):
        """Get test user authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        data = response.json()
        return {
            "token": data["access_token"],
            "user_id": data["user"]["id"],
            "chat_id": f"chat_{data['user']['id']}",
            "is_admin": data["user"]["isAdmin"]
        }
    
    def test_admin_user_is_admin(self, admin_auth):
        """Verify admin user has isAdmin flag set"""
        assert admin_auth["is_admin"] == True, "Admin user should have isAdmin=True"
        print("Admin isAdmin flag verified")
    
    def test_regular_user_is_not_admin(self, test_user_auth):
        """Verify regular user does not have isAdmin flag"""
        assert test_user_auth["is_admin"] == False, "Test user should have isAdmin=False"
        print("Test user isAdmin flag verified")
    
    def test_chat_id_format(self, test_user_auth):
        """Verify chat ID format is chat_{userId}"""
        expected_chat_id = f"chat_{test_user_auth['user_id']}"
        assert test_user_auth["chat_id"] == expected_chat_id, f"Chat ID format incorrect"
        print(f"Chat ID format verified: {test_user_auth['chat_id']}")
    
    def test_full_chat_flow(self, test_user_auth, admin_auth):
        """Test the complete chat flow"""
        # 1. User can access their chat messages endpoint
        user_messages_response = requests.get(
            f"{BASE_URL}/api/chat/messages/{test_user_auth['chat_id']}",
            headers={"Authorization": f"Bearer {test_user_auth['token']}"}
        )
        assert user_messages_response.status_code == 200, "User should access their chat messages"
        
        # 2. Admin can access the chats list
        admin_chats_response = requests.get(
            f"{BASE_URL}/api/admin/chats",
            headers={"Authorization": f"Bearer {admin_auth['token']}"}
        )
        assert admin_chats_response.status_code == 200, "Admin should access chat sessions list"
        
        # 3. Admin can also access user's chat messages
        admin_user_messages_response = requests.get(
            f"{BASE_URL}/api/chat/messages/{test_user_auth['chat_id']}",
            headers={"Authorization": f"Bearer {admin_auth['token']}"}
        )
        assert admin_user_messages_response.status_code == 200, "Admin should access any user's chat messages"
        
        print("Full chat flow test passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
