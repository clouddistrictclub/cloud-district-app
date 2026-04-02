from database import db, UPLOADS_DIR
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timedelta
from fastapi import HTTPException
import base64
import uuid
import asyncio
import logging
import math
import httpx
from services.loyalty_service import log_cloudz_transaction, maybe_award_streak_bonus, check_and_unlock_referral_reward

logger = logging.getLogger(__name__)


def _save_base64_image(b64: str) -> str:
    """Decode a data-URI base64 image, write to disk, return the /api/uploads/... URL."""
    header, encoded = b64.split(",", 1)
    mime = header.split(";")[0].split(":")[1]
    ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
    ext = ext_map.get(mime, ".jpg")
    raw = base64.b64decode(encoded)
    filename = f"{uuid.uuid4().hex}{ext}"
    (UPLOADS_DIR / filename).write_bytes(raw)
    return f"/api/uploads/products/{filename}"


async def migrate_catalog_images():
    """
    Production startup migration – applies EXACT verified image URLs for CLIO and CLR.
    Also replaces /api/uploads/ local paths with CDN equivalents for known model groups.
    SAFE to run multiple times (idempotent).
    """

    # ── CLIO Platinum 50K: flavor-specific images (verified HTTP 200) ─────────
    CLIO_IMAGES = {
        "Code Red":             "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-code-red.webp",
        "Cool Mint":            "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-cool-mint.webp",
        "White Peach Raspberry":"https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-white-peach-raspberry.webp",
        "Dragonfruit Lemonade": "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-dragonfruit-lemonade.webp",
        "Fcuking Fab":          "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-fcuking-fab.webp",
        "Peach Slush":          "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-peach-slush.webp",
        "Sour Watermelon Drop": "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-sour-watermelon-drop.webp",
        "Strawberry B-Burst":   "https://bigmosmokeshop.com/wp-content/uploads/2026/02/clio-strawberry-bburst.webp",
    }
    for flavor, url in CLIO_IMAGES.items():
        await db.products.update_many(
            {"brandName": "Geek Bar", "model": "CLIO Platinum 50K", "flavor": flavor},
            {"$set": {"image": url}},
        )

    # ── CLR 50K: flavor-specific images (verified HTTP 200) ──────────────────
    CLR_IMAGES = {
        "Sour Apple Ice":   "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Sour-Apple-Ice.jpg",
        "Sour Gush":        "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Sour-Gush.jpg",
        "Sour Strawberry":  "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Sour-Strawberry.jpg",
        "Amazon Lemonade":  "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Amazon-Lemonade.jpg",
        "Banana Ice":       "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Banana-Ice.jpg",
        "Strazz":           "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Strazz.jpg",
        "Triple Berry Ice": "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Triple-Berry-Ice.jpg",
        "Watermelon Ice":   "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Watermelon-Ice.jpg",
        "White Gummy":      "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-White-Gummy.jpg",
        "Blue Rancher":     "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Blue-Rancher.jpg",
        "Blue Razz Ice":    "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Blue-Razz-Ice.jpg",
        "Cool Mint":        "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Cool-Mint.jpg",
        "Miami Mint":       "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Mint-Mint.jpg",
        "Peach Berry":      "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Peach-Berry.jpg",
        "Pineapple Savers": "https://ebcreate.store/cdn/shop/files/Geek-Bar-CLR-50K-Pineapple-Savers.jpg",
    }
    for flavor, url in CLR_IMAGES.items():
        await db.products.update_many(
            {"brandName": "Geek Bar", "model": "CLR 50K", "flavor": flavor},
            {"$set": {"image": url}},
        )

    # ── Replace any remaining /api/uploads/ paths with CDN for known models ──
    # Only replaces broken local paths – never overwrites a valid CDN URL
    LOCAL_UPLOAD_QUERY = {"image": {"$regex": "^/api/uploads/"}}
    MODEL_CDN_MAP = {
        # (brandName, model)   → CDN URL
        ("Geek Bar", "Pulse X"):          "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2539/9022/PULSE_X_01-800x800__41304.1755553340.jpg?c=2",
        ("Geek Bar", "Pulse"):            "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2490/8990/geek-bar-geek-bar-pulse-15000__33880.1717506396.jpg?c=2",
        ("Geek Bar", "Meloso Mini"):      "https://oss.geekbar.com/products/meloso-mini/flavor3.jpg",
        ("Geek Bar", "Meloso"):           "https://oss.geekbar.com/products/meloso-mini/flavor3.jpg",
        ("Geek Bar", "Meloso Max"):       "https://oss.geekbar.com/products/meloso-mini/flavor3.jpg",
        ("RAZ",      "CA6000"):           "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2399/5769/raz-ca6000-disposable-6000-puffs__71199.1713328264.jpg?c=2",
        ("RAZ",      "TN9000"):           "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2480/8471/raz-tn9000__46610.1713328462.jpg?c=2",
        ("RAZ",      "RYL 35K"):          "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2628/9490/RYL-Classic-35K-Box_Blue-Raz-Ice-800x800__55999.1738881104.jpg?c=2",
        ("RAZ",      "VUE 50K"):          None,   # handled per-type below
        ("Lost Mary","Nera 70K"):         None,   # handled per-type below
        ("Lost Mary","MT35000 Turbo"):    "https://d31ixytk8zua6i.cloudfront.net/products/mt35000/p3_product_2x.png",
    }
    VUE_KIT_IMG  = "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2807/10165/RAZ-VUE-50K-Full-Kit_00-800x800__68447.1769025029.jpg?c=2"
    VUE_POD_IMG  = "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2808/10169/VUE_Pods_Web_Square-800x800__45772.1769025312.jpg?c=2"
    NERA_POD_IMG = "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2768/10013/___77235.1760038255.png?c=2"
    NERA_KIT_IMG = "https://cdn11.bigcommerce.com/s-nlylv/images/stencil/1280x1280/products/2767/10010/___71173.1760037985.png?c=2"

    broken_prods = await db.products.find(LOCAL_UPLOAD_QUERY).to_list(500)
    for p in broken_prods:
        bn  = p.get("brandName", "")
        mod = p.get("model", "")
        pt  = p.get("productType", "")
        new_img = None

        if (bn, mod) in MODEL_CDN_MAP:
            cdn = MODEL_CDN_MAP[(bn, mod)]
            if cdn:
                new_img = cdn
            elif mod == "VUE 50K":
                new_img = VUE_KIT_IMG if pt == "kit" else VUE_POD_IMG
            elif mod == "Nera 70K":
                new_img = NERA_KIT_IMG if pt == "kit" else NERA_POD_IMG

        if new_img:
            await db.products.update_one({"_id": p["_id"]}, {"$set": {"image": new_img}})

    # ── RAZ RX50K Dew Edition: flavor-specific images (verified HTTP 200) ────
    RX50K_IMAGES = {
        "Code Green (Dew Edition)":  "https://cdn11.bigcommerce.com/s-w062o0xp7r/images/stencil/1280x1280/products/5285/20751/RAZ-RX50K-Dew-Edition-Disposable-Vape-Code-Green__53639.1764815893.jpg?c=1",
        "Code Pink (Dew Edition)":   "https://cdn11.bigcommerce.com/s-w062o0xp7r/images/stencil/1280x1280/products/5285/20747/RAZ-RX50K-Dew-Edition-Disposable-Vape-Code-Pink__54438.1764815893.jpg?c=1",
        "Code Red (Dew Edition)":    "https://cdn11.bigcommerce.com/s-w062o0xp7r/images/stencil/1280x1280/products/5285/20750/RAZ-RX50K-Dew-Edition-Disposable-Vape-Code-Red__76650.1764815893.jpg?c=1",
        "Code White (Dew Edition)":  "https://cdn11.bigcommerce.com/s-w062o0xp7r/images/stencil/1280x1280/products/5285/20748/RAZ-RX50K-Dew-Edition-Disposable-Vape-Code-White__86701.1764815893.jpg?c=1",
    }
    for flavor, url in RX50K_IMAGES.items():
        await db.products.update_many(
            {"brandName": "RAZ", "model": "RX50K", "flavor": flavor},
            {"$set": {"image": url}},
        )

    # ── Geek Bar RIA 25K: flavor-specific images (verified HTTP 200) ─────────
    RIA_IMAGES = {
        "Deep Purple":        "https://nexussmoke.com/wp-content/uploads/2025/11/Deep-Purple-Watermark-600x600.png",
        "Dualicious":         "https://nexussmoke.com/wp-content/uploads/2025/05/Dualicious-600x600.png",
        "Watermelon B-Burst": "https://nexussmoke.com/wp-content/uploads/2025/05/Watermelon_B-Pop-600x600.png",
    }
    for flavor, url in RIA_IMAGES.items():
        await db.products.update_many(
            {"brandName": "Geek Bar", "model": "RIA", "flavor": flavor},
            {"$set": {"image": url}},
        )

    logger.info("migrate_catalog_images: CLIO + CLR + local-upload replacement complete")


