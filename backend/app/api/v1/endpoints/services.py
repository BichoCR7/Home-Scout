"""Service discovery, provider management, bookings, move planning, and maintenance APIs."""

from datetime import date
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db
from app.core.errors import ApiError
from app.models.services import ServiceOffering
from app.schemas.services import (
    BookingAction,
    BookingCreate,
    BookingHistoryResponse,
    BookingResponse,
    MaintenanceAction,
    MaintenanceAssignment,
    MaintenanceCreate,
    MaintenanceResponse,
    MoveBudgetCreate,
    MoveBudgetResponse,
    MovePlanCreate,
    MovePlanResponse,
    MoveTaskCreate,
    MoveTaskResponse,
    MoveTaskStatus,
    OrderResponse,
    ProviderImageResponse,
    ProviderProfileResponse,
    ProviderProfileSave,
    ResidentAccessCreate,
    ResidentAccessResponse,
    ResidentPropertyResponse,
    RoomSetupCreate,
    RoomSetupResponse,
    RoomSetupStatus,
    ServiceOfferingResponse,
    ServiceOfferingSave,
    ServiceReviewCreate,
    ServiceReviewResponse,
)
from app.services.authentication import AuthenticatedPrincipal
from app.services.maintenance_requests import MaintenanceService
from app.services.media_storage import LocalMediaStorage
from app.services.moving_plans import MovingPlanService
from app.services.service_bookings import ServiceBookingService
from app.services.service_catalog import ServiceCatalogService

router = APIRouter(prefix="/services", tags=["services and moving"])
catalog = ServiceCatalogService()
bookings = ServiceBookingService()
moving = MovingPlanService()
maintenance = MaintenanceService()


