from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from bson import ObjectId
from typing import Optional
import jwt
import os
import asyncio
from datetime import datetime, timedelta

from database import db
from models.schemas import UserResponse

SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Throttle: only write lastActiveAt if older than this many seconds
_LAST_ACTIVE_TTL = 300  # 5 minutes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.exceptions.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if user.get("isDisabled", False):
        raise HTTPException(status_code=401, detail="Account has been disabled")
    force_logout_at = user.get("forceLogoutAt")
    if force_logout_at is not None:
        token_iat = payload.get("iat", 0)
        if token_iat < force_logout_at:
            raise HTTPException(status_code=401, detail="Session has been invalidated")

    # Fire-and-forget lastActiveAt update — throttled to once every 5 minutes
    now = datetime.utcnow()
    last_active = user.get("lastActiveAt")
    if last_active is None or (now - last_active).total_seconds() > _LAST_ACTIVE_TTL:
        async def _touch_last_active(uid: str, ts: datetime) -> None:
            try:
                await db.users.update_one(
                    {"_id": ObjectId(uid)},
                    {"$set": {"lastActiveAt": ts}},
                )
            except Exception:
                pass
        asyncio.create_task(_touch_last_active(user_id, now))

    return user


async def get_admin_user(user=Depends(get_current_user)):
    if not user.get("isAdmin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def touch_last_active(user_id: str) -> None:
    """Directly update lastActiveAt for explicit activity events (orders, check-ins).
    No throttle — these are high-value signals always worth recording."""
    try:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"lastActiveAt": datetime.utcnow()}},
        )
    except Exception:
        pass


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
