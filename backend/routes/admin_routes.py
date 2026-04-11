from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth import get_admin_user, build_user_response, get_password_hash
from models.schemas import (
    UserResponse, AdminUserResponse, AdminUserUpdate, CreditAdjust, AdminReferrerUpdate,
    CloudzAdjust, AdminSetPassword, AdminUserNotes, MergeRequest,
    Order, OrderStatusUpdate, OrderEdit, ReviewModerationUpdate,
    UserUsernameUpdate
)
from services.loyalty_service import log_cloudz_transaction, issue_referral_signup_rewards
from services.order_service import send_push_notification, chat_manager, update_order_status_shared
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Optional
import re as _re
import asyncio
import logging
import time

router = APIRouter()
logger = logging.getLogger(__name__)

# ==================== IN-MEMORY ANALYTICS CACHE ====================
_analytics_cache: dict = {}
_ANALYTICS_TTL = 60  # seconds


# ==================== ADMIN REVIEWS ====================

@router.get("/admin/reviews")
async def get_all_reviews(admin=Depends(get_admin_user)):
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


@router.patch("/admin/reviews/{review_id}")
async def admin_update_review(review_id: str, update: ReviewModerationUpdate, admin=Depends(get_admin_user)):
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


@router.delete("/admin/reviews/{review_id}")
async def admin_delete_review(review_id: str, admin=Depends(get_admin_user)):
    result = await db.reviews.delete_one({"_id": ObjectId(review_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review deleted"}


# ==================== ADMIN USER PROFILE ====================

@router.get("/admin/users/{user_id}/profile")
async def get_user_profile(user_id: str, admin=Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)}, {"password": 0, "hashedPassword": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_data = {k: v for k, v in user.items() if k != "_id"}
    user_data["id"] = user_id
    if isinstance(user_data.get("createdAt"), datetime):
        user_data["createdAt"] = user_data["createdAt"].isoformat()
    user_data["referredByUserId"] = user_data.pop("referredBy", None)
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
    paid_statuses = {"Completed"}
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

@router.post("/admin/users/{user_id}/assign-referrer")
async def admin_assign_referrer(user_id: str, data: AdminReferrerUpdate, admin=Depends(get_admin_user)):
    """Assign a referrer to a user. Body: { "referrerIdentifier": "username|referralCode|email" }"""
    identifier = (data.referrerIdentifier or "").strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="referrerIdentifier is required")

    # Lookup referrer by username, referralCode, or email
    referrer = (
        await db.users.find_one({"username": {"$regex": f"^{_re.escape(identifier)}$", "$options": "i"}})
        or await db.users.find_one({"referralCode": {"$regex": f"^{_re.escape(identifier)}$", "$options": "i"}})
        or await db.users.find_one({"email": {"$regex": f"^{_re.escape(identifier)}$", "$options": "i"}})
    )
    if not referrer:
        raise HTTPException(status_code=404, detail="Referrer not found")

    referrer_id = str(referrer["_id"])
    if referrer_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot assign user as their own referrer")

    target_user = await db.users.find_one({"_id": ObjectId(user_id)}, {"referredBy": 1, "firstName": 1})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    had_referrer = bool(target_user.get("referredBy"))
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"referredBy": referrer_id}})

    rewards_issued = {"user_bonus": 0, "referrer_bonus": 0}
    if not had_referrer:
        rewards_issued = await issue_referral_signup_rewards(
            new_user_id=user_id,
            referrer_identifier=referrer_id,
            new_user_first_name=target_user.get("firstName", "A user"),
        )

    paid_orders = await db.orders.count_documents({
        "userId": user_id,
        "status": {"$in": ["Paid", "Ready for Pickup", "Completed"]},
    })
    return {
        "message": "Referrer assigned",
        "referrerId": referrer_id,
        "referrerUsername": referrer.get("username"),
        "rewardsIssued": rewards_issued,
        "warning": f"User has {paid_orders} paid order(s) — referral earnings not retroactive" if paid_orders else None,
    }


@router.post("/admin/users/{user_id}/remove-referrer")
async def admin_remove_referrer(user_id: str, admin=Depends(get_admin_user)):
    """Remove the referrer association from a user."""
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"referredBy": None}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Referrer removed"}