async def migrate_base64_images():
    # Migrate product images
    cursor = db.products.find({"image": {"$regex": "^data:image/"}})
    count = 0
    async for product in cursor:
        b64 = product["image"]
        try:
            header, encoded = b64.split(",", 1)
            mime = header.split(";")[0].split(":")[1]
            ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
            ext = ext_map.get(mime, ".jpg")
            raw = base64.b64decode(encoded)
            if len(raw) < 100:
                await db.products.update_one({"_id": product["_id"]}, {"$set": {"image": ""}})
                logging.info(f"Cleared invalid image for product {product['_id']}")
                continue
            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = UPLOADS_DIR / filename
            filepath.write_bytes(raw)
            url = f"/api/uploads/products/{filename}"
            await db.products.update_one({"_id": product["_id"]}, {"$set": {"image": url}})
            count += 1
        except Exception as e:
            await db.products.update_one({"_id": product["_id"]}, {"$set": {"image": ""}})
            logging.warning(f"Migration cleared corrupt image for product {product['_id']}: {e}")
    if count:
        logging.info(f"Migrated {count} product images from base64 to files")

    # Migrate brand images
    cursor = db.brands.find({"image": {"$regex": "^data:image/"}})
    bcount = 0
    async for brand in cursor:
        b64 = brand["image"]
        try:
            header, encoded = b64.split(",", 1)
            mime = header.split(";")[0].split(":")[1]
            ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
            ext = ext_map.get(mime, ".jpg")
            raw = base64.b64decode(encoded)
            if len(raw) < 100:
                continue
            filename = f"brand_{uuid.uuid4().hex}{ext}"
            filepath = UPLOADS_DIR / filename
            filepath.write_bytes(raw)
            url = f"/api/uploads/products/{filename}"
            await db.brands.update_one({"_id": brand["_id"]}, {"$set": {"image": url}})
            bcount += 1
        except Exception as e:
            logging.warning(f"Migration skip brand {brand['_id']}: {e}")
    if bcount:
        logging.info(f"Migrated {bcount} brand images from base64 to files")


