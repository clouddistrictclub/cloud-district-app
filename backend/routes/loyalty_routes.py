from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth import get_current_user
from models.schemas import TierRedeemRequest, LOYALTY_TIERS
from services.loyalty_service import (
    log_cloudz_transaction, calculate_streak, get_streak_bonus, resolve_tier,
    process_daily_checkin, issue_weekly_leaderboard_rewards,
)
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List

router = APIRouter()


@router.get("/loyalty/tiers")
async def get_loyalty_tiers(user=Depends(get_current_user)):
    user_points = user.get("loyaltyPoints", 0)
    tiers = []
    for tier in LOYALTY_TIERS:
        tiers.append({
            **tier,
            "unlocked": user_points >= tier["pointsRequired"],
            "pointsNeeded": max(0, tier["pointsRequired"] - user_points),
        })
    return {"userPoints": user_points, "tiers": tiers}


@router.post("/loyalty/redeem")
async def redeem_tier(req: TierRedeemRequest, user=Depends(get_current_user)):
    tier = next((t for t in LOYALTY_TIERS if t["id"] == req.tierId), None)
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")

    user_points = user.get("loyaltyPoints", 0)
    if user_points < tier["pointsRequired"]:
        raise HTTPException(status_code=400, detail="Not enough points to redeem this tier")

    existing = await db.loyalty_rewards.find_one({
        "userId": str(user["_id"]),
        "tierId": req.tierId,
        "used": False,
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already have an active reward for this tier. Use it at checkout first.")

    await log_cloudz_transaction(
        str(user["_id"]), "tier_redemption", -tier["pointsRequired"],
        f"Redeemed {tier['name']} (${tier['reward']:.2f} off)",
        f"Tier redemption: {tier['name']} for ${tier['reward']:.2f} off",
    )

    reward_doc = {
        "userId": str(user["_id"]),
        "tierId": tier["id"],
        "tierName": tier["name"],
        "pointsSpent": tier["pointsRequired"],
        "rewardAmount": tier["reward"],
        "used": False,
        "createdAt": datetime.utcnow(),
    }
    result = await db.loyalty_rewards.insert_one(reward_doc)

    return {
        "message": f"Redeemed {tier['name']} for ${tier['reward']:.2f} off!",
        "rewardId": str(result.inserted_id),
        "rewardAmount": tier["reward"],
        "pointsSpent": tier["pointsRequired"],
        "remainingPoints": user_points - tier["pointsRequired"],
    }


@router.get("/loyalty/rewards")
async def get_active_rewards(user=Depends(get_current_user)):
    rewards = await db.loyalty_rewards.find({
        "userId": str(user["_id"]),
        "used": False,
    }).to_list(100)
    return [
        {
            "id": str(r["_id"]),
            "tierId": r["tierId"],
            "tierName": r["tierName"],
            "rewardAmount": r["rewardAmount"],
            "pointsSpent": r["pointsSpent"],
            "createdAt": r["createdAt"].isoformat() if isinstance(r["createdAt"], datetime) else r["createdAt"],
        }
        for r in rewards
    ]


@router.get("/loyalty/history")
async def get_redemption_history(user=Depends(get_current_user)):
    rewards = await db.loyalty_rewards.find({
        "userId": str(user["_id"]),
    }).sort("createdAt", -1).to_list(100)
    return [
        {
            "id": str(r["_id"]),
            "tierId": r["tierId"],
            "tierName": r["tierName"],
            "rewardAmount": r["rewardAmount"],
            "pointsSpent": r["pointsSpent"],
            "used": r["used"],
            "createdAt": r["createdAt"].isoformat() if isinstance(r["createdAt"], datetime) else r["createdAt"],
        }
        for r in rewards
    ]


@router.get("/loyalty/ledger")
async def get_cloudz_ledger(user=Depends(get_current_user)):
    entries = await db.cloudz_ledger.find(
        {"userId": str(user["_id"])}, {"_id": 0}
    ).sort("createdAt", -1).to_list(200)
    for e in entries:
        if isinstance(e.get("createdAt"), datetime):
            e["createdAt"] = e["createdAt"].isoformat()
    return entries


@router.get("/loyalty/streak")
async def get_user_streak(user=Depends(get_current_user)):
    user_id = str(user["_id"])
    streak = await calculate_streak(user_id)
    bonus = get_streak_bonus(streak)
    next_bonus = get_streak_bonus(streak + 1)
    now = datetime.utcnow()
    iso_year, iso_week = now.isocalendar()[:2]
    current_weekday = now.isocalendar()[2]
    days_left = 7 - current_weekday
    return {
        "streak": streak,
        "currentBonus": bonus,
        "nextBonus": next_bonus,
        "daysUntilExpiry": days_left,
        "isoWeek": iso_week,
        "isoYear": iso_year,
    }


@router.get("/leaderboard")
async def get_leaderboard(user=Depends(get_current_user)):
    projection = {"_id": 1, "firstName": 1, "lastName": 1, "loyaltyPoints": 1, "referralCount": 1}

    # ── DIAGNOSTIC BLOCK ─────────────────────────────────────────────────────
    raw_id   = user["_id"]
    current_uid = str(raw_id)
    user_pts = user.get("loyaltyPoints", 0) or 0
    user_refs = user.get("referralCount", 0) or 0
    print("[LB] ===== LEADERBOARD REQUEST =====")
    print(f"[LB] current_uid={current_uid!r}  type={type(raw_id).__name__}")
    print(f"[LB] loyaltyPoints={user_pts}  referralCount={user_refs}")
    # ─────────────────────────────────────────────────────────────────────────

    by_points_raw    = await db.users.find({}, projection).sort("loyaltyPoints", -1).limit(20).to_list(20)
    by_referrals_raw = await db.users.find({}, projection).sort("referralCount", -1).limit(20).to_list(20)

    # Diagnostic: show every raw uid in the top-20 and whether it matches
    raw_uids_pts = [str(d["_id"]) for d in by_points_raw]
    in_top20_pts = current_uid in raw_uids_pts
    print(f"[LB] byPoints raw count={len(by_points_raw)}, current_uid in raw={in_top20_pts}")
    if not in_top20_pts:
        for i, u in enumerate(raw_uids_pts):
            print(f"[LB]   byPoints[{i}] uid={u!r}  pts={by_points_raw[i].get('loyaltyPoints', 0)}")

    # Load yesterday's snapshot for rank movement calculation
    now = datetime.utcnow()
    iso_year, iso_week = now.isocalendar()[:2]

    # Issue weekly rewards if this is the first leaderboard request of a new ISO week
    await issue_weekly_leaderboard_rewards(iso_year, iso_week)

    yesterday_midnight = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_snap = await db.leaderboard_snapshots.find_one({"date": yesterday_midnight})
    prev_ranks: dict = {}
    if yesterday_snap:
        for r in yesterday_snap.get("rankings", []):
            prev_ranks[r["userId"]] = r["rank"]

    def build_entry(doc, rank):
        first = doc.get("firstName", "")
        last  = doc.get("lastName", "")
        display = f"{first} {last[0]}." if last else first
        pts      = doc.get("loyaltyPoints", 0) or 0
        tier_name, tier_color = resolve_tier(pts)
        uid      = str(doc["_id"])
        is_me    = uid == current_uid
        prev_rank = prev_ranks.get(uid)
        movement  = (prev_rank - rank) if prev_rank is not None else None
        return {
            "rank":          rank,
            "displayName":   display,
            "points":        pts,
            "referralCount": doc.get("referralCount", 0) or 0,
            "tier":          tier_name,
            "tierColor":     tier_color,
            "isCurrentUser": is_me,
            "movement":      movement,
        }

    by_points    = [build_entry(d, i + 1) for i, d in enumerate(by_points_raw)]
    by_referrals = [build_entry(d, i + 1) for i, d in enumerate(by_referrals_raw)]

    # ── ALWAYS INCLUDE CURRENT USER IN byPoints ───────────────────────────────
    if not any(e["isCurrentUser"] for e in by_points):
        ledger_count = await db.cloudz_ledger.count_documents({"userId": current_uid})
        has_activity = user_pts > 0 or ledger_count > 0
        print(f"[LB] byPoints: user NOT found. pts={user_pts} ledger_entries={ledger_count} has_activity={has_activity}")
        if has_activity:
            rank_above = await db.users.count_documents({"loyaltyPoints": {"$gt": user_pts}})
            user_rank  = rank_above + 1
            appended   = build_entry(user, user_rank)
            print(f"[LB] byPoints: appending user rank={user_rank} isCurrentUser={appended['isCurrentUser']} pts={appended['points']}")
            by_points.append(appended)
    else:
        print("[LB] byPoints: current user found in top-20 OK")

    # ── ALWAYS INCLUDE CURRENT USER IN byReferrals ────────────────────────────
    if not any(e["isCurrentUser"] for e in by_referrals):
        if user_refs > 0:
            rank_above = await db.users.count_documents({"referralCount": {"$gt": user_refs}})
            user_rank  = rank_above + 1
            appended   = build_entry(user, user_rank)
            print(f"[LB] byReferrals: appending user rank={user_rank} isCurrentUser={appended['isCurrentUser']}")
            by_referrals.append(appended)

    # ── FINAL PAYLOAD SUMMARY ─────────────────────────────────────────────────
    final_pts_any = any(e["isCurrentUser"] for e in by_points)
    final_ref_any = any(e["isCurrentUser"] for e in by_referrals)
    print(f"[LB] FINAL byPoints={len(by_points)} entries, any isCurrentUser={final_pts_any}")
    print(f"[LB] FINAL byReferrals={len(by_referrals)} entries, any isCurrentUser={final_ref_any}")
    if final_pts_any:
        me = next(e for e in by_points if e["isCurrentUser"])
        print(f"[LB] Current user entry: rank={me['rank']} pts={me['points']} isCurrentUser={me['isCurrentUser']}")
    print("[LB] ===== END =====")
    # ─────────────────────────────────────────────────────────────────────────

    return {
        "byPoints":    by_points,
        "byReferrals": by_referrals,
    }


@router.post("/loyalty/check-in")
async def daily_check_in(user=Depends(get_current_user)):
    user_id = str(user["_id"])
    result = await process_daily_checkin(user_id)
    return result
