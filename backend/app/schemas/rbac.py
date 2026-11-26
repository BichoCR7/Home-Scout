"""Role catalog and administrative role assignment contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, SecretStr, model_validator

from app.core.rbac_catalog import ALLOWED_SCOPE_TYPES


class RoleDefinitionResponse(BaseModel):
    code: str
    name: str
    description: str
    permissions: list[str]


class UserSummaryResponse(BaseModel):
    id: UUID
    email: EmailStr | None
    status: str
    roles: list[str]
    requested_role_code: str | None


class UserSearchResponse(BaseModel):
    items: list[UserSummaryResponse]


class RoleAssignmentRequest(BaseModel):
    role_code: str = Field(min_length=2, max_length=64)
    scope_type: str = "global"
    scope_id: str = "*"
    current_password: SecretStr

    @model_validator(mode="after")
    def validate_scope(self) -> RoleAssignmentRequest:
        if self.scope_type not in ALLOWED_SCOPE_TYPES:
            raise ValueError("Scope type is not supported.")
        if self.scope_type == "global" and self.scope_id != "*":
            raise ValueError("Global role assignments must use the wildcard scope id.")
        if self.scope_type != "global" and (not self.scope_id.strip() or self.scope_id == "*"):
            raise ValueError("Scoped role assignments require a concrete scope id.")
        return self


class RoleRevocationRequest(BaseModel):
    scope_type: str = "global"
    scope_id: str = "*"
    current_password: SecretStr

    @model_validator(mode="after")
    def validate_scope(self) -> RoleRevocationRequest:
        if self.scope_type not in ALLOWED_SCOPE_TYPES:
            raise ValueError("Scope type is not supported.")
        if self.scope_type == "global" and self.scope_id != "*":
            raise ValueError("Global role assignments must use the wildcard scope id.")
        if self.scope_type != "global" and (not self.scope_id.strip() or self.scope_id == "*"):
            raise ValueError("Scoped role assignments require a concrete scope id.")
        return self


class RoleAssignmentResponse(BaseModel):
    user_id: UUID
    role_code: str
    scope_type: str
    scope_id: str
    assigned_by_user_id: UUID
    assigned_at: datetime
