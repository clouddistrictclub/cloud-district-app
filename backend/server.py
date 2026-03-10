import asyncio
import logging
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from database import client, db, UPLOADS_DIR, DIST_DIR
from auth import SECRET_KEY, ALGORITHM
from services.order_service import migrate_base64_images, expire_pending_orders_loop, chat_manager
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

if (DIST_DIR / "_expo").exists():
    app.mount("/_expo", StaticFiles(directory=str(DIST_DIR / "_expo")), name="spa-expo-assets")
if (DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="spa-static-assets")


# ==================== HEALTH CHECKS ====================

@app.get("/api/health")
def api_health():
    return {"status": "ok"}


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


# ==================== SPA FALLBACK ====================

@app.get("/", include_in_schema=False)
async def serve_index():
    index_path = DIST_DIR / "index.html"
    if not index_path.is_file():
        return JSONResponse(
            {"error": "Frontend not built", "dist_dir": str(DIST_DIR), "exists": DIST_DIR.exists()},
            status_code=503
        )
    return FileResponse(str(index_path))


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    file_path = DIST_DIR / full_path
    if file_path.is_file():
        return FileResponse(str(file_path))
    index_path = DIST_DIR / "index.html"
    if not index_path.is_file():
        return JSONResponse(
            {"error": "Frontend not built", "dist_dir": str(DIST_DIR), "path": full_path},
            status_code=503
        )
    return FileResponse(str(index_path))


# ==================== STARTUP / SHUTDOWN ====================

@app.on_event("startup")
async def startup_migrate():
    await migrate_base64_images()
    asyncio.create_task(expire_pending_orders_loop())


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
