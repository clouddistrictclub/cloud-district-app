from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import base64
import uuid
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
from bson import ObjectId
import string
import secrets as sec_module
import httpx
import re as _re
import math

ROOT_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = ROOT_DIR / 'uploads' / 'products'
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

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

import time as _time

@app.middleware("http")
async def request_logger(request: Request, call_next):
    if "/uploads/" in request.url.path or request.url.path in ("/", "/health", "/healthz"):
        return await call_next(request)
    start = _time.time()
    method = request.method
    path = request.url.path
    response = await call_next(request)
    ms = round((_time.time() - start) * 1000)
    status_code = response.status_code
    level = "ERROR" if status_code >= 500 else ("WARN" if status_code >= 400 else "INFO")
    logger_line = f"{level} | {method} {path} -> {status_code} ({ms}ms)"
    if status_code >= 400:
        logging.warning(logger_line)
    else:
        logging.info(logger_line)
    return response

# ==================== MODELS ====================

def generate_referral_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(sec_module.choice(chars) for _ in range(7))
        return code

RESERVED_USERNAMES = {"admin", "support", "api", "clouddistrict", "orders", "root", "help"}
USERNAME_RE = _re.compile(r'^[a-zA-Z0-9_]{3,20}$')

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
    username: Optional[str] = None
    referredByUserId: Optional[str] = None
    creditBalance: float = 0.0
    isDisabled: bool = False

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
    model: Optional[str] = None
    category: str
    image: str  # URL or base64
    images: Optional[List[str]] = []  # Multiple images
    puffCount: int
    flavor: str
    nicotinePercent: float = 5.0
    nicotineStrength: Optional[str] = None
    deviceType: Optional[str] = None
    slug: Optional[str] = None
    price: float
    stock: int
    lowStockThreshold: int = 5
    description: Optional[str] = None
    isActive: bool = True
    isFeatured: bool = False
    loyaltyEarnRate: Optional[float] = None  # Override default rate
    cloudzReward: Optional[int] = None
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
    customerName: Optional[str] = None
    customerEmail: Optional[str] = None
    adminNotes: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    status: str

class OrderEditItem(BaseModel):
    productId: str
    quantity: int
    name: str
    price: float

class OrderEdit(BaseModel):
    items: List[OrderEditItem]
    total: float
    adminNotes: Optional[str] = None

# Admin User Management Models
class AdminUserUpdate(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    isAdmin: Optional[bool] = None
    isDisabled: Optional[bool] = None
    loyaltyPoints: Optional[int] = None
    creditBalance: Optional[float] = None
    profilePhoto: Optional[str] = None

class CreditAdjust(BaseModel):
    amount: float   # positive = add, negative = deduct
    description: str

# Review Models
class ReviewCreate(BaseModel):
    productId: str
    orderId: str
    rating: int  # 1–5
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: str
    productId: str
    userId: str
    orderId: str
    rating: int
    comment: Optional[str] = None
    createdAt: str
    userName: str
    isHidden: bool = False

class ReviewModerationUpdate(BaseModel):
    isHidden: Optional[bool] = None
    comment: Optional[str] = None

class UserUsernameUpdate(BaseModel):
    username: str

class AdminReferrerUpdate(BaseModel):
    referrerIdentifier: Optional[str] = None

class CloudzAdjust(BaseModel):
    amount: int
    description: str

# ==================== CLOUDZ LEDGER ====================

async def log_cloudz_transaction(user_id: str, tx_type: str, amount: int, reference: str = "", description: str = "", order_id: str = ""):
    """Log every Cloudz balance change to the ledger collection."""
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    balance_after = user.get("loyaltyPoints", 0) if user else 0
    entry = {
        "userId": user_id,
        "type": tx_type,
        "amount": amount,
        "balanceAfter": balance_after,
        "reference": reference,
        "description": description or reference,
        "createdAt": datetime.utcnow(),
    }
    if order_id:
        entry["orderId"] = order_id
    await db.cloudz_ledger.insert_one(entry)

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
        username=user_doc.get("username"),
        referredByUserId=user_doc.get("referredBy"),
        creditBalance=user_doc.get("creditBalance", 0.0),
        isDisabled=user_doc.get("isDisabled", False),
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
        referred_by = None

    # Award 500 Cloudz signup bonus
    signup_bonus = 500
    await db.users.update_one(
        {"_id": result.inserted_id},
        {"$set": {"loyaltyPoints": signup_bonus}}
    )
    await log_cloudz_transaction(user_id, "signup_bonus", signup_bonus, "Welcome to Cloud District Club!")
    
    access_token = create_access_token(data={"sub": user_id})
    
    user_response = UserResponse(
        id=user_id,
        email=user_data.email,
        firstName=user_data.firstName,
        lastName=user_data.lastName,
        dateOfBirth=user_data.dateOfBirth,
        phone=user_data.phone,
        isAdmin=False,
        loyaltyPoints=signup_bonus,
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

@api_router.patch("/me/username", response_model=UserResponse)
async def update_username(data: UserUsernameUpdate, user = Depends(get_current_user)):
    username = data.username.strip()
    if not USERNAME_RE.match(username):
        raise HTTPException(status_code=400, detail="Username must be 3–20 characters: letters, numbers, underscore only")
    if username.lower() in RESERVED_USERNAMES:
        raise HTTPException(status_code=400, detail="This username is reserved")
    existing = await db.users.find_one({
        "username": {"$regex": f"^{_re.escape(username)}$", "$options": "i"},
        "_id": {"$ne": user["_id"]},
    })
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"username": username, "referralCode": username.lower()}}
    )
    updated = await db.users.find_one({"_id": user["_id"]})
    return build_user_response(updated)

