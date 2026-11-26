"""HomeScout Assistant configuration, privacy, conversations, and messaging."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db
from app.schemas.assistant import (
    AssistantConfigurationResponse,
    AssistantConversationDetailResponse,
    AssistantConversationResponse,
    AssistantMessageRequest,
    AssistantMessageResult,
    AssistantPrivacyResponse,
    AssistantPrivacyUpdate,
    AssistantRenameRequest,
)
from app.services.assistant import AssistantService
from app.services.authentication import AuthenticatedPrincipal

router = APIRouter(prefix="/assistant", tags=["HomeScout Assistant"])

Principal = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]
Database = Annotated[Session, Depends(get_db)]


def get_assistant_service(request: Request) -> AssistantService:
    return AssistantService(
        request.app.state.settings,
        request.app.state.assistant_client,
    )


Service = Annotated[AssistantService, Depends(get_assistant_service)]


@router.get("/configuration", response_model=AssistantConfigurationResponse)
def configuration(service: Service) -> AssistantConfigurationResponse:
    return service.configuration()


@router.get("/privacy", response_model=AssistantPrivacyResponse)
def privacy(principal: Principal, session: Database, service: Service) -> AssistantPrivacyResponse:
    service.require_access(session, principal.user_id, "assistant:use:self")
    return service.privacy(session, principal.user_id)


@router.put("/privacy", response_model=AssistantPrivacyResponse)
def update_privacy(
    body: AssistantPrivacyUpdate,
    principal: Principal,
    session: Database,
    service: Service,
) -> AssistantPrivacyResponse:
    service.require_access(session, principal.user_id, "assistant:use:self")
    return service.update_privacy(session, principal.user_id, body)


@router.get("/conversations", response_model=list[AssistantConversationResponse])
def conversations(
    principal: Principal,
    session: Database,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AssistantConversationResponse]:
    service.require_access(session, principal.user_id, "assistant:history:self")
    return service.list_conversations(session, principal.user_id, limit)


@router.post("/messages", response_model=AssistantMessageResult)
def send_message(
    body: AssistantMessageRequest,
    principal: Principal,
    session: Database,
    service: Service,
) -> AssistantMessageResult:
    return service.send(session, principal.user_id, body)


@router.get(
    "/conversations/{conversation_id}",
    response_model=AssistantConversationDetailResponse,
)
def conversation(
    conversation_id: UUID,
    principal: Principal,
    session: Database,
    service: Service,
) -> AssistantConversationDetailResponse:
    return service.get_conversation(session, principal.user_id, conversation_id)


@router.patch(
    "/conversations/{conversation_id}",
    response_model=AssistantConversationResponse,
)
def rename_conversation(
    conversation_id: UUID,
    body: AssistantRenameRequest,
    principal: Principal,
    session: Database,
    service: Service,
) -> AssistantConversationResponse:
    return service.rename(session, principal.user_id, conversation_id, body)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: UUID,
    principal: Principal,
    session: Database,
    service: Service,
) -> Response:
    service.delete(session, principal.user_id, conversation_id)
    return Response(status_code=204)