@router.patch("/admin/users/{user_id}/referrer")
async def admin_set_referrer(user_id: str, data: AdminReferrerUpdate, admin=Depends(get_admin_user)):
    if not data.referrerIdentifier or not data.referrerIdentifier.strip():
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"referredBy": None}})
        return {"message": "Referrer removed"}

    identifier = data.referrerIdentifier.strip()
    referrer = await db.users.find_one({"referralCode": {"$regex": f"^{_re.escape(identifier)}$", "$options": "i"}})
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

    # Check if user previously had a referrer
    target_user = await db.users.find_one(
        {"_id": ObjectId(user_id)}, {"referredBy": 1, "firstName": 1}
    )
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    had_referrer = bool(target_user.get("referredBy"))

    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"referredBy": referrer_id}})

    # Issue referral rewards if this is a FIRST-TIME referrer assignment
    rewards_issued = {"user_bonus": 0, "referrer_bonus": 0}
    if not had_referrer:
        rewards_issued = await issue_referral_signup_rewards(
            new_user_id=user_id,
            referrer_identifier=referrer_id,
            new_user_first_name=target_user.get("firstName", "A user"),
        )

    paid_orders = await db.orders.count_documents({
        "userId": user_id,
        "status": {"$in": ["Paid", "Ready for Pickup", "Completed"]},
    })
    return {
        "message": "Referrer updated",
        "rewardsIssued": rewards_issued,
        "warning": f"User has {paid_orders} paid orders — referral earnings will not be retroactive" if paid_orders > 0 else None,
    }


@router.get("/admin/users/{user_id}/cloudz-ledger")
async def admin_get_cloudz_ledger(user_id: str, admin=Depends(get_admin_user)):
    entries = await db.cloudz_ledger.find(
        {"userId": user_id}, {"_id": 0}
    ).sort("createdAt", -1).to_list(500)

    # Batch-resolve referredUserId → referredUsername (same enrichment as user-facing ledger)
    referred_ids: set = set()
    for e in entries:
        rid = e.get("referredUserId") or e.get("metadata", {}).get("referredUserId")
        if rid:
            referred_ids.add(str(rid))
    username_map: dict = {}
    if referred_ids:
        cursor = db.users.find(
            {"_id": {"$in": [ObjectId(r) for r in referred_ids if r]}},
            {"_id": 1, "username": 1},
        )
        async for u in cursor:
            username_map[str(u["_id"])] = u.get("username") or None

    for e in entries:
        if isinstance(e.get("createdAt"), datetime):
            e["createdAt"] = e["createdAt"].isoformat()
        rid = e.get("referredUserId") or e.get("metadata", {}).get("referredUserId")
        if rid:
            rid = str(rid)
            e["referredUsername"] = (
                username_map.get(rid)
                or e.get("metadata", {}).get("referredUsername")
                or e.get("metadata", {}).get("referredUser")
                or None
            )
    return entries


@router.post("/admin/users/{user_id}/cloudz-adjust")
async def admin_adjust_cloudz(user_id: str, data: CloudzAdjust, admin=Depends(get_admin_user)):
    new_balance = await log_cloudz_transaction(user_id, "admin_adjustment", data.amount, data.description, data.description)
    return {"message": "Balance updated", "newBalance": new_balance}


@router.post("/admin/users/{user_id}/reset-password")
async def admin_reset_password(user_id: str, admin=Depends(get_admin_user)):
    """Generate a temporary password and reset the user's password.
    Returns the temporary password in plaintext so the admin can share it."""
    import secrets, string
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    hashed = get_password_hash(temp_password)
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password": hashed}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"ADMIN ACTION: password reset for user {user_id} by admin {str(admin['_id'])}")
    return {"temporaryPassword": temp_password}


@router.post("/admin/users/{user_id}/set-password")
async def admin_set_user_password(user_id: str, data: AdminSetPassword, admin=Depends(get_admin_user)):
    if len(data.newPassword) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    hashed = get_password_hash(data.newPassword)
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password": hashed}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True}


