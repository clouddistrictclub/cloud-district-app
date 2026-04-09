"""
Web Push subscription management endpoints.
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import db
from auth import get_current_user

router = APIRouter()

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
print("VAPID KEY:", VAPID_PUBLIC_KEY)


class PushSubscriptionBody(BaseModel):
    endpoint:  str
    keys:      dict
    userAgent: Optional[str] = ""


@router.get("/push/vapid-public-key")
async def get_vapid_public_key():
    """Return the VAPID public key so the browser can subscribe.
    Reads from os.environ at request time — always reflects the bootstrapped value."""
    key = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
    print("VAPID KEY (request-time):", key[:20] + "..." if key else "EMPTY")
    return {"vapidPublicKey": key}


@router.post("/push/subscribe")
async def subscribe_push(sub: PushSubscriptionBody, user=Depends(get_current_user)):
    """
    Store or upsert a Web Push subscription for the authenticated user.
    Upserted by endpoint so re-subscribing the same browser is idempotent.
    """
    user_id = str(user["_id"])
    if not sub.endpoint or not sub.keys.get("p256dh") or not sub.keys.get("auth"):
        raise HTTPException(status_code=400, detail="Invalid push subscription — missing endpoint or keys")

    await db.push_subscriptions.update_one(
        {"endpoint": sub.endpoint},
        {
            "$set": {
                "userId":    user_id,
                "endpoint":  sub.endpoint,
                "keys":      sub.keys,
                "userAgent": sub.userAgent or "",
                "updatedAt": datetime.utcnow(),
            },
            "$setOnInsert": {"createdAt": datetime.utcnow()},
        },
        upsert=True,
    )
    return {"message": "Subscribed"}


@router.post("/push/unsubscribe")
async def unsubscribe_push(sub: PushSubscriptionBody, user=Depends(get_current_user)):
    """Remove a Web Push subscription."""
    user_id = str(user["_id"])
    await db.push_subscriptions.delete_one({"endpoint": sub.endpoint, "userId": user_id})
    return {"message": "Unsubscribed"}
