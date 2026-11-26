"""Explicit, low-data schemas for staff operations."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AccountStatusUpdate(BaseModel):
    status: Literal["active", "suspended"]
    current_password: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=10, max_length=500)


class ListingModerationUpdate(BaseModel):
    status: Literal["clear", "under_review", "removed"]
    reason: str = Field(min_length=10, max_length=500)


class ServiceReviewModerationUpdate(BaseModel):
    status: Literal["clear", "under_review", "removed"]
    reason: str = Field(min_length=10, max_length=500)


class ProviderPublicationUpdate(BaseModel):
    is_published: bool
    reason: str = Field(min_length=10, max_length=500)


class OfferingStatusUpdate(BaseModel):
    is_active: bool
    reason: str = Field(min_length=10, max_length=500)


class LocationStatusUpdate(BaseModel):
    is_active: bool
    reason: str = Field(min_length=10, max_length=500)


class SupportTicketUpdate(BaseModel):
    status: Literal["open", "waiting", "closed"] | None = None
    priority: Literal["normal", "high", "urgent"] | None = None
    assigned_to_user_id: UUID | None = None
    escalate: bool | None = None
    note: str | None = Field(default=None, max_length=1000)


class SupportReply(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class SettingUpdate(BaseModel):
    value: bool


class SupportCategoryUpdate(BaseModel):
    is_active: bool


class MessageReportUpdate(BaseModel):
    status: Literal["reviewed", "closed"]
    remove_message: bool = False
    reason: str = Field(min_length=10, max_length=500)


class AdminUserSummary(BaseModel):
    id: UUID
    email: str | None
    status: str
    roles: list[str]
    requested_role_code: str | None
    created_at: datetime


class SupportActionSummary(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    action: str
    note: str | None
    created_at: datetime


class SupportAdminTicket(BaseModel):
    id: UUID
    owner_user_id: UUID
    owner_email: str | None
    subject: str
    category: str
    status: str
    priority: str
    assigned_to_user_id: UUID | None
    escalated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    messages: list[dict[str, object]] = Field(default_factory=list)
    actions: list[SupportActionSummary] = Field(default_factory=list)
