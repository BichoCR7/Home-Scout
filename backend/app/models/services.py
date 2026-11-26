"""Service marketplace, booking, maintenance, and private moving-plan records."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class ServiceProviderProfile(Base):
    __tablename__ = "service_provider_profiles"
    __table_args__ = (Index("ix_service_provider_profiles_public", "is_published", "updated_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    public_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    availability_note: Mapped[str | None] = mapped_column(String(300))
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class ServiceOffering(Base):
    __tablename__ = "service_offerings"
    __table_args__ = (
        CheckConstraint(
            "category IN ('movers','cleaners','plumbers','electricians',"
            "'internet_providers','furniture_providers','handymen','home_maintenance','other')",
            name="service_category",
        ),
        CheckConstraint(
            "pricing_model IN ('fixed','hourly','from','quote')", name="service_pricing_model"
        ),
        CheckConstraint("currency = 'KES'", name="service_currency_kes"),
        CheckConstraint(
            "price_amount IS NULL OR price_amount >= 0", name="service_price_nonnegative"
        ),
        CheckConstraint(
            "pricing_model = 'quote' OR price_amount IS NOT NULL", name="service_price_required"
        ),
        Index("ix_service_offerings_category_active", "category", "is_active"),
        Index("ix_service_offerings_provider_active", "provider_user_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    pricing_model: Mapped[str] = mapped_column(String(12), nullable=False)
    price_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    availability_schedule: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class ServiceArea(Base):
    __tablename__ = "service_areas"
    __table_args__ = (
        ForeignKeyConstraint(
            ["town_id", "county_id"],
            ["towns.id", "towns.county_id"],
            name="fk_service_areas_town_county",
            ondelete="CASCADE",
        ),
        UniqueConstraint("offering_id", "county_id", "town_id", name="uq_service_area_location"),
        CheckConstraint(
            "town_id IS NOT NULL OR county_id IS NOT NULL", name="service_area_location_required"
        ),
        Index("ix_service_areas_county_town", "county_id", "town_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offering_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("service_offerings.id", ondelete="CASCADE"), nullable=False
    )
    county_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("counties.id", ondelete="CASCADE")
    )
    town_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))


class ServiceProviderImage(Base):
    __tablename__ = "service_provider_images"
    __table_args__ = (
        Index("ix_service_provider_images_provider", "provider_user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(180), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    caption: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class ServiceBooking(Base):
    __tablename__ = "service_bookings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','rejected','reschedule_proposed',"
            "'rescheduled','cancelled','completed')",
            name="service_booking_status",
        ),
        Index("ix_service_bookings_customer_created", "customer_user_id", "created_at"),
        Index("ix_service_bookings_provider_status", "provider_user_id", "status", "requested_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offering_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("service_offerings.id", ondelete="RESTRICT"), nullable=False
    )
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    provider_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL")
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Africa/Nairobi")
    proposed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reschedule_return_status: Mapped[str | None] = mapped_column(String(16))
    request_details: Mapped[str] = mapped_column(Text, nullable=False)
    provider_response: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class ServiceOrder(Base):
    __tablename__ = "service_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','rejected','reschedule_proposed',"
            "'rescheduled','cancelled','completed')",
            name="service_order_status",
        ),
        Index("ix_service_orders_provider_status", "provider_user_id", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("service_bookings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    provider_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    offering_title_snapshot: Mapped[str] = mapped_column(String(140), nullable=False)
    category_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    estimated_amount_kes: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    pricing_model_snapshot: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class ServiceBookingEvent(Base):
    __tablename__ = "service_booking_events"
    __table_args__ = (
        Index("ix_service_booking_events_booking_created", "booking_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("service_bookings.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class ServiceReview(Base):
    __tablename__ = "service_reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="service_review_rating"),
        CheckConstraint(
            "moderation_status IN ('clear','under_review','removed')",
            name="service_review_moderation_status",
        ),
        UniqueConstraint("booking_id", name="uq_service_review_booking"),
        Index("ix_service_reviews_offering_created", "offering_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("service_bookings.id", ondelete="CASCADE"), nullable=False
    )
    offering_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("service_offerings.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    provider_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review_text: Mapped[str | None] = mapped_column(String(1000))
    moderation_status: Mapped[str] = mapped_column(String(24), nullable=False, default="clear")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class PropertyResidentAccess(Base):
    __tablename__ = "property_resident_access"
    __table_args__ = (
        CheckConstraint("status IN ('active','revoked')", name="resident_access_status"),
        UniqueConstraint("property_id", "resident_user_id", name="uq_property_resident"),
        Index("ix_property_resident_access_resident", "resident_user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    resident_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    granted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="active")
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"
    __table_args__ = (
        CheckConstraint(
            "category IN ('plumbing','electrical','cleaning','internet',"
            "'appliance','structural','other')",
            name="maintenance_category",
        ),
        CheckConstraint(
            "priority IN ('low','normal','high','urgent')", name="maintenance_priority"
        ),
        CheckConstraint(
            "status IN ('submitted','assigned','in_progress','completed','cancelled')",
            name="maintenance_status",
        ),
        Index("ix_maintenance_requests_property_status", "property_id", "status", "created_at"),
        Index("ix_maintenance_requests_provider_status", "assigned_provider_user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    resident_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    assigned_manager_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_provider_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="SET NULL")
    )
    assigned_offering_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("service_offerings.id", ondelete="SET NULL")
    )
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(12), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="submitted")
    completion_record: Mapped[str | None] = mapped_column(String(1000))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class MaintenanceRequestPhoto(Base):
    __tablename__ = "maintenance_request_photos"
    __table_args__ = (
        UniqueConstraint("request_id", "document_id", name="uq_maintenance_photo_document"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("maintenance_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("private_documents.id", ondelete="CASCADE"), nullable=False
    )


class MaintenanceHistory(Base):
    __tablename__ = "maintenance_history"
    __table_args__ = (Index("ix_maintenance_history_request_created", "request_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("maintenance_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class MovePlan(Base):
    __tablename__ = "move_plans"
    __table_args__ = (Index("ix_move_plans_owner_move_date", "owner_user_id", "move_date"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    move_date: Mapped[date | None] = mapped_column(Date)
    target_budget_kes: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class MovePlanTask(Base):
    __tablename__ = "move_plan_tasks"
    __table_args__ = (
        CheckConstraint(
            "category IN ('packing','moving_day','utilities','internet_setup',"
            "'cleaning','furniture','post_move','other')",
            name="move_task_category",
        ),
        CheckConstraint("status IN ('open','completed','cancelled')", name="move_task_status"),
        Index("ix_move_plan_tasks_plan_due", "move_plan_id", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    move_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("move_plans.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    details: Mapped[str | None] = mapped_column(String(1000))
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    provider_offering_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("service_offerings.id", ondelete="SET NULL")
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("service_bookings.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="open")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class MoveBudgetItem(Base):
    __tablename__ = "move_budget_items"
    __table_args__ = (CheckConstraint("amount_kes >= 0", name="move_budget_nonnegative"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    move_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("move_plans.id", ondelete="CASCADE"), nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    amount_kes: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    provider_offering_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("service_offerings.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class RoomSetupItem(Base):
    __tablename__ = "room_setup_items"
    __table_args__ = (
        CheckConstraint("quantity BETWEEN 1 AND 100", name="room_item_quantity"),
        CheckConstraint(
            "estimated_cost_kes IS NULL OR estimated_cost_kes >= 0", name="room_item_cost"
        ),
        CheckConstraint("status IN ('planned','purchased')", name="room_item_status"),
        Index("ix_room_setup_items_plan_room", "move_plan_id", "room_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    move_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("move_plans.id", ondelete="CASCADE"), nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    room_name: Mapped[str] = mapped_column(String(80), nullable=False)
    item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    estimated_cost_kes: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="planned")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