@router.post("/dev/reset-checkin/{user_id}")
async def dev_reset_checkin(user_id: str, admin=Depends(get_admin_user)):
    """DEV ONLY — Reset daily check-in state so the user can check in again immediately."""
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"lastCheckInDate": None, "checkInStreak": 0}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "message": "Check-in state reset — user can check in immediately"}
async def admin_disable_user(user_id: str, admin=Depends(get_admin_user)):
    """Disable a user account. Blocks all authenticated actions immediately.
    Also sets forceLogoutAt to invalidate any existing tokens."""
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"isDisabled": True, "forceLogoutAt": time.time()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"ADMIN ACTION: user {user_id} disabled by admin {str(admin['_id'])}")
    return {"success": True, "message": "Account disabled and all active sessions invalidated"}


@router.post("/admin/users/{user_id}/enable")
async def admin_enable_user(user_id: str, admin=Depends(get_admin_user)):
    """Re-enable a disabled user account. User must log in fresh to get a new token."""
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"isDisabled": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"ADMIN ACTION: user {user_id} enabled by admin {str(admin['_id'])}")
    return {"success": True, "message": "Account enabled — user must log in again to get a new token"}


@router.post("/admin/users/{user_id}/force-logout")
async def admin_force_logout(user_id: str, admin=Depends(get_admin_user)):
    """Invalidate all active sessions by setting forceLogoutAt to now.
    Any token with iat < forceLogoutAt will be rejected by auth middleware."""
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"forceLogoutAt": time.time()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"ADMIN ACTION: force-logout user {user_id} by admin {str(admin['_id'])}")
    return {"success": True, "message": "All active sessions invalidated — user must log in again"}


@router.post("/admin/users/{user_id}/clear-force-logout")
async def admin_clear_force_logout(user_id: str, admin=Depends(get_admin_user)):
    """Clear forceLogoutAt so the user can access their account with fresh tokens."""
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$unset": {"forceLogoutAt": ""}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "message": "forceLogoutAt cleared"}


@router.patch("/admin/users/{user_id}/username", response_model=UserResponse)
async def admin_set_username(user_id: str, data: UserUsernameUpdate, admin=Depends(get_admin_user)):
    username = data.username.strip().lower()
    if not _re.match(r'^[a-z0-9_]{3,20}$', username):
        raise HTTPException(status_code=400, detail="Username must be 3–20 characters: lowercase letters, numbers, underscores only")
    existing = await db.users.find_one({
        "username": username,
        "_id": {"$ne": ObjectId(user_id)},
    })
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"username": username}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    return build_user_response(user)


@router.patch("/admin/users/{user_id}/notes")
async def update_admin_notes(user_id: str, data: AdminUserNotes, admin=Depends(get_admin_user)):
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"adminNotes": data.notes}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True}


@router.post("/admin/users/merge")
async def merge_users(data: MergeRequest, admin=Depends(get_admin_user)):
    source = await db.users.find_one({"_id": ObjectId(data.sourceUserId)})
    target = await db.users.find_one({"_id": ObjectId(data.targetUserId)})
    if not source or not target:
        raise HTTPException(status_code=404, detail="One or both users not found")
    if data.sourceUserId == data.targetUserId:
        raise HTTPException(status_code=400, detail="Cannot merge a user with themselves")
    await db.orders.update_many({"userId": data.sourceUserId}, {"$set": {"userId": data.targetUserId}})
    await db.cloudz_ledger.update_many({"userId": data.sourceUserId}, {"$set": {"userId": data.targetUserId}})
    source_credit = source.get("creditBalance", 0.0)
    source_points = source.get("loyaltyPoints", 0)
    if source_credit > 0 or source_points > 0:
        if source_credit > 0:
            await db.users.update_one(
                {"_id": ObjectId(data.targetUserId)},
                {"$inc": {"creditBalance": source_credit}}
            )
        if source_points > 0:
            await log_cloudz_transaction(
                data.targetUserId, "admin_adjustment", source_points,
                f"Merged from account {data.sourceUserId}", "Account merge"
            )
    await db.users.update_one(
        {"_id": ObjectId(data.sourceUserId)},
        {"$set": {"isDisabled": True, "mergedInto": data.targetUserId, "creditBalance": 0, "loyaltyPoints": 0}}
    )
    return {"success": True, "message": "Accounts merged successfully"}


# ==================== ADMIN ORDER EDITING ====================

