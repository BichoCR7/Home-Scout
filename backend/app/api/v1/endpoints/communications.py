"""Private messaging and viewing coordination endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db, get_settings
from app.core.config import Settings
from app.core.errors import ApiError
from app.models.personal_hub import PrivateDocument
from app.models.phase10 import ViewingJournal
from app.schemas.phase10 import (
    ConversationResponse,
    JournalShareCreate,
    MessageCreate,
    MessageReportCreate,
    MessageResponse,
    ViewingAction,
    ViewingJournalCreate,
    ViewingJournalResponse,
    ViewingRequestCreate,
    ViewingResponse,
)
from app.services.authentication import AuthenticatedPrincipal
from app.services.communications import CommunicationsService
from app.services.media_storage import LocalMediaStorage
from app.services.phase10_cipher import Phase10Cipher
from app.services.viewings import ViewingService

router = APIRouter(prefix="", tags=["communications and viewings"])


def _communications(settings: Settings) -> CommunicationsService:
    return CommunicationsService(Phase10Cipher(settings))


def _viewings(settings: Settings) -> ViewingService:
    return ViewingService(Phase10Cipher(settings))


@router.get("/communications/inbox", response_model=list[ConversationResponse])
def inbox(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    include_archived: bool = False,
) -> list[ConversationResponse]:
    return _communications(settings).inbox(
        session, principal.user_id, include_archived=include_archived
    )


@router.post(
    "/communications/property-enquiries/{enquiry_id}/conversation",
    response_model=ConversationResponse,
)
def enquiry_conversation(
    enquiry_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConversationResponse:
    return _communications(settings).get_or_create_for_enquiry(
        session, principal.user_id, enquiry_id
    )


@router.post(
    "/communications/roommate-interests/{interest_id}/conversation",
    response_model=ConversationResponse,
)
def roommate_conversation(
    interest_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConversationResponse:
    return _communications(settings).get_or_create_for_roommate_interest(
        session, principal.user_id, interest_id
    )


@router.get(
    "/communications/groups/{group_id}/conversation",
    response_model=ConversationResponse,
)
def group_conversation(
    group_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConversationResponse:
    return _communications(settings).group_conversation(session, principal.user_id, group_id)


@router.get(
    "/communications/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
def conversation_messages(
    conversation_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[MessageResponse]:
    return _communications(settings).messages(
        session, principal.user_id, conversation_id, limit=limit
    )


@router.post(
    "/communications/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    conversation_id: UUID,
    body: MessageCreate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MessageResponse:
    return _communications(settings).send_message(
        session,
        principal.user_id,
        conversation_id,
        body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/communications/conversations/{conversation_id}/archive", status_code=204)
def archive_conversation(
    conversation_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    _communications(settings).archive(session, principal.user_id, conversation_id)
    return Response(status_code=204)


@router.put("/communications/blocks/{other_user_id}")
def block_user(
    other_user_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    _communications(settings).set_block(session, principal.user_id, other_user_id, blocked=True)
    return {"blocked_user_id": other_user_id, "blocked": True}


@router.get("/communications/blocks")
def blocked_users(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, object]]:
    return _communications(settings).blocks(session, principal.user_id)


@router.delete("/communications/blocks/{other_user_id}")
def unblock_user(
    other_user_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    _communications(settings).set_block(session, principal.user_id, other_user_id, blocked=False)
    return {"blocked_user_id": other_user_id, "blocked": False}


@router.post("/communications/messages/{message_id}/reports", status_code=201)
def report_message(
    message_id: UUID,
    body: MessageReportCreate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, UUID | str]:
    report_id = _communications(settings).report_message(
        session,
        principal.user_id,
        message_id,
        body,
        request_id=getattr(request.state, "request_id", None),
    )
    return {"id": report_id, "status": "received"}


@router.get("/communications/messages/{message_id}/attachments/{document_id}")
def download_message_attachment(
    message_id: UUID,
    document_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    document: PrivateDocument = _communications(settings).attachment_file(
        session, principal.user_id, message_id, document_id
    )
    path = LocalMediaStorage(settings.private_document_storage_dir).get(document.storage_key)
    if path is None:
        raise ApiError(404, "document_missing", "The private attachment is no longer available.")
    return FileResponse(
        path,
        media_type=document.content_type,
        filename=document.original_filename,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/viewings/requests", response_model=ViewingResponse, status_code=201)
def create_viewing_request(
    body: ViewingRequestCreate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ViewingResponse:
    return _viewings(settings).request_viewing(
        session,
        principal.user_id,
        body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/viewings/calendar", response_model=list[ViewingResponse])
def viewing_calendar(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    start: datetime | None = None,
    end: datetime | None = None,
    status_filter: Annotated[
        str | None,
        Query(pattern="^(requested|confirmed|reschedule_proposed|declined|cancelled|completed)$"),
    ] = None,
) -> list[ViewingResponse]:
    return _viewings(settings).calendar(
        session, principal.user_id, start=start, end=end, status_filter=status_filter
    )


@router.post("/viewings/{viewing_id}/actions", response_model=ViewingResponse)
def viewing_action(
    viewing_id: UUID,
    body: ViewingAction,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ViewingResponse:
    return _viewings(settings).viewing_action(
        session,
        principal.user_id,
        viewing_id,
        body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/viewings/journals", response_model=ViewingJournalResponse, status_code=201)
def create_viewing_journal(
    body: ViewingJournalCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ViewingJournalResponse:
    return _viewings(settings).create_journal(session, principal.user_id, body)


@router.get("/viewings/journals", response_model=list[ViewingJournalResponse])
def viewing_journals(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[ViewingJournalResponse]:
    return _viewings(settings).journals(session, principal.user_id)


@router.get("/viewings/journals/{journal_id}", response_model=ViewingJournalResponse)
def viewing_journal(
    journal_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ViewingJournalResponse:
    return _viewings(settings).journal(session, principal.user_id, journal_id)


@router.put("/viewings/journals/{journal_id}", response_model=ViewingJournalResponse)
def update_viewing_journal(
    journal_id: UUID,
    body: ViewingJournalCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ViewingJournalResponse:
    return _viewings(settings).update_journal(session, principal.user_id, journal_id, body)


@router.delete("/viewings/journals/{journal_id}", status_code=204)
def delete_viewing_journal(
    journal_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    row = session.get(ViewingJournal, journal_id)
    if row is None or row.owner_user_id != principal.user_id:
        raise ApiError(404, "viewing_journal_not_found", "The journal was not found.")
    session.delete(row)
    session.commit()
    return Response(status_code=204)


@router.put("/viewings/journals/{journal_id}/shares", status_code=204)
def share_viewing_journal(
    journal_id: UUID,
    body: JournalShareCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    _viewings(settings).share_journal(session, principal.user_id, journal_id, body)
    return Response(status_code=204)


@router.delete("/viewings/journals/{journal_id}/shares/{recipient_id}", status_code=204)
def revoke_viewing_journal_share(
    journal_id: UUID,
    recipient_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    _viewings(settings).revoke_journal_share(session, principal.user_id, journal_id, recipient_id)
    return Response(status_code=204)


@router.get("/viewings/journals/{journal_id}/photos/{document_id}")
def download_viewing_journal_photo(
    journal_id: UUID,
    document_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    document = _viewings(settings).journal_photo(
        session, principal.user_id, journal_id, document_id
    )
    path = LocalMediaStorage(settings.private_document_storage_dir).get(document.storage_key)
    if path is None:
        raise ApiError(404, "document_missing", "The private photo is no longer available.")
    return FileResponse(
        path,
        media_type=document.content_type,
        filename=document.original_filename,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
