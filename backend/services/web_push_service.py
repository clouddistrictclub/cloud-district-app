"""
Web Push Notification service using VAPID + pywebpush.
Separate from the Expo mobile push in order_service.py.
"""
import os
import json
import logging
from datetime import datetime
from database import db
from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY  = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS      = {"sub": "mailto:admin@clouddistrict.club"}


async def send_web_push(user_id: str, payload: dict) -> int:
    """
    Send a Web Push notification to all active browser subscriptions for user_id.

    payload shape:
        { title: str, body: str, icon?: str, url?: str }

    Returns number of successful sends.
    Automatically removes expired/invalid (404/410) subscriptions.
    """
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        logger.debug("[web_push] VAPID keys not configured — skipping")
        return 0

    subs = await db.push_subscriptions.find(
        {"userId": user_id},
        {"_id": 1, "endpoint": 1, "keys": 1},
    ).to_list(20)

    if not subs:
        return 0

    sent = 0
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys":     sub["keys"],
                },
                data=json.dumps(payload),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS,
            )
            sent += 1
        except WebPushException as e:
            if e.response is not None and e.response.status_code in (404, 410):
                await db.push_subscriptions.delete_one({"_id": sub["_id"]})
                logger.info(f"[web_push] Removed expired subscription for {user_id}")
            else:
                logger.warning(f"[web_push] Send failed for {user_id}: {e}")
        except Exception as e:
            logger.error(f"[web_push] Unexpected error for {user_id}: {e}")

    return sent
