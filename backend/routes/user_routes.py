from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth import get_current_user, build_user_response
from models.schemas import (
    UserProfileUpdate, UserUsernameUpdate, UserResponse,
    PushTokenRegister, SupportTicketCreate, RESERVED_USERNAMES, USERNAME_RE
)
from datetime import datetime
from bson import ObjectId
import re as _re

router = APIRouter()


@router.patch("/profile", response_model=UserResponse)
async def update_profile(profile_data: UserProfileUpdate, user=Depends(get_current_user)):
    update_dict = {k: v for k, v in profile_data.dict().items() if v is not None}
    if update_dict:
        await db.users.update_one({"_id": user["_id"]}, {"$set": update_dict})
        updated_user = await db.users.find_one({"_id": user["_id"]})
        return build_user_response(updated_user)
    return build_user_response(user)


@router.patch("/me/username", response_model=UserResponse)
async def update_username(data: UserUsernameUpdate, user=Depends(get_current_user)):
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
        {"$set": {"username": username}}
    )
    updated = await db.users.find_one({"_id": user["_id"]})
    return build_user_response(updated)


@router.get("/me/referral-earnings")
async def get_my_referral_earnings(user=Depends(get_current_user)):
    user_id = str(user["_id"])
    pipeline = [
        {"$match": {"userId": user_id, "type": "referral_reward"}},
        {"$group": {"_id": None, "totalCloudz": {"$sum": "$amount"}, "orderCount": {"$sum": 1}}},
    ]
    result = await db.cloudz_ledger.aggregate(pipeline).to_list(1)
    if result:
        return {"totalReferralCloudz": result[0]["totalCloudz"], "referralOrderCount": result[0]["orderCount"]}
    return {"totalReferralCloudz": 0, "referralOrderCount": 0}


@router.get("/me/cloudz-ledger")
async def get_my_cloudz_ledger(user=Depends(get_current_user)):
    entries = await db.cloudz_ledger.find(
        {"userId": str(user["_id"])}, {"_id": 0}
    ).sort("createdAt", -1).to_list(500)
    for e in entries:
        if isinstance(e.get("createdAt"), datetime):
            e["createdAt"] = e["createdAt"].isoformat()
    return entries


@router.get("/me/coupon")
async def get_my_coupon(user=Depends(get_current_user)):
    from datetime import timezone
    user_doc = await db.users.find_one({"_id": user["_id"]}, {"nextOrderCoupon": 1})
    coupon = user_doc.get("nextOrderCoupon") if user_doc else None
    if coupon:
        expires_at = coupon.get("expiresAt")
        if expires_at:
            try:
                exp = datetime.fromisoformat(expires_at)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp < datetime.now(timezone.utc):
                    await db.users.update_one({"_id": user["_id"]}, {"$unset": {"nextOrderCoupon": ""}})
                    return {"coupon": None}
            except Exception:
                pass
        if coupon.get("used"):
            return {"coupon": None}
        return {"coupon": coupon}
    return {"coupon": None}


@router.post("/push/register")
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


@router.post("/support/tickets")
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
