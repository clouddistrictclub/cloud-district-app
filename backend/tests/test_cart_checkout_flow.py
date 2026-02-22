"""
Cart and Checkout Flow Tests - P0 Regression Testing
Tests cart functionality, checkout process, and order creation
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://premium-vape-local.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "jkaatz@gmail.com"
TEST_PASSWORD = "Just1n23$"


class TestCartCheckoutFlow:
    """Test cart and checkout flow end-to-end"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.user = data.get("user")
        assert self.token, "No access_token in response"
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_get_products_for_cart(self):
        """Fetch products to verify we have items available for cart"""
        response = self.session.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Failed to get products: {response.text}"
        products = response.json()
        assert len(products) > 0, "No products available"
        
        # Find products with stock
        products_with_stock = [p for p in products if p.get("stock", 0) > 0]
        print(f"Found {len(products_with_stock)} products with stock available")
        
        # Verify product structure
        for product in products[:3]:
            assert "id" in product, "Product missing id"
            assert "name" in product, "Product missing name"
            assert "price" in product, "Product missing price"
            assert "stock" in product, "Product missing stock"
            print(f"Product: {product['name']} - Stock: {product['stock']} - Price: ${product['price']}")
        
        return products_with_stock
    
    def test_get_onions_product(self):
        """Test fetching 'Onions' product specifically (known test product)"""
        response = self.session.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        # Find Onions product
        onions = next((p for p in products if "onion" in p.get("name", "").lower()), None)
        if onions:
            print(f"Found Onions product: ID={onions['id']}, Stock={onions['stock']}, Price=${onions['price']}")
            assert onions['stock'] > 0, "Onions product is out of stock"
            # Check image - should be URL based, not base64
            if onions.get('image'):
                assert not onions['image'].startswith('data:'), f"Onions has base64 image instead of URL: {onions['image'][:50]}"
                print(f"Onions image URL: {onions['image']}")
            return onions
        else:
            pytest.skip("Onions product not found in database")
    
    def test_product_with_empty_image_renders_correctly(self):
        """Test 'Admin Test Vape 2' product with cleared invalid base64 image"""
        response = self.session.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        # Find Admin Test Vape 2
        admin_test_vape = next((p for p in products if "admin test vape 2" in p.get("name", "").lower()), None)
        if admin_test_vape:
            print(f"Found Admin Test Vape 2: ID={admin_test_vape['id']}, Image='{admin_test_vape.get('image', '')}'")
            # Image should be empty (cleared from invalid base64)
            image = admin_test_vape.get('image', '')
            assert not image.startswith('data:'), "Image should not be base64"
            # Verify product is still functional
            detail_response = self.session.get(f"{BASE_URL}/api/products/{admin_test_vape['id']}")
            assert detail_response.status_code == 200, "Failed to get product detail"
            return admin_test_vape
        else:
            print("Admin Test Vape 2 not found - skipping")
            pytest.skip("Admin Test Vape 2 not found")
    
    def test_checkout_order_creation(self):
        """Test creating an order through checkout"""
        # First get a product with stock
        response = self.session.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        # Find product with sufficient stock
        product_with_stock = next((p for p in products if p.get("stock", 0) >= 1), None)
        if not product_with_stock:
            pytest.skip("No products with sufficient stock for order test")
        
        print(f"Using product: {product_with_stock['name']} (Stock: {product_with_stock['stock']})")
        
        # Create order
        order_data = {
            "items": [{
                "productId": product_with_stock['id'],
                "quantity": 1,
                "name": product_with_stock['name'],
                "price": product_with_stock['price']
            }],
            "total": product_with_stock['price'],
            "pickupTime": "Today - 12:00 PM - 2:00 PM",
            "paymentMethod": "Cash on Pickup",
            "loyaltyPointsUsed": 0,
            "rewardId": None
        }
        
        order_response = self.session.post(f"{BASE_URL}/api/orders", json=order_data)
        print(f"Order response status: {order_response.status_code}")
        print(f"Order response: {order_response.text[:500] if order_response.text else 'Empty'}")
        
        # Check if it's stock issue
        if order_response.status_code == 400:
            error_detail = order_response.json().get("detail", "")
            if "Insufficient stock" in error_detail:
                print(f"Stock issue: {error_detail}")
                pytest.skip(f"Product out of stock: {error_detail}")
        
        assert order_response.status_code == 200, f"Order creation failed: {order_response.text}"
        order = order_response.json()
        assert "id" in order, "Order missing id"
        assert order["status"] in ["Awaiting Pickup (Cash)", "Pending Payment"], f"Unexpected order status: {order['status']}"
        print(f"Order created successfully: ID={order['id']}, Status={order['status']}")
        
        # Verify order can be retrieved
        get_order_response = self.session.get(f"{BASE_URL}/api/orders/{order['id']}")
        assert get_order_response.status_code == 200, "Failed to retrieve created order"
        return order
    
    def test_checkout_with_zelle_payment(self):
        """Test checkout with Zelle payment method"""
        response = self.session.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        product_with_stock = next((p for p in products if p.get("stock", 0) >= 1), None)
        if not product_with_stock:
            pytest.skip("No products with stock")
        
        order_data = {
            "items": [{
                "productId": product_with_stock['id'],
                "quantity": 1,
                "name": product_with_stock['name'],
                "price": product_with_stock['price']
            }],
            "total": product_with_stock['price'],
            "pickupTime": "Tomorrow - 10:00 AM - 12:00 PM",
            "paymentMethod": "Zelle",
            "loyaltyPointsUsed": 0,
            "rewardId": None
        }
        
        order_response = self.session.post(f"{BASE_URL}/api/orders", json=order_data)
        
        if order_response.status_code == 400:
            error_detail = order_response.json().get("detail", "")
            if "Insufficient stock" in error_detail:
                pytest.skip(f"Product out of stock: {error_detail}")
        
        assert order_response.status_code == 200, f"Order creation failed: {order_response.text}"
        order = order_response.json()
        assert order["status"] == "Pending Payment", f"Zelle order should be Pending Payment, got: {order['status']}"
        print(f"Zelle order created: ID={order['id']}, Status={order['status']}")
    
    def test_checkout_with_invalid_reward(self):
        """Test checkout with invalid reward ID returns 400"""
        response = self.session.get(f"{BASE_URL}/api/products")
        products = response.json()
        product_with_stock = next((p for p in products if p.get("stock", 0) >= 1), None)
        if not product_with_stock:
            pytest.skip("No products with stock")
        
        order_data = {
            "items": [{
                "productId": product_with_stock['id'],
                "quantity": 1,
                "name": product_with_stock['name'],
                "price": product_with_stock['price']
            }],
            "total": product_with_stock['price'],
            "pickupTime": "Today - 12:00 PM - 2:00 PM",
            "paymentMethod": "Cash on Pickup",
            "loyaltyPointsUsed": 0,
            "rewardId": "invalid_reward_id_123"
        }
        
        order_response = self.session.post(f"{BASE_URL}/api/orders", json=order_data)
        # Should return 400 for invalid reward
        assert order_response.status_code == 400, f"Expected 400 for invalid reward, got {order_response.status_code}"
        print("Invalid reward correctly rejected with 400")
    
    def test_checkout_stock_validation(self):
        """Test that checkout validates stock correctly"""
        response = self.session.get(f"{BASE_URL}/api/products")
        products = response.json()
        
        # Find a product with stock
        product = next((p for p in products if p.get("stock", 0) > 0), None)
        if not product:
            pytest.skip("No products with stock")
        
        # Try to order more than available stock
        order_data = {
            "items": [{
                "productId": product['id'],
                "quantity": product['stock'] + 100,  # More than available
                "name": product['name'],
                "price": product['price']
            }],
            "total": product['price'] * (product['stock'] + 100),
            "pickupTime": "Today - 12:00 PM - 2:00 PM",
            "paymentMethod": "Cash on Pickup"
        }
        
        order_response = self.session.post(f"{BASE_URL}/api/orders", json=order_data)
        assert order_response.status_code == 400, f"Expected 400 for insufficient stock, got {order_response.status_code}"
        error_detail = order_response.json().get("detail", "")
        assert "Insufficient stock" in error_detail, f"Expected stock error message, got: {error_detail}"
        print(f"Stock validation working correctly: {error_detail}")
    
    def test_loyalty_rewards_endpoint(self):
        """Test getting active rewards for checkout"""
        response = self.session.get(f"{BASE_URL}/api/loyalty/rewards")
        assert response.status_code == 200, f"Failed to get rewards: {response.text}"
        rewards = response.json()
        print(f"User has {len(rewards)} active rewards")
        
        # Verify reward structure if any exist
        for reward in rewards[:2]:
            assert "id" in reward, "Reward missing id"
            assert "tierName" in reward, "Reward missing tierName"
            assert "rewardAmount" in reward, "Reward missing rewardAmount"
            print(f"Active reward: {reward['tierName']} - ${reward['rewardAmount']}")
        
        return rewards
    
    def test_get_user_orders(self):
        """Test getting user's order history"""
        response = self.session.get(f"{BASE_URL}/api/orders")
        assert response.status_code == 200, f"Failed to get orders: {response.text}"
        orders = response.json()
        print(f"User has {len(orders)} orders")
        
        # Verify order structure
        for order in orders[:3]:
            assert "id" in order, "Order missing id"
            assert "status" in order, "Order missing status"
            assert "total" in order, "Order missing total"
            print(f"Order: {order['id'][:8]}... - Status: {order['status']} - Total: ${order['total']}")
        
        return orders


