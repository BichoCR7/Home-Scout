"""Validated location hierarchy API contracts."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CountyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    slug: str
    aliases: list[str]
    country_name: str = "Kenya"


class TownResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    county_id: UUID
    name: str
    slug: str
    kind: Literal["city", "town", "municipality", "locality"]
    aliases: list[str]
    latitude: float | None
    longitude: float | None
    coordinate_source: str | None


class NeighbourhoodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    town_id: UUID
    name: str
    slug: str
    aliases: list[str]
    latitude: float | None
    longitude: float | None
    coordinate_source: str | None


class LocationSearchResult(BaseModel):
    id: UUID
    kind: Literal["county", "town", "neighbourhood"]
    name: str
    county_id: UUID
    county_name: str
    town_id: UUID | None = None
    town_name: str | None = None


class MapGeocodeResult(BaseModel):
    id: str
    name: str
    label: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class LocationCreateBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    coordinate_source: str | None = Field(default=None, min_length=3, max_length=300)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_name: str = Field(min_length=3, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)

    @field_validator("name", "source_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Value must not be blank.")
        return clean

    @field_validator("aliases")
    @classmethod
    def clean_aliases(cls, values: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        if any(len(value) > 120 for value in cleaned):
            raise ValueError("Aliases must be 120 characters or fewer.")
        return cleaned

    @model_validator(mode="after")
    def coordinate_pair_and_source(self):
        values_present = (self.latitude is not None, self.longitude is not None)
        if values_present[0] != values_present[1]:
            raise ValueError("Latitude and longitude must be supplied together.")
        if values_present[0] != bool(self.coordinate_source):
            raise ValueError("Coordinates require their source, and a source requires coordinates.")
        return self


class TownCreateRequest(LocationCreateBase):
    county_id: UUID
    kind: Literal["city", "town", "municipality", "locality"] = "town"


class NeighbourhoodCreateRequest(LocationCreateBase):
    town_id: UUID
