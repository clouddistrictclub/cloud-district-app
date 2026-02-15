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
import string
import secrets as sec_module

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

def generate_referral_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(sec_module.choice(chars) for _ in range(7))
        return code

# User Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    firstName: str
    lastName: str
    dateOfBirth: str
    phone: Optional[str] = None
    referralCode: Optional[str] = None

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
    referralCode: Optional[str] = None
    referralCount: int = 0
    referralRewardsEarned: int = 0

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
    rewardId: Optional[str] = None

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

# ==================== CLOUDZ LEDGER ====================

async def log_cloudz_transaction(user_id: str, tx_type: str, amount: int, reference: str = ""):
    """Log every Cloudz balance change to the ledger collection."""
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    balance_after = user.get("loyaltyPoints", 0) if user else 0
    await db.cloudz_ledger.insert_one({
        "userId": user_id,
        "type": tx_type,
        "amount": amount,
        "balanceAfter": balance_after,
        "reference": reference,
        "createdAt": datetime.utcnow(),
    })

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
    except jwt.exceptions.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_admin_user(user = Depends(get_current_user)):
    if not user.get("isAdmin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def build_user_response(user_doc: dict) -> UserResponse:
    uid = str(user_doc["_id"]) if "_id" in user_doc else user_doc.get("id", "")
    return UserResponse(
        id=uid,
        email=user_doc["email"],
        firstName=user_doc["firstName"],
        lastName=user_doc["lastName"],
        dateOfBirth=user_doc["dateOfBirth"],
        phone=user_doc.get("phone"),
        isAdmin=user_doc.get("isAdmin", False),
        loyaltyPoints=user_doc.get("loyaltyPoints", 0),
        profilePhoto=user_doc.get("profilePhoto"),
        referralCode=user_doc.get("referralCode"),
        referralCount=user_doc.get("referralCount", 0),
        referralRewardsEarned=user_doc.get("referralRewardsEarned", 0),
    )

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
    
    # Handle referral code
    referred_by = None
    if user_data.referralCode:
        referrer = await db.users.find_one({"referralCode": user_data.referralCode.upper().strip()})
        if not referrer:
            raise HTTPException(status_code=400, detail="Invalid referral code")
        referred_by = str(referrer["_id"])

    # Generate unique referral code for new user
    ref_code = generate_referral_code()
    while await db.users.find_one({"referralCode": ref_code}):
        ref_code = generate_referral_code()

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
        "referralCode": ref_code,
        "referredBy": referred_by,
        "referralCount": 0,
        "referralRewardsEarned": 0,
        "referralRewardIssued": False,
        "createdAt": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_dict)
    user_id = str(result.inserted_id)

    # Prevent self-referral (edge case: code belonged to same email re-registered)
    if referred_by == user_id:
        await db.users.update_one({"_id": result.inserted_id}, {"$set": {"referredBy": None}})
    
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
        profilePhoto=None,
        referralCode=ref_code,
        referralCount=0,
        referralRewardsEarned=0
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
        profilePhoto=user.get("profilePhoto"),
        referralCode=user.get("referralCode"),
        referralCount=user.get("referralCount", 0),
        referralRewardsEarned=user.get("referralRewardsEarned", 0)
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user = Depends(get_current_user)):
    return build_user_response(user)

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
        return build_user_response(updated_user)
    
    return build_user_response(user)

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
    reward_discount = 0.0
    reward_points_used = 0

    # Handle tier-based reward redemption at checkout
    if order_data.rewardId:
        reward = await db.loyalty_rewards.find_one({
            "_id": ObjectId(order_data.rewardId),
            "userId": str(user["_id"]),
            "used": False,
        })
        if not reward:
            raise HTTPException(status_code=400, detail="Invalid or already used reward")
        reward_discount = reward["rewardAmount"]
        reward_points_used = reward["pointsSpent"]
        # Mark reward as used
        await db.loyalty_rewards.update_one(
            {"_id": ObjectId(order_data.rewardId)},
            {"$set": {"used": True, "usedAt": datetime.utcnow()}}
        )
    
    order_dict = {
        "userId": str(user["_id"]),
        "items": [item.dict() for item in order_data.items],
        "total": order_data.total,
        "pickupTime": order_data.pickupTime,
        "paymentMethod": order_data.paymentMethod,
        "status": "Pending Payment",
        "loyaltyPointsEarned": points_earned,
        "loyaltyPointsUsed": reward_points_used,
        "rewardId": order_data.rewardId,
        "rewardDiscount": reward_discount,
        "createdAt": datetime.utcnow()
    }
    
    result = await db.orders.insert_one(order_dict)
    
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
        await log_cloudz_transaction(
            order["userId"], "purchase_reward", order["loyaltyPointsEarned"],
            f"Order #{order_id[:8]}"
        )
        
        # Reduce inventory for each item
        for item in order["items"]:
            await db.products.update_one(
                {"_id": ObjectId(item["productId"])},
                {"$inc": {"stock": -item["quantity"]}}
            )

        # Referral reward trigger: first paid order for referred user
        buyer = await db.users.find_one({"_id": ObjectId(order["userId"])})
        if buyer and buyer.get("referredBy") and not buyer.get("referralRewardIssued", False):
            referrer_id = buyer["referredBy"]
            # Grant 1,000 Cloudz to new user
            await db.users.update_one(
                {"_id": ObjectId(order["userId"])},
                {"$inc": {"loyaltyPoints": 1000}, "$set": {"referralRewardIssued": True}}
            )
            await log_cloudz_transaction(
                order["userId"], "referral_bonus", 1000, "Welcome bonus (referred)"
            )
            # Grant 2,000 Cloudz to referrer + increment count
            await db.users.update_one(
                {"_id": ObjectId(referrer_id)},
                {"$inc": {"loyaltyPoints": 2000, "referralCount": 1, "referralRewardsEarned": 2000}}
            )
            await log_cloudz_transaction(
                referrer_id, "referral_bonus", 2000, f"Referral reward for user #{order['userId'][:8]}"
            )
            # Log rewards for both users in loyalty history
            now = datetime.utcnow()
            await db.loyalty_rewards.insert_many([
                {
                    "userId": order["userId"],
                    "tierId": "referral_bonus",
                    "tierName": "Referral Welcome Bonus",
                    "pointsSpent": 0,
                    "rewardAmount": 0,
                    "used": True,
                    "createdAt": now,
                    "type": "referral_earned",
                    "pointsEarned": 1000,
                },
                {
                    "userId": referrer_id,
                    "tierId": "referral_reward",
                    "tierName": "Referral Reward",
                    "pointsSpent": 0,
                    "rewardAmount": 0,
                    "used": True,
                    "createdAt": now,
                    "type": "referral_earned",
                    "pointsEarned": 2000,
                },
            ])
    
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": status_update.status}}
    )
    
    return {"message": "Order status updated"}