@router.patch("/admin/orders/{order_id}/edit")
async def admin_edit_order(order_id: str, edit: OrderEdit, admin=Depends(get_admin_user)):
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    old_items = order.get("items", [])
    new_items = [item.dict() for item in edit.items]
    for item in old_items:
        await db.products.update_one({"_id": ObjectId(item["productId"])}, {"$inc": {"stock": item["quantity"]}})
    for item in new_items:
        await db.products.update_one({"_id": ObjectId(item["productId"])}, {"$inc": {"stock": -item["quantity"]}})
    update_dict: dict = {"items": new_items, "total": edit.total}
    if edit.adminNotes is not None:
        update_dict["adminNotes"] = edit.adminNotes
    if edit.pickupTime is not None:
        update_dict["pickupTime"] = edit.pickupTime
    if edit.paymentMethod is not None:
        update_dict["paymentMethod"] = edit.paymentMethod
    await db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": update_dict})
    return {"message": "Order updated"}


# ==================== ADMIN ORDER ENDPOINTS ====================

# Statuses where stock has already been restored (safe to delete without touching inventory)
_STOCK_ALREADY_RESTORED = {"Cancelled", "Expired"}
# Pending Payment stock is still held — must restore before deleting
_ALLOW_DELETE_STATUSES   = {"Cancelled", "Expired", "Pending Payment"}


@router.delete("/admin/orders/{order_id}")
async def admin_delete_order(order_id: str, admin=Depends(get_admin_user)):
    """
    Permanently delete an order. Restricted to safe statuses only.

    Allowed:  Cancelled, Expired, Pending Payment
    Blocked:  Paid, Preparing, Ready for Pickup, Completed  (financial / fulfillment risk)

    Inventory safety:
    - Cancelled / Expired  → stock already restored; deletion touches nothing.
    - Pending Payment      → stock is still reserved; restored here before deletion.

    Ledger: cloudz_ledger entries are intentionally preserved for audit integrity.
    Loyalty rewards cannot have been issued for these statuses (rewards fire only on Completed).
    """
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    order = await db.orders.find_one({"_id": oid})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    current_status = order.get("status", "")
    if current_status not in _ALLOW_DELETE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot delete order with status '{current_status}'. "
                f"Only {sorted(_ALLOW_DELETE_STATUSES)} orders may be deleted."
            ),
        )

    stock_restored = False
    if current_status == "Pending Payment":
        # Stock is still reserved — restore it before removing the record
        for item in order.get("items", []):
            try:
                await db.products.update_one(
                    {"_id": ObjectId(item["productId"])},
                    {"$inc": {"stock": item["quantity"]}},
                )
            except Exception:
                pass
        stock_restored = True

    await db.orders.delete_one({"_id": oid})
    return {"message": "Order deleted", "orderId": order_id, "stockRestored": stock_restored}


@router.get("/admin/orders", response_model=List[Order])
async def get_all_orders(admin=Depends(get_admin_user)):
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


@router.patch("/admin/orders/{order_id}/status")
async def update_order_status(order_id: str, status_update: OrderStatusUpdate, admin=Depends(get_admin_user)):
    return await update_order_status_shared(order_id, status_update.status, source="admin")


# ==================== ADMIN USER MANAGEMENT ====================

@router.get("/admin/users", response_model=List[AdminUserResponse])
async def get_all_users(admin=Depends(get_admin_user)):
    users = await db.users.find(
        {},
        {"_id": 1, "email": 1, "firstName": 1, "lastName": 1, "username": 1,
         "isAdmin": 1, "loyaltyPoints": 1, "creditBalance": 1, "isDisabled": 1,
         "lastActiveAt": 1}
    ).to_list(1000)
    return [
        AdminUserResponse(
            id=str(u["_id"]),
            email=u.get("email", ""),
            username=u.get("username"),
            firstName=u.get("firstName", ""),
            lastName=u.get("lastName", ""),
            isAdmin=u.get("isAdmin", False),
            loyaltyPoints=u.get("loyaltyPoints", 0),
            creditBalance=u.get("creditBalance", 0.0),
            isDisabled=u.get("isDisabled", False),
            lastActiveAt=u.get("lastActiveAt"),
        )
        for u in users
    ]


