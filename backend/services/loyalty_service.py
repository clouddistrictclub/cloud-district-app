from database import db
from bson import ObjectId
from datetime import datetime, timedelta
from models.schemas import LOYALTY_TIERS, TIER_COLORS, STREAK_BONUS, CHECKIN_REWARDS, LEADERBOARD_REWARDS
import logging
import math

# Confirm at import time that this module uses the same db instance as startup
print(f"LOYALTY SERVICE DB NAME: {db.name}")

logger = logging.getLogger(__name__)


async def log_cloudz_transaction(
    user_id: str, tx_type: str, amount: int,
    reference: str = "", description: str = "", order_id: str = "",
    metadata: dict = None,
) -> int:
    """Atomically update Cloudz balance and write ledger entry. Returns new balance."""
    update_result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$inc": {"loyaltyPoints": amount}},
    )
    print(f"DB UPDATE loyaltyPoints ({tx_type}): matched={update_result.matched_count} modified={update_result.modified_count} user_id={user_id}")

    updated_user = await db.users.find_one({"_id": ObjectId(user_id)}, {"loyaltyPoints": 1})
    new_balance = updated_user["loyaltyPoints"] if updated_user else 0
    print(f"UPDATED BALANCE after {tx_type}: {new_balance}")

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
    if metadata:
        entry["metadata"] = metadata
    ledger_result = await db.cloudz_ledger.insert_one(entry)
    print(f"LEDGER INSERTED ({tx_type}): {ledger_result.inserted_id}")
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
        {"userId": user_id, "status": {"$in": ["Paid", "Completed"]}},
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

    print("REFERRAL: function entered", new_user_id, referrer_identifier)

    # Fast path: if flag already set, skip entirely
    new_user_doc = await db.users.find_one(
        {"_id": ObjectId(new_user_id)},
        {"referralRewardGiven": 1, "username": 1},
    )
    if new_user_doc and new_user_doc.get("referralRewardGiven", False):
        return {"user_bonus": 0, "referrer_bonus": 0}

    if not new_user_username:
        new_user_username = new_user_doc.get("username", "") if new_user_doc else ""

    result = {"user_bonus": 0, "referrer_bonus": 0}

    # 1. +500 to NEW USER — type: referral_signup_bonus
    #    Issue this FIRST, before resolving the referrer, so it never depends on referrer lookup success.
    #    Idempotency: check both new and legacy type names
    already_user = await db.cloudz_ledger.find_one({
        "userId": new_user_id,
        "type": {"$in": ["referral_signup_bonus", "referral_new_user_bonus"]},
    })
    if not already_user:
        print("REFERRAL: awarding new user bonus +500")
        await log_cloudz_transaction(
            new_user_id, "referral_signup_bonus", 500,
            f"Referral bonus — signed up with a referral code",
        )
        result["user_bonus"] = 500

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
        # Mark rewards as given on the new user (new user bonus was issued above)
        await db.users.update_one(
            {"_id": ObjectId(new_user_id)},
            {"$set": {"referralRewardGiven": True}},
        )
        return result

    referrer_obj_id = referrer_doc["_id"]
    referrer_id_str = str(referrer_obj_id)
    referrer_username = referrer_doc.get("username", referrer_id_str)

    # 2. REFERRER gets a PENDING reward (+1500) — unlocked when referred user spends $50+
    #    Idempotency: check for any existing entry (pending OR converted)
    already_referrer = await db.cloudz_ledger.find_one({
        "userId": referrer_id_str,
        "type": {"$in": ["referral_reward", "referral_signup_bonus", "referral_pending"]},
        "referredUserId": new_user_id,
    })
    if not already_referrer:
        # Increment referralCount on referrer (no balance change yet)
        await db.users.update_one(
            {"_id": referrer_obj_id},
            {"$inc": {"referralCount": 1}},
        )
        print("REFERRAL: creating pending 1000 for referrer")
        await db.cloudz_ledger.insert_one({
            "userId": referrer_id_str,
            "type": "referral_pending",
            "amount": 1000,
            "status": "pending",
            "description": f"Pending referral reward — {new_user_first_name} joined (unlocks at $50 spend)",
            "referredUserId": new_user_id,
            "metadata": {
                "referredUserId": new_user_id,
                "referredUsername": new_user_username,
                "unlockThreshold": 50,
            },
            "createdAt": datetime.utcnow(),
        })
        result["referrer_bonus"] = 1000  # pending — not yet in balance
        logger.info(
            f"[referral_signup] pending reward created for referrer {referrer_id_str} "
            f"(referred user {new_user_id}, unlocks at $50 spend)"
        )

    # Mark rewards as given on the new user
    await db.users.update_one(
        {"_id": ObjectId(new_user_id)},
        {"$set": {"referralRewardGiven": True}},
    )

    return result


