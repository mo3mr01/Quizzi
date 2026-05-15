import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.context import RequestContextFilter
from app.routers import health, quiz, analytics, admin
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.error_handler import (
    validation_error_handler,
    http_error_handler,
    global_error_handler,
)

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [%(request_id)s]  [%(user_id)s]  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

for handler in logging.root.handlers:
    handler.addFilter(RequestContextFilter())

logger = logging.getLogger("quiz_api")


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    settings.validate_required()
    logger.info("Required environment variables validated")

    logger.info(
        "Environment: %s | Debug: %s | Max questions: %s | Daily limit: %s | "
        "Groq timeout: %ds | Groq retries: %d | CORS: %s",
        settings.environment,
        settings.debug,
        settings.max_questions,
        settings.daily_quiz_limit,
        settings.groq_timeout_seconds,
        settings.groq_max_retries,
        settings.cors_origins,
    )

    yield

    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="AI-powered Quiz Generator from PDFs",
    version=settings.app_version,
    lifespan=lifespan,
)

allowed_origins = (
    settings.cors_origins.split(",")
    if settings.cors_origins != "*"
    else ["*"]
)

if settings.is_production and "*" in allowed_origins:
    logger.warning(
        "CORS is set to wildcard '*' in production — restrict CORS_ORIGINS "
        "to your Flutter app's domain"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=("*" not in allowed_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

MAX_BODY = settings.max_upload_bytes


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY:
        return JSONResponse(
            status_code=413,
            content={
                "success": False,
                "error": f"Request body too large (max {settings.max_upload_size_mb} MB)",
            },
        )
    return await call_next(request)


app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.add_exception_handler(Exception, global_error_handler)

app.include_router(health.router)
app.include_router(quiz.router)
app.include_router(analytics.router)
app.include_router(admin.router)