# ==================== ADMIN USER MANAGEMENT ====================

@api_router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(admin = Depends(get_admin_user)):
    users = await db.users.find().to_list(1000)
    return [build_user_response(u) for u in users]

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
    return build_user_response(user)

# ==================== LOYALTY TIER SYSTEM ====================

LOYALTY_TIERS = [
    {"id": "tier_1", "name": "Bronze Cloud", "pointsRequired": 1000, "reward": 5.00, "icon": "cloud-outline"},
    {"id": "tier_2", "name": "Silver Storm", "pointsRequired": 5000, "reward": 30.00, "icon": "cloud"},
    {"id": "tier_3", "name": "Gold Thunder", "pointsRequired": 10000, "reward": 75.00, "icon": "thunderstorm-outline"},
    {"id": "tier_4", "name": "Platinum Haze", "pointsRequired": 20000, "reward": 175.00, "icon": "thunderstorm"},
    {"id": "tier_5", "name": "Diamond Sky", "pointsRequired": 30000, "reward": 300.00, "icon": "diamond"},
]

class TierRedeemRequest(BaseModel):
    tierId: str

@api_router.get("/loyalty/tiers")
async def get_loyalty_tiers(user = Depends(get_current_user)):
    user_points = user.get("loyaltyPoints", 0)
    tiers = []
    for tier in LOYALTY_TIERS:
        tiers.append({
            **tier,
            "unlocked": user_points >= tier["pointsRequired"],
            "pointsNeeded": max(0, tier["pointsRequired"] - user_points),
        })
    return {
        "userPoints": user_points,
        "tiers": tiers,
    }