@router.get("/admin/ledger")
async def get_admin_ledger(
    skip: int = 0,
    limit: int = 50,
    userId: Optional[str] = None,
    type: Optional[str] = None,
    admin=Depends(get_admin_user),
):
    query = {}
    if userId:
        query["userId"] = userId
    if type:
        query["type"] = type
    entries = await db.cloudz_ledger.find(query, {"_id": 0}).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.cloudz_ledger.count_documents(query)

    # ── Batch-resolve affected users (userId on each entry) ──────────────────
    user_ids = list({e["userId"] for e in entries if e.get("userId")})
    users_map: dict = {}  # userId_str → {email, username, firstName, lastName}
    if user_ids:
        users_cursor = db.users.find(
            {"_id": {"$in": [ObjectId(uid) for uid in user_ids]}},
            {"_id": 1, "email": 1, "username": 1, "firstName": 1, "lastName": 1},
        )
        async for u in users_cursor:
            users_map[str(u["_id"])] = {
                "email":     u.get("email", "unknown"),
                "username":  u.get("username") or None,
                "firstName": u.get("firstName") or "",
                "lastName":  u.get("lastName") or "",
            }

    # ── Batch-resolve referredUserId → referredUsername ──────────────────────
    referred_ids: set = set()
    for e in entries:
        rid = e.get("referredUserId") or e.get("metadata", {}).get("referredUserId")
        if rid:
            referred_ids.add(str(rid))
    ref_username_map: dict = {}
    if referred_ids:
        ref_cursor = db.users.find(
            {"_id": {"$in": [ObjectId(r) for r in referred_ids if r]}},
            {"_id": 1, "username": 1},
        )
        async for u in ref_cursor:
            ref_username_map[str(u["_id"])] = u.get("username") or None

    # ── Per-entry enrichment ──────────────────────────────────────────────────
    for e in entries:
        if isinstance(e.get("createdAt"), datetime):
            e["createdAt"] = e["createdAt"].isoformat()

        ud = users_map.get(e.get("userId", ""), {})
        email     = ud.get("email", "unknown")
        username  = ud.get("username") or None
        first     = ud.get("firstName", "")
        last      = ud.get("lastName", "")
        full_name = " ".join(filter(None, [first, last])) or None

        # Existing field — preserved unchanged
        e["userEmail"] = email

        # New: username of user whose balance was changed
        e["affectedUsername"] = username or full_name or email

        # New: friendly display string (username preferred, then full name, then email)
        e["affectedDisplayName"] = (
            f"@{username}" if username else (full_name or email)
        )

        # New: referredUsername enrichment
        rid = e.get("referredUserId") or e.get("metadata", {}).get("referredUserId")
        if rid:
            rid = str(rid)
            e["referredUsername"] = (
                ref_username_map.get(rid)
                or e.get("metadata", {}).get("referredUsername")
                or e.get("metadata", {}).get("referredUser")
                or None
            )

    return {"entries": entries, "total": total, "skip": skip, "limit": limit}


@router.patch("/admin/users/{user_id}", response_model=UserResponse)
async def admin_update_user(user_id: str, user_data: AdminUserUpdate, admin=Depends(get_admin_user)):
    update_dict = {k: v for k, v in user_data.dict().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    old_points = None
    if "loyaltyPoints" in update_dict:
        old_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if old_user:
            old_points = old_user.get("loyaltyPoints", 0)
    # Remove loyaltyPoints from $set — log_cloudz_transaction handles the $inc
    points_target = update_dict.pop("loyaltyPoints", None)
    if update_dict:
        result = await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_dict})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
    if points_target is not None and old_points is not None:
        delta = points_target - old_points
        if delta != 0:
            await log_cloudz_transaction(
                user_id, "admin_adjustment", delta,
                f"Admin set balance to {points_target}"
            )
    elif points_target is not None:
        # edge: user not found for old_points fetch — verify user exists
        if not await db.users.find_one({"_id": ObjectId(user_id)}, {"_id": 1}):
            raise HTTPException(status_code=404, detail="User not found")
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    return build_user_response(user)


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin=Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("isAdmin") and str(user["_id"]) != str(admin["_id"]):
        raise HTTPException(status_code=400, detail="Cannot delete another admin account")
    await db.users.delete_one({"_id": ObjectId(user_id)})
    return {"message": "User deleted"}