@api_router.get("/me/referral-earnings")
async def get_my_referral_earnings(user = Depends(get_current_user)):
    user_id = str(user["_id"])
    pipeline = [
        {"$match": {"userId": user_id, "type": "referral_reward"}},
        {"$group": {"_id": None, "totalCloudz": {"$sum": "$amount"}, "orderCount": {"$sum": 1}}},
    ]
    result = await db.cloudz_ledger.aggregate(pipeline).to_list(1)
    if result:
        return {"totalReferralCloudz": result[0]["totalCloudz"], "referralOrderCount": result[0]["orderCount"]}
    return {"totalReferralCloudz": 0, "referralOrderCount": 0}

@api_router.get("/me/cloudz-ledger")
async def get_my_cloudz_ledger(user = Depends(get_current_user)):
    entries = await db.cloudz_ledger.find(
        {"userId": str(user["_id"])}, {"_id": 0}
    ).sort("createdAt", -1).to_list(500)
    for e in entries:
        if isinstance(e.get("createdAt"), datetime):
            e["createdAt"] = e["createdAt"].isoformat()
    return entries

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
    active_only: bool = True,
    in_stock_only: bool = False
):
    query = {}
    if active_only:
        query["isActive"] = True
    if in_stock_only:
        query["stock"] = {"$gt": 0}
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


# ==================== ADMIN EXPORT ====================

@api_router.get("/admin/export/products")
async def export_products(admin = Depends(get_admin_user)):
    """Return all product documents as a raw JSON array for backup purposes."""
    docs = await db.products.find({}).to_list(None)
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs


