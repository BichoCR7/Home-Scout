"""Restricted user and role administration; private account data stays out of scope."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db
from app.core.errors import ApiError
from app.schemas.rbac import (
    RoleAssignmentRequest,
    RoleAssignmentResponse,
    RoleDefinitionResponse,
    RoleRevocationRequest,
    UserSearchResponse,
)
from app.services.authentication import AuthenticatedPrincipal
from app.services.authorization import AuthorizationService
from app.services.role_management import RoleManagementService

router = APIRouter(prefix="/admin", tags=["administration"])


@router.get("/roles", response_model=list[RoleDefinitionResponse])
def list_roles(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[RoleDefinitionResponse]:
    _require_permission(session, principal.user_id, "roles:view:global")
    return [RoleDefinitionResponse(**item) for item in RoleManagementService().definitions(session)]


@router.get("/users", response_model=UserSearchResponse)
def search_users(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    q: Annotated[str, Query(min_length=2, max_length=254)],
    limit: Annotated[int, Query(ge=1, le=50)] = 25,
) -> UserSearchResponse:
    _require_permission(session, principal.user_id, "user:view:basic")
    results = RoleManagementService().search_users(session, query=q, limit=limit)
    return UserSearchResponse(items=results)


@router.post(
    "/users/{user_id}/roles",
    response_model=RoleAssignmentResponse,
    status_code=201,
)
def assign_role(
    user_id: UUID,
    body: RoleAssignmentRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> RoleAssignmentResponse:
    assignment = RoleManagementService().assign_role(
        session,
        actor_id=principal.user_id,
        target_user_id=user_id,
        role_code=body.role_code,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        current_password=body.current_password.get_secret_value(),
    )
    return RoleAssignmentResponse(
        user_id=assignment.user_id,
        role_code=assignment.role.code,
        scope_type=assignment.scope_type,
        scope_id=assignment.scope_id,
        assigned_by_user_id=assignment.assigned_by_user_id or principal.user_id,
        assigned_at=assignment.assigned_at,
    )


@router.post("/users/{user_id}/roles/{role_code}/revoke", status_code=204)
def revoke_role(
    user_id: UUID,
    role_code: str,
    body: RoleRevocationRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> None:
    RoleManagementService().revoke_role(
        session,
        actor_id=principal.user_id,
        target_user_id=user_id,
        role_code=role_code,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        current_password=body.current_password.get_secret_value(),
    )


def _require_permission(session: Session, user_id: UUID, code: str) -> None:
    if not AuthorizationService().has_permission(
        session,
        user_id=user_id,
        permission_code=code,
        resource_scope_type="global",
        resource_scope_id="*",
    ):
        raise ApiError(
            status_code=403,
            code="permission_denied",
            message="You are not authorized to perform this action.",
        )
