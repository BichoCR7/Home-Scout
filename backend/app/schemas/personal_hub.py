"""Request and response contracts for private HomeScout hub data."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

Appearance = Literal["system", "light", "dark"]
SavedKind = Literal["property", "search", "neighbourhood", "provider", "lesson", "comparison"]
ScheduleCategory = Literal["task", "viewing", "service", "follow_up", "financial", "lease", "other"]


class ProfileResponse(BaseModel):
    id: UUID
    given_name: str | None
    family_name: str | None
    preferred_name: str | None
    requested_role_code: str | None
    email: str | None
    phone_number: str | None
    location_label: str | None
    bio: str | None
    profile_photo_available: bool
    roles: list[str]
    active_role_code: str | None
    email_verified: bool
    phone_verified: bool


class ProfileUpdate(BaseModel):
    given_name: str | None = Field(default=None, min_length=1, max_length=100)
    family_name: str | None = Field(default=None, max_length=100)
    preferred_name: str | None = Field(default=None, max_length=100)
    phone_number: str | None = Field(default=None, max_length=32)
    location_label: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=1000)


class ActiveRoleUpdate(BaseModel):
    role_code: str = Field(min_length=2, max_length=64)


class PreferenceUpdate(BaseModel):
    appearance: Appearance | None = None
    notification_preferences: dict[str, bool] | None = None
    accessibility_preferences: dict[str, bool] | None = None

    @field_validator("notification_preferences", "accessibility_preferences")
    @classmethod
    def bounded_preferences(cls, value: dict[str, bool] | None) -> dict[str, bool] | None:
        if value is not None and (len(value) > 40 or any(len(key) > 64 for key in value)):
            raise ValueError("Preference set is too large.")
        return value


class PreferenceResponse(BaseModel):
    appearance: Appearance
    active_role_code: str | None
    notification_preferences: dict[str, bool]
    accessibility_preferences: dict[str, bool]


class SavedItemCreate(BaseModel):
    kind: SavedKind
    title: str = Field(min_length=1, max_length=180)
    reference_id: UUID | None = None
    target_path: str | None = Field(default=None, max_length=240)
    personal_note: str | None = Field(default=None, max_length=1000)
    collection_id: UUID | None = None

    @field_validator("target_path")
    @classmethod
    def local_path_only(cls, value: str | None) -> str | None:
        if value is not None and (not value.startswith("/") or "://" in value or "\\" in value):
            raise ValueError("Target must be a local HomeScout path.")
        return value


class SavedItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    personal_note: str | None = Field(default=None, max_length=1000)
    collection_id: UUID | None = None


class SavedItemResponse(BaseModel):
    id: UUID
    kind: str
    reference_id: UUID | None
    title: str
    target_path: str | None
    personal_note: str | None
    collection_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=300)


class CollectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=300)


class CollectionResponse(BaseModel):
    id: UUID
    owner_user_id: UUID
    name: str
    description: str | None
    can_edit: bool = False
    shared_with_user_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CollectionShareCreate(BaseModel):
    user_id: UUID
    can_edit: bool = False


class ActivityCreate(BaseModel):
    event_type: Literal[
        "property_view",
        "saved_item",
        "search",
        "comparison",
        "viewing",
        "lesson",
        "service_booking",
        "report",
        "message",
        "finance",
        "account",
    ]
    title: str = Field(min_length=1, max_length=180)
    details: str | None = Field(default=None, max_length=500)
    target_path: str | None = Field(default=None, max_length=240)

    @field_validator("target_path")
    @classmethod
    def local_path_only(cls, value: str | None) -> str | None:
        if value is not None and (not value.startswith("/") or "://" in value or "\\" in value):
            raise ValueError("Target must be a local HomeScout path.")
        return value


class ActivityResponse(BaseModel):
    id: UUID
    event_type: str
    title: str
    details: str | None
    target_path: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    category: ScheduleCategory = "task"
    starts_at: datetime
    ends_at: datetime | None = None
    timezone: str = Field(default="Africa/Nairobi", min_length=1, max_length=64)
    reminder_minutes: int | None = Field(default=None, ge=0, le=43_200)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Schedule times must include a timezone offset.")
        return value


class ScheduleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    category: ScheduleCategory | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    reminder_minutes: int | None = Field(default=None, ge=0, le=43_200)
    status: Literal["planned", "done", "cancelled"] | None = None

    @field_validator("starts_at", "ends_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Schedule times must include a timezone offset.")
        return value


class ScheduleResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    category: str
    starts_at: datetime
    ends_at: datetime | None
    timezone: str
    reminder_minutes: int | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("starts_at", "ends_at", mode="before")
    @classmethod
    def make_sqlite_datetimes_explicit(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class ManualRecordCreate(BaseModel):
    category: Literal[
        "rent", "deposit", "expense", "receipt", "booking", "order", "viewing", "other"
    ]
    title: str = Field(min_length=1, max_length=160)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    record_date: datetime
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("record_date")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Record date must include a timezone offset.")
        return value


class ManualRecordResponse(BaseModel):
    id: UUID
    category: str
    title: str
    amount: Decimal | None
    currency: str
    record_date: datetime
    notes: str | None
    evidence_status: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("record_date", mode="before")
    @classmethod
    def make_sqlite_date_explicit(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=160)
    category: Literal["account", "property", "safety", "privacy", "technical", "feedback", "other"]
    message: str = Field(min_length=5, max_length=4000)


class SupportMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class SupportMessageResponse(BaseModel):
    id: UUID
    sender_user_id: UUID
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SupportTicketResponse(BaseModel):
    id: UUID
    subject: str
    category: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[SupportMessageResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: UUID
    category: str
    title: str
    body: str
    target_path: str | None
    created_at: datetime
    read_at: datetime | None
    dismissed_at: datetime | None

    model_config = {"from_attributes": True}


class DeletionRequestCreate(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    confirmation: Literal["DELETE"]


class DeletionRequestResponse(BaseModel):
    id: UUID
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    category: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}