@api_router.post("/admin/import/products")
async def import_products(
    request: Request,
    wipe: bool = False,
    admin = Depends(get_admin_user),
):
    """Restore product catalog from a backup JSON array.

    - wipe=true  → delete all existing products, then insert
    - wipe=false → upsert each document by _id (default, safe)
    """
    try:
        products = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body must be valid JSON")

    if not isinstance(products, list):
        raise HTTPException(status_code=400, detail="Input must be a JSON array")

    if wipe:
        await db.products.delete_many({})

    inserted = updated = skipped = 0
    for raw in products:
        if not isinstance(raw, dict):
            skipped += 1
            continue

        doc = dict(raw)  # copy so we don't mutate caller data

        # Resolve _id
        raw_id = doc.pop("_id", None)
        if raw_id:
            try:
                oid = ObjectId(str(raw_id))
            except Exception:
                oid = ObjectId()  # bad _id → generate new
        else:
            oid = ObjectId()

        if wipe:
            doc["_id"] = oid
            await db.products.insert_one(doc)
            inserted += 1
        else:
            result = await db.products.replace_one(
                {"_id": oid},
                {**doc, "_id": oid},
                upsert=True,
            )
            if result.upserted_id:
                inserted += 1
            else:
                updated += 1

    return {
        "imported": inserted + updated,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "wipe": wipe,
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
    
    points_earned = int(order_data.total) * 3
    reward_discount = 0.0
    reward_points_used = 0

    # Handle tier-based reward redemption at checkout
    if order_data.rewardId:
        try:
            reward_oid = ObjectId(order_data.rewardId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid reward ID format")
        reward = await db.loyalty_rewards.find_one({
            "_id": reward_oid,
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
        "status": "Awaiting Pickup (Cash)" if order_data.paymentMethod == "Cash on Pickup" else "Pending Payment",
        "loyaltyPointsEarned": points_earned,
        "loyaltyPointsUsed": reward_points_used,
        "rewardId": order_data.rewardId,
        "rewardDiscount": reward_discount,
        "createdAt": datetime.utcnow()
    }
    
    result = await db.orders.insert_one(order_dict)
    
    order_dict["id"] = str(result.inserted_id)

    # Deduct inventory immediately on order creation
    for item in order_data.items:
        await db.products.update_one(
            {"_id": ObjectId(item.productId)},
            {"$inc": {"stock": -item.quantity}}
        )

    # Send order confirmation email (non-blocking, only if SMTP configured)
    try:
        from email_utils import is_email_configured, send_email, build_order_confirmation_html
        if is_email_configured():
            email_html = build_order_confirmation_html(
                order_id=order_dict["id"],
                items=order_dict["items"],
                total=order_dict["total"],
            )
            send_email(user.get("email", ""), "Order Confirmation - Cloud District Club", email_html)
    except Exception as e:
        logging.warning(f"Order confirmation email skipped: {e}")

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

@api_router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str, user = Depends(get_current_user)):
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["userId"] != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    if order["status"] != "Pending Payment":
        raise HTTPException(status_code=400, detail="Only orders with status 'Pending Payment' can be cancelled")
    # Restore inventory
    for item in order.get("items", []):
        await db.products.update_one(
            {"_id": ObjectId(item["productId"])},
            {"$inc": {"stock": item["quantity"]}}
        )
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": "Cancelled"}}
    )
    return {"message": "Order cancelled"}

# ==================== REVIEW ENDPOINTS ====================

@api_router.get("/reviews/check/{product_id}")
async def check_can_review(product_id: str, user = Depends(get_current_user)):
    user_id = str(user["_id"])
    # Find a qualifying order (Paid, Ready for Pickup, or Completed)
    qualifying_order = await db.orders.find_one({
        "userId": user_id,
        "status": {"$in": ["Paid", "Ready for Pickup", "Completed"]},
        "items.productId": product_id,
    })
    if not qualifying_order:
        return {"canReview": False, "hasReviewed": False, "orderId": None}
    existing_review = await db.reviews.find_one({"productId": product_id, "userId": user_id})
    if existing_review:
        return {"canReview": False, "hasReviewed": True, "orderId": str(qualifying_order["_id"])}
    return {"canReview": True, "hasReviewed": False, "orderId": str(qualifying_order["_id"])}

@api_router.post("/reviews", response_model=ReviewResponse)
async def create_review(review_data: ReviewCreate, user = Depends(get_current_user)):
    user_id = str(user["_id"])
    if not (1 <= review_data.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    # Verify user purchased this product
    qualifying_order = await db.orders.find_one({
        "userId": user_id,
        "status": {"$in": ["Paid", "Ready for Pickup", "Completed"]},
        "items.productId": review_data.productId,
    })
    if not qualifying_order:
        raise HTTPException(status_code=403, detail="You can only review products you have purchased")
    # Prevent duplicate reviews
    existing = await db.reviews.find_one({"productId": review_data.productId, "userId": user_id})
    if existing:
        raise HTTPException(status_code=400, detail="You have already reviewed this product")
    doc = {
        "productId": review_data.productId,
        "userId": user_id,
        "orderId": review_data.orderId,
        "rating": review_data.rating,
        "comment": review_data.comment,
        "createdAt": datetime.utcnow().isoformat(),
        "userName": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
    }
    result = await db.reviews.insert_one(doc)
    return ReviewResponse(id=str(result.inserted_id), **{k: v for k, v in doc.items()})

@api_router.get("/reviews/product/{product_id}", response_model=List[ReviewResponse])
async def get_product_reviews(product_id: str):
    reviews = await db.reviews.find(
        {"productId": product_id, "isHidden": {"$ne": True}}
    ).sort("createdAt", -1).to_list(100)
    return [ReviewResponse(
        id=str(r["_id"]),
        isHidden=r.get("isHidden", False),
        **{k: v for k, v in r.items() if k not in ("_id", "isHidden")}
    ) for r in reviews]

# ==================== ADMIN REVIEW MODERATION ====================

@api_router.get("/admin/reviews")
async def get_all_reviews(admin = Depends(get_admin_user)):
    reviews = await db.reviews.find().sort("createdAt", -1).to_list(1000)
    result = []
    for r in reviews:
        product = await db.products.find_one({"_id": ObjectId(r["productId"])}, {"_id": 0, "name": 1})
        result.append({
            "id": str(r["_id"]),
            "productName": product.get("name", "Unknown") if product else "Unknown",
            "isHidden": r.get("isHidden", False),
            **{k: v for k, v in r.items() if k != "_id"},
        })
    return result

@api_router.patch("/admin/reviews/{review_id}")
async def admin_update_review(review_id: str, update: ReviewModerationUpdate, admin = Depends(get_admin_user)):
    update_dict = {}
    if update.isHidden is not None:
        update_dict["isHidden"] = update.isHidden
    if update.comment is not None:
        update_dict["comment"] = update.comment
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.reviews.update_one({"_id": ObjectId(review_id)}, {"$set": update_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review updated"}

@api_router.delete("/admin/reviews/{review_id}")
async def admin_delete_review(review_id: str, admin = Depends(get_admin_user)):
    result = await db.reviews.delete_one({"_id": ObjectId(review_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review deleted"}

# ==================== ADMIN USER PROFILE ====================

@api_router.get("/admin/users/{user_id}/profile")
async def get_user_profile(user_id: str, admin = Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)}, {"hashedPassword": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_data = {k: v for k, v in user.items() if k != "_id"}
    user_data["id"] = user_id
    if isinstance(user_data.get("createdAt"), datetime):
        user_data["createdAt"] = user_data["createdAt"].isoformat()
    user_data["referredByUserId"] = user_data.pop("referredBy", None)
    # Resolve referrer to a readable object
    if user_data["referredByUserId"]:
        try:
            ref_doc = await db.users.find_one(
                {"_id": ObjectId(user_data["referredByUserId"])},
                {"username": 1, "referralCode": 1, "email": 1}
            )
            if ref_doc:
                user_data["referredByUser"] = {
                    "id": str(ref_doc["_id"]),
                    "username": ref_doc.get("username"),
                    "referralCode": ref_doc.get("referralCode"),
                    "email": ref_doc.get("email"),
                }
        except Exception:
            pass
    orders = await db.orders.find({"userId": user_id}).sort("createdAt", -1).to_list(200)
    paid_statuses = {"Paid", "Ready for Pickup", "Completed"}
    total_spent = sum(o.get("total", 0) for o in orders if o.get("status") in paid_statuses)
    orders_resp = []
    for o in orders:
        od = {k: v for k, v in o.items() if k != "_id"}
        od["id"] = str(o["_id"])
        if isinstance(od.get("createdAt"), datetime):
            od["createdAt"] = od["createdAt"].isoformat()
        orders_resp.append(od)
    reviews = await db.reviews.find({"userId": user_id}).sort("createdAt", -1).to_list(100)
    reviews_resp = [{"id": str(r["_id"]), **{k: v for k, v in r.items() if k != "_id"}} for r in reviews]
    return {"user": user_data, "orders": orders_resp, "totalSpent": total_spent, "reviews": reviews_resp}

# ==================== ADMIN REFERRER & CLOUDZ ====================

@api_router.patch("/admin/users/{user_id}/referrer")
async def admin_set_referrer(user_id: str, data: AdminReferrerUpdate, admin = Depends(get_admin_user)):
    if not data.referrerIdentifier or not data.referrerIdentifier.strip():
        # Remove referrer
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"referredBy": None}})
        return {"message": "Referrer removed"}

    identifier = data.referrerIdentifier.strip().lower()

    # Resolve referrer: try referralCode, username, email, then ObjectId
    referrer = await db.users.find_one({"referralCode": identifier})
    if not referrer:
        referrer = await db.users.find_one({"username": {"$regex": f"^{_re.escape(identifier)}$", "$options": "i"}})
    if not referrer:
        referrer = await db.users.find_one({"email": {"$regex": f"^{_re.escape(identifier)}$", "$options": "i"}})
    if not referrer:
        try:
            referrer = await db.users.find_one({"_id": ObjectId(data.referrerIdentifier.strip())})
        except Exception:
            pass

    if not referrer:
        raise HTTPException(status_code=404, detail="Referrer not found")

    referrer_id = str(referrer["_id"])
    if referrer_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot assign user as their own referrer")

    paid_orders = await db.orders.count_documents({
        "userId": user_id,
        "status": {"$in": ["Paid", "Ready for Pickup", "Completed"]},
    })
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"referredBy": referrer_id}})
    return {
        "message": "Referrer updated",
        "warning": f"User has {paid_orders} paid orders — referral earnings will not be retroactive" if paid_orders > 0 else None,
    }

@api_router.get("/admin/users/{user_id}/cloudz-ledger")
async def admin_get_cloudz_ledger(user_id: str, admin = Depends(get_admin_user)):
    entries = await db.cloudz_ledger.find(
        {"userId": user_id}, {"_id": 0}
    ).sort("createdAt", -1).to_list(500)
    for e in entries:
        if isinstance(e.get("createdAt"), datetime):
            e["createdAt"] = e["createdAt"].isoformat()
    return entries

@api_router.post("/admin/users/{user_id}/cloudz-adjust")
async def admin_adjust_cloudz(user_id: str, data: CloudzAdjust, admin = Depends(get_admin_user)):
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$inc": {"loyaltyPoints": data.amount}})
    await log_cloudz_transaction(user_id, "admin_adjustment", data.amount, data.description, data.description)
    updated = await db.users.find_one({"_id": ObjectId(user_id)}, {"loyaltyPoints": 1})
    return {"message": "Balance updated", "newBalance": updated.get("loyaltyPoints", 0) if updated else 0}

# ==================== ADMIN ORDER EDITING ====================

@api_router.patch("/admin/orders/{order_id}/edit")
async def admin_edit_order(order_id: str, edit: OrderEdit, admin = Depends(get_admin_user)):
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    old_items = order.get("items", [])
    new_items = [item.dict() for item in edit.items]
    # Restore stock for old items then deduct for new items
    for item in old_items:
        await db.products.update_one(
            {"_id": ObjectId(item["productId"])},
            {"$inc": {"stock": item["quantity"]}}
        )
    for item in new_items:
        await db.products.update_one(
            {"_id": ObjectId(item["productId"])},
            {"$inc": {"stock": -item["quantity"]}}
        )
    update_dict: dict = {"items": new_items, "total": edit.total}
    if edit.adminNotes is not None:
        update_dict["adminNotes"] = edit.adminNotes
    await db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": update_dict})
    return {"message": "Order updated"}

# ==================== ADMIN ORDER ENDPOINTS ====================

@api_router.get("/admin/orders", response_model=List[Order])
async def get_all_orders(admin = Depends(get_admin_user)):
    orders = await db.orders.find().sort("createdAt", -1).to_list(1000)
    user_ids = list({o["userId"] for o in orders if o.get("userId")})
    users_map: dict = {}
    if user_ids:
        async for u in db.users.find(
            {"_id": {"$in": [ObjectId(uid) for uid in user_ids]}},
            {"_id": 1, "firstName": 1, "lastName": 1, "email": 1},
        ):
            uid = str(u["_id"])
            users_map[uid] = {
                "name": f"{u.get('firstName', '')} {u.get('lastName', '')}".strip(),
                "email": u.get("email", ""),
            }
    result = []
    for o in orders:
        uid = o.get("userId", "")
        user_info = users_map.get(uid, {})
        order_data = {k: v for k, v in o.items() if k != "_id"}
        order_data["id"] = str(o["_id"])
        order_data["customerName"] = user_info.get("name")
        order_data["customerEmail"] = user_info.get("email")
        result.append(Order(**order_data))
    return result

@api_router.patch("/admin/orders/{order_id}/status")
async def update_order_status(order_id: str, status_update: OrderStatusUpdate, admin = Depends(get_admin_user)):
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # If marking as "Cancelled", restore inventory (admin can cancel any order)
    if status_update.status == "Cancelled" and order["status"] != "Cancelled":
        for item in order.get("items", []):
            await db.products.update_one(
                {"_id": ObjectId(item["productId"])},
                {"$inc": {"stock": item["quantity"]}}
            )
        await db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": "Cancelled"}}
        )
        await send_push_notification(
            order["userId"],
            "Order Cancelled",
            f"Order #{order_id[-6:].upper()} has been cancelled.",
        )
        return {"message": "Order status updated"}

    # If marking as "Paid", award loyalty points and reduce inventory
    if status_update.status == "Paid" and order["status"] in ("Pending Payment", "Awaiting Pickup (Cash)"):
        # Award loyalty points
        await db.users.update_one(
            {"_id": ObjectId(order["userId"])},
            {"$inc": {"loyaltyPoints": order["loyaltyPointsEarned"]}}
        )
        await log_cloudz_transaction(
            order["userId"], "purchase_reward", order["loyaltyPointsEarned"],
            f"Order #{order_id[:8]}",
            f"Purchase reward from order #{order_id}",
            order_id,
        )

        # Per-order referral earnings: 0.5 Cloudz per $1 spent — handled below outside this gate

        # Streak bonus: award once per ISO week
        streak_bonus = await maybe_award_streak_bonus(order["userId"], order_id)

    # Per-order referral reward: 0.5 Cloudz per $1, fires whenever status becomes "Paid" (deduped per order)
    if status_update.status == "Paid" and not order.get("referralRewardIssued", False):
        buyer_doc = await db.users.find_one({"_id": ObjectId(order["userId"])}, {"referredBy": 1})
        referrer_id = buyer_doc.get("referredBy") if buyer_doc else None
        if referrer_id:
            reward = math.floor(float(order.get("total") or 0) * 0.5)
            try:
                referrer_check = await db.users.find_one({"_id": ObjectId(referrer_id)}, {"_id": 1})
                if referrer_check and reward > 0:
                    await db.users.update_one(
                        {"_id": ObjectId(referrer_id)},
                        {"$inc": {"loyaltyPoints": reward}}
                    )
                    await db.cloudz_ledger.insert_one({
                        "userId": referrer_id,
                        "type": "referral_reward",
                        "amount": reward,
                        "description": f"Referral reward from order #{order_id}",
                        "orderId": order_id,
                        "createdAt": datetime.utcnow(),
                    })
            except Exception as e:
                pass  # Invalid referrer ID stored — skip silently
        await db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"referralRewardIssued": True}}
        )
    
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": status_update.status}}
    )
    
    # Send push notification to the user about order status change
    await send_push_notification(
        order["userId"],
        "Order Update",
        f"Order #{order_id[-6:].upper()} is now: {status_update.status}",
    )
    
    return {"message": "Order status updated"}

