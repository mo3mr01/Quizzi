import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth import verify_token
from app.core.config import settings
from app.schemas.quiz import OverviewResponse

logger = logging.getLogger("quiz_api")

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    try:
        user_data = await verify_token(auth_header)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    email = user_data.get("email", "")
    if not email or email != settings.admin_email:
        raise HTTPException(status_code=403, detail="Not authorized")

    return user_data["id"]


@router.get("/stats/overview", response_model=OverviewResponse)
async def get_overview(
    _user_id: str = Depends(require_admin),
):
    headers = {
        "apikey": settings.supabase_service_key,
    }

    total_users = 0
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{settings.supabase_url}/auth/v1/admin/users",
                params={"per_page": "1000"},
                headers=headers,
            )
            total_users = len(resp.json().get("users", []))
    except httpx.RequestError as e:
        logger.error("Failed to fetch user count from Supabase: %s", e)

    counts = {"quiz_generated": 0, "pdf_uploaded": 0}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for event in ["quiz_generated", "pdf_uploaded"]:
                try:
                    resp = await client.get(
                        f"{settings.supabase_url}/rest/v1/analytics_events",
                        params={"event_name": f"eq.{event}", "limit": 0},
                        headers={**headers, "Prefer": "count=exact"},
                    )
                    cr = resp.headers.get("content-range", "0-0/0")
                    counts[event] = int(cr.split("/")[-1])
                except httpx.RequestError as e:
                    logger.error("Failed to fetch event count for %s: %s", event, e)
    except httpx.RequestError as e:
        logger.error("Supabase request failed in admin stats: %s", e)

    return OverviewResponse(
        total_users=total_users,
        total_quizzes=counts.get("quiz_generated", 0),
        total_uploads=counts.get("pdf_uploaded", 0),
    )
