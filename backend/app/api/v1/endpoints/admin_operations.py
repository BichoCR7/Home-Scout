"""Staff operations APIs; sensitive actions require capability and are audited."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db, get_settings
from app.core.config import Settings
from app.core.errors import ApiError
from app.schemas.admin_operations import (
    AccountStatusUpdate,
    ListingModerationUpdate,
    LocationStatusUpdate,
    MessageReportUpdate,
    OfferingStatusUpdate,
    ProviderPublicationUpdate,
    ServiceReviewModerationUpdate,
    SettingUpdate,
    SupportCategoryUpdate,
    SupportReply,
    SupportTicketUpdate,
)
from app.services.authentication import AuthenticatedPrincipal
from app.services.authorization import AuthorizationService
from app.services.phase10_cipher import Phase10Cipher
from app.services.platform_operations import PlatformOperationsService

router = APIRouter(prefix="/admin/operations", tags=["platform operations"])
service = PlatformOperationsService()


@router.get("/overview")
def overview(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, int]:
    _require(session, principal.user_id, "analytics:view:platform", "analytics")
    return service.overview(session)


@router.get("/users")
def users(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    q: Annotated[str, Query(max_length=120)] = "",
    status: Annotated[str | None, Query(pattern="^(pending|active|suspended|closed)$")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 30,
) -> list[dict[str, object]]:
    _require(session, principal.user_id, "user:view:basic", "users")
    return service.users(session, query=q, status=status, limit=limit)


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: UUID,
    body: AccountStatusUpdate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _require(session, principal.user_id, "user:edit:basic", "users")
    return service.update_account_status(
        session,
        actor_id=principal.user_id,
        target_id=user_id,
        status=body.status,
        current_password=body.current_password,
        reason=body.reason,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/listings")
def listings(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    status: Annotated[str | None, Query(pattern="^(clear|under_review|removed)$")] = None,
    q: Annotated[str, Query(max_length=120)] = "",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict[str, object]]:
    _require(session, principal.user_id, "listing:view:platform", "listings")
    return service.listings(session, status=status, query=q, limit=limit)


@router.patch("/listings/{property_id}/moderation")
def update_listing_moderation(
    property_id: UUID,
    body: ListingModerationUpdate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _require(session, principal.user_id, "listing:manage:platform", "listings")
    return service.update_listing_moderation(
        session,
        actor_id=principal.user_id,
        property_id=property_id,
        status=body.status,
        reason=body.reason,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/reviews/services")
def service_reviews(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    status: Annotated[str | None, Query(pattern="^(clear|under_review|removed)$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[dict[str, object]]:
    _require(session, principal.user_id, "service:manage:platform", "services")
    return service.service_reviews(session, status=status, limit=limit)


@router.patch("/reviews/services/{review_id}/moderation")
def update_service_review_moderation(
    review_id: UUID,
    body: ServiceReviewModerationUpdate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _require(session, principal.user_id, "service:manage:platform", "services")
    return service.update_service_review_moderation(
        session,
        actor_id=principal.user_id,
        review_id=review_id,
        status=body.status,
        reason=body.reason,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/services/providers")
def providers(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict[str, object]]:
    _require(session, principal.user_id, "service:manage:platform", "services")
    return service.providers(session, limit=limit)


@router.patch("/services/providers/{provider_id}/publication")
def update_provider_publication(
    provider_id: UUID,
    body: ProviderPublicationUpdate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _require(session, principal.user_id, "service:manage:platform", "services")
    return service.update_provider_publication(
        session,
        actor_id=principal.user_id,
        provider_id=provider_id,
        published=body.is_published,
        reason=body.reason,
        request_id=getattr(request.state, "request_id", None),
    )


@router.patch("/services/offerings/{offering_id}")
def update_offering(
    offering_id: UUID,
    body: OfferingStatusUpdate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _require(session, principal.user_id, "service:manage:platform", "services")
    return service.update_offering_status(
        session,
        actor_id=principal.user_id,
        offering_id=offering_id,
        active=body.is_active,
        reason=body.reason,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/locations")
def locations(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[dict[str, object]]:
    _require(session, principal.user_id, "location:manage:global", "*")
    return service.locations(session)


@router.patch("/locations/{location_type}/{location_id}")
def update_location(
    location_type: str,
    location_id: UUID,
    body: LocationStatusUpdate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _require(session, principal.user_id, "location:manage:global", "*")
    return service.update_location_status(
        session,
        actor_id=principal.user_id,
        location_type=location_type,
        location_id=location_id,
        active=body.is_active,
        reason=body.reason,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/support/tickets")
def support_tickets(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    status: Annotated[str | None, Query(pattern="^(open|waiting|closed)$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict[str, object]]:
    _require(session, principal.user_id, "support:manage:assigned", "support")
    return service.support_tickets(session, status=status, limit=limit)


@router.get("/support/tickets/{ticket_id}")
def support_ticket(
    ticket_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _require(session, principal.user_id, "support:manage:assigned", "support")
    return service.support_ticket(session, actor_id=principal.user_id, ticket_id=ticket_id)


@router.patch("/support/tickets/{ticket_id}")
def update_support_ticket(
    ticket_id: UUID,
    body: SupportTicketUpdate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _require(session, principal.user_id, "support:manage:assigned", "support")
    return service.update_support_ticket(
        session,
        actor_id=principal.user_id,
        ticket_id=ticket_id,
        values=body.model_dump(exclude_unset=True),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/support/tickets/{ticket_id}/reply")
def reply_support_ticket(
    ticket_id: UUID,
    body: SupportReply,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _require(session, principal.user_id, "support:manage:assigned", "support")
    return service.reply_support_ticket(
        session,
        actor_id=principal.user_id,
        ticket_id=ticket_id,
        body=body.body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/categories/support")
def support_categories(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[dict[str, object]]:
    _require(session, principal.user_id, "category:manage:global", "*")
    return service.categories(session)


@router.patch("/categories/support/{code}")
def update_support_category(
    code: str,
    body: SupportCategoryUpdate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _require(session, principal.user_id, "category:manage:global", "*")
    return service.update_category(
        session,
        actor_id=principal.user_id,
        code=code,
        active=body.is_active,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/settings")
def settings(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[dict[str, object]]:
    _require(session, principal.user_id, "system:manage:global", "*")
    return service.settings(session)


@router.put("/settings/{key}")
def update_setting(
    key: str,
    body: SettingUpdate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _require(session, principal.user_id, "system:manage:global", "*")
    return service.update_setting(
        session,
        actor_id=principal.user_id,
        key=key,
        value=body.value,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/audit")
def audit_events(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> list[dict[str, object]]:
    _require(session, principal.user_id, "audit:view:administrative_workflow", "operations")
    return service.audit_events(session, limit=limit, offset=offset)


@router.get("/reports/messages")
def message_reports(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict[str, object]]:
    _require(session, principal.user_id, "moderation:view:assigned", "reports", "moderation")
    return service.message_reports(session, limit=limit)


@router.get("/reports/messages/{report_id}")
def message_report_detail(
    report_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    _require(session, principal.user_id, "moderation:view:assigned", "reports", "moderation")
    return service.message_report_detail(
        session,
        actor_id=principal.user_id,
        report_id=report_id,
        cipher=Phase10Cipher(settings),
    )


@router.post("/reports/messages/{report_id}/review")
def review_message_report(
    report_id: UUID,
    body: MessageReportUpdate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    permission = (
        "moderation:reject:reported" if body.status == "closed" else "moderation:approve:reported"
    )
    _require(session, principal.user_id, permission, "reports", "moderation")
    return service.review_message_report(
        session,
        actor_id=principal.user_id,
        report_id=report_id,
        status=body.status,
        remove_message=body.remove_message,
        reason=body.reason,
        request_id=getattr(request.state, "request_id", None),
    )


def _require(
    session: Session,
    user_id: UUID,
    permission_code: str,
    scope_id: str,
    resource_scope_type: str = "administrative_workflow",
) -> None:
    if permission_code.endswith(":global"):
        resource_scope_type, scope_id = "global", "*"
    if not AuthorizationService().has_permission(
        session,
        user_id=user_id,
        permission_code=permission_code,
        resource_scope_type=resource_scope_type,
        resource_scope_id=scope_id,
    ):
        raise ApiError(
            403, "permission_denied", "You are not authorized to use this operations control."
        )