@api_router.post("/loyalty/redeem")
async def redeem_tier(req: TierRedeemRequest, user = Depends(get_current_user)):
    tier = next((t for t in LOYALTY_TIERS if t["id"] == req.tierId), None)
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")

    user_points = user.get("loyaltyPoints", 0)
    if user_points < tier["pointsRequired"]:
        raise HTTPException(status_code=400, detail="Not enough points to redeem this tier")

    # Check if user already has an active (unused) reward for this tier
    existing = await db.loyalty_rewards.find_one({
        "userId": str(user["_id"]),
        "tierId": req.tierId,
        "used": False,
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already have an active reward for this tier. Use it at checkout first.")

    # Deduct points
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$inc": {"loyaltyPoints": -tier["pointsRequired"]}}
    )
    await log_cloudz_transaction(
        str(user["_id"]), "tier_redemption", -tier["pointsRequired"],
        f"Redeemed {tier['name']} (${tier['reward']:.2f} off)"
    )

    # Create reward record
    reward_doc = {
        "userId": str(user["_id"]),
        "tierId": tier["id"],
        "tierName": tier["name"],
        "pointsSpent": tier["pointsRequired"],
        "rewardAmount": tier["reward"],
        "used": False,
        "createdAt": datetime.utcnow(),
    }
    result = await db.loyalty_rewards.insert_one(reward_doc)

    return {
        "message": f"Redeemed {tier['name']} for ${tier['reward']:.2f} off!",
        "rewardId": str(result.inserted_id),
        "rewardAmount": tier["reward"],
        "pointsSpent": tier["pointsRequired"],
        "remainingPoints": user_points - tier["pointsRequired"],
    }

@api_router.get("/loyalty/rewards")
async def get_active_rewards(user = Depends(get_current_user)):
    rewards = await db.loyalty_rewards.find({
        "userId": str(user["_id"]),
        "used": False,
    }).to_list(100)
    return [
        {
            "id": str(r["_id"]),
            "tierId": r["tierId"],
            "tierName": r["tierName"],
            "rewardAmount": r["rewardAmount"],
            "pointsSpent": r["pointsSpent"],
            "createdAt": r["createdAt"].isoformat() if isinstance(r["createdAt"], datetime) else r["createdAt"],
        }
        for r in rewards
    ]

@api_router.get("/loyalty/history")
async def get_redemption_history(user = Depends(get_current_user)):
    rewards = await db.loyalty_rewards.find({
        "userId": str(user["_id"]),
    }).sort("createdAt", -1).to_list(100)
    return [
        {
            "id": str(r["_id"]),
            "tierId": r["tierId"],
            "tierName": r["tierName"],
            "rewardAmount": r["rewardAmount"],
            "pointsSpent": r["pointsSpent"],
            "used": r["used"],
            "createdAt": r["createdAt"].isoformat() if isinstance(r["createdAt"], datetime) else r["createdAt"],
        }
        for r in rewards
    ]

# ==================== CATEGORIES ENDPOINT ====================

@api_router.get("/categories")
async def get_categories():
    return [
        {"name": "Best Sellers", "value": "best-sellers"},
        {"name": "New Arrivals", "value": "new-arrivals"},
        {"name": "All Products", "value": "all"}
    ]

# Include router
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
