"""HomeScout FastAPI application factory and process entry point."""

from __future__ import annotations

import logging
import re
import secrets
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import error_response, register_error_handlers
from app.core.logging import configure_logging
from app.db.session import create_database_engine, create_session_factory
from app.services.ai_provider import AiProviderClient
from app.services.daraja import DarajaClient

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
http_logger = logging.getLogger("homescout.http")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an isolated app instance; schema creation is handled only by Alembic."""

    runtime_settings = settings or get_settings()
    configure_logging(runtime_settings)
    engine: Engine = create_database_engine(runtime_settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title=runtime_settings.app_name,
        summary="HomeScout Kenya API foundation",
        description="Versioned API scaffold. Product features are added only in authorized phases.",
        version="0.1.0",
        docs_url="/docs" if runtime_settings.docs_enabled else None,
        redoc_url="/redoc" if runtime_settings.docs_enabled else None,
        openapi_url="/openapi.json" if runtime_settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = runtime_settings
    app.state.daraja_client = DarajaClient(runtime_settings)
    app.state.assistant_client = AiProviderClient(runtime_settings)
    app.state.db_engine = engine
    app.state.session_factory = create_session_factory(engine)
    configured_signing_key = (
        runtime_settings.auth_signing_key.get_secret_value()
        if runtime_settings.auth_signing_key
        else ""
    )
    if not configured_signing_key:
        # Ephemeral signing is safe only for local development and isolated tests.
        if runtime_settings.environment not in {"development", "test"}:
            raise ValueError("A configured signing key is required outside development and tests.")
        configured_signing_key = secrets.token_urlsafe(48)
    app.state.auth_signing_key = configured_signing_key
    register_error_handlers(app)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unavailable")
        http_logger.error(
            "unhandled_request_error error_type=%s request_id=%s",
            type(exc).__name__,
            request_id,
        )
        return error_response(
            request,
            status_code=500,
            code="internal_error",
            message="An unexpected error occurred.",
        )

    if runtime_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=runtime_settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "X-Request-ID"],
        )

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        supplied_id = request.headers.get("X-Request-ID", "").strip()
        request_id = supplied_id if REQUEST_ID_PATTERN.fullmatch(supplied_id) else uuid4().hex
        request.state.request_id = request_id
        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        response.headers["X-Request-ID"] = request_id
        http_logger.info(
            "request_complete method=%s status=%d duration_ms=%.1f request_id=%s",
            request.method,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response

    app.include_router(api_router)
    return app


app = create_app()
