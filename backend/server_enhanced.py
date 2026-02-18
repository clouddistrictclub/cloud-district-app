from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import base64
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
from bson import ObjectId

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# ==================== MODELS ====================

# User Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    firstName: str
    lastName: str
    dateOfBirth: str
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfileUpdate(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    profilePhoto: Optional[str] = None  # base64

class UserResponse(BaseModel):
    id: str
    email: str
    firstName: str
    lastName: str
    dateOfBirth: str
    isAdmin: bool
    loyaltyPoints: int
    phone: Optional[str] = None
    profilePhoto: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Brand Models
class Brand(BaseModel):
    id: Optional[str] = None
    name: str
    image: Optional[str] = None  # base64 logo
    isActive: bool = True
    displayOrder: int = 0
    productCount: int = 0

class BrandCreate(BaseModel):
    name: str
    image: Optional[str] = None
    isActive: bool = True
    displayOrder: int = 0

class BrandUpdate(BaseModel):
    name: Optional[str] = None
    image: Optional[str] = None
    isActive: Optional[bool] = None
    displayOrder: Optional[int] = None

# Product Models
class Product(BaseModel):
    id: Optional[str] = None
    name: str
    brandId: str  # Reference to brand
    brandName: str  # Denormalized for display
    category: str
    image: str  # base64
    images: Optional[List[str]] = []  # Multiple images
    puffCount: int
    flavor: str
    nicotinePercent: float
    price: float
    stock: int
    lowStockThreshold: int = 5
    description: Optional[str] = None
    isActive: bool = True
    isFeatured: bool = False
    loyaltyEarnRate: Optional[float] = None  # Override default rate
    displayOrder: int = 0

class ProductCreate(BaseModel):
    name: str
    brandId: str
    category: str
    image: str
    images: Optional[List[str]] = []
    puffCount: int
    flavor: str
    nicotinePercent: float
    price: float
    stock: int
    lowStockThreshold: int = 5
    description: Optional[str] = None
    isActive: bool = True
    isFeatured: bool = False
    loyaltyEarnRate: Optional[float] = None
    displayOrder: int = 0

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brandId: Optional[str] = None
    category: Optional[str] = None
    image: Optional[str] = None
    images: Optional[List[str]] = None
    puffCount: Optional[int] = None
    flavor: Optional[str] = None
    nicotinePercent: Optional[float] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    lowStockThreshold: Optional[int] = None
    description: Optional[str] = None
    isActive: Optional[bool] = None
    isFeatured: Optional[bool] = None
    loyaltyEarnRate: Optional[float] = None
    displayOrder: Optional[int] = None

class StockAdjustment(BaseModel):
    adjustment: int  # Positive to add, negative to remove
    reason: Optional[str] = None

# Order Models
class CartItem(BaseModel):
    productId: str
    quantity: int
    name: str
    price: float

class OrderCreate(BaseModel):
    items: List[CartItem]
    total: float
    pickupTime: str
    paymentMethod: str
    loyaltyPointsUsed: int = 0

class Order(BaseModel):
    id: Optional[str] = None
    userId: str
    items: List[CartItem]
    total: float
    pickupTime: str
    paymentMethod: str
    status: str = "Pending Payment"
    loyaltyPointsEarned: int = 0
    loyaltyPointsUsed: int = 0
    createdAt: datetime = Field(default_factory=datetime.utcnow)

class OrderStatusUpdate(BaseModel):
    status: str

# Admin User Management Models
class AdminUserUpdate(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    isAdmin: Optional[bool] = None
    loyaltyPoints: Optional[int] = None
    profilePhoto: Optional[str] = None

# ==================== AUTH UTILITIES ====================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_admin_user(user = Depends(get_current_user)):
    if not user.get("isAdmin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserRegister):
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    dob = datetime.strptime(user_data.dateOfBirth, "%Y-%m-%d")
    age = (datetime.utcnow() - dob).days / 365.25
    if age < 21:
        raise HTTPException(status_code=400, detail="Must be 21 or older")
    
    hashed_password = get_password_hash(user_data.password)
    user_dict = {
        "email": user_data.email,
        "password": hashed_password,
        "firstName": user_data.firstName,
        "lastName": user_data.lastName,
        "dateOfBirth": user_data.dateOfBirth,
        "phone": user_data.phone,
        "isAdmin": False,
        "loyaltyPoints": 0,
        "profilePhoto": None,
        "createdAt": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_dict)
    user_id = str(result.inserted_id)
    
    access_token = create_access_token(data={"sub": user_id})
    
    user_response = UserResponse(
        id=user_id,
        email=user_data.email,
        firstName=user_data.firstName,
        lastName=user_data.lastName,
        dateOfBirth=user_data.dateOfBirth,
        phone=user_data.phone,
        isAdmin=False,
        loyaltyPoints=0,
        profilePhoto=None
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user_id = str(user["_id"])
    access_token = create_access_token(data={"sub": user_id})
    
    user_response = UserResponse(
        id=user_id,
        email=user["email"],
        firstName=user["firstName"],
        lastName=user["lastName"],
        dateOfBirth=user["dateOfBirth"],
        phone=user.get("phone"),
        isAdmin=user.get("isAdmin", False),
        loyaltyPoints=user.get("loyaltyPoints", 0),
        profilePhoto=user.get("profilePhoto")
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user = Depends(get_current_user)):
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        firstName=user["firstName"],
        lastName=user["lastName"],
        dateOfBirth=user["dateOfBirth"],
        phone=user.get("phone"),
        isAdmin=user.get("isAdmin", False),
        loyaltyPoints=user.get("loyaltyPoints", 0),
        profilePhoto=user.get("profilePhoto")
    )

# ==================== USER PROFILE ENDPOINTS ====================

@api_router.patch("/profile", response_model=UserResponse)
async def update_profile(profile_data: UserProfileUpdate, user = Depends(get_current_user)):
    update_dict = {k: v for k, v in profile_data.dict().items() if v is not None}
    
    if update_dict:
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": update_dict}
        )
        
        updated_user = await db.users.find_one({"_id": user["_id"]})
        return UserResponse(
            id=str(updated_user["_id"]),
            email=updated_user["email"],
            firstName=updated_user["firstName"],
            lastName=updated_user["lastName"],
            dateOfBirth=updated_user["dateOfBirth"],
            phone=updated_user.get("phone"),
            isAdmin=updated_user.get("isAdmin", False),
            loyaltyPoints=updated_user.get("loyaltyPoints", 0),
            profilePhoto=updated_user.get("profilePhoto")
        )
    
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        firstName=user["firstName"],
        lastName=user["lastName"],
        dateOfBirth=user["dateOfBirth"],
        phone=user.get("phone"),
        isAdmin=user.get("isAdmin", False),
        loyaltyPoints=user.get("loyaltyPoints", 0),
        profilePhoto=user.get("profilePhoto")
    )

# ==================== BRAND ENDPOINTS ====================

@api_router.get("/brands", response_model=List[Brand])
async def get_brands(active_only: bool = False):
    query = {"isActive": True} if active_only else {}
    brands = await db.brands.find(query).to_list(1000)
    
    result = []
    for brand in brands:
        product_count = await db.products.count_documents({"brandId": str(brand["_id"])})
        result.append(Brand(
            id=str(brand["_id"]),
            name=brand["name"],
            image=brand.get("image"),
            isActive=brand.get("isActive", True),
            productCount=product_count
        ))
    
    return result

@api_router.post("/brands", response_model=Brand)
async def create_brand(brand: BrandCreate, admin = Depends(get_admin_user)):
    brand_dict = brand.dict()
    brand_dict["createdAt"] = datetime.utcnow()
    
    result = await db.brands.insert_one(brand_dict)
    
    return Brand(
        id=str(result.inserted_id),
        name=brand.name,
        image=brand.image,
        isActive=brand.isActive,
        productCount=0
    )

@api_router.patch("/brands/{brand_id}", response_model=Brand)
async def update_brand(brand_id: str, brand_data: BrandUpdate, admin = Depends(get_admin_user)):
    update_dict = {k: v for k, v in brand_data.dict().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.brands.update_one(
        {"_id": ObjectId(brand_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Update brand name in all products if name changed
    if "name" in update_dict:
        await db.products.update_many(
            {"brandId": brand_id},
            {"$set": {"brandName": update_dict["name"]}}
        )
    
    brand = await db.brands.find_one({"_id": ObjectId(brand_id)})
    product_count = await db.products.count_documents({"brandId": brand_id})
    
    return Brand(
        id=str(brand["_id"]),
        name=brand["name"],
        image=brand.get("image"),
        isActive=brand.get("isActive", True),
        productCount=product_count
    )

@api_router.delete("/brands/{brand_id}")
async def delete_brand(brand_id: str, admin = Depends(get_admin_user)):
    # Check if brand has products
    product_count = await db.products.count_documents({"brandId": brand_id})
    if product_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete brand with {product_count} products. Reassign or delete products first."
        )
    
    result = await db.brands.delete_one({"_id": ObjectId(brand_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    return {"message": "Brand deleted successfully"}

# ==================== PRODUCT ENDPOINTS ====================

@api_router.get("/products", response_model=List[Product])
async def get_products(
    category: Optional[str] = None,
    brand_id: Optional[str] = None,
    active_only: bool = True
):
    query = {}
    if active_only:
        query["isActive"] = True
    if category:
        query["category"] = category
    if brand_id:
        query["brandId"] = brand_id
    
    products = await db.products.find(query).to_list(1000)
    return [Product(id=str(p["_id"]), **{k: v for k, v in p.items() if k != "_id"}) for p in products]

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(id=str(product["_id"]), **{k: v for k, v in product.items() if k != "_id"})

@api_router.post("/products", response_model=Product)
async def create_product(product: ProductCreate, admin = Depends(get_admin_user)):
    # Get brand name
    brand = await db.brands.find_one({"_id": ObjectId(product.brandId)})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    product_dict = product.dict()
    product_dict["brandName"] = brand["name"]
    product_dict["createdAt"] = datetime.utcnow()
    
    result = await db.products.insert_one(product_dict)
    product_dict["id"] = str(result.inserted_id)
    
    return Product(**product_dict)

@api_router.patch("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product_data: ProductUpdate, admin = Depends(get_admin_user)):
    update_dict = {k: v for k, v in product_data.dict().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # If brandId is being updated, get the new brand name
    if "brandId" in update_dict:
        brand = await db.brands.find_one({"_id": ObjectId(update_dict["brandId"])})
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        update_dict["brandName"] = brand["name"]
    
    result = await db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    return Product(id=str(product["_id"]), **{k: v for k, v in product.items() if k != "_id"})

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, admin = Depends(get_admin_user)):
    result = await db.products.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

@api_router.patch("/products/{product_id}/stock")
async def adjust_product_stock(product_id: str, adjustment: StockAdjustment, admin = Depends(get_admin_user)):
    """Manually adjust product inventory"""
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    new_stock = product["stock"] + adjustment.adjustment
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Stock cannot be negative")
    
    await db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"stock": new_stock}}
    )
    
    # Log the adjustment (optional but recommended)
    log_entry = {
        "productId": product_id,
        "productName": product["name"],
        "adjustment": adjustment.adjustment,
        "previousStock": product["stock"],
        "newStock": new_stock,
        "reason": adjustment.reason,
        "adminId": str(admin["_id"]),
        "timestamp": datetime.utcnow()
    }
    await db.inventory_logs.insert_one(log_entry)
    
    return {
        "message": "Stock adjusted successfully",
        "previousStock": product["stock"],
        "newStock": new_stock,
        "adjustment": adjustment.adjustment
    }


# ==================== ORDER ENDPOINTS ====================

@api_router.post("/orders", response_model=Order)
async def create_order(order_data: OrderCreate, user = Depends(get_current_user)):
    # Check inventory for all items
    for item in order_data.items:
        product = await db.products.find_one({"_id": ObjectId(item.productId)})
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.productId} not found")
        if product["stock"] < item.quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient stock for {product['name']}. Available: {product['stock']}"
            )
    
    points_earned = int(order_data.total)
    
    order_dict = {
        "userId": str(user["_id"]),
        "items": [item.dict() for item in order_data.items],
        "total": order_data.total,
        "pickupTime": order_data.pickupTime,
        "paymentMethod": order_data.paymentMethod,
        "status": "Pending Payment",
        "loyaltyPointsEarned": points_earned,
        "loyaltyPointsUsed": order_data.loyaltyPointsUsed,
        "createdAt": datetime.utcnow()
    }
    
    result = await db.orders.insert_one(order_dict)
    
    # Deduct used loyalty points
    if order_data.loyaltyPointsUsed > 0:
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$inc": {"loyaltyPoints": -order_data.loyaltyPointsUsed}}
        )
    
    order_dict["id"] = str(result.inserted_id)
    return Order(**order_dict)

@api_router.get("/orders", response_model=List[Order])
async def get_orders(user = Depends(get_current_user)):
    orders = await db.orders.find({"userId": str(user["_id"])}).sort("createdAt", -1).to_list(1000)
    return [Order(id=str(o["_id"]), **{k: v for k, v in o.items() if k != "_id"}) for o in orders]

@api_router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, user = Depends(get_current_user)):
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["userId"] != str(user["_id"]) and not user.get("isAdmin", False):
        raise HTTPException(status_code=403, detail="Access denied")
    return Order(id=str(order["_id"]), **{k: v for k, v in order.items() if k != "_id"})

# ==================== ADMIN ORDER ENDPOINTS ====================

@api_router.get("/admin/orders", response_model=List[Order])
async def get_all_orders(admin = Depends(get_admin_user)):
    orders = await db.orders.find().sort("createdAt", -1).to_list(1000)
    return [Order(id=str(o["_id"]), **{k: v for k, v in o.items() if k != "_id"}) for o in orders]

@api_router.patch("/admin/orders/{order_id}/status")
async def update_order_status(order_id: str, status_update: OrderStatusUpdate, admin = Depends(get_admin_user)):
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # If marking as "Paid", award loyalty points and reduce inventory
    if status_update.status == "Paid" and order["status"] == "Pending Payment":
        # Award loyalty points
        await db.users.update_one(
            {"_id": ObjectId(order["userId"])},
            {"$inc": {"loyaltyPoints": order["loyaltyPointsEarned"]}}
        )
        
        # Reduce inventory for each item
        for item in order["items"]:
            await db.products.update_one(
                {"_id": ObjectId(item["productId"])},
                {"$inc": {"stock": -item["quantity"]}}
            )
    
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": status_update.status}}
    )
    
    return {"message": "Order status updated"}

