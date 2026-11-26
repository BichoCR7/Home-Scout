"""Validated Kenyan property/listing API contracts."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

PropertyType = Literal["apartment", "house", "maisonette", "villa", "townhouse"]
AccommodationType = Literal["whole_property", "shared_accommodation", "student_accommodation"]
UnitType = Literal[
    "bedsitter",
    "studio",
    "one_bedroom",
    "two_bedroom",
    "three_bedroom",
    "four_bedroom",
    "five_plus_bedrooms",
]
Furnishing = Literal["furnished", "unfurnished", "semi_furnished"]
PetPolicy = Literal["allowed", "not_allowed", "case_by_case", "unknown"]
WaterAvailability = Literal["reliable", "intermittent", "not_available", "unknown"]


class PropertyMediaInput(BaseModel):
    media_type: Literal["image", "video", "floor_plan"]
    url: AnyUrl
    alt_text: str | None = Field(default=None, max_length=300)
    caption: str | None = Field(default=None, max_length=300)
    position: int = Field(default=0, ge=0, le=99)
    is_illustrative: bool = False
    source_credit: str | None = Field(default=None, max_length=300)

    @field_validator("url")
    @classmethod
    def require_https(cls, value: AnyUrl) -> AnyUrl:
        if value.scheme != "https":
            raise ValueError("Media URLs must use HTTPS.")
        return value


class PropertyCreateRequest(BaseModel):
    owner_user_id: UUID | None = None
    title: str = Field(min_length=8, max_length=140)
    description: str = Field(min_length=30, max_length=5000)
    property_type: PropertyType
    accommodation_type: AccommodationType = "whole_property"
    unit_type: UnitType
    rent_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    rent_frequency: Literal["monthly", "weekly", "daily"] = "monthly"
    deposit_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    bedrooms: int = Field(ge=0, le=50)
    bathrooms: Decimal = Field(gt=0, le=50, max_digits=4, decimal_places=1)
    size_sqm: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    parking_available: bool = False
    parking_spaces: int = Field(default=0, ge=0, le=100)
    furnishing: Furnishing
    pet_policy: PetPolicy = "unknown"
    water_availability: WaterAvailability = "unknown"
    electricity_available: bool | None = None
    internet_available: bool | None = None
    security_features: list[str] = Field(default_factory=list, max_length=30)
    amenities: list[str] = Field(default_factory=list, max_length=50)
    county_id: UUID
    town_id: UUID
    neighbourhood_id: UUID | None = None
    address: str | None = Field(default=None, max_length=300)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_digits=9, decimal_places=6)
    coordinate_source: str | None = Field(default=None, min_length=3, max_length=300)
    media: list[PropertyMediaInput] = Field(default_factory=list, max_length=30)

    @field_validator("title", "description")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Value must not be blank.")
        return clean

    @field_validator("address", "coordinate_source")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        return clean or None

    @field_validator("amenities", "security_features")
    @classmethod
    def clean_string_lists(cls, values: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        if any(len(value) > 80 for value in cleaned):
            raise ValueError("Feature names must be 80 characters or fewer.")
        return cleaned

    @model_validator(mode="after")
    def validate_property_relationships(self):
        expected = {
            "bedsitter": 0,
            "studio": 0,
            "one_bedroom": 1,
            "two_bedroom": 2,
            "three_bedroom": 3,
            "four_bedroom": 4,
        }
        if self.unit_type in expected and self.bedrooms != expected[self.unit_type]:
            raise ValueError("Bedroom count must match the selected unit type.")
        if self.unit_type == "five_plus_bedrooms" and self.bedrooms < 5:
            raise ValueError("Five-plus-bedroom units must contain at least five bedrooms.")
        if self.parking_spaces and not self.parking_available:
            raise ValueError("Parking spaces require parking availability.")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be supplied together.")
        if (self.latitude is None) != (self.coordinate_source is None):
            raise ValueError("Coordinates require a source and must not be guessed.")
        media_positions = [item.position for item in self.media]
        if len(media_positions) != len(set(media_positions)):
            raise ValueError("Media positions must be unique within the property.")
        if sum(item.media_type == "image" for item in self.media) > 20:
            raise ValueError("A property may include at most 20 images.")
        if sum(item.media_type == "video" for item in self.media) > 3:
            raise ValueError("A property may include at most 3 videos.")
        if sum(item.media_type == "floor_plan" for item in self.media) > 5:
            raise ValueError("A property may include at most 5 floor plans.")
        return self


class PropertyPatchRequest(BaseModel):
    title: str | None = Field(default=None, min_length=8, max_length=140)
    description: str | None = Field(default=None, min_length=30, max_length=5000)
    property_type: PropertyType | None = None
    accommodation_type: AccommodationType | None = None
    unit_type: UnitType | None = None
    rent_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    rent_frequency: Literal["monthly", "weekly", "daily"] | None = None
    deposit_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    bedrooms: int | None = Field(default=None, ge=0, le=50)
    bathrooms: Decimal | None = Field(default=None, gt=0, le=50, max_digits=4, decimal_places=1)
    size_sqm: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    parking_available: bool | None = None
    parking_spaces: int | None = Field(default=None, ge=0, le=100)
    furnishing: Furnishing | None = None
    pet_policy: PetPolicy | None = None
    water_availability: WaterAvailability | None = None
    electricity_available: bool | None = None
    internet_available: bool | None = None
    security_features: list[str] | None = Field(default=None, max_length=30)
    amenities: list[str] | None = Field(default=None, max_length=50)
    county_id: UUID | None = None
    town_id: UUID | None = None
    neighbourhood_id: UUID | None = None
    address: str | None = Field(default=None, max_length=300)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_digits=9, decimal_places=6)
    coordinate_source: str | None = Field(default=None, min_length=3, max_length=300)
    media: list[PropertyMediaInput] | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one property field must be supplied.")
        return self


class PropertyMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_type: Literal["image", "video", "floor_plan"]
    url: str
    alt_text: str | None
    caption: str | None
    position: int
    is_illustrative: bool
    source_credit: str | None
    mime_type: str | None = None
    byte_size: int | None = None


class PropertyLocationResponse(BaseModel):
    county_id: UUID
    county_name: str
    town_id: UUID
    town_name: str
    neighbourhood_id: UUID | None
    neighbourhood_name: str | None


class PropertyResponse(BaseModel):
    id: UUID
    title: str
    description: str
    property_type: PropertyType
    accommodation_type: AccommodationType
    unit_type: UnitType
    rent_amount: Decimal
    currency: Literal["KES"]
    rent_frequency: Literal["monthly", "weekly", "daily"]
    deposit_amount: Decimal | None
    bedrooms: int
    bathrooms: Decimal
    size_sqm: Decimal | None
    parking_available: bool
    parking_spaces: int
    furnishing: Furnishing
    pet_policy: PetPolicy
    water_availability: WaterAvailability
    electricity_available: bool | None
    internet_available: bool | None
    security_features: list[str]
    amenities: list[str]
    location: PropertyLocationResponse
    address: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    coordinate_source: str | None
    owner_user_id: UUID
    authorized_agent_user_id: UUID | None
    property_manager_user_id: UUID | None
    verification_status: Literal["not_submitted", "pending", "verified", "rejected", "expired"]
    moderation_status: Literal["clear", "under_review", "removed"] = "clear"
    availability_status: Literal["unknown", "available", "unavailable"]
    listing_status: Literal["draft", "pending_review", "published", "archived", "rejected"]
    is_demo: bool
    demo_disclaimer: str | None
    media: list[PropertyMediaResponse]
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    archived_at: datetime | None


class PropertyListResponse(BaseModel):
    items: list[PropertyResponse]
    total: int
    limit: int
    offset: int


class ListingAgentAssignment(BaseModel):
    agent_user_id: UUID | None = None
    manager_user_id: UUID | None = None

    @model_validator(mode="after")
    def select_one_assignment(self):
        if (self.agent_user_id is None) == (self.manager_user_id is None):
            raise ValueError("Supply either an agent or a manager assignment.")
        return self


class ListingMandateCreate(BaseModel):
    agent_user_id: UUID


class ListingMandateResponse(BaseModel):
    owner_user_id: UUID
    agent_user_id: UUID
    is_active: bool
    created_at: datetime


class AvailabilityUpdate(BaseModel):
    availability_status: Literal["available", "unavailable", "unknown"]
