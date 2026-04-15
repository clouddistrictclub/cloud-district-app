from fastapi import APIRouter, HTTPException, Depends, Request
from database import db
from auth import get_current_user, get_admin_user, touch_last_active
from models.schemas import Order, OrderCreate, OrderStatusUpdate
from services.loyalty_service import log_cloudz_transaction, check_and_unlock_referral_reward
from services.email_service import is_email_configured, send_email, build_order_confirmation_html
from services.order_service import chat_manager, update_order_status_shared
from limiter import limiter, get_user_id_or_ip
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/orders", response_model=Order)
@limiter.limit("5/minute", key_func=get_user_id_or_ip)
async def create_order(request: Request, order_data: OrderCreate, user=Depends(get_current_user)):
    # --- Resolve effective user (admin may create on behalf of another user) ---
    print(f"ORDER DATA USER ID: {order_data.userId}")
    print(f"AUTH USER ID: {str(user['_id'])}")
    print(f"IS ADMIN: {user.get('isAdmin', False)}")

    if user.get("isAdmin") and order_data.userId:
        try:
            target_oid = ObjectId(order_data.userId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid userId format")
        order_user = await db.users.find_one({"_id": target_oid})
        if not order_user:
            raise HTTPException(status_code=400, detail="Target user not found")
        effective_user_id = str(target_oid)
        effective_user_oid = target_oid
        print(f"ORDER CREATED FOR: {effective_user_id} (by admin {str(user['_id'])})")
    else:
        effective_user_id = str(user["_id"])
        effective_user_oid = user["_id"]
        order_user = user
        print(f"ORDER CREATED FOR: {effective_user_id} (no override)")

    # Verify products exist (non-atomic, fast pre-check for 404s only)
    for item in order_data.items:
        product = await db.products.find_one({"_id": ObjectId(item.productId)}, {"name": 1})
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.productId} not found")

    # --- Bulk discount: 10% when total quantity >= 10 items (applied BEFORE store credit) ---
    total_qty = sum(item.quantity for item in order_data.items)
    bulk_discount = 0.0
    if total_qty >= 10:
        bulk_discount = round(order_data.total * 0.10, 2)

    # Final total after discount
    final_total = round(order_data.total - bulk_discount, 2)

    # 1.75% processing fee for Apple Pay, Cash App, Chime — server-calculated only
    FEE_METHODS = {"Apple Pay", "Cash App", "Chime"}
    processing_fee = 0.0
    if order_data.paymentMethod in FEE_METHODS:
        processing_fee = round(final_total * 0.0175, 2)
        final_total = round(final_total + processing_fee, 2)

    points_earned = int(final_total) * 3
    reward_discount = 0.0
    reward_points_used = 0

    # Handle store credit application
    store_credit_applied = 0.0
    if order_data.storeCreditApplied > 0:
        user_doc = await db.users.find_one({"_id": effective_user_oid}, {"creditBalance": 1})
        available_credit = float(user_doc.get("creditBalance", 0)) if user_doc else 0.0
        store_credit_applied = min(order_data.storeCreditApplied, available_credit)
        if store_credit_applied > order_data.total:
            store_credit_applied = order_data.total

    # Handle next-order coupon application
    coupon_discount = 0.0
    if order_data.couponApplied:
        from datetime import timezone
        user_doc = await db.users.find_one({"_id": effective_user_oid}, {"nextOrderCoupon": 1})
        coupon = user_doc.get("nextOrderCoupon") if user_doc else None
        if coupon and not coupon.get("used", False):
            try:
                exp = datetime.fromisoformat(coupon["expiresAt"])
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp >= datetime.now(timezone.utc):
                    coupon_discount = float(coupon.get("amount", 0))
                    await db.users.update_one(
                        {"_id": user["_id"]},
                        {"$set": {"nextOrderCoupon.used": True, "nextOrderCoupon.usedAt": datetime.utcnow().isoformat()}}
                    )
            except Exception:
                pass

    # Handle tier-based reward redemption at checkout
    if order_data.rewardId:
        try:
            reward_oid = ObjectId(order_data.rewardId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid reward ID format")
        reward = await db.loyalty_rewards.find_one({
            "_id": reward_oid,
            "userId": effective_user_id,
            "used": False,
        })
        if not reward:
            raise HTTPException(status_code=400, detail="Invalid or already used reward")
        reward_discount = reward["rewardAmount"]
        reward_points_used = reward["pointsSpent"]
        await db.loyalty_rewards.update_one(
            {"_id": ObjectId(order_data.rewardId)},
            {"$set": {"used": True, "usedAt": datetime.utcnow()}}
        )

    created_at = datetime.utcnow()
    is_pending_payment = order_data.paymentMethod != "Cash on Pickup"
    order_dict = {
        "userId": effective_user_id,
        "items": [item.dict() for item in order_data.items],
        "total": final_total,
        "pickupTime": order_data.pickupTime,
        "paymentMethod": order_data.paymentMethod,
        "processingFee": processing_fee,
        "status": "Awaiting Pickup (Cash)" if order_data.paymentMethod == "Cash on Pickup" else "Pending Payment",
        "loyaltyPointsEarned": points_earned,
        "loyaltyPointsUsed": reward_points_used,
        "rewardId": order_data.rewardId,
        "rewardDiscount": reward_discount,
        "couponDiscount": coupon_discount,
        "storeCreditApplied": store_credit_applied,
        "discountApplied": bulk_discount,
        "createdAt": created_at,
        "expiresAt": created_at + timedelta(minutes=30) if is_pending_payment else None,
        "referralRewardIssued": False,
        "loyaltyRewardIssued": False,
        "customerName": order_data.name or None,
        "customerEmail": order_data.email or None,
        "customerPhone": order_data.phone or None,
    }

    result = await db.orders.insert_one(order_dict)
    order_dict["id"] = str(result.inserted_id)
    order_dict["requestedUserId"] = order_data.userId
    order_dict["effectiveUserId"] = effective_user_id

    # Deduct store credit from effective user balance
    if store_credit_applied > 0:
        await db.users.update_one(
            {"_id": effective_user_oid},
            {"$inc": {"creditBalance": -store_credit_applied}}
        )

    # Atomic inventory deduction
    decremented = []
    for item in order_data.items:
        res = await db.products.update_one(
            {"_id": ObjectId(item.productId), "stock": {"$gte": item.quantity}},
            {"$inc": {"stock": -item.quantity}}
        )
        if res.modified_count == 0:
            for rolled in decremented:
                await db.products.update_one(
                    {"_id": ObjectId(rolled.productId)},
                    {"$inc": {"stock": rolled.quantity}}
                )
            await db.orders.delete_one({"_id": result.inserted_id})
            raise HTTPException(status_code=409, detail=f"Out of stock: {item.name}")
        decremented.append(item)

    # Send order confirmation email (non-blocking)
    try:
        if is_email_configured():
            email_html = build_order_confirmation_html(
                order_id=order_dict["id"],
                items=order_dict["items"],
                total=order_dict["total"],
            )
            send_email(order_user.get("email", ""), "Order Confirmation - Cloud District Club", email_html)
    except Exception as e:
        logger.warning(f"Order confirmation email skipped: {e}")

    # Update lastActiveAt for the customer who placed the order
    await touch_last_active(effective_user_id)

    return Order(**order_dict)


async def _enrich_orders_with_review_state(orders: list, user_id: str) -> list:
    """
    Inject reviewPromptEligible + reviewedProductIds into Completed order dicts.
    One batch reviews query covers all orders — O(1) extra round-trips.
    """
    completed = [o for o in orders if o.get("status") == "Completed"]
    if not completed:
        return orders

    # Collect every productId from completed orders
    all_product_ids = {
        item["productId"]
        for o in completed
        for item in o.get("items", [])
    }

    # Single batch lookup: which of these products has this user already reviewed?
    reviewed_docs = await db.reviews.find(
        {"userId": user_id, "productId": {"$in": list(all_product_ids)}},
        {"productId": 1, "_id": 0},
    ).to_list(1000)
    reviewed_set = {r["productId"] for r in reviewed_docs}

    for o in orders:
        if o.get("status") == "Completed":
            order_product_ids = [item["productId"] for item in o.get("items", [])]
            reviewed_in_order = [pid for pid in order_product_ids if pid in reviewed_set]
            o["reviewedProductIds"] = reviewed_in_order
            o["reviewPromptEligible"] = any(pid not in reviewed_set for pid in order_product_ids)
        else:
            o["reviewPromptEligible"] = False
            o["reviewedProductIds"] = []
    return orders


@router.get("/orders", response_model=List[Order])
async def get_orders(user=Depends(get_current_user)):
    user_id = str(user["_id"])
    orders = await db.orders.find({"userId": user_id}).sort("createdAt", -1).to_list(1000)
    orders = await _enrich_orders_with_review_state(orders, user_id)
    return [Order(id=str(o["_id"]), **{k: v for k, v in o.items() if k != "_id"}) for o in orders]


@router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, user=Depends(get_current_user)):
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["userId"] != str(user["_id"]) and not user.get("isAdmin", False):
        raise HTTPException(status_code=403, detail="Access denied")
    await _enrich_orders_with_review_state([order], str(user["_id"]))
    return Order(id=str(order["_id"]), **{k: v for k, v in order.items() if k != "_id"})


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str, user=Depends(get_current_user)):
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["userId"] != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    if order["status"] != "Pending Payment":
        raise HTTPException(status_code=400, detail="Only orders with status 'Pending Payment' can be cancelled")
    for item in order.get("items", []):
        await db.products.update_one(
            {"_id": ObjectId(item["productId"])},
            {"$inc": {"stock": item["quantity"]}}
        )
    # Restore store credit if any was applied
    if order.get("storeCreditApplied", 0) > 0:
        await db.users.update_one(
            {"_id": ObjectId(order["userId"])},
            {"$inc": {"creditBalance": order["storeCreditApplied"]}}
        )
    await db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "Cancelled"}})
    return {"message": "Order cancelled"}


@router.patch("/orders/{order_id}/status")
async def update_order_status_web(order_id: str, status_update: OrderStatusUpdate, admin=Depends(get_admin_user)):
    """
    Web-accessible order status update endpoint.
    Identical reward logic to /admin/orders/:id/status — both call the shared service.
    """
    return await update_order_status_shared(order_id, status_update.status, source="web")


@router.get("/chat/messages/{chat_id}")
async def get_chat_messages(chat_id: str, user=Depends(get_current_user)):
    messages = await db.chat_messages.find(
        {"chatId": chat_id}, {"_id": 0}
    ).sort("createdAt", 1).to_list(200)
    return messages