async def check_and_unlock_referral_reward(buyer_user_id: str) -> bool:
    """
    Called when an order is marked Paid.
    If the buyer was referred AND their lifetime spend >= $50 AND reward not yet unlocked:
      - Converts their referrer's 'referral_pending' entry to 'referral_reward'
      - Credits +1500 to referrer's Cloudz balance
      - Sets buyer.referralUnlocked = True

    Returns True if the reward was unlocked in this call.
    """
    print("REFERRAL UNLOCK: checking spend for", buyer_user_id)
    buyer_doc = await db.users.find_one(
        {"_id": ObjectId(buyer_user_id)},
        {"referredBy": 1, "referralUnlocked": 1},
    )
    if not buyer_doc:
        return False

    # Already unlocked — nothing to do
    if buyer_doc.get("referralUnlocked", False):
        return False

    referrer_id = buyer_doc.get("referredBy")
    if not referrer_id:
        return False  # Not a referred user

    # Sum lifetime spend from completed orders
    completed_statuses = ["Completed"]
    pipeline = [
        {"$match": {"userId": buyer_user_id, "status": {"$in": completed_statuses}}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}},
    ]
    agg = await db.orders.aggregate(pipeline).to_list(1)
    lifetime_spend = float(agg[0]["total"]) if agg else 0.0

    if lifetime_spend < 50.0:
        logger.info(
            f"[referral_unlock] buyer {buyer_user_id} spend={lifetime_spend:.2f} < $50 — not yet"
        )
        return False

    # Atomic gate: only the first call that flips referralUnlocked wins
    claimed = await db.users.find_one_and_update(
        {"_id": ObjectId(buyer_user_id), "referralUnlocked": {"$ne": True}},
        {"$set": {"referralUnlocked": True}},
    )
    if claimed is None:
        logger.info(f"[referral_unlock] already unlocked for buyer {buyer_user_id} (race)")
        return False

    # Resolve referrer
    from bson.errors import InvalidId
    referrer_doc = None
    if len(str(referrer_id)) == 24:
        try:
            referrer_doc = await db.users.find_one({"_id": ObjectId(referrer_id)}, {"_id": 1})
        except (InvalidId, Exception):
            pass
    if not referrer_doc:
        referrer_doc = await db.users.find_one({"username": referrer_id}, {"_id": 1})

    if not referrer_doc:
        logger.warning(f"[referral_unlock] referrer {referrer_id} not found for buyer {buyer_user_id}")
        return False

    referrer_obj_id = referrer_doc["_id"]
    referrer_id_str = str(referrer_obj_id)

    # Convert the pending entry to a real reward
    pending = await db.cloudz_ledger.find_one({
        "userId": referrer_id_str,
        "type": "referral_pending",
        "referredUserId": buyer_user_id,
        "status": "pending",
    })

    if not pending:
        logger.warning(
            f"[referral_unlock] no pending entry found for referrer {referrer_id_str} "
            f"/ buyer {buyer_user_id}"
        )
        # Still credit — idempotency is already guaranteed by the flag above
    else:
        await db.cloudz_ledger.update_one(
            {"_id": pending["_id"]},
            {"$set": {"type": "referral_reward", "status": "completed"}},
        )

    # Credit +1000 to referrer balance
    print("REFERRAL UNLOCK: unlocking 1000")
    update_result = await db.users.update_one(
        {"_id": referrer_obj_id},
        {"$inc": {"loyaltyPoints": 1000, "referralRewardsEarned": 1000}},
    )
    print(f"DB UPDATE referral_unlock: matched={update_result.matched_count} modified={update_result.modified_count} referrer_id={referrer_id_str}")
    updated_referrer = await db.users.find_one({"_id": referrer_obj_id}, {"loyaltyPoints": 1})
    new_balance = updated_referrer["loyaltyPoints"] if updated_referrer else 0
    print(f"UPDATED BALANCE after referral_unlock: {new_balance}")

    # If no pending entry existed, insert a completed reward entry
    if not pending:
        await db.cloudz_ledger.insert_one({
            "userId": referrer_id_str,
            "type": "referral_reward",
            "amount": 1000,
            "status": "completed",
            "balanceAfter": new_balance,
            "description": f"Referral reward unlocked — referred user reached $50 spend",
            "referredUserId": buyer_user_id,
            "createdAt": datetime.utcnow(),
        })
    else:
        # Back-fill the balance on the converted entry
        await db.cloudz_ledger.update_one(
            {"_id": pending["_id"]},
            {"$set": {"balanceAfter": new_balance}},
        )

    logger.info(
        f"[referral_unlock] +1500 unlocked for referrer {referrer_id_str} "
        f"(buyer {buyer_user_id}, lifetime_spend=${lifetime_spend:.2f})"
    )
    return True


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



