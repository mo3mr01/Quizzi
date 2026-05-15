import logging

import httpx
from fastapi import Header, HTTPException

from app.core.config import settings
from app.core.context import user_id_var

logger = logging.getLogger("quiz_api")


async def verify_token(authorization: str) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    token = authorization.removeprefix("Bearer ")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.supabase_key,
                },
            )
    except httpx.TimeoutException:
        logger.error("Supabase auth request timed out")
        raise HTTPException(status_code=503, detail="Authentication service unavailable")
    except httpx.RequestError as e:
        logger.error("Supabase auth request failed: %s", e)
        raise HTTPException(status_code=503, detail="Authentication service unavailable")

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_data = resp.json()
    user_id = user_data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return user_data


async def get_current_user(authorization: str = Header(...)) -> str:
    user_data = await verify_token(authorization)
    uid = user_data["id"]
    user_id_var.set(uid)
    return uid
