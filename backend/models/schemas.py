from pydantic import BaseModel, Field, EmailStr, validator, ConfigDict
from typing import Any, List, Optional, Union
from datetime import datetime
import string
import secrets as sec_module
import re as _re


# ==================== CONSTANTS ====================

def generate_referral_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(sec_module.choice(chars) for _ in range(8))


RESERVED_USERNAMES = {"admin", "support", "api", "clouddistrict", "orders", "root", "help"}
USERNAME_RE = _re.compile(r'^[a-zA-Z0-9_]{3,20}$')

LOYALTY_TIERS = [
    {"id": "tier_1", "name": "Bronze Cloud", "pointsRequired": 1000, "reward": 5.00, "icon": "cloud-outline"},
    {"id": "tier_2", "name": "Silver Storm", "pointsRequired": 5000, "reward": 30.00, "icon": "cloud"},
    {"id": "tier_3", "name": "Gold Thunder", "pointsRequired": 10000, "reward": 75.00, "icon": "thunderstorm-outline"},
    {"id": "tier_4", "name": "Platinum Haze", "pointsRequired": 20000, "reward": 175.00, "icon": "thunderstorm"},
    {"id": "tier_5", "name": "Diamond Sky", "pointsRequired": 30000, "reward": 300.00, "icon": "diamond"},
]

TIER_COLORS = {
    "tier_1": "#CD7F32",
    "tier_2": "#C0C0C0",
    "tier_3": "#FFD700",
    "tier_4": "#A8B8D0",
    "tier_5": "#B9F2FF",
}

STREAK_BONUS = {2: 50, 3: 100, 4: 200}  # week: bonus; 5+ = 500


# ==================== USER MODELS ====================

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    firstName: str = Field(min_length=1, max_length=50)
    lastName: str = Field(min_length=1, max_length=50)
    dateOfBirth: str = Field(min_length=10, max_length=10)
    phone: Optional[str] = Field(default=None, max_length=20)
    username: str = Field(min_length=3, max_length=20)
    referralCode: Optional[str] = Field(default=None, max_length=50)
    profilePhoto: Optional[str] = Field(default=None)  # base64 data URI

    @validator("dateOfBirth")
    def validate_dob(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("dateOfBirth must be in YYYY-MM-DD format")
        return v

    @validator("username")
    def validate_username(cls, v):
        v = v.strip().lower().replace(" ", "")
        if not USERNAME_RE.match(v):
            raise ValueError("Username must be 3–20 characters: letters, numbers, underscores only")
        if v in RESERVED_USERNAMES:
            raise ValueError(f"Username '{v}' is not available")
        return v


class UserLogin(BaseModel):
    identifier: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1)


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


class UserUsernameUpdate(BaseModel):
    username: str


# ==================== BRAND MODELS ====================

class Brand(BaseModel):
    id: Optional[str] = None
    name: str
    image: Optional[str] = None
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


# ==================== PRODUCT MODELS ====================

class Product(BaseModel):
    model_config = ConfigDict(extra='ignore')

    id: Optional[str] = None
    name: str
    brandId: str
    brandName: str
    model: Optional[str] = None
    category: str
    image: str
    images: Optional[List[str]] = []
    puffCount: Optional[int] = None
    flavor: str
    nicotinePercent: Optional[float] = 5.0
    nicotineStrength: Optional[str] = None
    deviceType: Optional[str] = None
    slug: Optional[str] = None
    price: float
    stock: Optional[int] = 0
    lowStockThreshold: Optional[int] = 5
    description: Optional[str] = None
    isActive: bool = True
    isFeatured: bool = False
    loyaltyEarnRate: Optional[float] = None
    cloudzReward: Optional[int] = None
    displayOrder: Optional[int] = 0
    productType: Optional[str] = None
    sku: Optional[str] = None
    shipmentStatus: Optional[str] = None
    etaDays: Optional[int] = None
    incomingPackCount: Optional[int] = None
    createdAt: Optional[Any] = None
    updatedAt: Optional[Any] = None


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brandId: str = Field(min_length=1)
    category: str = Field(min_length=1, max_length=100)
    image: str = Field(min_length=1)
    images: Optional[List[str]] = []
    puffCount: int = Field(gt=0, le=100000)
    flavor: str = Field(min_length=1, max_length=100)
    nicotinePercent: float = Field(ge=0, le=20)
    price: float = Field(gt=0, le=10000)
    stock: int = Field(ge=0)
    lowStockThreshold: int = Field(default=5, ge=0)
    description: Optional[str] = Field(default=None, max_length=2000)
    isActive: bool = True
    isFeatured: bool = False
    loyaltyEarnRate: Optional[float] = Field(default=None, ge=0)
    displayOrder: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    brandId: Optional[str] = Field(default=None, min_length=1)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    image: Optional[str] = None
    images: Optional[List[str]] = None
    puffCount: Optional[int] = Field(default=None, gt=0, le=100000)
    flavor: Optional[str] = Field(default=None, min_length=1, max_length=100)
    nicotinePercent: Optional[float] = Field(default=None, ge=0, le=20)
    price: Optional[float] = Field(default=None, gt=0, le=10000)
    stock: Optional[int] = Field(default=None, ge=0)
    lowStockThreshold: Optional[int] = Field(default=None, ge=0)
    description: Optional[str] = Field(default=None, max_length=2000)
    isActive: Optional[bool] = None
    isFeatured: Optional[bool] = None
    loyaltyEarnRate: Optional[float] = Field(default=None, ge=0)
    displayOrder: Optional[int] = Field(default=None, ge=0)


class StockAdjustment(BaseModel):
    adjustment: int
    reason: Optional[str] = None


# ==================== ORDER MODELS ====================

class CartItem(BaseModel):
    productId: str = Field(min_length=1)
    quantity: int = Field(ge=1, le=100)
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(ge=0)


class OrderCreate(BaseModel):
    items: List[CartItem] = Field(min_items=1)
    total: float = Field(ge=0)
    pickupTime: str = Field(min_length=1, max_length=100)
    paymentMethod: str = Field(min_length=1, max_length=50)
    loyaltyPointsUsed: int = Field(default=0, ge=0)
    rewardId: Optional[str] = None
    couponApplied: bool = False
    storeCreditApplied: float = Field(default=0.0, ge=0)
    name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=20)


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
    expiresAt: Optional[datetime] = None
    customerName: Optional[str] = None
    customerEmail: Optional[str] = None
    customerPhone: Optional[str] = None
    adminNotes: Optional[str] = None
    discountApplied: float = 0.0
    storeCreditApplied: float = 0.0


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
    pickupTime: Optional[str] = None
    paymentMethod: Optional[str] = None


# ==================== ADMIN USER MODELS ====================

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
    amount: float
    description: str


class AdminReferrerUpdate(BaseModel):
    referrerIdentifier: Optional[str] = None


class CloudzAdjust(BaseModel):
    amount: int
    description: str


class AdminSetPassword(BaseModel):
    newPassword: str


class AdminUserNotes(BaseModel):
    notes: str


class MergeRequest(BaseModel):
    sourceUserId: str
    targetUserId: str


# ==================== REVIEW MODELS ====================

class ReviewCreate(BaseModel):
    productId: str = Field(min_length=1)
    orderId: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)


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


# ==================== MISC MODELS ====================

class PushTokenRegister(BaseModel):
    token: str


class SupportTicketCreate(BaseModel):
    subject: str
    message: str


class TierRedeemRequest(BaseModel):
    tierId: str


class ChatMessage(BaseModel):
    message: str