async def expire_pending_orders_loop():
    while True:
        try:
            now = datetime.utcnow()
            expired = await db.orders.find({
                "status": "Pending Payment",
                "expiresAt": {"$lt": now},
            }, {"_id": 1, "items": 1}).to_list(1000)

            for order in expired:
                for item in order.get("items", []):
                    try:
                        await db.products.update_one(
                            {"_id": ObjectId(item["productId"])},
                            {"$inc": {"stock": item["quantity"]}}
                        )
                    except Exception:
                        pass
                await db.orders.update_one(
                    {"_id": order["_id"]},
                    {"$set": {"status": "Expired"}}
                )

            if expired:
                logging.info(f"Order expiry: expired {len(expired)} order(s)")
        except Exception as e:
            logging.error(f"Order expiry task error: {e}")

        await asyncio.sleep(300)  # run every 5 minutes


async def send_push_notification(user_id: str, title: str, body: str):
    tokens = await db.push_tokens.find({"userId": user_id}, {"_id": 0, "token": 1}).to_list(10)
    if not tokens:
        return
    messages = [
        {"to": t["token"], "sound": "default", "title": title, "body": body}
        for t in tokens if t.get("token", "").startswith("ExponentPushToken")
    ]
    if not messages:
        return
    try:
        async with httpx.AsyncClient() as client_http:
            await client_http.post(
                "https://exp.host/--/api/v2/push/send",
                json=messages,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=10,
            )
    except Exception as e:
        logger.error(f"Push notification failed: {e}")


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list] = {}

    async def connect(self, chat_id: str, websocket):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)

    def disconnect(self, chat_id: str, websocket):
        if chat_id in self.active_connections:
            self.active_connections[chat_id] = [
                ws for ws in self.active_connections[chat_id] if ws != websocket
            ]
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def broadcast(self, chat_id: str, message: dict):
        if chat_id in self.active_connections:
            for ws in self.active_connections[chat_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

    def get_active_chat_ids(self) -> list:
        return list(self.active_connections.keys())


chat_manager = ConnectionManager()


async def leaderboard_snapshot_loop():
    while True:
        try:
            now = datetime.utcnow()
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            existing = await db.leaderboard_snapshots.find_one({"date": midnight})
            if not existing:
                users = await db.users.find(
                    {}, {"_id": 1, "loyaltyPoints": 1}
                ).sort("loyaltyPoints", -1).to_list(10000)
                rankings = [
                    {"userId": str(u["_id"]), "rank": i + 1, "loyaltyPoints": u.get("loyaltyPoints", 0)}
                    for i, u in enumerate(users)
                ]
                await db.leaderboard_snapshots.insert_one({"date": midnight, "rankings": rankings})
                logging.info(f"Leaderboard snapshot taken: {len(rankings)} users")
        except Exception as e:
            logging.error(f"Leaderboard snapshot error: {e}")

        now = datetime.utcnow()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await asyncio.sleep((next_midnight - now).total_seconds())


# ==================== SHARED ORDER COMPLETION LOGIC ====================

async def handle_order_completed(order: dict):
    """Single authoritative function for all order completion rewards. Idempotent."""
    order_id = str(order["_id"])
    user_id = order["userId"]
    print("HANDLE ORDER COMPLETED START", order_id)

    # 1. PURCHASE REWARD — idempotent via loyaltyRewardIssued flag
    claimed_loyalty = await db.orders.find_one_and_update(
        {"_id": ObjectId(order_id), "loyaltyRewardIssued": {"$ne": True}},
        {"$set": {"loyaltyRewardIssued": True}},
    )
    if claimed_loyalty is not None:
        points = int(float(order.get("total") or 0)) * 3
        print("PURCHASE REWARD: awarding", points, "for order", order_id)
        await log_cloudz_transaction(
            user_id, "purchase_reward", points,
            f"Order #{order_id[:8]}", f"Purchase reward from order #{order_id}", order_id,
        )
        await maybe_award_streak_bonus(user_id, order_id)
    else:
        print("PURCHASE REWARD: already issued for order", order_id, "— skipping")

    # 2. REFERRAL ORDER REWARD — idempotent via referralRewardIssued flag
    buyer_doc = await db.users.find_one({"_id": ObjectId(user_id)}, {"referredBy": 1})
    referrer_id = buyer_doc.get("referredBy") if buyer_doc else None
    if referrer_id:
        claimed_referral = await db.orders.find_one_and_update(
            {"_id": ObjectId(order_id), "referralRewardIssued": {"$ne": True}},
            {"$set": {"referralRewardIssued": True}},
        )
        if claimed_referral is not None:
            reward = math.floor(float(order.get("total") or 0) * 0.5)
            print("REFERRAL ORDER REWARD: awarding", reward, "to referrer", referrer_id)
            try:
                referrer_doc = None
                if len(str(referrer_id)) == 24:
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
                        {"_id": referrer_obj_id}, {"$inc": {"referralRewardsEarned": reward}}
                    )
                    ref_update = await db.users.update_one(
                        {"_id": referrer_obj_id}, {"$inc": {"loyaltyPoints": reward}}
                    )
                    print(f"DB UPDATE referral_order_reward: matched={ref_update.matched_count} modified={ref_update.modified_count}")
                    updated_ref = await db.users.find_one({"_id": referrer_obj_id}, {"loyaltyPoints": 1})
                    new_ref_bal = updated_ref["loyaltyPoints"] if updated_ref else 0
                    print("UPDATED BALANCE after referral_order_reward:", new_ref_bal)
                    ledger_r = await db.cloudz_ledger.insert_one({
                        "userId": referrer_id_str,
                        "type": "referral_order_reward",
                        "amount": reward,
                        "balanceAfter": new_ref_bal,
                        "description": f"Referral order reward from order #{order_id}",
                        "orderId": order_id,
                        "createdAt": datetime.utcnow(),
                    })
                    print("LEDGER INSERTED (referral_order_reward):", ledger_r.inserted_id)
                else:
                    print("REFERRAL ORDER REWARD: referrer doc not found or reward=0 — skipping")
            except Exception as e:
                logger.error(f"[referral_order_reward] error for order {order_id}: {e}")
        else:
            print("REFERRAL ORDER REWARD: already issued for order", order_id, "— skipping")
    else:
        print("REFERRAL ORDER REWARD: no referredBy on user", user_id, "— skipping")

    # 3. REFERRAL UNLOCK — always check, fully idempotent inside
    await check_and_unlock_referral_reward(user_id)

    print("HANDLE ORDER COMPLETED COMPLETE", order_id)


