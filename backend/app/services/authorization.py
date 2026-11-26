"""Central deny-by-default permission checks with ownership and scope predicates."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.access_control import Permission, Role, RolePermission, UserRoleAssignment


class AuthorizationService:
    def permission_codes(self, session: Session, user_id: UUID) -> list[str]:
        statement = (
            select(Permission.code)
            .select_from(UserRoleAssignment)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(UserRoleAssignment.user_id == user_id)
            .distinct()
            .order_by(Permission.code)
        )
        return list(session.scalars(statement))

    def role_codes(self, session: Session, user_id: UUID) -> list[str]:
        statement = (
            select(Role.code)
            .select_from(UserRoleAssignment)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .where(UserRoleAssignment.user_id == user_id)
            .distinct()
            .order_by(Role.code)
        )
        return list(session.scalars(statement))

    def has_permission(
        self,
        session: Session,
        *,
        user_id: UUID,
        permission_code: str,
        resource_owner_id: UUID | None = None,
        resource_scope_type: str | None = None,
        resource_scope_id: str | None = None,
    ) -> bool:
        try:
            _resource, _action, permission_scope = permission_code.split(":", maxsplit=2)
        except ValueError:
            return False

        if permission_scope in {"self", "owned"} and resource_owner_id != user_id:
            return False
        if permission_scope == "global":
            assignment_scope = (UserRoleAssignment.scope_type == "global") & (
                UserRoleAssignment.scope_id == "*"
            )
        elif permission_scope == "self":
            assignment_scope = True
        elif resource_scope_type and resource_scope_id:
            assignment_scope = (UserRoleAssignment.scope_type == "global") | (
                (UserRoleAssignment.scope_type == resource_scope_type)
                & (UserRoleAssignment.scope_id == resource_scope_id)
            )
        else:
            return False

        statement = (
            select(Permission.id)
            .select_from(UserRoleAssignment)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                UserRoleAssignment.user_id == user_id,
                Permission.code == permission_code,
                assignment_scope,
            )
            .limit(1)
        )
        return session.scalar(statement) is not None

    def require_permission(
        self,
        session: Session,
        *,
        user_id: UUID,
        permission_code: str,
        resource_owner_id: UUID | None = None,
        resource_scope_type: str | None = None,
        resource_scope_id: str | None = None,
    ) -> None:
        if not self.has_permission(
            session,
            user_id=user_id,
            permission_code=permission_code,
            resource_owner_id=resource_owner_id,
            resource_scope_type=resource_scope_type,
            resource_scope_id=resource_scope_id,
        ):
            raise ApiError(
                status_code=403,
                code="permission_denied",
                message="You are not authorized to perform this action.",
            )
