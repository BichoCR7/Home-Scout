"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.admin_operations import router as admin_operations_router
from app.api.v1.endpoints.assistant import router as assistant_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.collaboration import router as collaboration_router
from app.api.v1.endpoints.communications import router as communications_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.locations import router as locations_router
from app.api.v1.endpoints.marketplace import router as marketplace_router
from app.api.v1.endpoints.payments import router as payments_router
from app.api.v1.endpoints.personal_hub import router as personal_hub_router
from app.api.v1.endpoints.properties import router as properties_router
from app.api.v1.endpoints.services import router as services_router
from app.api.v1.endpoints.smartrent import router as smartrent_router
from app.api.v1.endpoints.trust import router as trust_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(assistant_router)
api_router.include_router(locations_router)
api_router.include_router(properties_router)
api_router.include_router(marketplace_router)
api_router.include_router(auth_router)
api_router.include_router(communications_router)
api_router.include_router(collaboration_router)
api_router.include_router(admin_router)
api_router.include_router(admin_operations_router)
api_router.include_router(personal_hub_router)
api_router.include_router(smartrent_router)
api_router.include_router(services_router)
api_router.include_router(trust_router)
api_router.include_router(payments_router)
