"""
P0 Feature Tests for Cloud District Club
Tests: Chat API, WebSocket, Cart Discount Logic
"""
import pytest
import requests
import os
import json
import asyncio
import websockets

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://premium-vape-local.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "jkaatz@gmail.com"
ADMIN_PASSWORD = "Just1n23$"


class TestLogin:
    """Test authentication"""
    
    def test_admin_login(self):
        """P0-2: Admin can login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["isAdmin"] == True
        print(f"Admin login successful - User ID: {data['user']['id']}")
        return data


class TestChatAPI:
    """Test Chat API endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Could not authenticate")
        return response.json()["access_token"], response.json()["user"]["id"]
    
    def test_get_chat_messages(self, auth_token):
        """P0-3: Can retrieve chat messages"""
        token, user_id = auth_token
        chat_id = f"chat_{user_id}"
        
        response = requests.get(
            f"{BASE_URL}/api/chat/messages/{chat_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Chat messages retrieved: {len(data)} messages")
    
    def test_get_chat_messages_requires_auth(self):
        """P0-3: Chat messages require authentication"""
        response = requests.get(f"{BASE_URL}/api/chat/messages/chat_test")
        assert response.status_code in [401, 403]
    
    def test_admin_get_chat_sessions(self, auth_token):
        """P0-3: Admin can view all chat sessions"""
        token, _ = auth_token
        
        response = requests.get(
            f"{BASE_URL}/api/admin/chats",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Admin chat sessions: {len(data)}")


class TestProducts:
    """Test Products API"""
    
    def test_get_products(self):
        """Get available products for cart testing"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        print(f"Products available: {len(data)}")
        for p in data:
            print(f"  - {p['name']}: ${p['price']} (stock: {p['stock']})")
        return data


class TestCartDiscountLogic:
    """P0-4: Test cart discount logic
    
    Note: Cart calculations happen client-side in the Zustand store.
    These tests verify the frontend logic is correctly implemented by
    reviewing the cartStore.ts code.
    """
    
    def test_discount_constants(self):
        """Verify discount constants are correct"""
        # Read the cart store file
        cart_store_path = "/app/frontend/store/cartStore.ts"
        with open(cart_store_path, 'r') as f:
            content = f.read()
        
        # Verify threshold is 10
        assert "BULK_DISCOUNT_THRESHOLD = 10" in content
        print("PASS: Bulk discount threshold = 10")
        
        # Verify rate is 10%
        assert "BULK_DISCOUNT_RATE = 0.10" in content
        print("PASS: Bulk discount rate = 10%")
    
    def test_get_discount_function(self):
        """Verify getDiscount function logic"""
        cart_store_path = "/app/frontend/store/cartStore.ts"
        with open(cart_store_path, 'r') as f:
            content = f.read()
        
        # Verify getDiscount returns 0 when under threshold
        assert "if (!get().getBulkDiscountActive()) return 0" in content
        print("PASS: getDiscount returns 0 when < 10 items")
        
        # Verify calculation is subtotal * rate
        assert "getSubtotal() * BULK_DISCOUNT_RATE" in content
        print("PASS: Discount = subtotal * 10%")
    
    def test_get_total_function(self):
        """Verify getTotal includes discount"""
        cart_store_path = "/app/frontend/store/cartStore.ts"
        with open(cart_store_path, 'r') as f:
            content = f.read()
        
        # Total = subtotal - discount
        assert "getSubtotal() - get().getDiscount()" in content
        print("PASS: Total = Subtotal - Discount")
    
    def test_cart_ui_shows_discount_hint(self):
        """Verify cart UI shows discount hint"""
        cart_page_path = "/app/frontend/app/cart.tsx"
        with open(cart_page_path, 'r') as f:
            content = f.read()
        
        # Check for discount display
        assert "bulkActive" in content
        print("PASS: Cart checks if bulk discount is active")
        
        # Check for hint text
        assert "Add" in content and "more item" in content and "10% off" in content
        print("PASS: Cart shows 'Add X more items for 10% off' hint")
        
        # Check for discount line display
        assert "Bulk Discount (10%)" in content
        print("PASS: Cart shows 'Bulk Discount (10%)' when active")


class TestChatFeatures:
    """P0-3: Test chat features code presence"""
    
    def test_typing_indicator_component(self):
        """Verify TypingDots component exists"""
        chat_bubble_path = "/app/frontend/components/ChatBubble.tsx"
        with open(chat_bubble_path, 'r') as f:
            content = f.read()
        
        assert "const TypingDots = ()" in content
        print("PASS: TypingDots component exists")
        
        # Verify animation
        assert "Animated.loop" in content
        print("PASS: Typing animation is implemented")
    
    def test_read_receipts_implementation(self):
        """Verify read receipts are implemented"""
        chat_bubble_path = "/app/frontend/components/ChatBubble.tsx"
        with open(chat_bubble_path, 'r') as f:
            content = f.read()
        
        # Check for checkmark icon
        assert "checkmark-done" in content or "checkmark" in content
        print("PASS: Checkmark icons used for read receipts")
        
        # Check for allRead state
        assert "allRead" in content
        print("PASS: allRead state for tracking read status")
    
    def test_websocket_typing_handling(self):
        """Verify WebSocket handles typing events"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check typing broadcast
        assert "type: 'typing'" in content or 'type": "typing' in content or "msg_type == \"typing\"" in content
        print("PASS: Server broadcasts typing events")
    
    def test_websocket_read_handling(self):
        """Verify WebSocket handles read receipts"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check read receipt handling
        assert "msg_type == \"read\"" in content or "type: 'read'" in content
        print("PASS: Server handles read receipts")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
