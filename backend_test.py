#!/usr/bin/env python3
"""
Backend API Tests for Cloud District Club
Testing all core endpoints as requested in the review.
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Backend URL from frontend .env
BASE_URL = "https://cloudz-local-pickup.preview.emergentagent.com/api"

# Test data
TEST_USER = {
    "email": "test@test.com",
    "password": "Test123!",
    "firstName": "John",
    "lastName": "Doe",
    "dateOfBirth": "1990-01-01"
}

TEST_PRODUCT = {
    "name": "Test Vape",
    "brand": "Geek Bar",
    "category": "geek-bar",
    "image": "data:image/png;base64,test",
    "puffCount": 5000,
    "flavor": "Strawberry",
    "nicotinePercent": 5.0,
    "price": 19.99,
    "stock": 10
}

class CloudDistrictTests:
    def __init__(self):
        self.user_token = None
        self.admin_token = None
        self.test_user_id = None
        self.test_product_id = None
        self.test_order_id = None
        self.results = []
        
    def log_result(self, test_name, success, message="", response_data=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        if response_data and not success:
            print(f"   Response: {response_data}")
        print()
        
        self.results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "response": response_data
        })
    
    def test_categories_endpoint(self):
        """Test GET /api/categories"""
        try:
            response = requests.get(f"{BASE_URL}/categories")
            
            if response.status_code == 200:
                categories = response.json()
                if isinstance(categories, list) and len(categories) > 0:
                    # Check if we have expected categories
                    category_values = [cat.get('value') for cat in categories]
                    expected_categories = ['geek-bar', 'lost-mary', 'raz']
                    has_expected = any(cat in category_values for cat in expected_categories)
                    
                    if has_expected:
                        self.log_result("Categories Endpoint", True, 
                                      f"Found {len(categories)} categories including expected ones")
                    else:
                        self.log_result("Categories Endpoint", False, 
                                      f"Categories returned but missing expected values", categories)
                else:
                    self.log_result("Categories Endpoint", False, 
                                  "Empty or invalid categories response", categories)
            else:
                self.log_result("Categories Endpoint", False, 
                              f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Categories Endpoint", False, f"Request failed: {str(e)}")
    
    def test_user_registration(self):
        """Test POST /api/auth/register"""
        try:
            # First clean up any existing user
            try:
                requests.delete(f"{BASE_URL}/test/cleanup")  # Optional cleanup endpoint
            except:
                pass
                
            response = requests.post(f"{BASE_URL}/auth/register", 
                                   json=TEST_USER,
                                   headers={"Content-Type": "application/json"})
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.user_token = data["access_token"]
                    self.test_user_id = data["user"]["id"]
                    self.log_result("User Registration", True, 
                                  f"User registered successfully. ID: {self.test_user_id}")
                else:
                    self.log_result("User Registration", False, 
                                  "Missing token or user in response", data)
            else:
                # User might already exist, try to login instead
                if response.status_code == 400 and "already registered" in response.text:
                    self.log_result("User Registration", True, 
                                  "User already exists (expected), will test login")
                else:
                    self.log_result("User Registration", False, 
                                  f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("User Registration", False, f"Request failed: {str(e)}")
    
    def test_user_login(self):
        """Test POST /api/auth/login"""
        try:
            login_data = {
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
            
            response = requests.post(f"{BASE_URL}/auth/login", 
                                   json=login_data,
                                   headers={"Content-Type": "application/json"})
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.user_token = data["access_token"]
                    self.test_user_id = data["user"]["id"]
                    
                    # Check if user is admin (for admin tests later)
                    if data["user"].get("isAdmin", False):
                        self.admin_token = self.user_token
                        
                    self.log_result("User Login", True, 
                                  f"Login successful. Admin: {data['user'].get('isAdmin', False)}")
                else:
                    self.log_result("User Login", False, 
                                  "Missing token or user in response", data)
            else:
                self.log_result("User Login", False, 
                              f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("User Login", False, f"Request failed: {str(e)}")
    
    def test_get_user_profile(self):
        """Test GET /api/auth/me"""
        if not self.user_token:
            self.log_result("Get User Profile", False, "No user token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"}
            response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "email" in data and "firstName" in data:
                    expected_email = TEST_USER["email"]
                    if data["email"] == expected_email:
                        self.log_result("Get User Profile", True, 
                                      f"Profile retrieved: {data['firstName']} {data['lastName']}")
                    else:
                        self.log_result("Get User Profile", False, 
                                      f"Email mismatch: got {data['email']}, expected {expected_email}")
                else:
                    self.log_result("Get User Profile", False, 
                                  "Missing required fields in profile", data)
            else:
                self.log_result("Get User Profile", False, 
                              f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Get User Profile", False, f"Request failed: {str(e)}")
    
    def test_get_products(self):
        """Test GET /api/products (public endpoint)"""
        try:
            response = requests.get(f"{BASE_URL}/products")
            
            if response.status_code == 200:
                products = response.json()
                if isinstance(products, list):
                    self.log_result("Get Products", True, 
                                  f"Retrieved {len(products)} products")
                else:
                    self.log_result("Get Products", False, 
                                  "Products response is not a list", products)
            else:
                self.log_result("Get Products", False, 
                              f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Get Products", False, f"Request failed: {str(e)}")
    
    def create_admin_user(self):
        """Helper: Create admin user for admin testing"""
        try:
            # Try to create an admin user directly in database or use existing one
            # For now, we'll try to promote current user to admin via a direct approach
            # This is a test setup, not a production endpoint
            
            # If we have MongoDB access, we could directly update the user
            # For now, let's assume admin exists or try alternate approach
            
            # Try creating admin with different credentials
            admin_data = {
                "email": "admin@test.com", 
                "password": "Admin123!",
                "firstName": "Admin",
                "lastName": "User", 
                "dateOfBirth": "1985-01-01"
            }
            
            response = requests.post(f"{BASE_URL}/auth/register", 
                                   json=admin_data,
                                   headers={"Content-Type": "application/json"})
            
            if response.status_code == 200:
                data = response.json()
                # Would need to manually set isAdmin: true in database
                # For testing, we'll note this limitation
                pass
            
        except Exception as e:
            print(f"Admin setup note: {str(e)}")
    
    def test_create_product_admin(self):
        """Test POST /api/products (requires admin auth)"""
        if not self.user_token:
            self.log_result("Create Product (Admin)", False, "No user token available")
            return
            
        try:
            headers = {
                "Authorization": f"Bearer {self.user_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(f"{BASE_URL}/products", 
                                   json=TEST_PRODUCT,
                                   headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data:
                    self.test_product_id = data["id"]
                    self.log_result("Create Product (Admin)", True, 
                                  f"Product created with ID: {self.test_product_id}")
                else:
                    self.log_result("Create Product (Admin)", False, 
                                  "Product created but no ID returned", data)
            elif response.status_code == 403:
                self.log_result("Create Product (Admin)", False, 
                              "User is not admin - this is expected behavior for security")
            else:
                self.log_result("Create Product (Admin)", False, 
                              f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Create Product (Admin)", False, f"Request failed: {str(e)}")
    
    def test_create_order(self):
        """Test POST /api/orders (requires auth)"""
        if not self.user_token:
            self.log_result("Create Order", False, "No user token available")
            return
            
        try:
            headers = {
                "Authorization": f"Bearer {self.user_token}",
                "Content-Type": "application/json"
            }
            
            # Create a test order
            order_data = {
                "items": [
                    {
                        "productId": "test-product-id",
                        "quantity": 2,
                        "name": "Test Vape Product",
                        "price": 19.99
                    }
                ],
                "total": 39.98,
                "pickupTime": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
                "paymentMethod": "Credit Card",
                "loyaltyPointsUsed": 0
            }
            
            response = requests.post(f"{BASE_URL}/orders", 
                                   json=order_data,
                                   headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data:
                    self.test_order_id = data["id"]
                    points_earned = data.get("loyaltyPointsEarned", 0)
                    self.log_result("Create Order", True, 
                                  f"Order created with ID: {self.test_order_id}, Points earned: {points_earned}")
                else:
                    self.log_result("Create Order", False, 
                                  "Order created but no ID returned", data)
            else:
                self.log_result("Create Order", False, 
                              f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Create Order", False, f"Request failed: {str(e)}")
    
    def test_get_user_orders(self):
        """Test GET /api/orders (requires auth)"""
        if not self.user_token:
            self.log_result("Get User Orders", False, "No user token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"}
            response = requests.get(f"{BASE_URL}/orders", headers=headers)
            
            if response.status_code == 200:
                orders = response.json()
                if isinstance(orders, list):
                    self.log_result("Get User Orders", True, 
                                  f"Retrieved {len(orders)} orders for user")
                else:
                    self.log_result("Get User Orders", False, 
                                  "Orders response is not a list", orders)
            else:
                self.log_result("Get User Orders", False, 
                              f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Get User Orders", False, f"Request failed: {str(e)}")
    
    def test_get_all_orders_admin(self):
        """Test GET /api/admin/orders (requires admin auth)"""
        if not self.user_token:
            self.log_result("Get All Orders (Admin)", False, "No user token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"}
            response = requests.get(f"{BASE_URL}/admin/orders", headers=headers)
            
            if response.status_code == 200:
                orders = response.json()
                if isinstance(orders, list):
                    self.log_result("Get All Orders (Admin)", True, 
                                  f"Retrieved {len(orders)} total orders")
                else:
                    self.log_result("Get All Orders (Admin)", False, 
                                  "Orders response is not a list", orders)
            elif response.status_code == 403:
                self.log_result("Get All Orders (Admin)", False, 
                              "User is not admin - this is expected behavior for security")
            else:
                self.log_result("Get All Orders (Admin)", False, 
                              f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Get All Orders (Admin)", False, f"Request failed: {str(e)}")
    
    def test_update_order_status_admin(self):
        """Test PATCH /api/admin/orders/{orderId}/status (requires admin auth)"""
        if not self.user_token:
            self.log_result("Update Order Status (Admin)", False, "No user token available")
            return
            
        if not self.test_order_id:
            self.log_result("Update Order Status (Admin)", False, "No test order ID available")
            return
            
        try:
            headers = {
                "Authorization": f"Bearer {self.user_token}",
                "Content-Type": "application/json"
            }
            
            status_update = {"status": "Paid"}
            
            response = requests.patch(f"{BASE_URL}/admin/orders/{self.test_order_id}/status", 
                                    json=status_update,
                                    headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("Update Order Status (Admin)", True, 
                              f"Order status updated to 'Paid': {data}")
            elif response.status_code == 403:
                self.log_result("Update Order Status (Admin)", False, 
                              "User is not admin - this is expected behavior for security")
            elif response.status_code == 404:
                self.log_result("Update Order Status (Admin)", False, 
                              f"Order {self.test_order_id} not found")
            else:
                self.log_result("Update Order Status (Admin)", False, 
                              f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Update Order Status (Admin)", False, f"Request failed: {str(e)}")
    
    def test_non_admin_access_control(self):
        """Test that non-admin users cannot access admin endpoints"""
        if not self.user_token:
            self.log_result("Non-Admin Access Control", False, "No user token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"}
            
            # Test admin endpoints that should be blocked
            admin_endpoints = [
                f"{BASE_URL}/admin/orders",
                f"{BASE_URL}/products"  # POST to products (create)
            ]
            
            blocked_count = 0
            for endpoint in admin_endpoints:
                if endpoint.endswith('/products'):
                    # Test POST to products
                    response = requests.post(endpoint, json=TEST_PRODUCT, headers={
                        **headers, "Content-Type": "application/json"
                    })
                else:
                    # Test GET 
                    response = requests.get(endpoint, headers=headers)
                    
                if response.status_code == 403:
                    blocked_count += 1
            
            if blocked_count == len(admin_endpoints):
                self.log_result("Non-Admin Access Control", True, 
                              "All admin endpoints properly blocked for non-admin user")
            else:
                self.log_result("Non-Admin Access Control", False, 
                              f"Only {blocked_count}/{len(admin_endpoints)} admin endpoints blocked")
                
        except Exception as e:
            self.log_result("Non-Admin Access Control", False, f"Request failed: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend API tests"""
        print("🧪 Starting Cloud District Club Backend API Tests\n")
        print(f"Testing backend at: {BASE_URL}\n")
        
        # Test sequence
        self.test_categories_endpoint()
        self.test_user_registration()
        self.test_user_login()
        self.test_get_user_profile()
        self.test_get_products()
        self.test_create_product_admin()
        self.test_create_order()
        self.test_get_user_orders()
        self.test_get_all_orders_admin()
        self.test_update_order_status_admin()
        self.test_non_admin_access_control()
        
        # Summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        print("\n📋 DETAILED RESULTS:")
        for result in self.results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}")
            if result["message"]:
                print(f"   └─ {result['message']}")
        
        # Critical issues
        critical_failures = [r for r in self.results if not r["success"] and 
                           not ("not admin" in r["message"] or "expected behavior" in r["message"])]
        
        if critical_failures:
            print("\n🚨 CRITICAL ISSUES:")
            for failure in critical_failures:
                print(f"   ❌ {failure['test']}: {failure['message']}")
        
        print("\n" + "=" * 60)
        return passed == total

if __name__ == "__main__":
    tester = CloudDistrictTests()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)