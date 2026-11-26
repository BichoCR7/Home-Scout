"""Verification, reporting, moderation, and viewing safety APIs."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db, get_settings
from app.core.config import Settings
from app.core.errors import ApiError
from app.models.personal_hub import PrivateDocument
from app.schemas.marketplace import PropertyReportCreate, PropertyReportResponse
from app.schemas.trust import (
    SafetyReportCreate,
    SafetyReportResponse,
    TrustReportReview,
    VerificationCaseResponse,
    VerificationReview,
    VerificationSubmit,
    ViewingCreate,
    ViewingResponse,
    ViewingUpdate,
)
from app.services.authentication import AuthenticatedPrincipal
from app.services.media_storage import LocalMediaStorage
from app.services.trust_cipher import TrustCipher
from app.services.trust_safety import TrustSafetyService

router = APIRouter(prefix="/trust", tags=["trust and safety"])


def _service(settings: Settings) -> TrustSafetyService:
    return TrustSafetyService(TrustCipher(settings))


def _document_response(
    document: PrivateDocument, settings: Settings, cipher: TrustCipher
) -> Response:
    file_path = LocalMediaStorage(settings.private_document_storage_dir).get(document.storage_key)
    if file_path is None:
        raise ApiError(404, "document_missing", "The private document file is no longer available.")
    headers = {
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    }
    if document.storage_encrypted:
        return Response(
            content=cipher.decrypt_document(
                document.owner_user_id, document.id, file_path.read_bytes()
            ),
            media_type=document.content_type,
            headers={
                **headers,
                "Content-Disposition": f'attachment; filename="{document.original_filename}"',
            },
        )
    return FileResponse(
        file_path,
        media_type=document.content_type,
        filename=document.original_filename,
        headers=headers,
    )


@router.get("/safety-guide")
def safety_guide() -> dict[str, Any]:
    return TrustSafetyService.safety_guide()


@router.get("/indicators/{property_id}")
def property_trust_indicators(
    property_id: UUID,
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return TrustSafetyService.property_trust_indicators(session, property_id)


@router.get("/verifications/mine", response_model=list[VerificationCaseResponse])
def my_verifications(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[VerificationCaseResponse]:
    return _service(settings).list_my_verifications(session, principal.user_id)


@router.post(
    "/verifications",
    response_model=VerificationCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_verification(
    body: VerificationSubmit,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VerificationCaseResponse:
    return _service(settings).submit_verification(session, principal.user_id, body)


@router.get("/verifications/queue", response_model=list[VerificationCaseResponse])
def verification_queue(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[VerificationCaseResponse]:
    return _service(settings).verification_queue(session, principal.user_id)


@router.post("/verifications/{case_id}/review", response_model=VerificationCaseResponse)
def review_verification(
    case_id: UUID,
    body: VerificationReview,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VerificationCaseResponse:
    return _service(settings).review_verification(
        session,
        principal.user_id,
        case_id,
        body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/verifications/{case_id}/evidence/{evidence_id}/download")
def download_verification_evidence(
    case_id: UUID,
    evidence_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    cipher = TrustCipher(settings)
    document = _service(settings).verification_evidence_document(
        session, principal.user_id, case_id, evidence_id
    )
    return _document_response(document, settings, cipher)


@router.post(
    "/properties/{property_id}/reports", response_model=PropertyReportResponse, status_code=201
)
def report_listing(
    property_id: UUID,
    body: PropertyReportCreate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PropertyReportResponse:
    return _service(settings).report_listing(
        session,
        principal.user_id,
        property_id,
        body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/listing-reports/mine", response_model=list[PropertyReportResponse])
def my_listing_reports(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[PropertyReportResponse]:
    return _service(settings).reports_by_user(session, principal.user_id)


@router.post(
    "/listing-reports/{report_id}/evidence/{document_id}", response_model=PropertyReportResponse
)
def attach_listing_report_evidence(
    report_id: UUID,
    document_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PropertyReportResponse:
    return _service(settings).add_listing_report_evidence(
        session, principal.user_id, report_id, document_id
    )


@router.get("/safety-reports/mine", response_model=list[SafetyReportResponse])
def my_safety_reports(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[SafetyReportResponse]:
    return _service(settings).my_safety_reports(session, principal.user_id)


@router.post("/safety-reports", response_model=SafetyReportResponse, status_code=201)
def create_safety_report(
    body: SafetyReportCreate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SafetyReportResponse:
    return _service(settings).report_safety_incident(
        session,
        principal.user_id,
        body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/viewings", response_model=list[ViewingResponse])
def my_viewings(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[ViewingResponse]:
    return _service(settings).list_viewings(session, principal.user_id)


@router.post("/viewings", response_model=ViewingResponse, status_code=201)
def create_viewing(
    body: ViewingCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ViewingResponse:
    return _service(settings).create_viewing(session, principal.user_id, body)


@router.patch("/viewings/{viewing_id}", response_model=ViewingResponse)
def update_viewing(
    viewing_id: UUID,
    body: ViewingUpdate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ViewingResponse:
    return _service(settings).update_viewing(session, principal.user_id, viewing_id, body)


@router.post("/viewings/{viewing_id}/{action}", response_model=ViewingResponse)
def transition_viewing(
    viewing_id: UUID,
    action: str,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ViewingResponse:
    if action not in {"check-in", "check-out", "cancel"}:
        raise ApiError(404, "viewing_action_not_found", "That viewing action is not available.")
    return _service(settings).viewing_transition(session, principal.user_id, viewing_id, action)


@router.get("/moderation/queue")
def moderation_queue(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, Any]]:
    return _service(settings).list_moderation_queue(session, principal.user_id)


@router.post("/moderation/{report_type}/{report_id}/review")
def review_report(
    report_type: str,
    report_id: UUID,
    body: TrustReportReview,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    return _service(settings).review_moderation_report(
        session,
        principal.user_id,
        report_type,
        report_id,
        body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/moderation/{report_type}/{report_id}/evidence/{document_id}/download")
def download_report_evidence(
    report_type: str,
    report_id: UUID,
    document_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    cipher = TrustCipher(settings)
    document = _service(settings).report_evidence_document(
        session, principal.user_id, report_type, report_id, document_id
    )
    return _document_response(document, settings, cipher)