@router.get("/offerings", response_model=list[ServiceOfferingResponse])
def search_offerings(
    session: Annotated[Session, Depends(get_db)],
    query: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[
        str | None,
        Query(
            pattern="^(movers|cleaners|plumbers|electricians|internet_providers|furniture_providers|handymen|home_maintenance|other)$"
        ),
    ] = None,
    county_id: UUID | None = None,
    town_id: UUID | None = None,
    min_price: Annotated[float | None, Query(ge=0, le=100_000_000)] = None,
    max_price: Annotated[float | None, Query(ge=0, le=100_000_000)] = None,
    verified_only: bool = False,
    sort: Annotated[str, Query(pattern="^(newest|price_low|price_high)$")] = "newest",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> list[ServiceOfferingResponse]:
    return catalog.search_offerings(
        session,
        query=query,
        category=category,
        county_id=county_id,
        town_id=town_id,
        min_price=min_price,
        max_price=max_price,
        verified_only=verified_only,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/offerings/compare", response_model=list[ServiceOfferingResponse])
def compare_offerings(
    service_ids: Annotated[list[UUID], Query()], session: Annotated[Session, Depends(get_db)]
) -> list[ServiceOfferingResponse]:
    return catalog.compare(session, service_ids=service_ids)


@router.get("/offerings/{service_id}", response_model=ServiceOfferingResponse)
def public_offering(
    service_id: UUID, session: Annotated[Session, Depends(get_db)]
) -> ServiceOfferingResponse:
    return catalog._offering_response(
        session, catalog.public_offering(session, service_id=service_id)
    )


@router.get("/offerings/{service_id}/reviews", response_model=list[ServiceReviewResponse])
def offering_reviews(
    service_id: UUID, session: Annotated[Session, Depends(get_db)]
) -> list[ServiceReviewResponse]:
    return catalog.reviews(session, service_id=service_id)


@router.get("/providers/me", response_model=ProviderProfileResponse | None)
def my_provider_profile(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ProviderProfileResponse | None:
    return catalog.my_profile(session, user_id=principal.user_id)


@router.put("/providers/me", response_model=ProviderProfileResponse)
def save_provider_profile(
    body: ProviderProfileSave,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ProviderProfileResponse:
    return catalog.save_profile(session, user_id=principal.user_id, body=body)


@router.get("/providers/me/offerings", response_model=list[ServiceOfferingResponse])
def my_offerings(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[ServiceOfferingResponse]:
    return catalog.my_offerings(session, user_id=principal.user_id)


@router.post("/providers/me/offerings", response_model=ServiceOfferingResponse, status_code=201)
def create_offering(
    body: ServiceOfferingSave,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ServiceOfferingResponse:
    return catalog.save_offering(session, user_id=principal.user_id, offering_id=None, body=body)


@router.put("/providers/me/offerings/{service_id}", response_model=ServiceOfferingResponse)
def update_offering(
    service_id: UUID,
    body: ServiceOfferingSave,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ServiceOfferingResponse:
    return catalog.save_offering(
        session, user_id=principal.user_id, offering_id=service_id, body=body
    )


@router.get("/providers/{provider_user_id}", response_model=ProviderProfileResponse)
def provider_profile(
    provider_user_id: UUID, session: Annotated[Session, Depends(get_db)]
) -> ProviderProfileResponse:
    return catalog.public_profile(session, provider_user_id=provider_user_id)


@router.get("/providers/{provider_user_id}/offerings", response_model=list[ServiceOfferingResponse])
def provider_offerings(
    provider_user_id: UUID, session: Annotated[Session, Depends(get_db)]
) -> list[ServiceOfferingResponse]:
    catalog.public_profile(session, provider_user_id=provider_user_id)
    rows = session.scalars(
        select(ServiceOffering)
        .where(
            ServiceOffering.provider_user_id == provider_user_id,
            ServiceOffering.is_active.is_(True),
        )
        .order_by(ServiceOffering.created_at.desc())
    )
    return [catalog._offering_response(session, row) for row in rows]


@router.post("/providers/me/images", response_model=ProviderImageResponse, status_code=201)
async def upload_provider_image(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    filename: Annotated[str, Query(min_length=1, max_length=240)] = "provider-image",
    caption: Annotated[str | None, Query(max_length=300)] = None,
) -> ProviderImageResponse:
    mime_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ApiError(415, "unsupported_image", "Upload a JPEG, PNG, or WebP image.")
    maximum = request.app.state.settings.media_max_image_bytes
    contents = bytearray()
    async for chunk in request.stream():
        if len(contents) + len(chunk) > maximum:
            raise ApiError(413, "image_too_large", "The image exceeds the configured upload limit.")
        contents.extend(chunk)
    raw = bytes(contents)
    signatures = {
        "image/jpeg": raw.startswith(b"\xff\xd8\xff"),
        "image/png": raw.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP",
    }
    if not raw or not signatures[mime_type]:
        raise ApiError(
            415, "invalid_image_content", "The image content does not match its file type."
        )
    storage = LocalMediaStorage(request.app.state.settings.media_storage_dir / "service-providers")
    safe_filename = Path(filename.replace("\\", "/")).name
    return catalog.upload_image(
        session,
        user_id=principal.user_id,
        contents=raw,
        mime_type=mime_type,
        filename=safe_filename,
        caption=caption.strip() if caption else None,
        storage=storage,
    )


@router.get("/providers/{provider_user_id}/images/{image_id}")
def provider_image(
    provider_user_id: UUID,
    image_id: UUID,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    storage = LocalMediaStorage(request.app.state.settings.media_storage_dir / "service-providers")
    row, path = catalog.image(
        session, provider_user_id=provider_user_id, image_id=image_id, storage=storage
    )
    return FileResponse(
        path,
        media_type=row.content_type,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "public, max-age=3600"},
    )


@router.delete("/providers/me/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider_image(
    image_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    storage = LocalMediaStorage(request.app.state.settings.media_storage_dir / "service-providers")
    catalog.delete_image(session, user_id=principal.user_id, image_id=image_id, storage=storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bookings", response_model=BookingResponse, status_code=201)
def create_booking(
    body: BookingCreate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> BookingResponse:
    return bookings.create(
        session,
        customer_id=principal.user_id,
        body=body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/bookings", response_model=list[BookingResponse])
def my_bookings(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[BookingResponse]:
    return bookings.list_for_user(session, user_id=principal.user_id)


@router.get("/bookings/{booking_id}/history", response_model=list[BookingHistoryResponse])
def booking_history(
    booking_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[BookingHistoryResponse]:
    return bookings.history(session, user_id=principal.user_id, booking_id=booking_id)


@router.patch("/bookings/{booking_id}", response_model=BookingResponse)
def booking_action(
    booking_id: UUID,
    body: BookingAction,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> BookingResponse:
    return bookings.act(
        session,
        user_id=principal.user_id,
        booking_id=booking_id,
        body=body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/orders", response_model=list[OrderResponse])
def my_orders(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[OrderResponse]:
    return bookings.orders(session, user_id=principal.user_id)


@router.post("/bookings/{booking_id}/review", response_model=ServiceReviewResponse, status_code=201)
def review_completed_booking(
    booking_id: UUID,
    body: ServiceReviewCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ServiceReviewResponse:
    return bookings.create_review(
        session, user_id=principal.user_id, booking_id=booking_id, body=body
    )


@router.post(
    "/properties/{property_id}/residents", response_model=ResidentAccessResponse, status_code=201
)
def grant_resident_access(
    property_id: UUID,
    body: ResidentAccessCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ResidentAccessResponse:
    return maintenance.grant_resident(
        session, manager_id=principal.user_id, property_id=property_id, body=body
    )


@router.get("/properties/{property_id}/residents", response_model=list[ResidentAccessResponse])
def property_residents(
    property_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[ResidentAccessResponse]:
    return maintenance.residents(session, manager_id=principal.user_id, property_id=property_id)


@router.delete(
    "/properties/{property_id}/residents/{resident_user_id}", response_model=ResidentAccessResponse
)
def revoke_resident_access(
    property_id: UUID,
    resident_user_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ResidentAccessResponse:
    return maintenance.revoke_resident(
        session,
        manager_id=principal.user_id,
        property_id=property_id,
        resident_user_id=resident_user_id,
    )


@router.post("/maintenance", response_model=MaintenanceResponse, status_code=201)
def create_maintenance(
    body: MaintenanceCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> MaintenanceResponse:
    return maintenance.create(session, user_id=principal.user_id, body=body)


@router.get("/resident-properties", response_model=list[ResidentPropertyResponse])
def resident_properties(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[ResidentPropertyResponse]:
    return maintenance.resident_properties(session, resident_id=principal.user_id)


@router.get("/maintenance", response_model=list[MaintenanceResponse])
def list_maintenance(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[MaintenanceResponse]:
    return maintenance.list_for_user(session, user_id=principal.user_id)


@router.get("/maintenance/{request_id}", response_model=MaintenanceResponse)
def get_maintenance(
    request_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> MaintenanceResponse:
    return maintenance.get(session, user_id=principal.user_id, request_id=request_id)


@router.patch("/maintenance/{request_id}/assignment", response_model=MaintenanceResponse)
def assign_maintenance_provider(
    request_id: UUID,
    body: MaintenanceAssignment,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> MaintenanceResponse:
    return maintenance.assign(
        session,
        manager_id=principal.user_id,
        request_id=request_id,
        body=body,
        request_id_header=getattr(request.state, "request_id", None),
    )


@router.patch("/maintenance/{request_id}/actions", response_model=MaintenanceResponse)
def maintenance_action(
    request_id: UUID,
    body: MaintenanceAction,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> MaintenanceResponse:
    return maintenance.act(session, user_id=principal.user_id, request_id=request_id, body=body)


@router.get("/maintenance/{request_id}/photos/{document_id}")
def download_maintenance_photo(
    request_id: UUID,
    document_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    document = maintenance.photo_document(
        session, user_id=principal.user_id, request_id=request_id, document_id=document_id
    )
    path = LocalMediaStorage(request.app.state.settings.private_document_storage_dir).get(
        document.storage_key
    )
    if path is None:
        raise ApiError(404, "maintenance_photo_not_found", "The maintenance photo is unavailable.")
    return FileResponse(
        path,
        media_type=document.content_type,
        filename=document.original_filename,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.post("/move-plans", response_model=MovePlanResponse, status_code=201)
def create_move_plan(
    body: MovePlanCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> MovePlanResponse:
    return moving.create_plan(session, user_id=principal.user_id, body=body)


@router.get("/move-plans", response_model=list[MovePlanResponse])
def list_move_plans(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[MovePlanResponse]:
    return moving.plans(session, user_id=principal.user_id)


@router.put("/move-plans/{plan_id}", response_model=MovePlanResponse)
def update_move_plan(
    plan_id: UUID,
    body: MovePlanCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> MovePlanResponse:
    return moving.update_plan(session, user_id=principal.user_id, plan_id=plan_id, body=body)


@router.delete("/move-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_move_plan(
    plan_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    moving.delete_plan(session, user_id=principal.user_id, plan_id=plan_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/move-plans/{plan_id}/tasks", response_model=list[MoveTaskResponse])
def list_move_tasks(
    plan_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[MoveTaskResponse]:
    return moving.tasks(session, user_id=principal.user_id, plan_id=plan_id)


@router.post("/move-plans/{plan_id}/tasks", response_model=MoveTaskResponse, status_code=201)
def create_move_task(
    plan_id: UUID,
    body: MoveTaskCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> MoveTaskResponse:
    return moving.create_task(session, user_id=principal.user_id, plan_id=plan_id, body=body)


@router.patch("/move-tasks/{task_id}", response_model=MoveTaskResponse)
def update_move_task(
    task_id: UUID,
    body: MoveTaskStatus,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> MoveTaskResponse:
    return moving.update_task(session, user_id=principal.user_id, task_id=task_id, body=body)


@router.get("/move-calendar", response_model=list[MoveTaskResponse])
def move_calendar(
    start_date: date,
    end_date: date,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[MoveTaskResponse]:
    return moving.calendar(
        session, user_id=principal.user_id, start_date=start_date, end_date=end_date
    )


@router.get("/move-plans/{plan_id}/budget", response_model=list[MoveBudgetResponse])
def list_move_budget(
    plan_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[MoveBudgetResponse]:
    return moving.budget_items(session, user_id=principal.user_id, plan_id=plan_id)


@router.post("/move-plans/{plan_id}/budget", response_model=MoveBudgetResponse, status_code=201)
def add_move_budget(
    plan_id: UUID,
    body: MoveBudgetCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> MoveBudgetResponse:
    return moving.add_budget_item(session, user_id=principal.user_id, plan_id=plan_id, body=body)


@router.get("/move-plans/{plan_id}/room-setup", response_model=list[RoomSetupResponse])
def room_setup(
    plan_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[RoomSetupResponse]:
    return moving.room_items(session, user_id=principal.user_id, plan_id=plan_id)


@router.post("/move-plans/{plan_id}/room-setup", response_model=RoomSetupResponse, status_code=201)
def add_room_setup(
    plan_id: UUID,
    body: RoomSetupCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> RoomSetupResponse:
    return moving.add_room_item(session, user_id=principal.user_id, plan_id=plan_id, body=body)


@router.patch("/room-setup/{item_id}", response_model=RoomSetupResponse)
def update_room_setup(
    item_id: UUID,
    body: RoomSetupStatus,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> RoomSetupResponse:
    return moving.update_room_item(session, user_id=principal.user_id, item_id=item_id, body=body)
