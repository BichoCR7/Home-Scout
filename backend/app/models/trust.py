"""Owner-scoped verification, safety planning, and moderation records."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class VerificationCase(Base):
    __tablename__ = "verification_cases"
    __table_args__ = (
        CheckConstraint(
            "(subject_type = 'property' AND property_id IS NOT NULL AND "
            "subject_user_id IS NULL) OR "
            "(subject_type <> 'property' AND subject_user_id IS NOT NULL AND property_id IS NULL)",
            name="verification_subject_shape",
        ),
        CheckConstraint(
            "subject_type IN ('landlord', 'agent', 'property', 'service_provider')",
            name="verification_subject_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired')",
            name="verification_case_status",
        ),
        Index("ix_verification_cases_status_submitted", "status", "submitted_at"),
        Index("ix_verification_cases_owner_updated", "owner_user_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(24), nullable=False)
    subject_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE")
    )
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    submission_number: Mapped[int] = mapped_column(nullable=False, default=1)
    expires_on: Mapped[date | None] = mapped_column(Date)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class VerificationEvidence(Base):
    __tablename__ = "verification_evidence"
    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "submission_number",
            "document_id",
            name="uq_verification_evidence_submission_doc",
        ),
        Index("ix_verification_evidence_case_submission", "case_id", "submission_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("verification_cases.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("private_documents.id", ondelete="CASCADE"), nullable=False
    )
    submission_number: Mapped[int] = mapped_column(nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class VerificationHistory(Base):
    __tablename__ = "verification_history"
    __table_args__ = (
        CheckConstraint(
            "action IN ('submitted', 'resubmitted', 'approved', 'rejected', 'expired')",
            name="verification_history_action",
        ),
        Index("ix_verification_history_case_created", "case_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("verification_cases.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(16))
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    submission_number: Mapped[int] = mapped_column(nullable=False)
    encrypted_note: Mapped[bytes | None] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class SafeViewing(Base):
    __tablename__ = "safe_viewings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'checked_in', 'checked_out', 'cancelled')",
            name="safe_viewing_status",
        ),
        Index("ix_safe_viewings_owner_start", "owner_user_id", "starts_at"),
        Index("ix_safe_viewings_shared_start", "shared_with_user_id", "starts_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL")
    )
    shared_with_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="SET NULL")
    )
    details_share_consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    encrypted_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="planned")
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class SafetyIncidentReport(Base):
    __tablename__ = "safety_incident_reports"
    __table_args__ = (
        CheckConstraint(
            "category IN ('viewing_safety', 'impersonation', 'pressure_or_threat', "
            "'payment_request', 'privacy', 'other')",
            name="safety_report_category",
        ),
        CheckConstraint(
            "status IN ('received', 'in_review', 'escalated', 'resolved', 'dismissed')",
            name="safety_report_status",
        ),
        Index("ix_safety_incident_reports_status_created", "status", "created_at"),
        Index("ix_safety_incident_reports_owner_created", "owner_user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    viewing_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("safe_viewings.id", ondelete="SET NULL")
    )
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL")
    )
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    encrypted_details: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="received")
    staff_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class TrustReportEvidence(Base):
    __tablename__ = "trust_report_evidence"
    __table_args__ = (
        CheckConstraint(
            "(listing_report_id IS NOT NULL AND incident_report_id IS NULL) OR "
            "(listing_report_id IS NULL AND incident_report_id IS NOT NULL)",
            name="trust_report_evidence_target",
        ),
        UniqueConstraint("listing_report_id", "document_id", name="uq_trust_evidence_listing_doc"),
        UniqueConstraint(
            "incident_report_id", "document_id", name="uq_trust_evidence_incident_doc"
        ),
        Index("ix_trust_report_evidence_listing", "listing_report_id"),
        Index("ix_trust_report_evidence_incident", "incident_report_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("property_reports.id", ondelete="CASCADE")
    )
    incident_report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("safety_incident_reports.id", ondelete="CASCADE")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("private_documents.id", ondelete="CASCADE"), nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class SafetyIncidentHistory(Base):
    __tablename__ = "safety_incident_history"
    __table_args__ = (
        CheckConstraint(
            "action IN ('submitted', 'in_review', 'escalated', 'resolved', 'dismissed')",
            name="safety_incident_history_action",
        ),
        Index("ix_safety_incident_history_report_created", "report_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("safety_incident_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