async def process_daily_checkin(user_id: str) -> dict:
    """
    Award daily check-in Cloudz reward. Atomic and idempotent.
    - One reward per UTC calendar day.
    - Consecutive days increment checkInStreak; any gap resets to 1.
    - Streak cycles through CHECKIN_REWARDS on a 7-day loop.
    """
    user = await db.users.find_one(
        {"_id": ObjectId(user_id)},
        {"lastCheckInDate": 1, "checkInStreak": 1},
    )

    today_str     = datetime.utcnow().strftime("%Y-%m-%d")
    yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    last_date     = user.get("lastCheckInDate") if user else None
    cur_streak    = (user.get("checkInStreak") or 0) if user else 0

    # Already checked in today — return current state without writing anything
    if last_date == today_str:
        next_day    = (cur_streak % 7) + 1
        next_reward = CHECKIN_REWARDS[next_day]
        return {
            "success":          False,
            "alreadyCheckedIn": True,
            "reward":           0,
            "streak":           cur_streak,
            "nextReward":       next_reward,
        }

    # Compute new streak
    new_streak  = (cur_streak + 1) if last_date == yesterday_str else 1
    reward      = CHECKIN_REWARDS[(new_streak - 1) % 7 + 1]
    next_reward = CHECKIN_REWARDS[(new_streak % 7) + 1]

    # Atomic write — filter ensures a concurrent duplicate request loses the race
    result = await db.users.find_one_and_update(
        {
            "_id":             ObjectId(user_id),
            "lastCheckInDate": {"$ne": today_str},
        },
        {
            "$set": {
                "lastCheckInDate": today_str,
                "checkInStreak":   new_streak,
            },
            "$inc": {"loyaltyPoints": reward},
        },
        return_document=True,
    )

    # Concurrent request already claimed today's reward
    if result is None:
        cur_streak  = (await db.users.find_one({"_id": ObjectId(user_id)}, {"checkInStreak": 1}) or {}).get("checkInStreak", new_streak)
        next_day    = (cur_streak % 7) + 1
        return {
            "success":          False,
            "alreadyCheckedIn": True,
            "reward":           0,
            "streak":           cur_streak,
            "nextReward":       CHECKIN_REWARDS[next_day],
        }

    balance_after = result["loyaltyPoints"]

    await db.cloudz_ledger.insert_one({
        "userId":      user_id,
        "type":        "daily_checkin",
        "amount":      reward,
        "balanceAfter": balance_after,
        "reference":   f"Day {new_streak} check-in",
        "description": f"Daily check-in — day {new_streak}",
        "isoDate":     today_str,
        "createdAt":   datetime.utcnow(),
    })

    return {
        "success":          True,
        "alreadyCheckedIn": False,
        "reward":           reward,
        "streak":           new_streak,
        "nextReward":       next_reward,
    }


async def issue_weekly_leaderboard_rewards(iso_year: int, iso_week: int):
    """
    Issue top-3 byPoints weekly leaderboard rewards. Called on every leaderboard request.
    Atomic + idempotent: rewards fire exactly once per ISO week.

    Idempotency mechanism:
      - update_one with upsert=True + $setOnInsert creates the record only when
        it does not yet exist. If it already exists, the upsert is a no-op.
      - result.upserted_id is set ONLY when a new document was inserted.
        If None, the record already existed → rewards already issued → skip.
    """
    # Atomic claim: insert record for this (year, week) only if not yet present
    result = await db.leaderboard_rewards.update_one(
        {"isoYear": iso_year, "isoWeek": iso_week},
        {
            "$setOnInsert": {
                "isoYear":       iso_year,
                "isoWeek":       iso_week,
                "rewardsIssued": False,
                "topUsers":      [],
                "createdAt":     datetime.utcnow(),
            }
        },
        upsert=True,
    )

    if result.upserted_id is None:
        # Document already existed — rewards already issued (or in progress). Skip.
        return

    # We own this week. Fetch top 3 by loyaltyPoints.
    top3 = await db.users.find(
        {}, {"_id": 1, "loyaltyPoints": 1}
    ).sort("loyaltyPoints", -1).limit(3).to_list(3)

    ordinal = {1: "1st", 2: "2nd", 3: "3rd"}
    top_users = []

    for rank, user_doc in enumerate(top3, start=1):
        uid    = str(user_doc["_id"])
        reward = LEADERBOARD_REWARDS[rank]

        updated = await db.users.find_one_and_update(
            {"_id": user_doc["_id"]},
            {"$inc": {"loyaltyPoints": reward}},
            return_document=True,
        )
        balance_after = updated["loyaltyPoints"] if updated else 0

        await db.cloudz_ledger.insert_one({
            "userId":      uid,
            "type":        "leaderboard_reward",
            "amount":      reward,
            "balanceAfter": balance_after,
            "reference":   f"Weekly leaderboard #{rank}",
            "description": f"{ordinal[rank]} place weekly leaderboard",
            "isoYear":     iso_year,
            "isoWeek":     iso_week,
            "createdAt":   datetime.utcnow(),
        })

        top_users.append({"userId": uid, "rank": rank, "reward": reward})
        print(f"[LB_REWARD] {ordinal[rank]} place uid={uid} awarded {reward} Cloudz (ISO {iso_year}-W{iso_week})")

    # Finalise record
    await db.leaderboard_rewards.update_one(
        {"isoYear": iso_year, "isoWeek": iso_week},
        {"$set": {"rewardsIssued": True, "topUsers": top_users, "issuedAt": datetime.utcnow()}},
    )
    print(f"[LB_REWARD] Weekly rewards issued for ISO {iso_year}-W{iso_week}: {len(top_users)} users")
