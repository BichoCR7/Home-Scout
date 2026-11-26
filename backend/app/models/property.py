"""Property and listing data foundations; records are not inherently verified."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.location import County, Neighbourhood, Town
    from app.models.user import UserAccount


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        ForeignKeyConstraint(
            ["town_id", "county_id"],
            ["towns.id", "towns.county_id"],
            name="fk_properties_town_county",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["neighbourhood_id", "town_id"],
            ["neighbourhoods.id", "neighbourhoods.town_id"],
            name="fk_properties_neighbourhood_town",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "property_type IN ('apartment', 'house', 'maisonette', 'villa', 'townhouse')",
            name="property_type",
        ),
        CheckConstraint(
            "accommodation_type IN ('whole_property', 'shared_accommodation', "
            "'student_accommodation')",
            name="accommodation_type",
        ),
        CheckConstraint(
            "unit_type IN ('bedsitter', 'studio', 'one_bedroom', 'two_bedroom', "
            "'three_bedroom', 'four_bedroom', 'five_plus_bedrooms')",
            name="unit_type",
        ),
        CheckConstraint(
            "(unit_type IN ('bedsitter', 'studio') AND bedrooms = 0) OR "
            "(unit_type = 'one_bedroom' AND bedrooms = 1) OR "
            "(unit_type = 'two_bedroom' AND bedrooms = 2) OR "
            "(unit_type = 'three_bedroom' AND bedrooms = 3) OR "
            "(unit_type = 'four_bedroom' AND bedrooms = 4) OR "
            "(unit_type = 'five_plus_bedrooms' AND bedrooms >= 5)",
            name="bedroom_configuration",
        ),
        CheckConstraint("rent_amount > 0", name="positive_rent"),
        CheckConstraint("currency = 'KES'", name="currency_kes"),
        CheckConstraint("rent_frequency IN ('monthly', 'weekly', 'daily')", name="rent_frequency"),
        CheckConstraint(
            "deposit_amount IS NULL OR deposit_amount >= 0", name="deposit_nonnegative"
        ),
        CheckConstraint("bathrooms > 0 AND bathrooms <= 50", name="bathroom_range"),
        CheckConstraint("size_sqm IS NULL OR size_sqm > 0", name="size_positive"),
        CheckConstraint("parking_spaces >= 0", name="parking_nonnegative"),
        CheckConstraint(
            "parking_spaces = 0 OR parking_available = TRUE", name="parking_spaces_consistent"
        ),
        CheckConstraint(
            "furnishing IN ('furnished', 'unfurnished', 'semi_furnished')", name="furnishing"
        ),
        CheckConstraint(
            "pet_policy IN ('allowed', 'not_allowed', 'case_by_case', 'unknown')", name="pet_policy"
        ),
        CheckConstraint(
            "water_availability IN ('reliable', 'intermittent', 'not_available', 'unknown')",
            name="water_availability",
        ),
        CheckConstraint(
            "verification_status IN ('not_submitted', 'pending', 'verified', "
            "'rejected', 'expired')",
            name="verification_status",
        ),
        CheckConstraint(
            "moderation_status IN ('clear', 'under_review', 'removed')",
            name="moderation_status",
        ),
        CheckConstraint(
            "availability_status IN ('unknown', 'available', 'unavailable')",
            name="availability_status",
        ),
        CheckConstraint(
            "listing_status IN ('draft', 'pending_review', 'published', 'archived', 'rejected')",
            name="listing_status",
        ),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL AND coordinate_source IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL AND coordinate_source IS NOT NULL)",
            name="property_coordinate_pair_source",
        ),
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="property_latitude_range",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="property_longitude_range",
        ),
        CheckConstraint(
            "is_demo = FALSE OR (listing_status = 'draft' AND availability_status = 'unknown' "
            "AND verification_status = 'not_submitted')",
            name="demo_listing_disclosure_state",
        ),
        Index("ix_properties_public_status_rent", "listing_status", "rent_amount"),
        Index("ix_properties_location_status", "county_id", "town_id", "listing_status"),
        Index("ix_properties_owner_created", "owner_user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    property_type: Mapped[str] = mapped_column(String(32), nullable=False)
    accommodation_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="whole_property"
    )
    unit_type: Mapped[str] = mapped_column(String(32), nullable=False)
    rent_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    rent_frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="monthly")
    deposit_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    bedrooms: Mapped[int] = mapped_column(nullable=False)
    bathrooms: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    size_sqm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    parking_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parking_spaces: Mapped[int] = mapped_column(nullable=False, default=0)
    furnishing: Mapped[str] = mapped_column(String(24), nullable=False)
    pet_policy: Mapped[str] = mapped_column(String(24), nullable=False, default="unknown")
    water_availability: Mapped[str] = mapped_column(String(24), nullable=False, default="unknown")
    electricity_available: Mapped[bool | None] = mapped_column(Boolean)
    internet_available: Mapped[bool | None] = mapped_column(Boolean)
    security_features: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    amenities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    county_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("counties.id", ondelete="RESTRICT"), nullable=False
    )
    town_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    neighbourhood_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    address: Mapped[str | None] = mapped_column(String(300))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    coordinate_source: Mapped[str | None] = mapped_column(String(300))
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    authorized_agent_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="SET NULL")
    )
    property_manager_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="SET NULL")
    )
    verification_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="not_submitted"
    )
    moderation_status: Mapped[str] = mapped_column(String(24), nullable=False, default="clear")
    availability_status: Mapped[str] = mapped_column(String(24), nullable=False, default="unknown")
    listing_status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    demo_disclaimer: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    county: Mapped[County] = relationship(foreign_keys=[county_id], viewonly=True)
    town: Mapped[Town] = relationship(foreign_keys=[town_id, county_id], viewonly=True)
    neighbourhood: Mapped[Neighbourhood | None] = relationship(
        foreign_keys=[neighbourhood_id, town_id], viewonly=True
    )
    owner: Mapped[UserAccount] = relationship(foreign_keys=[owner_user_id])
    authorized_agent: Mapped[UserAccount | None] = relationship(
        foreign_keys=[authorized_agent_user_id]
    )
    property_manager: Mapped[UserAccount | None] = relationship(
        foreign_keys=[property_manager_user_id]
    )
    media: Mapped[list[PropertyMedia]] = relationship(
        back_populates="property", cascade="all, delete-orphan", order_by="PropertyMedia.position"
    )
    amenity_records: Mapped[list[PropertyAmenity]] = relationship(
        back_populates="property", cascade="all, delete-orphan"
    )


class PropertyAmenity(Base):
    """Normalized amenity values so marketplace filters work on SQLite and PostgreSQL."""

    __tablename__ = "property_amenities"
    __table_args__ = (Index("ix_property_amenities_name_property", "amenity", "property_id"),)

    property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), primary_key=True
    )
    amenity: Mapped[str] = mapped_column(String(80), primary_key=True)

    property: Mapped[Property] = relationship(back_populates="amenity_records")


class PropertyMedia(Base):
    __tablename__ = "property_media"
    __table_args__ = (
        CheckConstraint("media_type IN ('image', 'video', 'floor_plan')", name="media_type"),
        CheckConstraint("position >= 0", name="media_position_nonnegative"),
        CheckConstraint("byte_size IS NULL OR byte_size > 0", name="media_byte_size_nonnegative"),
        CheckConstraint(
            "(storage_key IS NULL AND mime_type IS NULL AND byte_size IS NULL) OR "
            "(storage_key IS NOT NULL AND mime_type IS NOT NULL AND byte_size IS NOT NULL)",
            name="media_storage_metadata_complete",
        ),
        UniqueConstraint("property_id", "position", name="uq_property_media_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(100))
    mime_type: Mapped[str | None] = mapped_column(String(40))
    byte_size: Mapped[int | None] = mapped_column()
    alt_text: Mapped[str | None] = mapped_column(String(300))
    caption: Mapped[str | None] = mapped_column(String(300))
    position: Mapped[int] = mapped_column(nullable=False, default=0)
    is_illustrative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_credit: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    property: Mapped[Property] = relationship(back_populates="media")