@router.post("/admin/users/{user_id}/credit")
async def admin_adjust_credit(user_id: str, data: CreditAdjust, admin=Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    current = user.get("creditBalance", 0.0)
    new_balance = round(current + data.amount, 2)
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="Insufficient credit balance")
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"creditBalance": new_balance}})
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


@router.get("/admin/chats")
async def get_admin_chats(admin=Depends(get_admin_user)):
    sessions = await db.chat_sessions.find({}, {"_id": 0}).sort("lastMessageAt", -1).to_list(100)
    active_ids = chat_manager.get_active_chat_ids()
    for s in sessions:
        s["online"] = s.get("chatId") in active_ids
        uid = s.get("userId")
        if uid:
            try:
                u = await db.users.find_one({"_id": ObjectId(uid)}, {"firstName": 1, "lastName": 1, "username": 1, "email": 1})
                s["userName"] = " ".join(filter(None, [u.get("firstName"), u.get("lastName")])) \
                    or u.get("username") or u.get("email", "Unknown") if u else "Unknown"
            except Exception:
                s["userName"] = "Unknown"
    return sessions


@router.get("/admin/support/tickets")
async def get_support_tickets(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    admin=Depends(get_admin_user),
):
    query = {}
    if status:
        query["status"] = status
    tickets = await db.support_tickets.find(query, {"_id": 0}).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.support_tickets.count_documents(query)
    return {"tickets": tickets, "total": total}


