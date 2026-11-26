"""Audited administrative role assignment with strict anti-escalation rules."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import ApiError
from app.core.rbac_catalog import ROLE_DEFINITIONS, ROLE_PERMISSION_CODES
from app.models.access_control import Role, UserRoleAssignment
from app.models.audit import AuditEvent
from app.models.user import UserAccount
from app.services.authorization import AuthorizationService
from app.services.passwords import password_service

OPERATIONAL_ROLES = {
    "tenant",
    "roommate",
    "landlord",
    "real_estate_agent",
    "property_manager",
    "service_provider",
}
ADMINISTRATIVE_ROLES = {"moderator", "admin", "super_admin"}
ROLE_ALLOWED_SCOPES = {
    "tenant": {"global"},
    "roommate": {"group"},
    "landlord": {"property"},
    "real_estate_agent": {"property"},
    "property_manager": {"property", "portfolio"},
    "service_provider": {"booking"},
    "moderator": {"moderation"},
    "admin": {"administrative_workflow"},
    "super_admin": {"global"},
}


class RoleManagementService:
    def __init__(self) -> None:
        self.authorization = AuthorizationService()

    def definitions(self, session: Session) -> list[dict[str, object]]:
        definitions = {role.code: role for role in ROLE_DEFINITIONS if role.persistent}
        rows = session.scalars(select(Role).order_by(Role.name)).all()
        return [
            {
                "code": row.code,
                "name": row.name,
                "description": row.description or definitions[row.code].description,
                "permissions": sorted(ROLE_PERMISSION_CODES.get(row.code, frozenset())),
            }
            for row in rows
            if row.code in definitions
        ]

    def search_users(self, session: Session, *, query: str, limit: int) -> list[dict[str, object]]:
        normalized = query.strip().lower()
        if len(normalized) < 2:
            raise ApiError(
                status_code=422,
                code="search_query_too_short",
                message="Enter at least two characters to search users.",
            )
        users = session.scalars(
            select(UserAccount)
            .options(joinedload(UserAccount.profile), joinedload(UserAccount.role_assignments))
            .where(func.lower(UserAccount.email).like(f"{normalized}%"))
            .order_by(UserAccount.email)
            .limit(limit)
        ).unique()
        results: list[dict[str, object]] = []
        for user in users:
            role_codes = self.authorization.role_codes(session, user.id)
            results.append(
                {
                    "id": user.id,
                    "email": user.email,
                    "status": user.status,
                    "roles": role_codes,
                    "requested_role_code": (
                        user.profile.requested_role_code if user.profile else None
                    ),
                }
            )
        return results

    def assign_role(
        self,
        session: Session,
        *,
        actor_id: UUID,
        target_user_id: UUID,
        role_code: str,
        scope_type: str,
        scope_id: str,
        current_password: str,
    ) -> UserRoleAssignment:
        actor = session.get(UserAccount, actor_id)
        target = session.get(UserAccount, target_user_id)
        if actor is None:
            raise self._permission_error()
        if target_user_id == actor_id:
            raise ApiError(
                status_code=403,
                code="self_role_change_forbidden",
                message="You cannot change your own roles.",
            )
        if target is None or target.status != "active" or target.email_verified_at is None:
            raise ApiError(
                status_code=404,
                code="eligible_user_not_found",
                message="An active verified account was not found.",
            )
        if not actor.password_hash or not password_service.verify(
            actor.password_hash, current_password
        ):
            raise ApiError(
                status_code=401,
                code="reauthentication_required",
                message="Confirm your password to manage roles.",
            )
        self._require_role_assignment_authority(session, actor_id, role_code)
        self._validate_role_scope(
            session,
            actor_id=actor_id,
            role_code=role_code,
            scope_type=scope_type,
        )

        role_query = select(Role).where(Role.code == role_code)
        if role_code == "super_admin":
            role_query = role_query.with_for_update()
        role = session.scalar(role_query)
        if role is None:
            raise ApiError(status_code=404, code="role_not_found", message="Role not found.")
        assignment = session.get(
            UserRoleAssignment,
            (target_user_id, role.id, scope_type, scope_id),
        )
        if assignment is None:
            assignment = UserRoleAssignment(
                user_id=target_user_id,
                role_id=role.id,
                scope_type=scope_type,
                scope_id=scope_id,
                assigned_by_user_id=actor_id,
            )
            session.add(assignment)
            session.add(
                AuditEvent(
                    event_type="authorization.role_assigned",
                    actor_user_id=actor_id,
                    subject_type="user",
                    subject_id=str(target_user_id),
                    metadata_json={"role_code": role_code, "scope_type": scope_type},
                )
            )
        session.commit()
        session.refresh(assignment)
        return assignment

    def revoke_role(
        self,
        session: Session,
        *,
        actor_id: UUID,
        target_user_id: UUID,
        role_code: str,
        scope_type: str,
        scope_id: str,
        current_password: str,
    ) -> None:
        if target_user_id == actor_id:
            raise ApiError(
                status_code=403,
                code="self_role_change_forbidden",
                message="You cannot change your own roles.",
            )
        actor = session.get(UserAccount, actor_id)
        if (
            actor is None
            or not actor.password_hash
            or not password_service.verify(actor.password_hash, current_password)
        ):
            raise ApiError(
                status_code=401,
                code="reauthentication_required",
                message="Confirm your password to manage roles.",
            )
        self._require_role_assignment_authority(session, actor_id, role_code)
        self._validate_role_scope(
            session,
            actor_id=actor_id,
            role_code=role_code,
            scope_type=scope_type,
        )
        if role_code == "tenant":
            raise ApiError(
                status_code=409,
                code="default_role_required",
                message="The default tenant role cannot be removed.",
            )
        role_query = select(Role).where(Role.code == role_code)
        if role_code == "super_admin":
            role_query = role_query.with_for_update()
        role = session.scalar(role_query)
        assignment = (
            session.get(UserRoleAssignment, (target_user_id, role.id, scope_type, scope_id))
            if role
            else None
        )
        if assignment is None:
            raise ApiError(
                status_code=404,
                code="role_assignment_not_found",
                message="Role assignment not found.",
            )
        if role_code == "super_admin":
            remaining = session.scalar(
                select(func.count())
                .select_from(UserRoleAssignment)
                .where(UserRoleAssignment.role_id == role.id)
            )
            if remaining is not None and remaining <= 1:
                raise ApiError(
                    status_code=409,
                    code="last_super_admin_required",
                    message="The last Super Admin assignment cannot be removed.",
                )
        session.add(
            AuditEvent(
                event_type="authorization.role_revoked",
                actor_user_id=actor_id,
                subject_type="user",
                subject_id=str(target_user_id),
                metadata_json={"role_code": role_code, "scope_type": scope_type},
            )
        )
        session.delete(assignment)
        session.commit()

    def _require_role_assignment_authority(
        self,
        session: Session,
        actor_id: UUID,
        role_code: str,
    ) -> None:
        if role_code not in OPERATIONAL_ROLES | ADMINISTRATIVE_ROLES:
            raise ApiError(status_code=404, code="role_not_found", message="Role not found.")
        if role_code in ADMINISTRATIVE_ROLES:
            allowed = self.authorization.has_permission(
                session,
                user_id=actor_id,
                permission_code="roles:assign:administrative",
                resource_scope_type="global",
                resource_scope_id="*",
            )
        else:
            allowed = self.authorization.has_permission(
                session,
                user_id=actor_id,
                permission_code="roles:assign:operational",
                resource_scope_type="global",
                resource_scope_id="*",
            )
        if not allowed:
            raise self._permission_error()

    def _validate_role_scope(
        self,
        session: Session,
        *,
        actor_id: UUID,
        role_code: str,
        scope_type: str,
    ) -> None:
        if scope_type not in ROLE_ALLOWED_SCOPES[role_code]:
            raise ApiError(
                status_code=422,
                code="invalid_role_scope",
                message="This role cannot be assigned within the selected scope.",
            )
        if scope_type == "global" and not self.authorization.has_permission(
            session,
            user_id=actor_id,
            permission_code="roles:assign:administrative",
            resource_scope_type="global",
            resource_scope_id="*",
        ):
            raise self._permission_error()

    @staticmethod
    def _permission_error() -> ApiError:
        return ApiError(
            status_code=403,
            code="permission_denied",
            message="You are not authorized to perform this action.",
        )