# ==================== PUSH NOTIFICATIONS ====================

class PushTokenRegister(BaseModel):
    token: str

async def send_push_notification(user_id: str, title: str, body: str):
    tokens = await db.push_tokens.find({"userId": user_id}, {"_id": 0, "token": 1}).to_list(10)
    if not tokens:
        return
    messages = [
        {"to": t["token"], "sound": "default", "title": title, "body": body}
        for t in tokens if t.get("token", "").startswith("ExponentPushToken")
    ]
    if not messages:
        return
    try:
        async with httpx.AsyncClient() as client_http:
            await client_http.post(
                "https://exp.host/--/api/v2/push/send",
                json=messages,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=10,
            )
    except Exception as e:
        logger.error(f"Push notification failed: {e}")

@api_router.post("/push/register")
async def register_push_token(payload: PushTokenRegister, user=Depends(get_current_user)):
    user_id = str(user["_id"])
    if not payload.token.startswith("ExponentPushToken"):
        raise HTTPException(status_code=400, detail="Invalid Expo push token")
    await db.push_tokens.update_one(
        {"userId": user_id, "token": payload.token},
        {"$set": {"userId": user_id, "token": payload.token, "updatedAt": datetime.utcnow()}},
        upsert=True,
    )
    return {"message": "Push token registered"}

