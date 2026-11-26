"""Shared search, comparison, and opt-in roommate discovery endpoints."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db, get_settings
from app.core.config import Settings
from app.schemas.phase10 import (
    ComparisonBoardResponse,
    ComparisonBoardSave,
    GroupCreate,
    GroupInvite,
    GroupResponse,
    RoommateCandidateResponse,
    RoommateInterestDecision,
    RoommateInterestResponse,
    RoommateProfileResponse,
    RoommateProfileSave,
    SharedComparisonSave,
    SharedFinancialConsent,
    SharedMoveGoalCreate,
    SharedPropertyAdd,
    SharedPropertyCommentCreate,
    SharedPropertyVoteInput,
    SharedSearchCreate,
    SharedTaskCreate,
    SharedTaskUpdate,
)
from app.services.authentication import AuthenticatedPrincipal
from app.services.collaboration import CollaborationService
from app.services.phase10_cipher import Phase10Cipher

router = APIRouter(prefix="/collaboration", tags=["shared search and roommates"])


def _service(settings: Settings) -> CollaborationService:
    return CollaborationService(Phase10Cipher(settings))


@router.post("/groups", response_model=GroupResponse, status_code=201)
def create_group(
    body: GroupCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GroupResponse:
    return _service(settings).create_group(session, principal.user_id, body)


@router.get("/groups", response_model=list[GroupResponse])
def groups(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[GroupResponse]:
    return _service(settings).groups(session, principal.user_id)


@router.post("/groups/{group_id}/invitations", response_model=GroupResponse)
def invite_group_member(
    group_id: UUID,
    body: GroupInvite,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GroupResponse:
    return _service(settings).invite(session, principal.user_id, group_id, body)


@router.post("/groups/{group_id}/invitation-response", response_model=GroupResponse)
def respond_group_invitation(
    group_id: UUID,
    accept: bool,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GroupResponse:
    return _service(settings).respond_to_invitation(
        session, principal.user_id, group_id, accept=accept
    )


@router.delete("/groups/{group_id}/members/{target_user_id}", status_code=204)
def revoke_group_member(
    group_id: UUID,
    target_user_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    _service(settings).revoke_member(session, principal.user_id, group_id, target_user_id)
    return Response(status_code=204)


@router.post("/groups/{group_id}/searches", status_code=201)
def create_shared_search(
    group_id: UUID,
    body: SharedSearchCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    row = _service(settings).create_shared_search(session, principal.user_id, group_id, body)
    return {
        "id": row.id,
        "group_id": row.group_id,
        "created_by_user_id": row.created_by_user_id,
        "name": row.name,
        "filters": row.filters,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("/groups/{group_id}/searches")
def shared_searches(
    group_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, object]]:
    rows = _service(settings).shared_searches(session, principal.user_id, group_id)
    return [
        {
            "id": row.id,
            "group_id": row.group_id,
            "created_by_user_id": row.created_by_user_id,
            "name": row.name,
            "filters": row.filters,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


@router.post("/groups/{group_id}/properties", status_code=201)
def add_shared_property(
    group_id: UUID,
    body: SharedPropertyAdd,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    row = _service(settings).add_property(session, principal.user_id, group_id, body)
    return {
        "id": row.id,
        "group_id": row.group_id,
        "property_id": row.property_id,
        "created_at": row.created_at,
    }


@router.get("/groups/{group_id}/properties")
def shared_properties(
    group_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, object]]:
    return _service(settings).shared_properties(session, principal.user_id, group_id)


@router.put("/groups/{group_id}/properties/{shared_property_id}/vote")
def vote_shared_property(
    group_id: UUID,
    shared_property_id: UUID,
    body: SharedPropertyVoteInput,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    return _service(settings).vote_for_property(
        session, principal.user_id, group_id, shared_property_id, body
    )


@router.post("/groups/{group_id}/properties/{shared_property_id}/comments", status_code=201)
def comment_shared_property(
    group_id: UUID,
    shared_property_id: UUID,
    body: SharedPropertyCommentCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    return _service(settings).comment_on_property(
        session, principal.user_id, group_id, shared_property_id, body
    )


@router.post("/groups/{group_id}/comparisons", status_code=201)
def create_group_comparison(
    group_id: UUID,
    body: SharedComparisonSave,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    return _service(settings).create_group_comparison(session, principal.user_id, group_id, body)


@router.get("/groups/{group_id}/comparisons")
def group_comparisons(
    group_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, object]]:
    return _service(settings).group_comparisons(session, principal.user_id, group_id)


@router.post("/groups/{group_id}/tasks", status_code=201)
def create_group_task(
    group_id: UUID,
    body: SharedTaskCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    row = _service(settings).create_task(session, principal.user_id, group_id, body)
    return _task(row)


@router.get("/groups/{group_id}/tasks")
def group_tasks(
    group_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, object]]:
    return [_task(row) for row in _service(settings).tasks(session, principal.user_id, group_id)]


@router.patch("/groups/{group_id}/tasks/{task_id}")
def update_group_task(
    group_id: UUID,
    task_id: UUID,
    body: SharedTaskUpdate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    row = _service(settings).update_task(session, principal.user_id, group_id, task_id, body)
    return _task(row)


@router.post("/groups/{group_id}/moving-goals", status_code=201)
def create_group_moving_goal(
    group_id: UUID,
    body: SharedMoveGoalCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    return _service(settings).create_move_goal(session, principal.user_id, group_id, body)


@router.get("/groups/{group_id}/moving-goals")
def group_moving_goals(
    group_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, object]]:
    return _service(settings).move_goals(session, principal.user_id, group_id)


@router.put("/groups/{group_id}/moving-goals/{goal_id}/financial-consent")
def moving_goal_financial_consent(
    group_id: UUID,
    goal_id: UUID,
    body: SharedFinancialConsent,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    return _service(settings).set_move_goal_financial_consent(
        session, principal.user_id, group_id, goal_id, body
    )


@router.get("/comparisons", response_model=list[ComparisonBoardResponse])
def comparisons(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[ComparisonBoardResponse]:
    return _service(settings).comparisons(session, principal.user_id)


@router.post("/comparisons", response_model=ComparisonBoardResponse, status_code=201)
def create_comparison(
    body: ComparisonBoardSave,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ComparisonBoardResponse:
    return _service(settings).create_comparison(session, principal.user_id, body)


@router.get("/comparisons/{board_id}", response_model=ComparisonBoardResponse)
def get_comparison(
    board_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ComparisonBoardResponse:
    return _service(settings).get_comparison_board(session, principal.user_id, board_id)


@router.put("/comparisons/{board_id}", response_model=ComparisonBoardResponse)
def update_comparison(
    board_id: UUID,
    body: ComparisonBoardSave,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ComparisonBoardResponse:
    return _service(settings).update_comparison(session, principal.user_id, board_id, body)


@router.delete("/comparisons/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comparison(
    board_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    _service(settings).delete_comparison(session, principal.user_id, board_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/roommates/me", response_model=RoommateProfileResponse | None)
def my_roommate_profile(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RoommateProfileResponse | None:
    return _service(settings).my_roommate_profile(session, principal.user_id)


@router.put("/roommates/me", response_model=RoommateProfileResponse)
def save_roommate_profile(
    body: RoommateProfileSave,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RoommateProfileResponse:
    return _service(settings).save_roommate_profile(session, principal.user_id, body)


@router.get("/roommates/suggestions", response_model=list[RoommateCandidateResponse])
def roommate_suggestions(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    county_id: UUID | None = None,
    town_id: UUID | None = None,
    budget_max: Annotated[Decimal | None, Query(ge=0, le=10_000_000)] = None,
) -> list[RoommateCandidateResponse]:
    return _service(settings).roommate_suggestions(
        session,
        principal.user_id,
        county_id=county_id,
        town_id=town_id,
        budget_max=budget_max,
    )


@router.post(
    "/roommates/{profile_id}/interests", response_model=RoommateInterestResponse, status_code=201
)
def request_roommate_connection(
    profile_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RoommateInterestResponse:
    return _service(settings).roommate_interest(session, principal.user_id, profile_id)


@router.get("/roommates/interests", response_model=list[RoommateInterestResponse])
def roommate_interests(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[RoommateInterestResponse]:
    return _service(settings).roommate_interests(session, principal.user_id)


@router.patch("/roommates/interests/{interest_id}", response_model=RoommateInterestResponse)
def decide_roommate_interest(
    interest_id: UUID,
    body: RoommateInterestDecision,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RoommateInterestResponse:
    return _service(settings).decide_roommate_interest(
        session, principal.user_id, interest_id, body
    )


def _task(row) -> dict[str, object]:
    return {
        "id": row.id,
        "group_id": row.group_id,
        "created_by_user_id": row.created_by_user_id,
        "assigned_to_user_id": row.assigned_to_user_id,
        "title": row.title,
        "details": row.details,
        "due_at": row.due_at,
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
