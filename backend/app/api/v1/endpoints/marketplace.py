"""Saved homes, compare, alerts, search history, and property enquiries."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db, get_settings
from app.core.config import Settings
from app.schemas.marketplace import (
    PropertyAlertCreate,
    PropertyAlertResponse,
    PropertyEnquiryCreate,
    PropertyEnquiryResponse,
    PropertyEnquiryStatusUpdate,
    PropertyReportCreate,
    PropertyReportResponse,
    SearchHistoryCreate,
    SearchHistoryResponse,
)
from app.schemas.properties import (
    ListingMandateCreate,
    ListingMandateResponse,
    PropertyListResponse,
    PropertyResponse,
)
from app.services.authentication import AuthenticatedPrincipal
from app.services.marketplace import MarketplaceService
from app.services.trust_cipher import TrustCipher
from app.services.trust_safety import TrustSafetyService

router = APIRouter(prefix="/marketplace", tags=["marketplace"])
service = MarketplaceService()


@router.post(
    "/properties/{property_id}/reports",
    response_model=PropertyReportResponse,
    status_code=201,
)
def report_property(
    property_id: UUID,
    body: PropertyReportCreate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PropertyReportResponse:
    return TrustSafetyService(TrustCipher(settings)).report_listing(
        session,
        reporter_id=principal.user_id,
        property_id=property_id,
        body=body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/reports/mine", response_model=list[PropertyReportResponse])
def reports_by_me(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[PropertyReportResponse]:
    return TrustSafetyService(TrustCipher(settings)).reports_by_user(session, principal.user_id)


@router.post("/listing-mandates", response_model=ListingMandateResponse, status_code=201)
def create_listing_mandate(
    body: ListingMandateCreate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ListingMandateResponse:
    return service.create_listing_mandate(
        session,
        owner_user_id=principal.user_id,
        request=body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/listing-mandates", response_model=list[ListingMandateResponse])
def listing_mandates(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[ListingMandateResponse]:
    return service.listing_mandates(session, user_id=principal.user_id)


@router.delete("/listing-mandates/{agent_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_listing_mandate(
    agent_user_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    service.revoke_listing_mandate(
        session,
        owner_user_id=principal.user_id,
        agent_user_id=agent_user_id,
        request_id=getattr(request.state, "request_id", None),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/saved", response_model=PropertyListResponse)
def saved_properties(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PropertyListResponse:
    return service.saved(
        session,
        user_id=principal.user_id,
        include_demo=settings.environment in {"development", "test"},
    )


@router.put("/saved/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def save_property(
    property_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    service.save(
        session,
        user_id=principal.user_id,
        property_id=property_id,
        include_demo=settings.environment in {"development", "test"},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/saved/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsave_property(
    property_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    service.unsave(session, user_id=principal.user_id, property_id=property_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/compare", response_model=list[PropertyResponse])
def compare_properties(
    property_ids: list[UUID],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    include_demo: bool = False,
) -> list[PropertyResponse]:
    return service.compare(
        session,
        user_id=principal.user_id,
        property_ids=property_ids,
        include_demo=include_demo and settings.environment in {"development", "test"},
    )


@router.post("/search-history", response_model=SearchHistoryResponse, status_code=201)
def record_search(
    body: SearchHistoryCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> SearchHistoryResponse:
    return service.record_search(session, user_id=principal.user_id, request=body)


@router.get("/search-history", response_model=list[SearchHistoryResponse])
def search_history(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=30)] = 10,
) -> list[SearchHistoryResponse]:
    return service.history(session, user_id=principal.user_id, limit=limit)


@router.post("/alerts", response_model=PropertyAlertResponse, status_code=201)
def create_alert(
    body: PropertyAlertCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PropertyAlertResponse:
    return service.create_alert(session, user_id=principal.user_id, request=body)


@router.get("/alerts", response_model=list[PropertyAlertResponse])
def list_alerts(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[PropertyAlertResponse]:
    return service.alerts(session, user_id=principal.user_id)


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    service.delete_alert(session, user_id=principal.user_id, alert_id=alert_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/properties/{property_id}/enquiries",
    response_model=PropertyEnquiryResponse,
    status_code=201,
)
def create_enquiry(
    property_id: UUID,
    body: PropertyEnquiryCreate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PropertyEnquiryResponse:
    return service.create_enquiry(
        session,
        user_id=principal.user_id,
        property_id=property_id,
        request=body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/enquiries/sent", response_model=list[PropertyEnquiryResponse])
def sent_enquiries(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[PropertyEnquiryResponse]:
    return service.sent_enquiries(session, user_id=principal.user_id)


@router.get("/enquiries/received", response_model=list[PropertyEnquiryResponse])
def received_enquiries(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[PropertyEnquiryResponse]:
    return service.received_enquiries(session, user_id=principal.user_id)


@router.patch("/enquiries/{enquiry_id}", response_model=PropertyEnquiryResponse)
def update_enquiry(
    enquiry_id: UUID,
    body: PropertyEnquiryStatusUpdate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PropertyEnquiryResponse:
    return service.update_enquiry(
        session,
        user_id=principal.user_id,
        enquiry_id=enquiry_id,
        request=body,
        request_id=getattr(request.state, "request_id", None),
    )