@router.get("/admin/analytics")
async def get_admin_analytics(
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    admin=Depends(get_admin_user),
):
    t0 = time.monotonic()

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

    # Cache key based on date range — serve cached result if fresh
    cache_key = f"{startDate}:{endDate}"
    cached = _analytics_cache.get(cache_key)
    if cached and (time.monotonic() - cached["ts"]) < _ANALYTICS_TTL:
        logger.info(f"[analytics] cache hit ({cache_key}) — 0ms")
        return cached["data"]

    date_filter: dict = {"createdAt": {"$gte": start_dt, "$lt": end_dt}}
    seven_days_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)

    # ── RUN ALL 8 AGGREGATIONS IN PARALLEL ──────────────────────────────
    t_db_start = time.monotonic()
    (
        totals,
        payment_data,
        top_products_data,
        top_cust_data,
        low_inv_docs,
        customer_agg,
        rpr_agg,
        trend_raw,
    ) = await asyncio.gather(
        db.orders.aggregate([
            {"$match": date_filter},
            {"$group": {"_id": None, "count": {"$sum": 1}, "revenue": {"$sum": "$total"}}},
        ]).to_list(1),
        db.orders.aggregate([
            {"$match": date_filter},
            {"$group": {"_id": "$paymentMethod", "total": {"$sum": "$total"}, "count": {"$sum": 1}}},
            {"$sort": {"total": -1}},
        ]).to_list(20),
        db.orders.aggregate([
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
        ]).to_list(8),
        db.orders.aggregate([
            {"$match": date_filter},
            {"$group": {"_id": "$userId", "totalSpent": {"$sum": "$total"}, "orderCount": {"$sum": 1}}},
            {"$sort": {"totalSpent": -1}},
            {"$limit": 8},
        ]).to_list(8),
        db.products.find(
            {"stock": {"$lt": 3}, "isActive": True}, {"_id": 1, "name": 1, "stock": 1}
        ).sort("stock", 1).to_list(20),
        db.orders.aggregate([
            {"$match": date_filter},
            {"$group": {"_id": "$userId", "totalSpent": {"$sum": "$total"}, "orderCount": {"$sum": 1}}},
            {"$group": {
                "_id": None,
                "totalCustomers": {"$sum": 1},
                "repeatCustomers": {"$sum": {"$cond": [{"$gt": ["$orderCount", 1]}, 1, 0]}},
                "avgCLV": {"$avg": "$totalSpent"},
            }},
        ]).to_list(1),
        db.orders.aggregate([
            {"$match": {"status": {"$ne": "Cancelled"}}},
            {"$group": {"_id": "$userId", "orderCount": {"$sum": 1}}},
            {"$group": {
                "_id": None,
                "totalUnique": {"$sum": 1},
                "repeatUnique": {"$sum": {"$cond": [{"$gte": ["$orderCount", 2]}, 1, 0]}},
            }},
        ]).to_list(1),
        db.orders.aggregate([
            {"$match": {"createdAt": {"$gte": seven_days_ago}}},
            {"$group": {
                "_id": {"y": {"$year": "$createdAt"}, "m": {"$month": "$createdAt"}, "d": {"$dayOfMonth": "$createdAt"}},
                "revenue": {"$sum": "$total"},
            }},
            {"$sort": {"_id.y": 1, "_id.m": 1, "_id.d": 1}},
        ]).to_list(7),
    )
    t_db = time.monotonic() - t_db_start
    logger.info(f"[analytics] parallel DB queries: {t_db * 1000:.0f}ms")

    # ── BATCH USER LOOKUP (eliminates N+1 loop) ──────────────────────────
    t_users_start = time.monotonic()
    cust_user_ids = [c["_id"] for c in top_cust_data if c.get("_id")]
    users_map: dict = {}
    if cust_user_ids:
        async for u in db.users.find(
            {"_id": {"$in": [ObjectId(uid) for uid in cust_user_ids if uid]}},
            {"_id": 1, "firstName": 1, "lastName": 1, "email": 1},
        ):
            users_map[str(u["_id"])] = u
    t_users = time.monotonic() - t_users_start
    logger.info(f"[analytics] batch user lookup: {t_users * 1000:.0f}ms")

    # ── BUILD RESPONSE ───────────────────────────────────────────────────
    total_orders = totals[0]["count"] if totals else 0
    total_revenue = totals[0]["revenue"] if totals else 0.0
    avg_order_value = total_revenue / total_orders if total_orders else 0.0

    revenue_by_payment = [
        {"method": r["_id"] or "Unknown", "total": r["total"], "count": r["count"]}
        for r in payment_data
    ]

    top_products = [
        {"productId": p["_id"], "name": p["name"], "quantity": p["quantity"], "revenue": p["revenue"]}
        for p in top_products_data
    ]

    top_customers = []
    for c in top_cust_data:
        user = users_map.get(c["_id"])
        name = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip() if user else "Unknown"
        top_customers.append({
            "userId": c["_id"],
            "name": name or (user.get("email", "Unknown") if user else "Unknown"),
            "email": user.get("email", "") if user else "",
            "totalSpent": c["totalSpent"],
            "orderCount": c["orderCount"],
        })

    low_inventory = [
        {"productId": str(p["_id"]), "name": p["name"], "stock": p["stock"]}
        for p in low_inv_docs
    ]

    if customer_agg:
        ca = customer_agg[0]
        total_customers = ca["totalCustomers"]
        repeat_customers = ca["repeatCustomers"]
        repeat_rate = round(repeat_customers / total_customers * 100, 1) if total_customers else 0.0
        avg_clv = ca["avgCLV"]
    else:
        total_customers = repeat_customers = 0
        repeat_rate = avg_clv = 0.0

    if rpr_agg:
        rpr = rpr_agg[0]
        repeat_purchase_rate = round(rpr["repeatUnique"] / rpr["totalUnique"] * 100, 1) if rpr["totalUnique"] else 0.0
    else:
        repeat_purchase_rate = 0.0

    trend_map: dict = {}
    for t in trend_raw:
        key = f"{t['_id']['y']}-{t['_id']['m']:02d}-{t['_id']['d']:02d}"
        trend_map[key] = round(t["revenue"], 2)
    revenue_trend = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        key = day.strftime("%Y-%m-%d")
        revenue_trend.append({"date": key, "revenue": trend_map.get(key, 0)})

    result = {
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
        "revenueTrendLast7Days": revenue_trend,
        "repeatPurchaseRate": repeat_purchase_rate,
    }

    # Store in cache
    _analytics_cache[cache_key] = {"data": result, "ts": time.monotonic()}

    total_ms = (time.monotonic() - t0) * 1000
    logger.info(f"[analytics] TOTAL: {total_ms:.0f}ms  (db={t_db*1000:.0f}ms, users={t_users*1000:.0f}ms)")

    return result


# ==================== TEMPORARY DATA MIGRATION ENDPOINTS ====================

