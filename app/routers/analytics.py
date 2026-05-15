import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth import get_current_user
from app.core.config import settings
from app.schemas.quiz import TrackEventRequest, TrackEventResponse

logger = logging.getLogger("quiz_api")

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/track-event", response_model=TrackEventResponse)
async def track_event(
    body: TrackEventRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    auth_header = request.headers.get("authorization", "")
    user_token = auth_header.removeprefix("Bearer ")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.supabase_url}/rest/v1/analytics_events",
                headers={
                    "apikey": settings.supabase_key,
                    "Authorization": f"Bearer {user_token}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json={
                    "user_id": user_id,
                    "event_name": body.event_name,
                    "metadata": body.metadata,
                },
            )
            resp.raise_for_status()
    except httpx.TimeoutException:
        logger.error("Analytics tracking timed out for user=%s event=%s", user_id, body.event_name)
    except httpx.RequestError as e:
        logger.error("Analytics tracking failed for user=%s event=%s: %s", user_id, body.event_name, e)

    return TrackEventResponse()
