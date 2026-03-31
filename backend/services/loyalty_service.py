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


async def issue_referral_signup_rewards(
    new_user_id: str,
    referrer_identifier: str,
    new_user_first_name: str = "A user",
    new_user_username: str = "",
) -> dict:
    """
    Issue one-time referral signup rewards:
      - +500 Cloudz to the new user   (type: referral_signup_bonus)
      - +500 Cloudz to the referrer   (type: referral_reward)

    Idempotent: gated by user.referralRewardGiven flag, with ledger as secondary check.
    Returns {"user_bonus": int, "referrer_bonus": int}.
    """
    import re
    from bson.errors import InvalidId

    # Fast path: if flag already set, skip entirely
    new_user_doc = await db.users.find_one(
        {"_id": ObjectId(new_user_id)},
        {"referralRewardGiven": 1, "username": 1},
    )
    if new_user_doc and new_user_doc.get("referralRewardGiven", False):
        return {"user_bonus": 0, "referrer_bonus": 0}

    if not new_user_username:
        new_user_username = new_user_doc.get("username", "") if new_user_doc else ""

    # Resolve referrer document (stored as userId or username)
    referrer_doc = None
    if len(str(referrer_identifier)) == 24:
        try:
            referrer_doc = await db.users.find_one(
                {"_id": ObjectId(referrer_identifier)}, {"_id": 1, "username": 1}
            )
        except (InvalidId, Exception):
            pass
    if not referrer_doc:
        referrer_doc = await db.users.find_one(
            {"username": {"$regex": f"^{re.escape(referrer_identifier)}$", "$options": "i"}},
            {"_id": 1, "username": 1},
        )

    if not referrer_doc:
        logger.warning(f"[referral_signup] referrer not found: {referrer_identifier}")
        return {"user_bonus": 0, "referrer_bonus": 0}

    referrer_obj_id = referrer_doc["_id"]
    referrer_id_str = str(referrer_obj_id)
    referrer_username = referrer_doc.get("username", referrer_id_str)
    result = {"user_bonus": 0, "referrer_bonus": 0}

    # 1. +500 to NEW USER — type: referral_signup_bonus
    #    Idempotency: check both new and legacy type names
    already_user = await db.cloudz_ledger.find_one({
        "userId": new_user_id,
        "type": {"$in": ["referral_signup_bonus", "referral_new_user_bonus"]},
    })
    if not already_user:
        await log_cloudz_transaction(
            new_user_id, "referral_signup_bonus", 500,
            f"Referral bonus — signed up with {referrer_username}'s referral",
        )
        result["user_bonus"] = 500

    # 2. +500 to REFERRER — type: referral_reward, keyed on referredUserId
    #    Idempotency: check both new and legacy type names
    already_referrer = await db.cloudz_ledger.find_one({
        "userId": referrer_id_str,
        "type": {"$in": ["referral_reward", "referral_signup_bonus"]},
        "referredUserId": new_user_id,
    })
    if not already_referrer:
        ref_result = await db.users.find_one_and_update(
            {"_id": referrer_obj_id},
            {"$inc": {"referralCount": 1, "loyaltyPoints": 500, "referralRewardsEarned": 500}},
            return_document=True,
        )
        await db.cloudz_ledger.insert_one({
            "userId": referrer_id_str,
            "type": "referral_reward",
            "amount": 500,
            "balanceAfter": ref_result["loyaltyPoints"] if ref_result else 0,
            "description": f"Referral signup reward — {new_user_first_name} joined",
            "referredUserId": new_user_id,
            "metadata": {"referredUser": new_user_username},
            "createdAt": datetime.utcnow(),
        })
        result["referrer_bonus"] = 500
        logger.info(
            f"[referral_signup] +500 to referrer {referrer_id_str} for user {new_user_id}"
        )

    # Mark rewards as given on the new user
    await db.users.update_one(
        {"_id": ObjectId(new_user_id)},
        {"$set": {"referralRewardGiven": True}},
    )

    return result


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
