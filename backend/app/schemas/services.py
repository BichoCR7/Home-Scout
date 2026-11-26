"""Validation and response contracts for HomeScout services and moving tools."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ServiceCategory = Literal[
    "movers",
    "cleaners",
    "plumbers",
    "electricians",
    "internet_providers",
    "furniture_providers",
    "handymen",
    "home_maintenance",
    "other",
]
PricingModel = Literal["fixed", "hourly", "from", "quote"]
BookingStatus = Literal[
    "pending",
    "accepted",
    "rejected",
    "reschedule_proposed",
    "rescheduled",
    "cancelled",
    "completed",
]
MaintenanceCategory = Literal[
    "plumbing",
    "electrical",
    "cleaning",
    "internet",
    "appliance",
    "structural",
    "other",
]
MaintenancePriority = Literal["low", "normal", "high", "urgent"]
MoveTaskCategory = Literal[
    "packing",
    "moving_day",
    "utilities",
    "internet_setup",
    "cleaning",
    "furniture",
    "post_move",
    "other",
]


def _clean(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("This field must not be blank.")
    return cleaned


class ServiceAreaInput(BaseModel):
    county_id: UUID | None = None
    town_id: UUID | None = None

    @model_validator(mode="after")
    def location_required(self):
        if self.county_id is None and self.town_id is None:
            raise ValueError("Choose a county or town for this service area.")
        if self.town_id is not None and self.county_id is None:
            raise ValueError("A town service area must include its county.")
        return self


class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProviderProfileSave(BaseModel):
    public_name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=3000)
    availability_note: str | None = Field(default=None, max_length=300)
    is_published: bool = False

    @field_validator("public_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return _clean(value)

    @field_validator("description", "availability_note")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class ProviderProfileResponse(ServiceResponse):
    id: UUID
    provider_user_id: UUID
    public_name: str
    description: str
    availability_note: str | None
    is_published: bool
    verification_status: Literal["not_submitted", "pending", "verified", "rejected", "expired"]
    service_areas: list[dict[str, str | None]]
    image_ids: list[UUID]
    average_rating: float | None
    review_count: int
    created_at: datetime
    updated_at: datetime


class ServiceOfferingSave(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    category: ServiceCategory
    description: str = Field(min_length=10, max_length=3000)
    pricing_model: PricingModel
    price_amount: Decimal | None = Field(
        default=None, ge=0, le=100_000_000, max_digits=12, decimal_places=2
    )
    estimated_duration_minutes: int | None = Field(default=None, ge=15, le=100_800)
    availability_schedule: dict[str, list[list[str]]] = Field(default_factory=dict, max_length=7)
    service_areas: list[ServiceAreaInput] = Field(default_factory=list, max_length=50)
    is_active: bool = True

    @field_validator("title", "description")
    @classmethod
    def clean_required(cls, value: str) -> str:
        return _clean(value)

    @field_validator("availability_schedule")
    @classmethod
    def validate_schedule(cls, value: dict[str, list[list[str]]]) -> dict[str, list[list[str]]]:
        allowed_days = {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        }
        import re

        time_pattern = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
        for day, windows in value.items():
            if day.lower() not in allowed_days:
                raise ValueError("Availability days must use full English weekday names.")
            for window in windows:
                if (
                    len(window) != 2
                    or not all(time_pattern.fullmatch(part) for part in window)
                    or window[0] >= window[1]
                ):
                    raise ValueError("Each availability window needs valid start and end times.")
        return {day.lower(): windows for day, windows in value.items()}

    @model_validator(mode="after")
    def pricing_is_consistent(self):
        if self.pricing_model == "quote" and self.price_amount is not None:
            raise ValueError("Quote pricing should not include a fixed price.")
        if self.pricing_model != "quote" and self.price_amount is None:
            raise ValueError("Enter the listed KES price for this pricing model.")
        return self

    @field_validator("service_areas")
    @classmethod
    def unique_areas(cls, value: list[ServiceAreaInput]) -> list[ServiceAreaInput]:
        if not value:
            raise ValueError("Add at least one county or town service area.")
        keys = [(item.county_id, item.town_id) for item in value]
        if len(set(keys)) != len(keys):
            raise ValueError("Choose each service area once.")
        return value


class ServiceOfferingResponse(ServiceResponse):
    id: UUID
    provider_user_id: UUID
    provider_name: str
    provider_verification_status: Literal[
        "not_submitted", "pending", "verified", "rejected", "expired"
    ]
    title: str
    category: ServiceCategory
    description: str
    pricing_model: PricingModel
    price_amount: Decimal | None
    currency: Literal["KES"]
    estimated_duration_minutes: int | None
    availability_schedule: dict[str, list[list[str]]]
    service_areas: list[dict[str, str | None]]
    average_rating: float | None
    review_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProviderImageResponse(ServiceResponse):
    id: UUID
    provider_user_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    caption: str | None
    url: str
    created_at: datetime


class BookingCreate(BaseModel):
    offering_id: UUID
    requested_at: datetime
    timezone: str = "Africa/Nairobi"
    request_details: str = Field(min_length=10, max_length=2000)
    property_id: UUID | None = None

    @field_validator("requested_at")
    @classmethod
    def aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Choose a date and time with a timezone.")
        return value

    @field_validator("request_details")
    @classmethod
    def clean_details(cls, value: str) -> str:
        return _clean(value)


class BookingAction(BaseModel):
    action: Literal[
        "accept",
        "reject",
        "propose_reschedule",
        "accept_reschedule",
        "decline_reschedule",
        "cancel",
        "complete",
    ]
    proposed_at: datetime | None = None
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def action_fields(self):
        if self.action == "propose_reschedule":
            if (
                self.proposed_at is None
                or self.proposed_at.tzinfo is None
                or self.proposed_at.utcoffset() is None
            ):
                raise ValueError("A timezone-aware proposed date and time are required.")
        elif self.proposed_at is not None:
            raise ValueError("A proposed time is only used when rescheduling.")
        if self.note is not None:
            self.note = self.note.strip() or None
        return self


class BookingResponse(ServiceResponse):
    id: UUID
    offering_id: UUID
    offering_title: str
    category: ServiceCategory
    customer_user_id: UUID
    provider_user_id: UUID
    provider_name: str
    property_id: UUID | None
    requested_at: datetime
    proposed_at: datetime | None
    timezone: str
    request_details: str
    provider_response: str | None
    status: BookingStatus
    is_customer: bool
    order_id: UUID | None
    estimated_amount_kes: Decimal | None
    currency: Literal["KES"]
    created_at: datetime
    updated_at: datetime


class BookingHistoryResponse(ServiceResponse):
    id: UUID
    action: str
    details: str | None
    created_at: datetime


class OrderResponse(ServiceResponse):
    id: UUID
    booking_id: UUID
    offering_title_snapshot: str
    category_snapshot: ServiceCategory
    estimated_amount_kes: Decimal | None
    pricing_model_snapshot: PricingModel
    status: BookingStatus
    created_at: datetime
    updated_at: datetime


class ServiceReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_text: str | None = Field(default=None, max_length=1000)

    @field_validator("review_text")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ServiceReviewResponse(ServiceResponse):
    id: UUID
    booking_id: UUID
    offering_id: UUID
    reviewer_user_id: UUID
    rating: int
    review_text: str | None
    created_at: datetime


class ResidentAccessCreate(BaseModel):
    resident_user_id: UUID


class ResidentAccessResponse(ServiceResponse):
    id: UUID
    property_id: UUID
    resident_user_id: UUID
    status: Literal["active", "revoked"]
    granted_at: datetime
    revoked_at: datetime | None


class ResidentPropertyResponse(ServiceResponse):
    id: UUID
    title: str
    location: str


class MaintenanceCreate(BaseModel):
    property_id: UUID
    category: MaintenanceCategory
    description: str = Field(min_length=10, max_length=3000)
    priority: MaintenancePriority = "normal"
    photo_document_ids: list[UUID] = Field(default_factory=list, max_length=8)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        return _clean(value)

    @field_validator("photo_document_ids")
    @classmethod
    def unique_photos(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Choose each photo once.")
        return value


class MaintenanceAssignment(BaseModel):
    provider_user_id: UUID | None = None
    offering_id: UUID | None = None


class MaintenanceAction(BaseModel):
    action: Literal["start", "complete", "cancel"]
    note: str | None = Field(default=None, max_length=1000)


class MaintenanceResponse(ServiceResponse):
    id: UUID
    property_id: UUID
    property_title: str
    resident_user_id: UUID
    assigned_manager_user_id: UUID
    assigned_provider_user_id: UUID | None
    assigned_offering_id: UUID | None
    category: MaintenanceCategory
    description: str
    priority: MaintenancePriority
    status: Literal["submitted", "assigned", "in_progress", "completed", "cancelled"]
    completion_record: str | None
    photo_document_ids: list[UUID]
    history: list[dict[str, object]]
    created_at: datetime
    updated_at: datetime


class MovePlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    move_date: date | None = None
    target_budget_kes: Decimal | None = Field(
        default=None, ge=0, le=100_000_000, max_digits=12, decimal_places=2
    )

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return _clean(value)


class MovePlanResponse(ServiceResponse):
    id: UUID
    title: str
    move_date: date | None
    target_budget_kes: Decimal | None
    created_at: datetime
    updated_at: datetime


class MoveTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    details: str | None = Field(default=None, max_length=1000)
    category: MoveTaskCategory
    due_date: date | None = None
    provider_offering_id: UUID | None = None
    booking_id: UUID | None = None


class MoveTaskStatus(BaseModel):
    status: Literal["open", "completed", "cancelled"]


class MoveTaskResponse(ServiceResponse):
    id: UUID
    move_plan_id: UUID
    title: str
    details: str | None
    category: MoveTaskCategory
    due_date: date | None
    provider_offering_id: UUID | None
    booking_id: UUID | None
    status: Literal["open", "completed", "cancelled"]
    completed_at: datetime | None


class MoveBudgetCreate(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    amount_kes: Decimal = Field(ge=0, le=100_000_000, max_digits=12, decimal_places=2)
    provider_offering_id: UUID | None = None


class MoveBudgetResponse(ServiceResponse):
    id: UUID
    title: str
    amount_kes: Decimal
    provider_offering_id: UUID | None
    created_at: datetime


class RoomSetupCreate(BaseModel):
    room_name: str = Field(min_length=1, max_length=80)
    item_name: str = Field(min_length=1, max_length=120)
    quantity: int = Field(default=1, ge=1, le=100)
    estimated_cost_kes: Decimal | None = Field(
        default=None, ge=0, le=100_000_000, max_digits=12, decimal_places=2
    )


class RoomSetupResponse(ServiceResponse):
    id: UUID
    room_name: str
    item_name: str
    quantity: int
    estimated_cost_kes: Decimal | None
    status: Literal["planned", "purchased"]
    created_at: datetime


class RoomSetupStatus(BaseModel):
    status: Literal["planned", "purchased"]
