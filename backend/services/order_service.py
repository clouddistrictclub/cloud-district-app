from database import db, UPLOADS_DIR
from bson import ObjectId
from datetime import datetime
import base64
import uuid
import asyncio
import logging
import httpx

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
