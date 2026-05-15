import logging
from datetime import date

import httpx

from app.core.config import settings

logger = logging.getLogger("quiz_api")


async def check_and_increment_quiz_usage(user_id: str) -> bool:
    today = date.today()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.supabase_url}/rest/v1/rpc/check_and_increment_quiz_usage",
                headers={
                    "apikey": settings.supabase_service_key,
                    "Authorization": f"Bearer {settings.supabase_service_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "p_user_id": user_id,
                    "p_date": today.isoformat(),
                    "p_max_count": settings.daily_quiz_limit,
                },
            )
    except httpx.TimeoutException:
        logger.error("Supabase usage check timed out for user=%s", user_id)
        raise RuntimeError("Usage check timed out")
    except httpx.RequestError as e:
        logger.error("Supabase usage check failed for user=%s: %s", user_id, e)
        raise RuntimeError("Usage check failed")

    if resp.status_code == 200:
        result = resp.json()
        allowed = result.get("allowed", False)
        current_count = result.get("current_count", 0)
        logger.info(
            "Quiz usage for user=%s date=%s: count=%d allowed=%s",
            user_id, today.isoformat(), current_count, allowed,
        )
        return allowed

    logger.error(
        "Usage check returned unexpected status for user=%s: status=%d body=%s",
        user_id, resp.status_code, resp.text,
    )
    raise RuntimeError("Usage check failed")


async def get_usage_stats(user_id: str) -> dict:
    today = date.today()
    current_count = 0

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.supabase_url}/rest/v1/quiz_usage",
                params={
                    "user_id": f"eq.{user_id}",
                    "date": f"eq.{today.isoformat()}",
                    "select": "count",
                },
                headers={
                    "apikey": settings.supabase_service_key,
                    "Authorization": f"Bearer {settings.supabase_service_key}",
                    "Prefer": "count=exact",
                },
            )

        if resp.status_code == 200:
            cr = resp.headers.get("content-range", "0-0/0")
            current_count = int(cr.split("/")[-1])
    except httpx.RequestError as e:
        logger.error("Failed to fetch usage stats for user=%s: %s", user_id, e)

    return {
        "date": today.isoformat(),
        "used": current_count,
        "limit": settings.daily_quiz_limit,
        "remaining": max(0, settings.daily_quiz_limit - current_count),
    }
