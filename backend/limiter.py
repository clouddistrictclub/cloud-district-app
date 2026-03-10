from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


limiter = Limiter(key_func=get_remote_address)


def get_user_id_or_ip(request: Request) -> str:
    """Use authenticated user ID as key; fall back to IP for unauthenticated requests."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        try:
            import jwt, os
            payload = jwt.decode(token, os.environ.get("JWT_SECRET_KEY", ""), algorithms=["HS256"])
            uid = payload.get("sub")
            if uid:
                return f"user:{uid}"
        except Exception:
            pass
    return get_remote_address(request)