MIGRATABLE_COLLECTIONS = [
    "users", "orders", "cloudz_ledger", "products", "brands",
    "reviews", "chat_messages", "chat_sessions", "loyalty_rewards",
    "push_tokens", "support_tickets", "inventory_logs", "leaderboard_snapshots",
]


def _restore_bson(doc: dict) -> dict:
    """Convert serialized strings back to BSON types for MongoDB insertion."""
    from dateutil import parser as dtparser
    restored = {}
    for k, v in doc.items():
        if k == "_id" and isinstance(v, str) and len(v) == 24:
            try:
                restored[k] = ObjectId(v)
            except Exception:
                restored[k] = v
        elif isinstance(v, str) and k in (
            "createdAt", "updatedAt", "lastMessageAt", "readAt", "timestamp",
            "expiresAt", "usedAt",
        ):
            try:
                restored[k] = dtparser.isoparse(v)
            except Exception:
                restored[k] = v
        elif isinstance(v, dict):
            restored[k] = _restore_bson(v)
        elif isinstance(v, list):
            restored[k] = [_restore_bson(i) if isinstance(i, dict) else i for i in v]
        else:
            restored[k] = v
    return restored


@router.post("/admin/migrate/import")
async def migrate_import_collection(
    data: dict,
    admin=Depends(get_admin_user),
):
    """
    Bulk-import documents into a collection. Skips duplicates by _id.
    For 'users' collection, also skips duplicates by email.

    Body: { "collection": "users", "documents": [ { "_id": "...", ... }, ... ] }
    """
    collection_name = data.get("collection")
    documents = data.get("documents", [])

    if collection_name not in MIGRATABLE_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Collection '{collection_name}' is not allowed")
    if not documents:
        return {"collection": collection_name, "inserted": 0, "skipped": 0, "errors": []}

    coll = db[collection_name]
    inserted = 0
    skipped = 0
    errors = []

    for raw_doc in documents:
        doc = _restore_bson(raw_doc)
        doc_id = doc.get("_id")

        try:
            # Skip if _id already exists
            if doc_id and await coll.find_one({"_id": doc_id}, {"_id": 1}):
                skipped += 1
                continue

            # For users: also skip if email already exists
            if collection_name == "users" and doc.get("email"):
                existing_email = await coll.find_one(
                    {"email": doc["email"]}, {"_id": 1}
                )
                if existing_email:
                    skipped += 1
                    continue

            await coll.insert_one(doc)
            inserted += 1
        except Exception as e:
            err_msg = str(e)
            if "duplicate key" in err_msg.lower():
                skipped += 1
            else:
                errors.append(f"doc _id={doc_id}: {err_msg[:200]}")

    return {
        "collection": collection_name,
        "total_received": len(documents),
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
    }


@router.get("/admin/migrate/export/{collection_name}")
async def migrate_export_collection(collection_name: str, admin=Depends(get_admin_user)):
    """Export all documents from a collection. Returns JSON array."""
    if collection_name not in MIGRATABLE_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Collection '{collection_name}' is not allowed")

    coll = db[collection_name]
    docs = await coll.find({}).to_list(100000)
    serialized = []
    for doc in docs:
        d = {}
        for k, v in doc.items():
            if k == "_id":
                d[k] = str(v)
            elif isinstance(v, ObjectId):
                d[k] = str(v)
            elif isinstance(v, datetime):
                d[k] = v.isoformat()
            else:
                d[k] = v
        serialized.append(d)
    return {"collection": collection_name, "count": len(serialized), "documents": serialized}


DELETABLE_COLLECTIONS = ["orders", "order_items", "payments", "transactions"]

@router.delete("/admin/migrate/purge/{collection_name}")
async def migrate_purge_collection(collection_name: str, admin=Depends(get_admin_user)):
    """Delete ALL documents from a collection. Restricted to safe-listed collections only."""
    if collection_name not in DELETABLE_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Collection '{collection_name}' cannot be purged")
    coll = db[collection_name]
    count_before = await coll.count_documents({})
    result = await coll.delete_many({})
    return {
        "collection": collection_name,
        "deleted": result.deleted_count,
        "count_before": count_before,
        "count_after": await coll.count_documents({}),
    }