# ==================== ADMIN USER MANAGEMENT ====================

@api_router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(admin = Depends(get_admin_user)):
    users = await db.users.find().to_list(1000)
    return [
        UserResponse(
            id=str(u["_id"]),
            email=u["email"],
            firstName=u["firstName"],
            lastName=u["lastName"],
            dateOfBirth=u["dateOfBirth"],
            phone=u.get("phone"),
            isAdmin=u.get("isAdmin", False),
            loyaltyPoints=u.get("loyaltyPoints", 0),
            profilePhoto=u.get("profilePhoto")
        ) for u in users
    ]

@api_router.patch("/admin/users/{user_id}", response_model=UserResponse)
async def admin_update_user(user_id: str, user_data: AdminUserUpdate, admin = Depends(get_admin_user)):
    update_dict = {k: v for k, v in user_data.dict().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        firstName=user["firstName"],
        lastName=user["lastName"],
        dateOfBirth=user["dateOfBirth"],
        phone=user.get("phone"),
        isAdmin=user.get("isAdmin", False),
        loyaltyPoints=user.get("loyaltyPoints", 0),
        profilePhoto=user.get("profilePhoto")
    )

# ==================== CATEGORIES ENDPOINT ====================

@api_router.get("/categories")
async def get_categories():
    return [
        {"name": "Best Sellers", "value": "best-sellers"},
        {"name": "New Arrivals", "value": "new-arrivals"},
        {"name": "All Products", "value": "all"}
    ]

# Include router
@app.get("/")
async def root():
    return {"message": "Cloud District API is live"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "server_enhanced:app",
        host="0.0.0.0",
        port=int(os.environ["PORT"]),
    )
