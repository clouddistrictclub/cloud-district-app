from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
import string
import secrets as sec_module
import re as _re


# ==================== CONSTANTS ====================

def generate_referral_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(sec_module.choice(chars) for _ in range(7))


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
    id: Optional[str] = None
    name: str
    brandId: str
    brandName: str
    model: Optional[str] = None
    category: str
    image: str
    images: Optional[List[str]] = []
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
    loyaltyEarnRate: Optional[float] = None
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
    adjustment: int
    reason: Optional[str] = None


# ==================== ORDER MODELS ====================

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
    couponApplied: bool = False


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
    productId: str
    orderId: str
    rating: int
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
