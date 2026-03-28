from fastapi import APIRouter, HTTPException, Depends, Request
from database import db
from auth import get_current_user, verify_password, get_password_hash, create_access_token, build_user_response
from models.schemas import UserRegister, UserLogin, Token, UserResponse
from services.loyalty_service import log_cloudz_transaction
from limiter import limiter
from datetime import datetime
from bson import ObjectId
import re as _re

router = APIRouter()


@router.post("/auth/register", response_model=Token)
@limiter.limit("5/minute")
async def register(request: Request, user_data: UserRegister):
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    # username is already normalized (lowercase, trimmed) by the validator
    username = user_data.username
    if await db.users.find_one({"username": username}):
        raise HTTPException(status_code=409, detail="Username already taken")

    dob = datetime.strptime(user_data.dateOfBirth, "%Y-%m-%d")
    age = (datetime.utcnow() - dob).days / 365.25
    if age < 21:
        raise HTTPException(status_code=400, detail="Must be 21 or older")

    referred_by = None
    if user_data.referralCode:
        ref_input = user_data.referralCode.strip().lower()
        referrer = await db.users.find_one({"username": {"$regex": f"^{_re.escape(ref_input)}$", "$options": "i"}})
        if not referrer:
            raise HTTPException(status_code=400, detail="Invalid referral code — enter a valid username")
        referred_by = referrer.get("username") or str(referrer["_id"])

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
        "username": username,
        "referralCode": username,
        "referredBy": referred_by,
        "referralCount": 0,
        "referralRewardsEarned": 0,
        "referralRewardIssued": False,
        "createdAt": datetime.utcnow()
    }

    result = await db.users.insert_one(user_dict)
    user_id = str(result.inserted_id)

    if referred_by and referred_by == username:
        await db.users.update_one({"_id": result.inserted_id}, {"$set": {"referredBy": None}})
        referred_by = None

    signup_bonus = 500
    await log_cloudz_transaction(user_id, "signup_bonus", signup_bonus, "Welcome to Cloud District Club!")

    # Instant referral signup bonus (non-duplicate)
    if referred_by:
        referrer_doc = await db.users.find_one(
            {"$or": [{"username": referred_by}, {"_id": ObjectId(referred_by)} if len(referred_by) == 24 else {"username": referred_by}]},
            {"_id": 1, "username": 1, "loyaltyPoints": 1}
        )
        if referrer_doc:
            referrer_obj_id = referrer_doc["_id"]
            referrer_id_str = str(referrer_obj_id)
            already_issued = await db.cloudz_ledger.find_one({
                "userId": referrer_id_str,
                "type": "referral_signup_bonus",
                "referredUserId": user_id,
            })
            if not already_issued:
                await db.users.update_one(
                    {"_id": referrer_obj_id},
                    {"$inc": {"referralCount": 1}}
                )
                ref_result = await db.users.find_one_and_update(
                    {"_id": referrer_obj_id},
                    {"$inc": {"loyaltyPoints": 500}},
                    return_document=True,
                )
                await db.cloudz_ledger.insert_one({
                    "userId": referrer_id_str,
                    "type": "referral_signup_bonus",
                    "amount": 500,
                    "balanceAfter": ref_result["loyaltyPoints"] if ref_result else 0,
                    "description": f"Referral signup bonus — {user_data.firstName} joined",
                    "referredUserId": user_id,
                    "createdAt": datetime.utcnow(),
                })

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
        username=username,
        referralCode=username,
        referralCount=0,
        referralRewardsEarned=0
    )

    return Token(access_token=access_token, token_type="bearer", user=user_response)


@router.post("/auth/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("isDisabled", False):
        raise HTTPException(status_code=403, detail="Account has been disabled. Contact support.")

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


@router.get("/auth/me", response_model=UserResponse)
async def get_me(user=Depends(get_current_user)):
    return build_user_response(user)
