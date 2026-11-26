"""Validated contracts for marketplace saves, alerts, search history, and enquiries."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class SearchFilters(BaseModel):
    query: str | None = Field(default=None, max_length=120)
    county_id: UUID | None = None
    town_id: UUID | None = None
    neighbourhood_id: UUID | None = None
    rent_min: int | None = Field(default=None, ge=1, le=10_000_000)
    rent_max: int | None = Field(default=None, ge=1, le=10_000_000)
    bedrooms: int | None = Field(default=None, ge=0, le=50)
    bedrooms_min: int | None = Field(default=None, ge=0, le=50)
    property_type: Literal["apartment", "house", "maisonette", "villa", "townhouse"] | None = None
    unit_type: (
        Literal[
            "bedsitter",
            "studio",
            "one_bedroom",
            "two_bedroom",
            "three_bedroom",
            "four_bedroom",
            "five_plus_bedrooms",
        ]
        | None
    ) = None
    furnishing: Literal["furnished", "unfurnished", "semi_furnished"] | None = None
    amenities: list[str] = Field(default_factory=list, max_length=20)
    verified_only: bool = False
    sort_by: Literal["newest", "rent_low", "rent_high", "bedrooms"] = "newest"

    @model_validator(mode="after")
    def validate_ranges(self):
        if (
            self.rent_min is not None
            and self.rent_max is not None
            and self.rent_min > self.rent_max
        ):
            raise ValueError("Minimum rent cannot exceed maximum rent.")
        if self.bedrooms is not None and self.bedrooms_min is not None:
            raise ValueError("Choose exact bedrooms or minimum bedrooms, not both.")
        self.amenities = list(
            dict.fromkeys(item.strip() for item in self.amenities if item.strip())
        )
        if any(len(item) > 80 for item in self.amenities):
            raise ValueError("Amenity names must be 80 characters or fewer.")
        if self.query is not None:
            self.query = self.query.strip() or None
        return self


class SearchHistoryCreate(BaseModel):
    filters: SearchFilters
    result_count: int = Field(ge=0, le=100_000)


class SearchHistoryResponse(BaseModel):
    id: UUID
    filters: SearchFilters
    result_count: int
    created_at: datetime


class PropertyAlertCreate(BaseModel):
    filters: SearchFilters


class PropertyAlertResponse(BaseModel):
    id: UUID
    filters: SearchFilters
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PropertyEnquiryCreate(BaseModel):
    message: str = Field(min_length=10, max_length=2000)

    @model_validator(mode="after")
    def strip_message(self):
        self.message = self.message.strip()
        if len(self.message) < 10:
            raise ValueError("Please include a little more detail in your message.")
        return self


class PropertyEnquiryResponse(BaseModel):
    id: UUID
    property_id: UUID
    property_title: str
    sender_user_id: UUID
    recipient_user_id: UUID
    message: str
    status: Literal["new", "read", "closed"]
    created_at: datetime
    updated_at: datetime


class PropertyEnquiryStatusUpdate(BaseModel):
    status: Literal["read", "closed"]


class PropertyReportCreate(BaseModel):
    reason: Literal[
        "inaccurate_details", "suspected_scam", "unsafe_or_prohibited", "duplicate", "other"
    ]
    details: str | None = Field(default=None, max_length=2000)
    evidence_document_ids: list[UUID] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def clean_details(self):
        if self.details is not None:
            self.details = self.details.strip() or None
        return self


class PropertyReportResponse(BaseModel):
    id: UUID
    property_id: UUID
    property_title: str
    reason: Literal[
        "inaccurate_details", "suspected_scam", "unsafe_or_prohibited", "duplicate", "other"
    ]
    details: str | None
    status: Literal[
        "received", "reviewed", "closed", "in_review", "escalated", "resolved", "dismissed"
    ]
    evidence_document_ids: list[UUID] = Field(default_factory=list)
    updated_at: datetime | None = None
    resolution_message: str | None = None
    created_at: datetime
