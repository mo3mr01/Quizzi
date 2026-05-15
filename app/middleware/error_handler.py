import logging
from traceback import format_exception

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger("quiz_api")


async def validation_error_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    field = " -> ".join(str(loc) for loc in first_error.get("loc", [])) if first_error else "unknown"
    msg = first_error.get("msg", "Invalid input")
    logger.warning(
        "Validation error on %s %s | field=%s msg=%s",
        request.method, request.url.path, field, msg,
    )
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": f"Validation failed: {field} - {msg}",
        },
    )


async def http_error_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", str(detail))
    else:
        message = str(detail)

    status_code = exc.status_code
    if status_code >= 500:
        logger.error(
            "HTTP %d on %s %s | detail=%s",
            status_code, request.method, request.url.path, message,
        )

    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": message},
    )


async def global_error_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception on %s %s: %s",
        request.method, request.url.path, exc,
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
        },
    )
