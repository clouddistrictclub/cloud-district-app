"""
VAPID key bootstrapper.
Priority:  env var (Railway) → MongoDB config collection → auto-generate + persist.
This ensures the production deployment never serves an empty key regardless of
whether VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY are set in the Railway dashboard.
"""
import os
import base64
import logging
from database import db

logger = logging.getLogger(__name__)
_CONFIG_DOC_ID = "vapid_keys"


async def ensure_vapid_keys() -> tuple[str, str]:
    """
    Return (public_key, private_key).
    Generates and persists to MongoDB if not already available.
    """
    # 1. Use Railway / process env vars if both are set
    pub  = os.environ.get("VAPID_PUBLIC_KEY",  "").strip()
    priv = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    if pub and priv:
        logger.info("[vapid] keys loaded from environment variables")
        return pub, priv

    # 2. Try the config collection in MongoDB
    doc = await db.app_config.find_one({"_id": _CONFIG_DOC_ID})
    if doc and doc.get("vapidPublicKey") and doc.get("vapidPrivateKey"):
        pub  = doc["vapidPublicKey"]
        priv = doc["vapidPrivateKey"]
        os.environ["VAPID_PUBLIC_KEY"]  = pub
        os.environ["VAPID_PRIVATE_KEY"] = priv
        logger.info("[vapid] keys loaded from MongoDB app_config")
        return pub, priv

    # 3. Generate fresh keys and persist to MongoDB
    from py_vapid import Vapid
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    v = Vapid()
    v.generate_keys()

    pub_bytes = v.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    pub       = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()
    priv      = v.private_pem().decode().strip()

    await db.app_config.update_one(
        {"_id": _CONFIG_DOC_ID},
        {"$set": {"vapidPublicKey": pub, "vapidPrivateKey": priv}},
        upsert=True,
    )
    os.environ["VAPID_PUBLIC_KEY"]  = pub
    os.environ["VAPID_PRIVATE_KEY"] = priv
    logger.info("[vapid] keys generated and persisted to MongoDB app_config")
    return pub, priv
