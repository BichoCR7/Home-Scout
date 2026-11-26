"""Liveness and database-readiness endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.errors import ApiError
from app.schemas.health import HealthLiveResponse, HealthReadyResponse
from app.services.health import HealthService

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger("homescout.health")
health_service = HealthService()


@router.get("", response_model=HealthLiveResponse, summary="Check API liveness")
def live_health() -> HealthLiveResponse:
    """Confirm that the API process is responding; this does not touch the database."""

    return HealthLiveResponse(status="ok")


@router.get("/ready", response_model=HealthReadyResponse, summary="Check database readiness")
def ready_health(session: Annotated[Session, Depends(get_db)]) -> HealthReadyResponse:
    """Confirm that the configured database accepts a simple read query."""

    try:
        health_service.database_is_ready(session)
    except SQLAlchemyError as exc:
        logger.warning("database_readiness_failed error_type=%s", type(exc).__name__)
        raise ApiError(
            status_code=503,
            code="database_unavailable",
            message="A required service is temporarily unavailable.",
        ) from None
    return HealthReadyResponse(status="ready", database="ok")
