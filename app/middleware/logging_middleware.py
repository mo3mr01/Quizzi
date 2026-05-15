import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.context import generate_request_id, request_id_var, user_id_var

logger = logging.getLogger("quiz_api")

_request_timings: dict[str, dict] = {}
_prometheus_style = False


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = generate_request_id()
        request_id_var.set(rid)
        user_id_var.set("")

        request.state.request_id = rid
        start = time.time()

        response = await call_next(request)

        duration = time.time() - start
        query = str(request.url.query) if request.url.query else ""
        path = request.url.path

        uid = user_id_var.get() or "-"

        logger.info(
            "%s %s%s %s | %.3fs | rid=%s uid=%s",
            request.method,
            path,
            f"?{query}" if query else "",
            response.status_code,
            duration,
            rid,
            uid,
        )

        response.headers["X-Request-ID"] = rid

        return response
