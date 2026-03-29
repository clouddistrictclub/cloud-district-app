from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth import get_admin_user, build_user_response, get_password_hash
from models.schemas import (
    UserResponse, AdminUserUpdate, CreditAdjust, AdminReferrerUpdate,
    CloudzAdjust, AdminSetPassword, AdminUserNotes, MergeRequest,
    Order, OrderStatusUpdate, OrderEdit, ReviewModerationUpdate,
    UserUsernameUpdate
)
from services.loyalty_service import log_cloudz_transaction, maybe_award_streak_bonus, issue_referral_signup_rewards
from services.order_service import send_push_notification, chat_manager
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Optional
import re as _re
import math
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


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
    for e in entries:
        if isinstance(e.get("createdAt"), datetime):
            e["createdAt"] = e["createdAt"].isoformat()
    return entries


@router.post("/admin/users/{user_id}/cloudz-adjust")
async def admin_adjust_cloudz(user_id: str, data: CloudzAdjust, admin=Depends(get_admin_user)):
    new_balance = await log_cloudz_transaction(user_id, "admin_adjustment", data.amount, data.description, data.description)
    return {"message": "Balance updated", "newBalance": new_balance}


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


@router.post("/admin/users/{user_id}/force-logout")
async def admin_force_logout(user_id: str, admin=Depends(get_admin_user)):
    import time
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"forceLogoutAt": time.time()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True}


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
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if status_update.status == "Cancelled" and order["status"] != "Cancelled":
        for item in order.get("items", []):
            await db.products.update_one(
                {"_id": ObjectId(item["productId"])},
                {"$inc": {"stock": item["quantity"]}}
            )
        await db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "Cancelled"}})
        await send_push_notification(
            order["userId"], "Order Cancelled",
            f"Order #{order_id[-6:].upper()} has been cancelled.",
        )
        return {"message": "Order status updated"}

    if status_update.status == "Paid" and order["status"] in ("Pending Payment", "Awaiting Pickup (Cash)"):
        await log_cloudz_transaction(
            order["userId"], "purchase_reward", order["loyaltyPointsEarned"],
            f"Order #{order_id[:8]}",
            f"Purchase reward from order #{order_id}",
            order_id,
        )
        await maybe_award_streak_bonus(order["userId"], order_id)
        coupon_expires = datetime.utcnow() + timedelta(days=7)
        await db.users.update_one(
            {"_id": ObjectId(order["userId"])},
            {"$set": {"nextOrderCoupon": {
                "amount": 5.00,
                "expiresAt": coupon_expires.isoformat(),
                "orderId": order_id,
                "used": False,
                "issuedAt": datetime.utcnow().isoformat(),
            }}}
        )

    if status_update.status == "Paid" and not order.get("referralRewardIssued", False):
        # Atomic claim: only the request that flips the flag gets to issue the reward.
        # Concurrent requests will receive None here and skip entirely.
        claimed = await db.orders.find_one_and_update(
            {"_id": ObjectId(order_id), "referralRewardIssued": False},
            {"$set": {"referralRewardIssued": True}},
        )
        if claimed is None:
            logger.info(f"[referral_reward] skipped — already issued for order {order_id}")
        else:
            buyer_doc = await db.users.find_one({"_id": ObjectId(order["userId"])}, {"referredBy": 1})
            referrer_id = buyer_doc.get("referredBy") if buyer_doc else None
            if referrer_id:
                reward = math.floor(float(order.get("total") or 0) * 0.5)
                try:
                    from bson.errors import InvalidId
                    referrer_doc = None
                    is_object_id = len(str(referrer_id)) == 24
                    if is_object_id:
                        try:
                            referrer_doc = await db.users.find_one({"_id": ObjectId(referrer_id)})
                        except (InvalidId, Exception):
                            pass
                    if not referrer_doc:
                        referrer_doc = await db.users.find_one({"username": referrer_id})
                    if referrer_doc and reward > 0:
                        referrer_obj_id = referrer_doc["_id"]
                        referrer_id_str = str(referrer_obj_id)
                        await db.users.update_one(
                            {"_id": referrer_obj_id},
                            {"$inc": {"referralRewardsEarned": reward}}
                        )
                        ref_result = await db.users.find_one_and_update(
                            {"_id": referrer_obj_id},
                            {"$inc": {"loyaltyPoints": reward}},
                            return_document=True,
                        )
                        await db.cloudz_ledger.insert_one({
                            "userId": referrer_id_str,
                            "type": "referral_reward",
                            "amount": reward,
                            "balanceAfter": ref_result["loyaltyPoints"] if ref_result else 0,
                            "description": f"Referral reward from order #{order_id}",
                            "orderId": order_id,
                            "createdAt": datetime.utcnow(),
                        })
                        logger.info(
                            f"[referral_reward] issued {reward} Cloudz to {referrer_id_str} "
                            f"for order {order_id}"
                        )
                    else:
                        logger.info(
                            f"[referral_reward] skipped — referrer not found or reward=0 "
                            f"(referrer_id={referrer_id}, reward={reward})"
                        )
                except Exception as e:
                    logger.error(f"[referral_reward] error for order {order_id}: {e}")
            else:
                logger.info(f"[referral_reward] skipped — order {order_id} has no referredBy")

    await db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": status_update.status}})
    await send_push_notification(
        order["userId"], "Order Update",
        f"Order #{order_id[-6:].upper()} is now: {status_update.status}",
    )
    return {"message": "Order status updated"}


# ==================== ADMIN USER MANAGEMENT ====================

@router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(admin=Depends(get_admin_user)):
    users = await db.users.find().to_list(1000)
    return [build_user_response(u) for u in users]


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
                u = await db.users.find_one({"_id": ObjectId(uid)}, {"name": 1, "email": 1})
                s["userName"] = u.get("name", u.get("email", "Unknown")) if u else "Unknown"
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

    rpr_agg = await db.orders.aggregate([
        {"$match": {"status": {"$ne": "Cancelled"}}},
        {"$group": {"_id": "$userId", "orderCount": {"$sum": 1}}},
        {"$group": {
            "_id": None,
            "totalUnique": {"$sum": 1},
            "repeatUnique": {"$sum": {"$cond": [{"$gte": ["$orderCount", 2]}, 1, 0]}},
        }},
    ]).to_list(1)
    if rpr_agg:
        rpr = rpr_agg[0]
        repeat_purchase_rate = round(rpr["repeatUnique"] / rpr["totalUnique"] * 100, 1) if rpr["totalUnique"] else 0.0
    else:
        repeat_purchase_rate = 0.0

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
    revenue_trend = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        key = day.strftime("%Y-%m-%d")
        revenue_trend.append({"date": key, "revenue": trend_map.get(key, 0)})

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
        "revenueTrendLast7Days": revenue_trend,
        "repeatPurchaseRate": repeat_purchase_rate,
    }


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