async def update_order_status_shared(order_id: str, new_status: str, source: str = "unknown") -> dict:
    """
    Shared, single source of truth for all order status changes.
    Called by BOTH the web route (/orders/:id/status) and admin route (/admin/orders/:id/status).
    Idempotency is enforced inside handle_order_completed().
    """
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    old_status = order.get("status", "unknown")
    print(f"STATUS UPDATE SOURCE: {source}")
    print(f"ORDER STATUS CHANGE: {old_status} → {new_status}")

    # Cancellation: restore stock
    if new_status == "Cancelled" and old_status != "Cancelled":
        for item in order.get("items", []):
            await db.products.update_one(
                {"_id": ObjectId(item["productId"])},
                {"$inc": {"stock": item["quantity"]}}
            )
        await db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "Cancelled"}})
        asyncio.create_task(send_push_notification(
            order["userId"], "Order Cancelled",
            f"Order #{order_id[-6:].upper()} has been cancelled.",
        ))
        return {"message": "Order status updated"}

    # $5 coupon on first completion
    if new_status == "Completed" and old_status != "Completed":
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

    # Persist new status BEFORE reward logic so lifetime-spend aggregate sees this order
    await db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": new_status}})
    print(f"ORDER STATUS UPDATED: {order_id} {new_status}")

    # Reward trigger — idempotency handled inside handle_order_completed
    if new_status == "Completed":
        print("REWARD TRIGGER EXECUTED")
        await handle_order_completed(order)

    # Final balance read — confirms all writes committed before response
    final_user = await db.users.find_one(
        {"_id": ObjectId(order["userId"])}, {"loyaltyPoints": 1}
    )
    print(f"FINAL BALANCE BEFORE RESPONSE: {final_user.get('loyaltyPoints') if final_user else 'USER NOT FOUND'}")

    asyncio.create_task(send_push_notification(
        order["userId"], "Order Update",
        f"Order #{order_id[-6:].upper()} is now: {new_status}",
    ))
    return {"message": "Order status updated"}