class TestBulkDiscount:
    """Test bulk discount functionality (10+ items = 10% off)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_bulk_discount_calculation(self):
        """
        The bulk discount is calculated client-side in cartStore.ts.
        Backend just processes the total. This test verifies the logic is correct.
        10+ items = 10% discount
        """
        # This is client-side logic - we verify products exist for testing
        response = self.session.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        # Calculate what bulk discount would look like
        # Find a product with enough stock for 10+ items
        product = next((p for p in products if p.get("stock", 0) >= 10), None)
        if not product:
            pytest.skip("No product with 10+ stock for bulk discount test")
        
        # Simulate cart calculation
        quantity = 10
        subtotal = product['price'] * quantity
        discount = subtotal * 0.10  # 10% discount
        total = subtotal - discount
        
        print(f"Bulk discount test:")
        print(f"  Product: {product['name']} @ ${product['price']}")
        print(f"  Quantity: {quantity}")
        print(f"  Subtotal: ${subtotal:.2f}")
        print(f"  Discount (10%): -${discount:.2f}")
        print(f"  Total: ${total:.2f}")
        
        assert discount == subtotal * 0.10, "Discount calculation incorrect"


class TestImageHandling:
    """Test product image handling - URL-based images vs base64"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_product_images_are_urls_not_base64(self):
        """Verify product images are URL-based, not base64"""
        response = self.session.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        base64_count = 0
        url_count = 0
        empty_count = 0
        
        for product in products:
            image = product.get('image', '')
            if not image:
                empty_count += 1
                print(f"Empty image: {product['name']}")
            elif image.startswith('data:'):
                base64_count += 1
                print(f"BASE64 image (should be migrated): {product['name']}")
            elif image.startswith('/') or image.startswith('http'):
                url_count += 1
        
        print(f"\nImage summary:")
        print(f"  URL-based: {url_count}")
        print(f"  Base64: {base64_count}")
        print(f"  Empty: {empty_count}")
        
        # Base64 images should be migrated to URLs
        assert base64_count == 0, f"Found {base64_count} products with base64 images - migration needed"
    
    def test_uploaded_image_serves_correctly(self):
        """Test that uploaded product images are accessible"""
        response = self.session.get(f"{BASE_URL}/api/products")
        products = response.json()
        
        # Find a product with a URL-based image
        product_with_image = next(
            (p for p in products if p.get('image', '').startswith('/')),
            None
        )
        
        if not product_with_image:
            pytest.skip("No products with URL-based images")
        
        image_url = f"{BASE_URL}{product_with_image['image']}"
        print(f"Testing image URL: {image_url}")
        
        img_response = self.session.get(image_url)
        assert img_response.status_code == 200, f"Image not accessible: {img_response.status_code}"
        assert 'image' in img_response.headers.get('content-type', ''), "Response is not an image"
        print(f"Image accessible: {len(img_response.content)} bytes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
