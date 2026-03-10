from database import db
from bson import ObjectId
from datetime import datetime, timedelta
from models.schemas import LOYALTY_TIERS, TIER_COLORS, STREAK_BONUS
import logging
import math

logger = logging.getLogger(__name__)


async def log_cloudz_transaction(
    user_id: str, tx_type: str, amount: int,
    reference: str = "", description: str = "", order_id: str = ""
) -> int:
    """Atomically update Cloudz balance and write ledger entry. Returns new balance."""
    result = await db.users.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$inc": {"loyaltyPoints": amount}},
        return_document=True,
    )
    new_balance = result["loyaltyPoints"] if result else 0
    entry = {
        "userId": user_id,
        "type": tx_type,
        "amount": amount,
        "balanceAfter": new_balance,
        "reference": reference,
        "description": description or reference,
        "createdAt": datetime.utcnow(),
    }
    if order_id:
        entry["orderId"] = order_id
    await db.cloudz_ledger.insert_one(entry)
    return new_balance


def resolve_tier(points: int):
    tier_name = None
    tier_id = None
    for t in LOYALTY_TIERS:
        if points >= t["pointsRequired"]:
            tier_name = t["name"]
            tier_id = t["id"]
    return tier_name, TIER_COLORS.get(tier_id, "#666") if tier_id else "#666"


async def calculate_streak(user_id: str) -> int:
    """Return the number of consecutive ISO weeks (ending at current) with a Paid order."""
    paid_orders = await db.orders.find(
        {"userId": user_id, "status": "Paid"},
        {"_id": 0, "createdAt": 1},
    ).sort("createdAt", -1).to_list(5000)
    if not paid_orders:
        return 0
    weeks_with_orders: set = set()
    for o in paid_orders:
        dt = o["createdAt"]
        weeks_with_orders.add(dt.isocalendar()[:2])
    now = datetime.utcnow()
    current = now.isocalendar()[:2]
    streak = 0
    yr, wk = current
    while (yr, wk) in weeks_with_orders:
        streak += 1
        prev_day = datetime.fromisocalendar(yr, wk, 1) - timedelta(days=1)
        yr, wk = prev_day.isocalendar()[:2]
    return streak


def get_streak_bonus(streak: int) -> int:
    if streak < 2:
        return 0
    return STREAK_BONUS.get(streak, 500)


async def maybe_award_streak_bonus(user_id: str, order_id: str):
    """Award streak bonus once per ISO week when the first order is marked Paid."""
    now = datetime.utcnow()
    iso_year, iso_week = now.isocalendar()[:2]
    existing = await db.cloudz_ledger.find_one({
        "userId": user_id,
        "type": "streak_bonus",
        "isoYear": iso_year,
        "isoWeek": iso_week,
    })
    if existing:
        return 0
    streak = await calculate_streak(user_id)
    bonus = get_streak_bonus(streak)
    if bonus <= 0:
        return 0
    result = await db.users.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$inc": {"loyaltyPoints": bonus}},
        return_document=True,
    )
    balance_after = result["loyaltyPoints"] if result else 0
    await db.cloudz_ledger.insert_one({
        "userId": user_id,
        "type": "streak_bonus",
        "amount": bonus,
        "balanceAfter": balance_after,
        "reference": f"Week {iso_week} streak ({streak} weeks) - Order #{order_id[:8]}",
        "isoYear": iso_year,
        "isoWeek": iso_week,
        "createdAt": now,
    })
    return bonus
