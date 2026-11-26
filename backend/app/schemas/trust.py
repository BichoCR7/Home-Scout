"""Validation contracts for verification, rental safety, and moderation."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class VerificationSubmit(BaseModel):
    subject_type: Literal["landlord", "agent", "property", "service_provider"]
    property_id: UUID | None = None
    evidence_document_ids: list[UUID] = Field(min_length=1, max_length=10)
    submission_note: str | None = Field(default=None, max_length=1000)

    @field_validator("evidence_document_ids")
    @classmethod
    def require_distinct_evidence(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Each evidence document may only be attached once per submission.")
        return value

    @model_validator(mode="after")
    def validate_subject(self):
        if (self.subject_type == "property") != (self.property_id is not None):
            raise ValueError("Property verification needs one property ID; other requests do not.")
        if self.submission_note is not None:
            self.submission_note = self.submission_note.strip() or None
        return self


class VerificationReview(BaseModel):
    decision: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=1000)
    expires_on: date | None = None

    @model_validator(mode="after")
    def validate_review(self):
        if self.decision == "rejected" and not (self.review_note or "").strip():
            raise ValueError("Give the applicant a reason and next step when rejecting a request.")
        if self.review_note is not None:
            self.review_note = self.review_note.strip() or None
        if self.decision == "rejected" and self.expires_on is not None:
            raise ValueError("A rejected request cannot have an expiry date.")
        return self


class VerificationEvidenceResponse(BaseModel):
    id: UUID
    document_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    label: str
    submission_number: int
    download_path: str


class VerificationHistoryResponse(BaseModel):
    id: UUID
    action: Literal["submitted", "resubmitted", "approved", "rejected", "expired"]
    from_status: str | None
    to_status: str
    submission_number: int
    created_at: datetime


class VerificationCaseResponse(BaseModel):
    id: UUID
    owner_user_id: UUID
    subject_type: Literal["landlord", "agent", "property", "service_provider"]
    subject_user_id: UUID | None
    property_id: UUID | None
    property_title: str | None = None
    status: Literal["pending", "approved", "rejected", "expired"]
    submission_number: int
    expires_on: date | None
    submitted_at: datetime
    updated_at: datetime
    evidence: list[VerificationEvidenceResponse]
    history: list[VerificationHistoryResponse]
    submission_note: str | None = None
    review_note: str | None = None


class ViewingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    property_id: UUID | None = None
    starts_at: datetime
    meeting_point: str = Field(min_length=1, max_length=300)
    trusted_contact_name: str = Field(min_length=1, max_length=120)
    trusted_contact_phone: str = Field(min_length=7, max_length=24)
    notes: str | None = Field(default=None, max_length=1000)
    share_with_user_id: UUID | None = None
    consent_to_share_details: bool = False

    @field_validator("starts_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Viewing time must include a timezone offset.")
        return value

    @field_validator("trusted_contact_phone")
    @classmethod
    def normalize_contact_phone(cls, value: str) -> str:
        normalized = "".join(
            character for character in value if character.isdigit() or character == "+"
        )
        digits = normalized.removeprefix("+")
        if len(digits) < 7 or len(digits) > 15 or ("+" in normalized[1:]):
            raise ValueError("Enter a valid trusted-contact phone number.")
        return normalized

    @model_validator(mode="after")
    def validate_share(self):
        if self.share_with_user_id is not None and not self.consent_to_share_details:
            raise ValueError("Consent is required before sharing viewing details.")
        if self.share_with_user_id is None and self.consent_to_share_details:
            raise ValueError("Choose a HomeScout account before consenting to share details.")
        self.title = self.title.strip()
        self.meeting_point = self.meeting_point.strip()
        self.trusted_contact_name = self.trusted_contact_name.strip()
        return self


class ViewingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    starts_at: datetime | None = None
    meeting_point: str | None = Field(default=None, min_length=1, max_length=300)
    trusted_contact_name: str | None = Field(default=None, min_length=1, max_length=120)
    trusted_contact_phone: str | None = Field(default=None, min_length=7, max_length=24)
    notes: str | None = Field(default=None, max_length=1000)
    share_with_user_id: UUID | None = None
    consent_to_share_details: bool = False

    @model_validator(mode="after")
    def validate_share(self):
        if self.share_with_user_id is not None and not self.consent_to_share_details:
            raise ValueError("Consent is required before sharing viewing details.")
        if self.starts_at is not None and self.starts_at.tzinfo is None:
            raise ValueError("Viewing time must include a timezone offset.")
        return self


class ViewingResponse(BaseModel):
    id: UUID
    owner_user_id: UUID
    property_id: UUID | None
    property_title: str | None
    shared_with_user_id: UUID | None
    details_share_consented: bool
    title: str
    starts_at: datetime
    meeting_point: str
    trusted_contact_name: str
    trusted_contact_phone: str
    notes: str | None
    status: Literal["planned", "checked_in", "checked_out", "cancelled"]
    checked_in_at: datetime | None
    checked_out_at: datetime | None
    is_owner: bool
    created_at: datetime
    updated_at: datetime


class SafetyReportCreate(BaseModel):
    category: Literal[
        "viewing_safety",
        "impersonation",
        "pressure_or_threat",
        "payment_request",
        "privacy",
        "other",
    ]
    viewing_id: UUID | None = None
    property_id: UUID | None = None
    details: str = Field(min_length=10, max_length=2000)
    evidence_document_ids: list[UUID] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_target(self):
        if self.viewing_id is None and self.property_id is None:
            raise ValueError("Link the report to a viewing or property.")
        self.details = self.details.strip()
        if len(self.details) < 10:
            raise ValueError("Add a little more detail so the report can be reviewed.")
        return self


class SafetyReportResponse(BaseModel):
    id: UUID
    viewing_id: UUID | None
    property_id: UUID | None
    category: Literal[
        "viewing_safety",
        "impersonation",
        "pressure_or_threat",
        "payment_request",
        "privacy",
        "other",
    ]
    details: str | None
    status: Literal["received", "in_review", "escalated", "resolved", "dismissed"]
    evidence_document_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class TrustReportReview(BaseModel):
    action: Literal["in_review", "escalated", "resolved", "dismissed"]
    internal_note: str | None = Field(default=None, max_length=2000)
    public_message: str | None = Field(default=None, max_length=500)
    listing_action: Literal["none", "hide", "restore", "remove"] = "none"

    @model_validator(mode="after")
    def validate_action(self):
        if self.action in {"resolved", "dismissed"} and not (self.public_message or "").strip():
            raise ValueError("Add a brief status update for the person who reported this issue.")
        if self.action in {"in_review", "escalated"} and self.listing_action != "none":
            raise ValueError("A listing action requires a resolved moderation decision.")
        if self.public_message is not None:
            self.public_message = self.public_message.strip() or None
        if self.internal_note is not None:
            self.internal_note = self.internal_note.strip() or None
        return self
