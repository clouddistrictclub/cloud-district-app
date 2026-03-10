from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth import get_current_user
from models.schemas import Order, OrderCreate
from services.loyalty_service import log_cloudz_transaction
from services.email_service import is_email_configured, send_email, build_order_confirmation_html
from services.order_service import chat_manager
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/orders", response_model=Order)
async def create_order(order_data: OrderCreate, user=Depends(get_current_user)):
    # Verify products exist (non-atomic, fast pre-check for 404s only)
    for item in order_data.items:
        product = await db.products.find_one({"_id": ObjectId(item.productId)}, {"name": 1})
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.productId} not found")

    points_earned = int(order_data.total) * 3
    reward_discount = 0.0
    reward_points_used = 0

    # Handle next-order coupon application
    coupon_discount = 0.0
    if order_data.couponApplied:
        from datetime import timezone
        user_doc = await db.users.find_one({"_id": user["_id"]}, {"nextOrderCoupon": 1})
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
            "userId": str(user["_id"]),
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
        "userId": str(user["_id"]),
        "items": [item.dict() for item in order_data.items],
        "total": order_data.total,
        "pickupTime": order_data.pickupTime,
        "paymentMethod": order_data.paymentMethod,
        "status": "Awaiting Pickup (Cash)" if order_data.paymentMethod == "Cash on Pickup" else "Pending Payment",
        "loyaltyPointsEarned": points_earned,
        "loyaltyPointsUsed": reward_points_used,
        "rewardId": order_data.rewardId,
        "rewardDiscount": reward_discount,
        "couponDiscount": coupon_discount,
        "createdAt": created_at,
        "expiresAt": created_at + timedelta(minutes=30) if is_pending_payment else None,
    }

    result = await db.orders.insert_one(order_dict)
    order_dict["id"] = str(result.inserted_id)

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
            send_email(user.get("email", ""), "Order Confirmation - Cloud District Club", email_html)
    except Exception as e:
        logger.warning(f"Order confirmation email skipped: {e}")

    return Order(**order_dict)


@router.get("/orders", response_model=List[Order])
async def get_orders(user=Depends(get_current_user)):
    orders = await db.orders.find({"userId": str(user["_id"])}).sort("createdAt", -1).to_list(1000)
    return [Order(id=str(o["_id"]), **{k: v for k, v in o.items() if k != "_id"}) for o in orders]


@router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, user=Depends(get_current_user)):
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["userId"] != str(user["_id"]) and not user.get("isAdmin", False):
        raise HTTPException(status_code=403, detail="Access denied")
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
    await db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "Cancelled"}})
    return {"message": "Order cancelled"}


@router.get("/chat/messages/{chat_id}")
async def get_chat_messages(chat_id: str, user=Depends(get_current_user)):
    messages = await db.chat_messages.find(
        {"chatId": chat_id}, {"_id": 0}
    ).sort("createdAt", 1).to_list(200)
    return messages
