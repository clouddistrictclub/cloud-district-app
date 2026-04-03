import asyncio
import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from limiter import limiter

from database import client, db, UPLOADS_DIR
from auth import SECRET_KEY, ALGORITHM
from services.order_service import migrate_base64_images, migrate_catalog_images, cleanup_test_users, expire_pending_orders_loop, leaderboard_snapshot_loop, chat_manager
from routes.auth_routes import router as auth_router
from routes.user_routes import router as user_router
from routes.product_routes import router as product_router
from routes.order_routes import router as order_router
from routes.loyalty_routes import router as loyalty_router
from routes.admin_routes import router as admin_router

import jwt
from bson import ObjectId
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Cloud District Club API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request, call_next):
    response = await call_next(request)
    return response


# ==================== REGISTER ROUTERS ====================

api_prefix = "/api"

app.include_router(auth_router,    prefix=api_prefix)
app.include_router(user_router,    prefix=api_prefix)
app.include_router(product_router, prefix=api_prefix)
app.include_router(order_router,   prefix=api_prefix)
app.include_router(loyalty_router, prefix=api_prefix)
app.include_router(admin_router,   prefix=api_prefix)


# ==================== STATIC FILES ====================

app.mount("/api/uploads/products", StaticFiles(directory=str(UPLOADS_DIR)), name="product-uploads")


# ==================== HEALTH CHECKS ====================

@app.get("/")
def root():
    return {"status": "Cloud District API running"}


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


@app.get("/api/debug/version")
async def debug_version():
    from datetime import datetime, timezone
    return {
        "version": "REFERRAL_SYSTEM_V2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/debug/env")
async def debug_env():
    from datetime import datetime, timezone
    mongo_uri = os.environ.get("MONGO_URL", "NOT_SET")
    db_name = db.name
    users_count = await db.users.count_documents({})
    orders_count = await db.orders.count_documents({})
    return {
        "version": "REFERRAL_SYSTEM_V2",
        "mongo_uri": mongo_uri,
        "db_name": db_name,
        "users_count": users_count,
        "orders_count": orders_count,
    }


@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}


# ==================== WEBSOCKET (must be on app, not router) ====================

@app.websocket("/api/ws/chat/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: str, token: str = ""):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await chat_manager.connect(chat_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")

            if msg_type == "typing":
                await chat_manager.broadcast(chat_id, {
                    "type": "typing",
                    "senderId": user_id,
                    "senderName": user.get("name", user.get("email", "User")),
                    "isTyping": data.get("isTyping", False),
                })
                continue

            if msg_type == "read":
                await db.chat_messages.update_many(
                    {"chatId": chat_id, "senderId": {"$ne": user_id}, "readAt": {"$exists": False}},
                    {"$set": {"readAt": datetime.utcnow().isoformat(), "readBy": user_id}},
                )
                await chat_manager.broadcast(chat_id, {
                    "type": "read",
                    "readBy": user_id,
                    "readAt": datetime.utcnow().isoformat(),
                })
                continue

            msg_text = data.get("message", "").strip()
            if not msg_text:
                continue
            msg_doc = {
                "type": "message",
                "chatId": chat_id,
                "senderId": user_id,
                "senderName": user.get("name", user.get("email", "User")),
                "isAdmin": user.get("isAdmin", False),
                "message": msg_text,
                "createdAt": datetime.utcnow().isoformat(),
            }
            await db.chat_messages.insert_one({**msg_doc})
            await db.chat_sessions.update_one(
                {"chatId": chat_id},
                {"$set": {
                    "chatId": chat_id,
                    "userId": chat_id.replace("chat_", ""),
                    "lastMessage": msg_text,
                    "lastMessageAt": datetime.utcnow().isoformat(),
                    "updatedAt": datetime.utcnow().isoformat(),
                }, "$setOnInsert": {"createdAt": datetime.utcnow().isoformat()}},
                upsert=True,
            )
            msg_doc.pop("_id", None)
            await chat_manager.broadcast(chat_id, msg_doc)
    except WebSocketDisconnect:
        chat_manager.disconnect(chat_id, websocket)


# ==================== STARTUP / SHUTDOWN ====================

@app.on_event("startup")
async def startup_migrate():
    mongo_uri = os.environ.get("MONGO_URL", "NOT_SET")
    print(f"STARTUP: MONGO_URI = {mongo_uri}")
    print(f"STARTUP: DB_NAME = {db.name}")
    logger.info(f"STARTUP: MONGO_URI = {mongo_uri}")
    logger.info(f"STARTUP: DB_NAME = {db.name}")
    await migrate_base64_images()
    await migrate_catalog_images()
    await cleanup_test_users()
    asyncio.create_task(expire_pending_orders_loop())
    asyncio.create_task(leaderboard_snapshot_loop())


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