# ==================== STREAK BONUS ====================

STREAK_BONUS = {2: 50, 3: 100, 4: 200}  # week: bonus; 5+ = 500

async def calculate_streak(user_id: str) -> int:
    """Return the number of consecutive ISO weeks (ending at current) with a Paid order."""
    paid_orders = await db.orders.find(
        {"userId": user_id, "status": "Paid"},
        {"_id": 0, "createdAt": 1},
    ).sort("createdAt", -1).to_list(5000)
    if not paid_orders:
        return 0
    weeks_with_orders: set = set()
    for o in paid_orders:
        dt = o["createdAt"]
        weeks_with_orders.add(dt.isocalendar()[:2])  # (year, week)
    now = datetime.utcnow()
    current = now.isocalendar()[:2]
    streak = 0
    yr, wk = current
    while (yr, wk) in weeks_with_orders:
        streak += 1
        # Go to previous ISO week
        prev_day = datetime.fromisocalendar(yr, wk, 1) - timedelta(days=1)
        yr, wk = prev_day.isocalendar()[:2]
    return streak

def get_streak_bonus(streak: int) -> int:
    if streak < 2:
        return 0
    return STREAK_BONUS.get(streak, 500)

async def maybe_award_streak_bonus(user_id: str, order_id: str):
    """Award streak bonus once per ISO week when the first order is marked Paid."""
    now = datetime.utcnow()
    iso_year, iso_week = now.isocalendar()[:2]
    existing = await db.cloudz_ledger.find_one({
        "userId": user_id,
        "type": "streak_bonus",
        "isoYear": iso_year,
        "isoWeek": iso_week,
    })
    if existing:
        return 0
    streak = await calculate_streak(user_id)
    bonus = get_streak_bonus(streak)
    if bonus <= 0:
        return 0
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$inc": {"loyaltyPoints": bonus}},
    )
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    balance_after = user.get("loyaltyPoints", 0) if user else 0
    await db.cloudz_ledger.insert_one({
        "userId": user_id,
        "type": "streak_bonus",
        "amount": bonus,
        "balanceAfter": balance_after,
        "reference": f"Week {iso_week} streak ({streak} weeks) - Order #{order_id[:8]}",
        "isoYear": iso_year,
        "isoWeek": iso_week,
        "createdAt": now,
    })
    return bonus

@api_router.get("/loyalty/streak")
async def get_user_streak(user=Depends(get_current_user)):
    user_id = str(user["_id"])
    streak = await calculate_streak(user_id)
    bonus = get_streak_bonus(streak)
    next_bonus = get_streak_bonus(streak + 1)
    now = datetime.utcnow()
    iso_year, iso_week = now.isocalendar()[:2]
    # Days until end of current ISO week (Sunday)
    current_weekday = now.isocalendar()[2]  # 1=Mon .. 7=Sun
    days_left = 7 - current_weekday
    return {
        "streak": streak,
        "currentBonus": bonus,
        "nextBonus": next_bonus,
        "daysUntilExpiry": days_left,
        "isoWeek": iso_week,
        "isoYear": iso_year,
    }

# ==================== SUPPORT TICKETS ====================

class SupportTicketCreate(BaseModel):
    subject: str
    message: str

@api_router.post("/support/tickets")
async def create_support_ticket(ticket: SupportTicketCreate, user=Depends(get_current_user)):
    user_id = str(user["_id"])
    doc = {
        "userId": user_id,
        "userName": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
        "userEmail": user.get("email", ""),
        "subject": ticket.subject,
        "message": ticket.message,
        "status": "open",
        "createdAt": datetime.utcnow(),
    }
    result = await db.support_tickets.insert_one(doc)
    return {"id": str(result.inserted_id), "message": "Support ticket created"}

@api_router.get("/admin/support/tickets")
async def get_support_tickets(
    skip: int = 0,
    limit: int = 50,
    status: str = None,
    admin=Depends(get_admin_user),
):
    query = {}
    if status:
        query["status"] = status
    tickets = await db.support_tickets.find(query, {"_id": 0}).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.support_tickets.count_documents(query)
    return {"tickets": tickets, "total": total}

# ==================== ADMIN USER MANAGEMENT ====================

@api_router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(admin = Depends(get_admin_user)):
    users = await db.users.find().to_list(1000)
    return [build_user_response(u) for u in users]

