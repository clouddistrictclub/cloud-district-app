from fastapi import APIRouter, HTTPException, Depends, Request
from database import db
from auth import get_current_user, verify_password, get_password_hash, create_access_token, build_user_response
from models.schemas import UserRegister, UserLogin, Token, UserResponse, MeResponse
from services.loyalty_service import log_cloudz_transaction, issue_referral_signup_rewards, check_and_award_referral_milestones
from limiter import limiter
from datetime import datetime
from bson import ObjectId
import re as _re

router = APIRouter()


@router.get("/auth/check-username")
async def check_username(username: str):
    username = username.strip().lower()
    from models.schemas import USERNAME_RE, RESERVED_USERNAMES
    import re as _re2
    if not USERNAME_RE.match(username) or username in RESERVED_USERNAMES:
        return {"available": False}
    existing = await db.users.find_one(
        {"username": {"$regex": f"^{_re2.escape(username)}$", "$options": "i"}},
        {"_id": 1}
    )
    return {"available": existing is None}


@router.post("/auth/register", response_model=Token)
@limiter.limit("5/minute")
async def register(request: Request, user_data: UserRegister):
    # STEP 1 — LOG INPUT BEFORE ANYTHING
    print("REFERRAL CODE RECEIVED:", user_data.referralCode)

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
        "profilePhoto": user_data.profilePhoto or None,
        "username": username,
        "referralCode": username,
        "referredBy": None,
        "referralCount": 0,
        "referralRewardsEarned": 0,
        "referralRewardIssued": False,
        "referralRewardGiven": False,
        "createdAt": datetime.utcnow()
    }

    result = await db.users.insert_one(user_dict)
    user_id = str(result.inserted_id)
    print("SIGNUP: user created", result.inserted_id, username)

    # Base signup bonus — always +500
    await log_cloudz_transaction(user_id, "signup_bonus", 500, "Welcome to Cloud District Club!")
    user_points = 500
    print("SIGNUP: base bonus issued")

    # STEP 2 — FORCE LOOKUP + FAIL LOUD (after user creation)
    referrer = None
    referred_by = None
    if user_data.referralCode:
        ref_input = user_data.referralCode.strip().lower()
        if ref_input == username.lower():
            print("REFERRAL LOOKUP RESULT: self-referral ignored")
        else:
            referrer = await db.users.find_one(
                {"username": {"$regex": f"^{_re.escape(ref_input)}$", "$options": "i"}}
            )
            print("REFERRAL LOOKUP RESULT:", referrer)
            if referrer is None:
                raise Exception(f"REFERRER NOT FOUND — DO NOT SILENTLY FAIL: code={ref_input}")
            referred_by = str(referrer["_id"])
            # Persist referredBy on the new user record
            await db.users.update_one(
                {"_id": result.inserted_id},
                {"$set": {"referredBy": referred_by}}
            )

    # STEP 3 — FORCE EXECUTION (no conditions, no skips)
    if referred_by and referrer:
        print("REFERRAL FUNCTION CALLED")
        # +500 to new user
        await log_cloudz_transaction(
            user_id, "referral_signup_bonus", 500,
            "Referral bonus — signed up with a referral code"
        )
        user_points += 500
        print("REFERRAL: new user +500 issued, total=", user_points)

        # Pending 1000 for referrer — no balance change
        pending_result = await db.cloudz_ledger.insert_one({
            "userId": referred_by,
            "type": "referral_pending",
            "amount": 1000,
            "status": "pending",
            "referredUserId": user_id,
            "description": f"Pending referral reward — {username} signed up",
            "createdAt": datetime.utcnow(),
        })
        updated_referrer = await db.users.find_one_and_update(
            {"_id": ObjectId(referred_by)},
            {"$inc": {"referralCount": 1}},
            return_document=True,
            projection={"referralCount": 1},
        )
        new_referral_count = updated_referrer.get("referralCount", 0) if updated_referrer else 0
        print("REFERRAL: pending 1000 created for referrer", referred_by, "ledger=", pending_result.inserted_id)
        # Award milestone bonus if this referral count hits a threshold
        await check_and_award_referral_milestones(referred_by, new_referral_count)

    access_token = create_access_token(data={"sub": user_id})

    user_response = UserResponse(
        id=user_id,
        email=user_data.email,
        firstName=user_data.firstName,
        lastName=user_data.lastName,
        dateOfBirth=user_data.dateOfBirth,
        phone=user_data.phone,
        isAdmin=False,
        loyaltyPoints=user_points,
        profilePhoto=user_data.profilePhoto or None,
        username=username,
        referralCode=username,
        referralCount=0,
        referralRewardsEarned=0,
        referredByUserId=referred_by,
    )

    return Token(access_token=access_token, token_type="bearer", user=user_response)


@router.post("/auth/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, user_data: UserLogin):
    identifier = user_data.identifier.strip()
    # Detect email vs username: emails contain '@'
    if '@' in identifier:
        user = await db.users.find_one({"email": identifier.lower()})
    else:
        user = await db.users.find_one(
            {"username": {"$regex": f"^{_re.escape(identifier.lower())}$", "$options": "i"}}
        )
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email/username or password")
    if user.get("isDisabled", False):
        raise HTTPException(status_code=403, detail="Account has been disabled. Contact support.")

    user_id = str(user["_id"])
    access_token = create_access_token(data={"sub": user_id})

    # Fire-and-forget: web push if user hasn't checked in today
    from datetime import datetime as _dt
    import asyncio as _asyncio
    if user.get("lastCheckInDate") != _dt.utcnow().strftime("%Y-%m-%d"):
        from services.web_push_service import send_web_push as _web_push
        _asyncio.create_task(_web_push(user_id, {
            "title": "Your daily spin is ready \U0001f3b0",
            "body":  "Come spin and earn Cloudz",
            "icon":  "/android-chrome-192x192.png",
            "url":   "/cloudz",
        }))

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
        username=user.get("username"),
        referralCount=user.get("referralCount", 0),
        referralRewardsEarned=user.get("referralRewardsEarned", 0)
    )

    return Token(access_token=access_token, token_type="bearer", user=user_response)


@router.get("/auth/me", response_model=MeResponse)
async def get_me(user=Depends(get_current_user)):
    return MeResponse(
        id=str(user["_id"]),
        email=user["email"],
        username=user.get("username"),
        isAdmin=user.get("isAdmin", False),
        loyaltyPoints=user.get("loyaltyPoints", 0),
        creditBalance=user.get("creditBalance", 0.0),
        phone=user.get("phone"),
    )
