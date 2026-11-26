"""Validated identity, session, and account-action API contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator

from app.core.rbac_catalog import REQUESTABLE_ROLE_CODES


class RegisterRequest(BaseModel):
    email: EmailStr
    password: SecretStr
    given_name: str = Field(min_length=1, max_length=100)
    family_name: str | None = Field(default=None, max_length=100)
    requested_role_code: str = "tenant"

    @field_validator("password")
    @classmethod
    def password_length(cls, password: SecretStr) -> SecretStr:
        value = password.get_secret_value()
        if not 12 <= len(value) <= 128:
            raise ValueError("Password must be between 12 and 128 characters.")
        return password

    @field_validator("requested_role_code")
    @classmethod
    def requestable_role(cls, role_code: str) -> str:
        if role_code not in REQUESTABLE_ROLE_CODES:
            raise ValueError("Requested role is not available for self-registration.")
        return role_code


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class AccountActionRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class EmailRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: SecretStr

    @field_validator("new_password")
    @classmethod
    def password_length(cls, password: SecretStr) -> SecretStr:
        value = password.get_secret_value()
        if not 12 <= len(value) <= 128:
            raise ValueError("Password must be between 12 and 128 characters.")
        return password


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=256)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=256)


class AuthMessageResponse(BaseModel):
    message: str
    development_token: str | None = None


class UserProfileResponse(BaseModel):
    given_name: str | None
    family_name: str | None
    preferred_name: str | None
    requested_role_code: str | None


class AuthUserResponse(BaseModel):
    id: UUID
    email: EmailStr | None
    status: str
    email_verified: bool
    profile: UserProfileResponse | None
    roles: list[str]
    permissions: list[str]


class ProfileUpdateRequest(BaseModel):
    given_name: str | None = Field(default=None, min_length=1, max_length=100)
    family_name: str | None = Field(default=None, max_length=100)
    preferred_name: str | None = Field(default=None, max_length=100)


class SessionResponse(BaseModel):
    id: UUID
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    current: bool


class RefreshResponse(TokenPairResponse):
    pass