@api_router.get("/admin/ledger")
async def get_admin_ledger(
    skip: int = 0,
    limit: int = 50,
    userId: str = None,
    type: str = None,
    admin = Depends(get_admin_user),
):
    query = {}
    if userId:
        query["userId"] = userId
    if type:
        query["type"] = type

    entries = await db.cloudz_ledger.find(query, {"_id": 0}).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.cloudz_ledger.count_documents(query)

    # Batch-fetch user emails
    user_ids = list({e["userId"] for e in entries})
    users_map = {}
    if user_ids:
        users_cursor = db.users.find({"_id": {"$in": [ObjectId(uid) for uid in user_ids]}}, {"_id": 1, "email": 1})
        async for u in users_cursor:
            users_map[str(u["_id"])] = u.get("email", "unknown")

    for e in entries:
        e["userEmail"] = users_map.get(e["userId"], "unknown")
        if isinstance(e.get("createdAt"), datetime):
            e["createdAt"] = e["createdAt"].isoformat()

    return {"entries": entries, "total": total, "skip": skip, "limit": limit}

@api_router.patch("/admin/users/{user_id}", response_model=UserResponse)
async def admin_update_user(user_id: str, user_data: AdminUserUpdate, admin = Depends(get_admin_user)):
    update_dict = {k: v for k, v in user_data.dict().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Track loyalty point changes for ledger
    old_points = None
    if "loyaltyPoints" in update_dict:
        old_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if old_user:
            old_points = old_user.get("loyaltyPoints", 0)

    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Log admin grant/adjustment to ledger
    if old_points is not None:
        delta = update_dict["loyaltyPoints"] - old_points
        if delta != 0:
            await log_cloudz_transaction(
                user_id, "admin_adjustment", delta,
                f"Admin set balance to {update_dict['loyaltyPoints']}"
            )

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    return build_user_response(user)


@api_router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin = Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("isAdmin") and str(user["_id"]) != str(admin["_id"]):
        raise HTTPException(status_code=400, detail="Cannot delete another admin account")
    await db.users.delete_one({"_id": ObjectId(user_id)})
    return {"message": "User deleted"}


@api_router.post("/admin/users/{user_id}/credit")
async def admin_adjust_credit(user_id: str, data: CreditAdjust, admin = Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    current = user.get("creditBalance", 0.0)
    new_balance = round(current + data.amount, 2)
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="Insufficient credit balance")
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"creditBalance": new_balance}}
    )
    # Log to cloudz ledger as informational (0 cloudz)
    await db.cloudz_ledger.insert_one({
        "userId": user_id,
        "type": "credit_adjustment",
        "amount": 0,
        "creditAmount": data.amount,
        "newCreditBalance": new_balance,
        "balanceAfter": user.get("loyaltyPoints", 0),
        "description": data.description or f"Admin Credit Adjustment: ${data.amount:+.2f}",
        "createdAt": datetime.utcnow(),
    })
    return {"newCreditBalance": new_balance, "adjustment": data.amount}

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
        f"Redeemed {tier['name']} (${tier['reward']:.2f} off)",
        f"Tier redemption: {tier['name']} for ${tier['reward']:.2f} off",
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

@api_router.get("/loyalty/ledger")
async def get_cloudz_ledger(user = Depends(get_current_user)):
    entries = await db.cloudz_ledger.find(
        {"userId": str(user["_id"])}, {"_id": 0}
    ).sort("createdAt", -1).to_list(200)
    for e in entries:
        if isinstance(e.get("createdAt"), datetime):
            e["createdAt"] = e["createdAt"].isoformat()
    return entries

# ==================== CATEGORIES ENDPOINT ====================

TIER_COLORS = {
    "tier_1": "#CD7F32",
    "tier_2": "#C0C0C0",
    "tier_3": "#FFD700",
    "tier_4": "#A8B8D0",
    "tier_5": "#B9F2FF",
}

def resolve_tier(points: int):
    tier_name = None
    tier_id = None
    for t in LOYALTY_TIERS:
        if points >= t["pointsRequired"]:
            tier_name = t["name"]
            tier_id = t["id"]
    return tier_name, TIER_COLORS.get(tier_id, "#666") if tier_id else ("#666")

@api_router.get("/leaderboard")
async def get_leaderboard(user = Depends(get_current_user)):
    projection = {"_id": 1, "firstName": 1, "lastName": 1, "loyaltyPoints": 1, "referralCount": 1}
    current_uid = str(user["_id"])

    by_points_cursor = db.users.find({}, projection).sort("loyaltyPoints", -1).limit(20)
    by_referrals_cursor = db.users.find({}, projection).sort("referralCount", -1).limit(20)

    by_points_raw = await by_points_cursor.to_list(20)
    by_referrals_raw = await by_referrals_cursor.to_list(20)

    def build_entry(doc, rank):
        first = doc.get("firstName", "")
        last = doc.get("lastName", "")
        display = f"{first} {last[0]}." if last else first
        pts = doc.get("loyaltyPoints", 0)
        tier_name, tier_color = resolve_tier(pts)
        return {
            "rank": rank,
            "displayName": display,
            "points": pts,
            "referralCount": doc.get("referralCount", 0),
            "tier": tier_name,
            "tierColor": tier_color,
            "isCurrentUser": str(doc["_id"]) == current_uid,
        }

    return {
        "byPoints": [build_entry(d, i + 1) for i, d in enumerate(by_points_raw)],
        "byReferrals": [build_entry(d, i + 1) for i, d in enumerate(by_referrals_raw)],
    }

@api_router.get("/categories")
async def get_categories():
    return [
        {"name": "Best Sellers", "value": "best-sellers"},
        {"name": "New Arrivals", "value": "new-arrivals"},
        {"name": "All Products", "value": "all"}
    ]

# ==================== LIVE CHAT ====================

