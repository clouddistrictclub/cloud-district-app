from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
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

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    firstName: str
    lastName: str
    dateOfBirth: str  # Format: YYYY-MM-DD

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    firstName: str
    lastName: str
    dateOfBirth: str
    isAdmin: bool
    loyaltyPoints: int

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class Product(BaseModel):
    id: Optional[str] = None
    name: str
    brand: str
    category: str
    image: str  # base64
    puffCount: int
    flavor: str
    nicotinePercent: float
    price: float
    stock: int

class ProductCreate(BaseModel):
    name: str
    brand: str
    category: str
    image: str
    puffCount: int
    flavor: str
    nicotinePercent: float
    price: float
    stock: int

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
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check age (must be 21+)
    dob = datetime.strptime(user_data.dateOfBirth, "%Y-%m-%d")
    age = (datetime.utcnow() - dob).days / 365.25
    if age < 21:
        raise HTTPException(status_code=400, detail="Must be 21 or older")
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user_dict = {
        "email": user_data.email,
        "password": hashed_password,
        "firstName": user_data.firstName,
        "lastName": user_data.lastName,
        "dateOfBirth": user_data.dateOfBirth,
        "isAdmin": False,
        "loyaltyPoints": 0,
        "createdAt": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_dict)
    user_id = str(result.inserted_id)
    
    # Create token
    access_token = create_access_token(data={"sub": user_id})
    
    user_response = UserResponse(
        id=user_id,
        email=user_data.email,
        firstName=user_data.firstName,
        lastName=user_data.lastName,
        dateOfBirth=user_data.dateOfBirth,
        isAdmin=False,
        loyaltyPoints=0
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
        isAdmin=user.get("isAdmin", False),
        loyaltyPoints=user.get("loyaltyPoints", 0)
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
        isAdmin=user.get("isAdmin", False),
        loyaltyPoints=user.get("loyaltyPoints", 0)
    )

# ==================== PRODUCT ENDPOINTS ====================

@api_router.get("/products", response_model=List[Product])
async def get_products(category: Optional[str] = None, brand: Optional[str] = None):
    query = {}
    if category:
        query["category"] = category
    if brand:
        query["brand"] = brand
    
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
    product_dict = product.dict()
    result = await db.products.insert_one(product_dict)
    product_dict["id"] = str(result.inserted_id)
    return Product(**product_dict)

@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product: ProductCreate, admin = Depends(get_admin_user)):
    result = await db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": product.dict()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(id=product_id, **product.dict())

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, admin = Depends(get_admin_user)):
    result = await db.products.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}

# ==================== ORDER ENDPOINTS ====================

@api_router.post("/orders", response_model=Order)
async def create_order(order_data: OrderCreate, user = Depends(get_current_user)):
    # Calculate loyalty points earned (1 point per dollar)
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

# ==================== ADMIN ENDPOINTS ====================

@api_router.get("/admin/orders", response_model=List[Order])
async def get_all_orders(admin = Depends(get_admin_user)):
    orders = await db.orders.find().sort("createdAt", -1).to_list(1000)
    return [Order(id=str(o["_id"]), **{k: v for k, v in o.items() if k != "_id"}) for o in orders]

@api_router.patch("/admin/orders/{order_id}/status")
async def update_order_status(order_id: str, status_update: OrderStatusUpdate, admin = Depends(get_admin_user)):
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # If marking as "Paid", add loyalty points to user
    if status_update.status == "Paid" and order["status"] == "Pending Payment":
        await db.users.update_one(
            {"_id": ObjectId(order["userId"])},
            {"$inc": {"loyaltyPoints": order["loyaltyPointsEarned"]}}
        )
    
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": status_update.status}}
    )
    
    return {"message": "Order status updated"}

# ==================== CATEGORIES ENDPOINT ====================

@api_router.get("/categories")
async def get_categories():
    return [
        {"name": "Geek Bar", "value": "geek-bar"},
        {"name": "Lost Mary", "value": "lost-mary"},
        {"name": "RAZ", "value": "raz"},
        {"name": "Meloso", "value": "meloso"},
        {"name": "Digiflavor", "value": "digiflavor"},
        {"name": "Best Sellers", "value": "best-sellers"},
        {"name": "New Arrivals", "value": "new-arrivals"}
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
