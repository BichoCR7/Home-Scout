"""Validated request and response models for Phase 10 collaboration features."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.marketplace import SearchFilters


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    attachment_document_ids: list[UUID] = Field(default_factory=list, max_length=5)

    @field_validator("body")
    @classmethod
    def clean_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty.")
        return value

    @field_validator("attachment_document_ids")
    @classmethod
    def unique_documents(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Choose each attachment once.")
        return value


class MessageReportCreate(BaseModel):
    category: Literal["harassment", "scam", "unsafe_request", "spam", "other"]
    details: str | None = Field(default=None, max_length=1000)

    @field_validator("details")
    @classmethod
    def clean_details(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ConversationResponse(BaseModel):
    id: UUID
    context: Literal["property_enquiry", "roommate", "shared_group"]
    property_id: UUID | None
    group_id: UUID | None
    title: str
    last_message_at: datetime | None
    unread_count: int
    archived: bool


class MessageAttachmentResponse(BaseModel):
    document_id: UUID
    filename: str
    content_type: str


class MessageResponse(BaseModel):
    id: UUID
    sender_user_id: UUID
    body: str
    attachments: list[MessageAttachmentResponse]
    created_at: datetime


class BlockStatusResponse(BaseModel):
    blocked_user_id: UUID
    blocked: bool


class ViewingRequestCreate(BaseModel):
    property_id: UUID
    requested_at: datetime
    timezone: str = "Africa/Nairobi"
    message: str | None = Field(default=None, max_length=1000)
    safe_viewing_id: UUID | None = None

    @field_validator("requested_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Choose a viewing time with a timezone.")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Choose a supported timezone.") from error
        return value

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ViewingAction(BaseModel):
    action: Literal[
        "confirm", "propose_reschedule", "accept_reschedule", "decline", "cancel", "complete"
    ]
    proposed_at: datetime | None = None
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("proposed_at")
    @classmethod
    def require_aware_proposed_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Choose a proposed viewing time with a timezone.")
        return value

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.action == "propose_reschedule" and self.proposed_at is None:
            raise ValueError("A proposed time is required to reschedule.")
        if self.action != "propose_reschedule" and self.proposed_at is not None:
            raise ValueError("A proposed time is only used for rescheduling.")
        return self


class ViewingResponse(BaseModel):
    id: UUID
    property_id: UUID
    property_title: str
    requester_user_id: UUID
    host_user_id: UUID
    requested_at: datetime
    proposed_at: datetime | None
    confirmed_at: datetime | None
    timezone: str
    request_message: str | None
    host_message: str | None
    status: Literal[
        "requested", "confirmed", "reschedule_proposed", "declined", "cancelled", "completed"
    ]
    is_requester: bool
    history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ViewingJournalCreate(BaseModel):
    property_id: UUID
    viewing_id: UUID | None = None
    title: str = Field(min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=5000)
    pros: list[str] = Field(default_factory=list, max_length=20)
    cons: list[str] = Field(default_factory=list, max_length=20)
    rating: int | None = Field(default=None, ge=1, le=5)
    checklist: dict[str, bool] = Field(default_factory=dict, max_length=30)
    follow_up_at: datetime | None = None
    photo_document_ids: list[UUID] = Field(default_factory=list, max_length=10)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Add a journal title.")
        return value

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("pros", "cons")
    @classmethod
    def clean_bullets(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values if item.strip()]
        if any(len(item) > 240 for item in cleaned):
            raise ValueError("Each item must be 240 characters or fewer.")
        return cleaned

    @field_validator("photo_document_ids")
    @classmethod
    def unique_photos(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Choose each journal photo once.")
        return value

    @field_validator("follow_up_at")
    @classmethod
    def aware_follow_up(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Choose a follow-up time with a timezone.")
        return value


class ViewingJournalResponse(BaseModel):
    id: UUID
    property_id: UUID
    property_title: str
    viewing_id: UUID | None
    title: str
    notes: str | None
    pros: list[str]
    cons: list[str]
    rating: int | None
    checklist: dict[str, bool]
    follow_up_at: datetime | None
    photo_document_ids: list[UUID]
    owner_user_id: UUID
    can_edit: bool
    created_at: datetime
    updated_at: datetime


class JournalShareCreate(BaseModel):
    recipient_user_id: UUID


class ComparisonItemInput(BaseModel):
    property_id: UUID
    monthly_cost_input: Decimal | None = Field(default=None, ge=0, le=10_000_000)
    move_in_cost_input: Decimal | None = Field(default=None, ge=0, le=50_000_000)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ComparisonBoardSave(BaseModel):
    name: str = Field(default="My home comparison", min_length=1, max_length=100)
    items: list[ComparisonItemInput] = Field(min_length=2, max_length=5)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Add a comparison name.")
        return value

    @model_validator(mode="after")
    def unique_properties(self):
        ids = [item.property_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Choose each property once.")
        return self


class ComparisonBoardResponse(BaseModel):
    id: UUID
    owner_user_id: UUID
    name: str
    items: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class RoommateProfileSave(BaseModel):
    display_alias: str = Field(min_length=1, max_length=80)
    about: str | None = Field(default=None, max_length=500)
    budget_min: Decimal | None = Field(default=None, ge=0, le=10_000_000)
    budget_max: Decimal | None = Field(default=None, ge=0, le=10_000_000)
    county_id: UUID | None = None
    town_id: UUID | None = None
    preferred_move_in: date | None = None
    lifestyle_tags: list[str] = Field(default_factory=list, max_length=12)
    matching_enabled: bool = False

    @field_validator("display_alias")
    @classmethod
    def clean_alias(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Add a display name for roommate matching.")
        return value

    @field_validator("about")
    @classmethod
    def clean_about(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("lifestyle_tags")
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        result = list(dict.fromkeys(value.strip().lower() for value in values if value.strip()))
        if any(len(value) > 32 for value in result):
            raise ValueError("Lifestyle tags must be 32 characters or fewer.")
        return result

    @model_validator(mode="after")
    def ordered_budget(self):
        if (
            self.budget_min is not None
            and self.budget_max is not None
            and self.budget_min > self.budget_max
        ):
            raise ValueError("Minimum budget cannot exceed maximum budget.")
        return self


class RoommateProfileResponse(RoommateProfileSave):
    id: UUID
    created_at: datetime
    updated_at: datetime


class RoommateCandidateResponse(BaseModel):
    profile_id: UUID
    display_alias: str
    about: str | None
    budget_min: Decimal | None
    budget_max: Decimal | None
    county_id: UUID | None
    county_name: str | None
    town_id: UUID | None
    town_name: str | None
    preferred_move_in: date | None
    lifestyle_tags: list[str]
    shared_preferences: list[str]


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    invite_user_ids: list[UUID] = Field(default_factory=list, max_length=20)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Add a group name.")
        return value

    @field_validator("invite_user_ids")
    @classmethod
    def unique_invites(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Choose each group invitee once.")
        return value


class GroupInvite(BaseModel):
    user_id: UUID


class GroupMemberResponse(BaseModel):
    user_id: UUID
    role: Literal["owner", "member"]
    status: Literal["invited", "active", "declined", "revoked"]
    created_at: datetime
    responded_at: datetime | None


class GroupResponse(BaseModel):
    id: UUID
    name: str
    created_by_user_id: UUID
    status: Literal["invited", "active", "declined", "revoked"]
    members: list[GroupMemberResponse]
    created_at: datetime
    updated_at: datetime


class SharedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    filters: dict[str, Any]

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Add a search name.")
        return value

    @field_validator("filters")
    @classmethod
    def validate_search_filters(cls, value: dict[str, Any]) -> dict[str, Any]:
        return SearchFilters.model_validate(value).model_dump(mode="json", exclude_none=True)


class SharedPropertyAdd(BaseModel):
    property_id: UUID


class SharedComparisonSave(BaseModel):
    name: str = Field(default="Group home comparison", min_length=1, max_length=100)
    property_ids: list[UUID] = Field(min_length=2, max_length=5)

    @model_validator(mode="after")
    def unique_properties(self):
        if len(self.property_ids) != len(set(self.property_ids)):
            raise ValueError("Choose each property once.")
        return self


class SharedPropertyVoteInput(BaseModel):
    vote: Literal["interested", "unsure", "pass"]


class SharedPropertyCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=1000)

    @field_validator("body")
    @classmethod
    def clean_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Add a comment.")
        return value


class SharedTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    details: str | None = Field(default=None, max_length=1000)
    assigned_to_user_id: UUID | None = None
    due_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Add a task title.")
        return value

    @field_validator("due_at")
    @classmethod
    def aware_due_at(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Choose a due time with a timezone.")
        return value


class SharedTaskUpdate(BaseModel):
    status: Literal["open", "done", "cancelled"]


class SharedMoveGoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    target_date: date | None = None
    target_amount: Decimal | None = Field(default=None, gt=0, le=100_000_000)
    share_amount_with_members: bool = False

    @model_validator(mode="after")
    def require_financial_consent(self):
        if self.target_amount is not None and not self.share_amount_with_members:
            raise ValueError("Explicitly consent to sharing the amount with the group.")
        return self


class SharedFinancialConsent(BaseModel):
    consent_to_view_shared_amounts: bool


class RoommateInterestResponse(BaseModel):
    id: UUID
    profile_id: UUID
    requester_user_id: UUID
    target_user_id: UUID
    status: Literal["pending", "accepted", "declined", "withdrawn"]
    created_at: datetime
    updated_at: datetime


class RoommateInterestDecision(BaseModel):
    accept: bool