class ChatMessage(BaseModel):
    message: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, chat_id: str, websocket: WebSocket):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)

    def disconnect(self, chat_id: str, websocket: WebSocket):
        if chat_id in self.active_connections:
            self.active_connections[chat_id] = [ws for ws in self.active_connections[chat_id] if ws != websocket]
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def broadcast(self, chat_id: str, message: dict):
        if chat_id in self.active_connections:
            for ws in self.active_connections[chat_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

    def get_active_chat_ids(self) -> list[str]:
        return list(self.active_connections.keys())

chat_manager = ConnectionManager()

@api_router.get("/chat/messages/{chat_id}")
async def get_chat_messages(chat_id: str, user=Depends(get_current_user)):
    messages = await db.chat_messages.find(
        {"chatId": chat_id}, {"_id": 0}
    ).sort("createdAt", 1).to_list(200)
    return messages

@api_router.get("/admin/chats")
async def get_admin_chats(admin=Depends(get_admin_user)):
    sessions = await db.chat_sessions.find({}, {"_id": 0}).sort("lastMessageAt", -1).to_list(100)
    active_ids = chat_manager.get_active_chat_ids()
    for s in sessions:
        s["online"] = s.get("chatId") in active_ids
        uid = s.get("userId")
        if uid:
            try:
                u = await db.users.find_one({"_id": ObjectId(uid)}, {"name": 1, "email": 1})
                s["userName"] = u.get("name", u.get("email", "Unknown")) if u else "Unknown"
            except Exception:
                s["userName"] = "Unknown"
    return sessions

# --- Image Upload ---
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@api_router.post("/upload/product-image")
async def upload_product_image(file: UploadFile = File(...), admin=Depends(get_admin_user)):
    ext = Path(file.filename or "image.jpg").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOADS_DIR / filename
    filepath.write_bytes(data)
    return {"url": f"/api/uploads/products/{filename}"}

# --- Migration: base64 → file ---
async def migrate_base64_images():
    # Migrate product images
    cursor = db.products.find({"image": {"$regex": "^data:image/"}})
    count = 0
    async for product in cursor:
        b64 = product["image"]
        try:
            header, encoded = b64.split(",", 1)
            mime = header.split(";")[0].split(":")[1]
            ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
            ext = ext_map.get(mime, ".jpg")
            raw = base64.b64decode(encoded)
            if len(raw) < 100:
                # Invalid base64 data — clear the image field
                await db.products.update_one({"_id": product["_id"]}, {"$set": {"image": ""}})
                logging.info(f"Cleared invalid image for product {product['_id']}")
                continue
            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = UPLOADS_DIR / filename
            filepath.write_bytes(raw)
            url = f"/api/uploads/products/{filename}"
            await db.products.update_one({"_id": product["_id"]}, {"$set": {"image": url}})
            count += 1
        except Exception as e:
            # Clear corrupted image data
            await db.products.update_one({"_id": product["_id"]}, {"$set": {"image": ""}})
            logging.warning(f"Migration cleared corrupt image for product {product['_id']}: {e}")
    if count:
        logging.info(f"Migrated {count} product images from base64 to files")

    # Migrate brand images
    cursor = db.brands.find({"image": {"$regex": "^data:image/"}})
    bcount = 0
    async for brand in cursor:
        b64 = brand["image"]
        try:
            header, encoded = b64.split(",", 1)
            mime = header.split(";")[0].split(":")[1]
            ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
            ext = ext_map.get(mime, ".jpg")
            raw = base64.b64decode(encoded)
            if len(raw) < 100:
                continue
            filename = f"brand_{uuid.uuid4().hex}{ext}"
            filepath = UPLOADS_DIR / filename
            filepath.write_bytes(raw)
            url = f"/api/uploads/products/{filename}"
            await db.brands.update_one({"_id": brand["_id"]}, {"$set": {"image": url}})
            bcount += 1
        except Exception as e:
            logging.warning(f"Migration skip brand {brand['_id']}: {e}")
    if bcount:
        logging.info(f"Migrated {bcount} brand images from base64 to files")

@app.on_event("startup")
async def startup_migrate():
    await migrate_base64_images()

@api_router.get("/health")
def api_health():
    return {"status": "ok"}

# ==================== ADMIN ANALYTICS ====================

@api_router.get("/admin/analytics")
async def get_admin_analytics(
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    admin = Depends(get_admin_user),
):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    if startDate:
        try:
            start_dt = datetime.strptime(startDate, "%Y-%m-%d")
        except ValueError:
            start_dt = today
    else:
        start_dt = today

    if endDate:
        try:
            end_dt = datetime.strptime(endDate, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            end_dt = today + timedelta(days=1)
    else:
        end_dt = today + timedelta(days=1)

    date_filter: dict = {"createdAt": {"$gte": start_dt, "$lt": end_dt}}

    totals = await db.orders.aggregate([
        {"$match": date_filter},
        {"$group": {"_id": None, "count": {"$sum": 1}, "revenue": {"$sum": "$total"}}},
    ]).to_list(1)
    total_orders = totals[0]["count"] if totals else 0
    total_revenue = totals[0]["revenue"] if totals else 0.0
    avg_order_value = total_revenue / total_orders if total_orders else 0.0

    payment_data = await db.orders.aggregate([
        {"$match": date_filter},
        {"$group": {"_id": "$paymentMethod", "total": {"$sum": "$total"}, "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
    ]).to_list(20)
    revenue_by_payment = [{"method": r["_id"] or "Unknown", "total": r["total"], "count": r["count"]} for r in payment_data]

    top_products_data = await db.orders.aggregate([
        {"$match": date_filter},
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.productId",
            "name": {"$first": "$items.name"},
            "quantity": {"$sum": "$items.quantity"},
            "revenue": {"$sum": {"$multiply": ["$items.price", "$items.quantity"]}},
        }},
        {"$sort": {"quantity": -1}},
        {"$limit": 8},
    ]).to_list(8)
    top_products = [{"productId": p["_id"], "name": p["name"], "quantity": p["quantity"], "revenue": p["revenue"]} for p in top_products_data]

    top_cust_data = await db.orders.aggregate([
        {"$match": date_filter},
        {"$group": {"_id": "$userId", "totalSpent": {"$sum": "$total"}, "orderCount": {"$sum": 1}}},
        {"$sort": {"totalSpent": -1}},
        {"$limit": 8},
    ]).to_list(8)
    top_customers = []
    for c in top_cust_data:
        try:
            user = await db.users.find_one({"_id": ObjectId(c["_id"])}, {"firstName": 1, "lastName": 1, "email": 1})
        except Exception:
            user = None
        name = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip() if user else "Unknown"
        top_customers.append({
            "userId": c["_id"],
            "name": name or (user.get("email", "Unknown") if user else "Unknown"),
            "email": user.get("email", "") if user else "",
            "totalSpent": c["totalSpent"],
            "orderCount": c["orderCount"],
        })

    low_inv_docs = await db.products.find(
        {"stock": {"$lt": 3}, "isActive": True}, {"_id": 1, "name": 1, "stock": 1}
    ).sort("stock", 1).to_list(20)
    low_inventory = [{"productId": str(p["_id"]), "name": p["name"], "stock": p["stock"]} for p in low_inv_docs]

    customer_agg = await db.orders.aggregate([
        {"$match": date_filter},
        {"$group": {"_id": "$userId", "totalSpent": {"$sum": "$total"}, "orderCount": {"$sum": 1}}},
        {"$group": {
            "_id": None,
            "totalCustomers": {"$sum": 1},
            "repeatCustomers": {"$sum": {"$cond": [{"$gt": ["$orderCount", 1]}, 1, 0]}},
            "avgCLV": {"$avg": "$totalSpent"},
        }},
    ]).to_list(1)

    if customer_agg:
        ca = customer_agg[0]
        total_customers = ca["totalCustomers"]
        repeat_customers = ca["repeatCustomers"]
        repeat_rate = round(repeat_customers / total_customers * 100, 1) if total_customers else 0.0
        avg_clv = ca["avgCLV"]
    else:
        total_customers = repeat_customers = 0
        repeat_rate = avg_clv = 0.0

    return {
        "period": {"startDate": startDate, "endDate": endDate},
        "totalOrders": total_orders,
        "totalRevenue": round(total_revenue, 2),
        "avgOrderValue": round(avg_order_value, 2),
        "revenueByPayment": revenue_by_payment,
        "topProducts": top_products,
        "topCustomers": top_customers,
        "lowInventory": low_inventory,
        "avgCLV": round(avg_clv, 2),
        "repeatRate": repeat_rate,
        "totalCustomers": total_customers,
        "repeatCustomers": repeat_customers,
        "revenueTrendLast7Days": await _build_revenue_trend(),
    }

async def _build_revenue_trend():
    seven_days_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)
    trend_raw = await db.orders.aggregate([
        {"$match": {"createdAt": {"$gte": seven_days_ago}}},
        {"$group": {
            "_id": {"y": {"$year": "$createdAt"}, "m": {"$month": "$createdAt"}, "d": {"$dayOfMonth": "$createdAt"}},
            "revenue": {"$sum": "$total"},
        }},
        {"$sort": {"_id.y": 1, "_id.m": 1, "_id.d": 1}},
    ]).to_list(7)
    trend_map = {}
    for t in trend_raw:
        key = f"{t['_id']['y']}-{t['_id']['m']:02d}-{t['_id']['d']:02d}"
        trend_map[key] = round(t["revenue"], 2)
    result = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        key = day.strftime("%Y-%m-%d")
        result.append({"date": key, "revenue": trend_map.get(key, 0)})
    return result

# Include router
app.include_router(api_router)

# Serve uploaded images
app.mount("/api/uploads/products", StaticFiles(directory=str(UPLOADS_DIR)), name="product-uploads")


# WebSocket must be on app directly, not on router
@app.websocket("/api/ws/chat/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: str, token: str = ""):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")  # JWT stores user_id in 'sub' field
        if not user_id:
            await websocket.close(code=4001)
            return
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await chat_manager.connect(chat_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")

            # Typing indicator — just broadcast, don't persist
            if msg_type == "typing":
                await chat_manager.broadcast(chat_id, {
                    "type": "typing",
                    "senderId": user_id,
                    "senderName": user.get("name", user.get("email", "User")),
                    "isTyping": data.get("isTyping", False),
                })
                continue

            # Read receipt — mark messages as read and broadcast
            if msg_type == "read":
                await db.chat_messages.update_many(
                    {"chatId": chat_id, "senderId": {"$ne": user_id}, "readAt": {"$exists": False}},
                    {"$set": {"readAt": datetime.utcnow().isoformat(), "readBy": user_id}},
                )
                await chat_manager.broadcast(chat_id, {
                    "type": "read",
                    "readBy": user_id,
                    "readAt": datetime.utcnow().isoformat(),
                })
                continue

            # Regular message
            msg_text = data.get("message", "").strip()
            if not msg_text:
                continue
            msg_doc = {
                "type": "message",
                "chatId": chat_id,
                "senderId": user_id,
                "senderName": user.get("name", user.get("email", "User")),
                "isAdmin": user.get("isAdmin", False),
                "message": msg_text,
                "createdAt": datetime.utcnow().isoformat(),
            }
            await db.chat_messages.insert_one({**msg_doc})
            await db.chat_sessions.update_one(
                {"chatId": chat_id},
                {"$set": {
                    "chatId": chat_id,
                    "userId": chat_id.replace("chat_", ""),
                    "lastMessage": msg_text,
                    "lastMessageAt": datetime.utcnow().isoformat(),
                    "updatedAt": datetime.utcnow().isoformat(),
                }, "$setOnInsert": {"createdAt": datetime.utcnow().isoformat()}},
                upsert=True,
            )
            msg_doc.pop("_id", None)
            await chat_manager.broadcast(chat_id, msg_doc)
    except WebSocketDisconnect:
        chat_manager.disconnect(chat_id, websocket)

@app.get("/health", include_in_schema=False)
async def health_check():
    """Bare /health for Railway and other load-balancer health checks."""
    return {"status": "ok"}

@app.get("/", include_in_schema=False)
async def api_root():
    """API root — confirms the service is running."""
    return {"status": "Cloud District API running"}


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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
