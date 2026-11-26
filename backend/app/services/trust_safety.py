"""Manual verification, private viewing plans, evidence, and moderation workflows."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from statistics import median
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.data_access.properties import PropertyDataAccess
from app.models.audit import AuditEvent
from app.models.marketplace import (
    PropertyListingMandate,
    PropertyReport,
    PropertyReportReview,
)
from app.models.personal_hub import PersonalActivity, PrivateDocument
from app.models.property import Property
from app.models.settings import ApplicationSetting
from app.models.trust import (
    SafetyIncidentHistory,
    SafetyIncidentReport,
    SafeViewing,
    TrustReportEvidence,
    VerificationCase,
    VerificationEvidence,
    VerificationHistory,
)
from app.models.user import UserAccount
from app.schemas.marketplace import PropertyReportCreate, PropertyReportResponse
from app.schemas.trust import (
    SafetyReportCreate,
    SafetyReportResponse,
    TrustReportReview,
    VerificationCaseResponse,
    VerificationReview,
    VerificationSubmit,
    ViewingCreate,
    ViewingResponse,
    ViewingUpdate,
)
from app.services.authorization import AuthorizationService
from app.services.trust_cipher import TrustCipher


class TrustSafetyService:
    def __init__(self, cipher: TrustCipher) -> None:
        self.cipher = cipher
        self.authorization = AuthorizationService()
        self.properties = PropertyDataAccess()

    def submit_verification(
        self, session: Session, owner_id: UUID, body: VerificationSubmit
    ) -> VerificationCaseResponse:
        self.authorization.require_permission(
            session,
            user_id=owner_id,
            permission_code="verification:create:self",
            resource_owner_id=owner_id,
        )
        self._require_active_user(session, owner_id)
        if body.subject_type == "property":
            property_ = session.get(Property, body.property_id)
            if (
                property_ is None
                or property_.is_demo
                or not self._can_manage_property(session, owner_id, property_)
            ):
                raise self.not_found(
                    "The property is not available for verification by this account."
                )
            subject_user_id = None
        else:
            allowed_roles = {
                "landlord": {"landlord"},
                "agent": {"real_estate_agent"},
                "service_provider": {"service_provider"},
            }[body.subject_type]
            if not (allowed_roles & set(self.authorization.role_codes(session, owner_id))):
                raise ApiError(
                    403,
                    "verification_role_required",
                    "This account needs the matching approved role before it can "
                    "request verification.",
                )
            subject_user_id = owner_id
            property_ = None

        self._validate_verification_documents(session, owner_id, body.evidence_document_ids)
        current_query = select(VerificationCase).where(
            VerificationCase.subject_type == body.subject_type,
            VerificationCase.owner_user_id == owner_id,
        )
        current_query = (
            current_query.where(VerificationCase.property_id == body.property_id)
            if body.subject_type == "property"
            else current_query.where(VerificationCase.subject_user_id == subject_user_id)
        )
        case = session.scalar(current_query.order_by(VerificationCase.updated_at.desc()).limit(1))
        now = datetime.now(UTC)
        action = "submitted"
        previous_status = None
        if case is not None:
            self._expire_case(session, case, now.date())
            if case.status in {"pending", "approved"}:
                raise ApiError(
                    409,
                    "verification_already_active",
                    "A pending or approved verification already exists for this record.",
                )
            previous_status = case.status
            action = "resubmitted"
            case.submission_number += 1
            case.status = "pending"
            case.expires_on = None
            case.submitted_at = now
            case.reviewed_at = None
            case.updated_at = now
        else:
            case = VerificationCase(
                owner_user_id=owner_id,
                subject_type=body.subject_type,
                subject_user_id=subject_user_id,
                property_id=body.property_id,
                status="pending",
                submission_number=1,
                submitted_at=now,
                updated_at=now,
            )
            session.add(case)
            session.flush()

        self._replace_verification_evidence(session, case, owner_id, body.evidence_document_ids)
        session.add(
            VerificationHistory(
                case_id=case.id,
                actor_user_id=owner_id,
                action=action,
                from_status=previous_status,
                to_status="pending",
                submission_number=case.submission_number,
                encrypted_note=self.cipher.encrypt(owner_id, {"note": body.submission_note})
                if body.submission_note
                else None,
                created_at=now,
            )
        )
        if property_ is not None:
            property_.verification_status = "pending"
        session.add(
            AuditEvent(
                actor_user_id=owner_id,
                event_type="trust.verification_submitted",
                subject_type=body.subject_type,
                subject_id=str(body.property_id or owner_id),
                metadata_json={
                    "case_id": str(case.id),
                    "submission_number": case.submission_number,
                },
            )
        )
        session.commit()
        return self._verification_view(session, case, include_staff=False)

    def list_my_verifications(
        self, session: Session, owner_id: UUID
    ) -> list[VerificationCaseResponse]:
        rows = list(
            session.scalars(
                select(VerificationCase)
                .where(VerificationCase.owner_user_id == owner_id)
                .order_by(VerificationCase.updated_at.desc())
            )
        )
        changed = False
        for row in rows:
            changed = self._expire_case(session, row, date.today()) or changed
        if changed:
            session.commit()
        return [self._verification_view(session, row, include_staff=False) for row in rows]

    def verification_queue(
        self, session: Session, reviewer_id: UUID
    ) -> list[VerificationCaseResponse]:
        self._require_verification_reviewer(session, reviewer_id, "approve")
        rows = list(
            session.scalars(
                select(VerificationCase)
                .where(VerificationCase.status == "pending")
                .order_by(VerificationCase.submitted_at.asc())
                .limit(300)
            )
        )
        changed = False
        for row in rows:
            changed = self._expire_case(session, row, date.today()) or changed
        if changed:
            session.commit()
        return [self._verification_view(session, row, include_staff=True) for row in rows]

    def review_verification(
        self,
        session: Session,
        reviewer_id: UUID,
        case_id: UUID,
        body: VerificationReview,
        request_id: str | None = None,
    ) -> VerificationCaseResponse:
        case = session.get(VerificationCase, case_id)
        if case is None:
            raise self.not_found("The verification request was not found.")
        permission_action = "approve" if body.decision == "approved" else "reject"
        self._require_verification_reviewer(session, reviewer_id, permission_action)
        if case.status != "pending":
            raise ApiError(
                409, "verification_not_pending", "Only a pending verification can be reviewed."
            )
        if (
            body.decision == "approved"
            and body.expires_on is not None
            and body.expires_on <= date.today()
        ):
            raise ApiError(
                422, "verification_expiry_past", "The expiry date must be in the future."
            )

        old_status = case.status
        case.status = body.decision
        case.expires_on = body.expires_on if body.decision == "approved" else None
        case.reviewed_at = datetime.now(UTC)
        case.updated_at = case.reviewed_at
        if case.property_id is not None:
            property_ = session.get(Property, case.property_id)
            if property_ is not None:
                property_.verification_status = (
                    "verified" if body.decision == "approved" else "rejected"
                )
        session.add(
            VerificationHistory(
                case_id=case.id,
                actor_user_id=reviewer_id,
                action=body.decision,
                from_status=old_status,
                to_status=body.decision,
                submission_number=case.submission_number,
                encrypted_note=self.cipher.encrypt(case.owner_user_id, {"note": body.review_note})
                if body.review_note
                else None,
            )
        )
        session.add(
            AuditEvent(
                actor_user_id=reviewer_id,
                event_type=f"trust.verification_{body.decision}",
                subject_type=case.subject_type,
                subject_id=str(case.property_id or case.subject_user_id),
                request_id=request_id,
                metadata_json={
                    "case_id": str(case.id),
                    "submission_number": case.submission_number,
                },
            )
        )
        session.commit()
        return self._verification_view(session, case, include_staff=True)

    def verification_evidence_document(
        self, session: Session, reviewer_id: UUID, case_id: UUID, evidence_id: UUID
    ) -> PrivateDocument:
        self._require_verification_reviewer(session, reviewer_id, "approve")
        case = session.get(VerificationCase, case_id)
        evidence = session.get(VerificationEvidence, evidence_id)
        if case is None or evidence is None or evidence.case_id != case_id:
            raise self.not_found("The verification evidence was not found.")
        document = session.get(PrivateDocument, evidence.document_id)
        if document is None:
            raise self.not_found("The verification evidence file is no longer available.")
        session.add(
            AuditEvent(
                actor_user_id=reviewer_id,
                event_type="trust.verification_evidence_viewed",
                subject_type="verification_case",
                subject_id=str(case.id),
                metadata_json={"evidence_id": str(evidence.id)},
            )
        )
        session.commit()
        return document

    def report_evidence_document(
        self,
        session: Session,
        reviewer_id: UUID,
        report_type: str,
        report_id: UUID,
        document_id: UUID,
    ) -> PrivateDocument:
        self._require_moderation_view(session, reviewer_id)
        evidence = session.scalar(
            select(TrustReportEvidence).where(
                TrustReportEvidence.document_id == document_id,
                TrustReportEvidence.listing_report_id == report_id
                if report_type == "listing"
                else TrustReportEvidence.incident_report_id == report_id,
            )
        )
        if evidence is None or report_type not in {"listing", "safety_incident"}:
            raise self.not_found("The report evidence was not found.")
        document = session.get(PrivateDocument, evidence.document_id)
        if document is None:
            raise self.not_found("The report evidence file is no longer available.")
        session.add(
            AuditEvent(
                actor_user_id=reviewer_id,
                event_type="trust.report_evidence_viewed",
                subject_type=f"{report_type}_report",
                subject_id=str(report_id),
                metadata_json={"document_id": str(document_id)},
            )
        )
        session.commit()
        return document

    def report_listing(
        self,
        session: Session,
        reporter_id: UUID,
        property_id: UUID,
        body: PropertyReportCreate,
        request_id: str | None = None,
    ) -> PropertyReportResponse:
        self.authorization.require_permission(
            session,
            user_id=reporter_id,
            permission_code="property:report:self",
            resource_owner_id=reporter_id,
        )
        property_ = self.properties.list_public_by_id(session, property_id, include_demo=False)
        if property_ is None:
            raise self.not_found("This published listing is not available to report.")
        if property_.owner_user_id == reporter_id:
            raise ApiError(
                409, "own_listing_report_not_allowed", "You cannot report your own listing."
            )
        if session.scalar(
            select(PropertyReport.id).where(
                PropertyReport.property_id == property_id,
                PropertyReport.reporter_user_id == reporter_id,
            )
        ):
            raise ApiError(
                409, "listing_already_reported", "You have already reported this listing."
            )
        self._validate_evidence_documents(session, reporter_id, body.evidence_document_ids)
        now = datetime.now(UTC)
        report = PropertyReport(
            property_id=property_id,
            reporter_user_id=reporter_id,
            reason=body.reason,
            details=None,
            encrypted_details=self.cipher.encrypt(reporter_id, {"details": body.details})
            if body.details
            else None,
            status="received",
            created_at=now,
            updated_at=now,
        )
        session.add(report)
        session.flush()
        self._link_report_evidence(
            session, "listing", report.id, reporter_id, body.evidence_document_ids
        )
        session.add(
            AuditEvent(
                actor_user_id=reporter_id,
                event_type="property.report_submitted",
                subject_type="property",
                subject_id=str(property_id),
                request_id=request_id,
                metadata_json={"report_id": str(report.id), "reason": report.reason},
            )
        )
        session.add(
            PersonalActivity(
                owner_user_id=reporter_id,
                event_type="report",
                title=f"Reported {property_.title}"[:180],
                details="The report was recorded for review.",
                target_path=f"/property/{property_.id}",
            )
        )
        session.commit()
        return self._property_report_view(session, report, property_)

    def reports_by_user(self, session: Session, reporter_id: UUID) -> list[PropertyReportResponse]:
        rows = list(
            session.scalars(
                select(PropertyReport)
                .where(PropertyReport.reporter_user_id == reporter_id)
                .order_by(PropertyReport.created_at.desc())
            )
        )
        return [
            self._property_report_view(session, row, session.get(Property, row.property_id))
            for row in rows
        ]

    def add_listing_report_evidence(
        self, session: Session, reporter_id: UUID, report_id: UUID, document_id: UUID
    ) -> PropertyReportResponse:
        report = session.get(PropertyReport, report_id)
        if report is None or report.reporter_user_id != reporter_id:
            raise self.not_found("The report was not found.")
        if report.status in {"resolved", "dismissed", "closed"}:
            raise ApiError(
                409, "report_closed", "Evidence can no longer be added to a closed report."
            )
        self._validate_evidence_documents(session, reporter_id, [document_id])
        self._link_report_evidence(session, "listing", report.id, reporter_id, [document_id])
        session.commit()
        return self._property_report_view(
            session, report, session.get(Property, report.property_id)
        )

    def list_moderation_queue(self, session: Session, reviewer_id: UUID) -> list[dict[str, Any]]:
        self._require_moderation_view(session, reviewer_id)
        listing_rows = list(
            session.scalars(
                select(PropertyReport)
                .where(PropertyReport.status.in_(("received", "in_review", "escalated")))
                .order_by(PropertyReport.created_at.asc())
                .limit(300)
            )
        )
        incident_rows = list(
            session.scalars(
                select(SafetyIncidentReport)
                .where(SafetyIncidentReport.status.in_(("received", "in_review", "escalated")))
                .order_by(SafetyIncidentReport.created_at.asc())
                .limit(300)
            )
        )
        items: list[dict[str, Any]] = []
        for row in listing_rows:
            property_ = session.get(Property, row.property_id)
            items.append(
                {
                    "report_type": "listing",
                    "id": row.id,
                    "reporter_user_id": row.reporter_user_id,
                    "property_id": row.property_id,
                    "property_title": property_.title if property_ else "Listing",
                    "reason": row.reason,
                    "details": self._report_details(
                        row.reporter_user_id, row.encrypted_details, row.details
                    ),
                    "status": row.status,
                    "evidence_document_ids": self._evidence_ids(session, "listing", row.id),
                    "signals": self._listing_signals(session, property_) if property_ else [],
                    "created_at": row.created_at,
                    "history": self._listing_history(session, row.id),
                }
            )
        for row in incident_rows:
            items.append(
                {
                    "report_type": "safety_incident",
                    "id": row.id,
                    "reporter_user_id": row.owner_user_id,
                    "property_id": row.property_id,
                    "property_title": (
                        session.get(Property, row.property_id).title
                        if row.property_id and session.get(Property, row.property_id)
                        else None
                    ),
                    "reason": row.category,
                    "details": self.cipher.decrypt(row.owner_user_id, row.encrypted_details).get(
                        "details"
                    ),
                    "status": row.status,
                    "evidence_document_ids": self._evidence_ids(session, "incident", row.id),
                    "signals": [],
                    "created_at": row.created_at,
                    "history": self._incident_history(session, row.id),
                }
            )
        return sorted(items, key=lambda item: item["created_at"])

    def review_moderation_report(
        self,
        session: Session,
        reviewer_id: UUID,
        report_type: str,
        report_id: UUID,
        body: TrustReportReview,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_moderation_action(session, reviewer_id, body.action)
        note_setting = session.get(ApplicationSetting, "moderation.require_internal_note")
        if (
            note_setting is not None
            and note_setting.value.get("value", False)
            and not body.internal_note
        ):
            raise ApiError(
                422,
                "moderation_note_required",
                "Add an internal review note before submitting this decision.",
            )
        if body.listing_action != "none" and body.action != "resolved":
            raise ApiError(
                422,
                "listing_action_requires_resolution",
                "Resolve the report before changing listing visibility.",
            )
        now = datetime.now(UTC)
        if report_type == "listing":
            row = session.get(PropertyReport, report_id)
            if row is None:
                raise self.not_found("The listing report was not found.")
            if row.status in {"resolved", "dismissed", "closed"}:
                raise ApiError(409, "report_closed", "This report has already been resolved.")
            prop = session.get(Property, row.property_id)
            if body.listing_action != "none" and prop is None:
                raise ApiError(409, "property_unavailable", "The property record no longer exists.")
            if body.listing_action == "hide":
                prop.moderation_status = "under_review"
            elif body.listing_action == "restore":
                prop.moderation_status = "clear"
            elif body.listing_action == "remove":
                prop.moderation_status = "removed"
            row.status = body.action
            row.staff_note = body.internal_note
            row.resolution_message = body.public_message
            row.reviewed_by_user_id = reviewer_id
            row.updated_at = now
            session.add(
                PropertyReportReview(
                    report_id=row.id,
                    actor_user_id=reviewer_id,
                    action=body.action,
                    internal_note=body.internal_note,
                    public_message=body.public_message,
                    created_at=now,
                )
            )
            session.add(
                AuditEvent(
                    actor_user_id=reviewer_id,
                    event_type=f"trust.listing_report_{body.action}",
                    subject_type="property_report",
                    subject_id=str(row.id),
                    request_id=request_id,
                    metadata_json={"listing_action": body.listing_action},
                )
            )
        elif report_type == "safety_incident":
            if body.listing_action != "none":
                raise ApiError(
                    422,
                    "listing_action_not_applicable",
                    "A viewing incident cannot change property visibility through this action.",
                )
            row = session.get(SafetyIncidentReport, report_id)
            if row is None:
                raise self.not_found("The safety report was not found.")
            if row.status in {"resolved", "dismissed"}:
                raise ApiError(409, "report_closed", "This report has already been resolved.")
            row.status = body.action
            row.staff_note = body.internal_note
            row.reviewed_by_user_id = reviewer_id
            row.updated_at = now
            session.add(
                SafetyIncidentHistory(
                    report_id=row.id,
                    actor_user_id=reviewer_id,
                    action=body.action,
                    note=body.internal_note,
                    created_at=now,
                )
            )
            session.add(
                AuditEvent(
                    actor_user_id=reviewer_id,
                    event_type=f"trust.safety_report_{body.action}",
                    subject_type="safety_incident_report",
                    subject_id=str(row.id),
                    request_id=request_id,
                    metadata_json={"category": row.category},
                )
            )
        else:
            raise self.not_found("The report type was not found.")
        session.commit()
        return {"id": report_id, "report_type": report_type, "status": body.action}

    def create_viewing(
        self, session: Session, owner_id: UUID, body: ViewingCreate
    ) -> ViewingResponse:
        self._require_active_user(session, owner_id)
        if body.starts_at <= datetime.now(UTC):
            raise ApiError(
                422, "viewing_must_be_future", "Choose a future date and time for the viewing."
            )
        prop = None
        if body.property_id is not None:
            prop = self.properties.list_public_by_id(session, body.property_id, include_demo=False)
            if prop is None:
                raise self.not_found("Choose a published and available listing for the viewing.")
        self._validate_share_target(session, owner_id, body.share_with_user_id)
        now = datetime.now(UTC)
        data = {
            "title": body.title,
            "meeting_point": body.meeting_point,
            "trusted_contact_name": body.trusted_contact_name,
            "trusted_contact_phone": body.trusted_contact_phone,
            "notes": body.notes,
        }
        row = SafeViewing(
            owner_user_id=owner_id,
            property_id=body.property_id,
            shared_with_user_id=body.share_with_user_id,
            details_share_consented_at=now
            if body.share_with_user_id and body.consent_to_share_details
            else None,
            encrypted_data=self.cipher.encrypt(owner_id, data),
            starts_at=body.starts_at,
            status="planned",
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        session.add(
            AuditEvent(
                actor_user_id=owner_id,
                event_type="trust.safe_viewing_created",
                subject_type="safe_viewing",
                subject_id=str(row.id),
                metadata_json={
                    "property_id": str(row.property_id) if row.property_id else None,
                    "shared": row.shared_with_user_id is not None,
                },
            )
        )
        session.commit()
        return self._viewing_response(session, row, owner_id)

    def list_viewings(self, session: Session, user_id: UUID) -> list[ViewingResponse]:
        rows = list(
            session.scalars(
                select(SafeViewing)
                .where(
                    or_(
                        SafeViewing.owner_user_id == user_id,
                        SafeViewing.shared_with_user_id == user_id,
                    )
                )
                .order_by(SafeViewing.starts_at.desc())
                .limit(200)
            )
        )
        return [self._viewing_response(session, row, user_id) for row in rows]

    def update_viewing(
        self, session: Session, owner_id: UUID, viewing_id: UUID, body: ViewingUpdate
    ) -> ViewingResponse:
        row = session.get(SafeViewing, viewing_id)
        if row is None or row.owner_user_id != owner_id:
            raise self.not_found("The viewing plan was not found.")
        if row.status != "planned":
            raise ApiError(409, "viewing_not_editable", "Only a planned viewing can be edited.")
        payload = self.cipher.decrypt(owner_id, row.encrypted_data)
        updates = body.model_dump(mode="json", exclude_unset=True)
        consent = updates.pop("consent_to_share_details", False)
        if "share_with_user_id" in updates:
            share_id = updates.pop("share_with_user_id")
            self._validate_share_target(session, owner_id, UUID(share_id) if share_id else None)
            if share_id and not consent:
                raise ApiError(
                    422,
                    "viewing_share_consent_required",
                    "Consent is required before sharing viewing details.",
                )
            row.shared_with_user_id = UUID(share_id) if share_id else None
            row.details_share_consented_at = datetime.now(UTC) if share_id and consent else None
        for key in (
            "title",
            "meeting_point",
            "trusted_contact_name",
            "trusted_contact_phone",
            "notes",
        ):
            value = updates.pop(key, None)
            if value is not None:
                payload[key] = value
        if "starts_at" in updates and updates["starts_at"] is not None:
            row.starts_at = datetime.fromisoformat(updates["starts_at"])
        row.encrypted_data = self.cipher.encrypt(owner_id, payload)
        row.updated_at = datetime.now(UTC)
        session.commit()
        return self._viewing_response(session, row, owner_id)

    def viewing_transition(
        self, session: Session, owner_id: UUID, viewing_id: UUID, action: str
    ) -> ViewingResponse:
        row = session.get(SafeViewing, viewing_id)
        if row is None or row.owner_user_id != owner_id:
            raise self.not_found("The viewing plan was not found.")
        now = datetime.now(UTC)
        if action == "check-in" and row.status == "planned":
            row.status = "checked_in"
            row.checked_in_at = now
        elif action == "check-out" and row.status == "checked_in":
            row.status = "checked_out"
            row.checked_out_at = now
        elif action == "cancel" and row.status == "planned":
            row.status = "cancelled"
        else:
            raise ApiError(
                409,
                "invalid_viewing_transition",
                "This viewing cannot be updated from its current status.",
            )
        row.updated_at = now
        session.add(
            AuditEvent(
                actor_user_id=owner_id,
                event_type=f"trust.safe_viewing_{action.replace('-', '_')}",
                subject_type="safe_viewing",
                subject_id=str(row.id),
                metadata_json={"status": row.status},
            )
        )
        session.commit()
        return self._viewing_response(session, row, owner_id)

    def report_safety_incident(
        self,
        session: Session,
        owner_id: UUID,
        body: SafetyReportCreate,
        request_id: str | None = None,
    ) -> SafetyReportResponse:
        self._require_active_user(session, owner_id)
        self._validate_evidence_documents(session, owner_id, body.evidence_document_ids)
        if body.viewing_id is not None:
            viewing = session.get(SafeViewing, body.viewing_id)
            if viewing is None or owner_id not in {
                viewing.owner_user_id,
                viewing.shared_with_user_id,
            }:
                raise self.not_found("The viewing plan was not found.")
            property_id = viewing.property_id
        else:
            property_id = body.property_id
            if (
                property_id is None
                or self.properties.list_public_by_id(session, property_id, include_demo=False)
                is None
            ):
                raise self.not_found("This listing is not available for a safety report.")
        now = datetime.now(UTC)
        row = SafetyIncidentReport(
            owner_user_id=owner_id,
            viewing_id=body.viewing_id,
            property_id=property_id,
            category=body.category,
            encrypted_details=self.cipher.encrypt(owner_id, {"details": body.details}),
            status="received",
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        self._link_report_evidence(
            session, "incident", row.id, owner_id, body.evidence_document_ids
        )
        session.add(
            SafetyIncidentHistory(report_id=row.id, actor_user_id=owner_id, action="submitted")
        )
        session.add(
            AuditEvent(
                actor_user_id=owner_id,
                event_type="trust.safety_report_submitted",
                subject_type="safety_incident_report",
                subject_id=str(row.id),
                request_id=request_id,
                metadata_json={
                    "category": row.category,
                    "property_id": str(row.property_id) if row.property_id else None,
                },
            )
        )
        session.commit()
        return self._safety_report_view(session, row, include_details=True)

    def my_safety_reports(self, session: Session, owner_id: UUID) -> list[SafetyReportResponse]:
        rows = list(
            session.scalars(
                select(SafetyIncidentReport)
                .where(SafetyIncidentReport.owner_user_id == owner_id)
                .order_by(SafetyIncidentReport.created_at.desc())
                .limit(200)
            )
        )
        return [self._safety_report_view(session, row, include_details=True) for row in rows]

    @staticmethod
    def safety_guide() -> dict[str, Any]:
        return {
            "title": "Safer home viewings",
            "disclaimer": (
                "Practical reminders only. These steps do not guarantee safety or "
                "verify a person or property."
            ),
            "before": [
                "Arrange daytime viewings where practical and tell someone you trust "
                "where you are going.",
                "Use the viewing details you received through HomeScout and confirm "
                "any changes independently.",
                "Check the property address and ask for clear ownership or "
                "agent-authority evidence before paying.",
                "Do not share M-Pesa PINs, one-time codes, passwords, or identity "
                "documents through an untrusted chat.",
                "Avoid sending a deposit before you have inspected the home, "
                "confirmed who may rent it, and received written terms.",
            ],
            "during": [
                "Meet at the agreed location, keep your phone charged, and leave if "
                "you feel pressured or unsafe.",
                "Bring a trusted person where possible. Do not hand over original "
                "documents or cash during a viewing.",
                "Use check-in and check-out to mark your own progress; HomeScout "
                "does not send emergency or push alerts.",
            ],
            "after": [
                "Keep written terms and payment receipts. Confirm the recipient "
                "independently before sending money.",
                "Report concerning conduct with specific details. A report is "
                "reviewed and is not itself proof of wrongdoing.",
                "If you are in immediate danger, move to a safe place and contact "
                "local emergency services directly.",
            ],
        }

    @staticmethod
    def property_trust_indicators(session: Session, property_id: UUID) -> dict[str, Any]:
        property_ = PropertyDataAccess().list_public_by_id(session, property_id, include_demo=False)
        if property_ is None:
            raise ApiError(404, "trust_record_not_found", "This listing is not available.")
        property_case = session.scalar(
            select(VerificationCase)
            .where(
                VerificationCase.subject_type == "property",
                VerificationCase.property_id == property_id,
            )
            .order_by(VerificationCase.updated_at.desc())
        )
        if (
            property_case is not None
            and property_case.status == "approved"
            and property_case.expires_on is not None
            and property_case.expires_on < date.today()
        ):
            property_case.status = "expired"
            property_case.updated_at = datetime.now(UTC)
            property_.verification_status = "expired"
            session.add(
                VerificationHistory(
                    case_id=property_case.id,
                    actor_user_id=None,
                    action="expired",
                    from_status="approved",
                    to_status="expired",
                    submission_number=property_case.submission_number,
                    created_at=property_case.updated_at,
                )
            )
            session.commit()
        owner_case = session.scalar(
            select(VerificationCase)
            .where(
                VerificationCase.subject_type.in_(("landlord", "agent")),
                VerificationCase.subject_user_id == property_.owner_user_id,
                VerificationCase.status == "approved",
                or_(
                    VerificationCase.expires_on.is_(None),
                    VerificationCase.expires_on >= date.today(),
                ),
            )
            .order_by(VerificationCase.updated_at.desc())
        )
        agent_case = None
        if property_.authorized_agent_user_id is not None:
            agent_case = session.scalar(
                select(VerificationCase)
                .where(
                    VerificationCase.subject_type == "agent",
                    VerificationCase.subject_user_id == property_.authorized_agent_user_id,
                    VerificationCase.status == "approved",
                    or_(
                        VerificationCase.expires_on.is_(None),
                        VerificationCase.expires_on >= date.today(),
                    ),
                )
                .order_by(VerificationCase.updated_at.desc())
            )
        return {
            "property_id": property_.id,
            "property_verification": property_case.status if property_case else "not_submitted",
            "listing_contact_account_check": (
                "approved" if owner_case is not None else "not_verified"
            ),
            "authorized_agent_account_check": (
                "approved" if agent_case is not None else "not_verified"
            ),
            "account_check_expiry": owner_case.expires_on if owner_case else None,
            "moderation_status": property_.moderation_status,
            "signals": [],
            "trust_score": None,
            "review_count": 0,
            "note": (
                "Only completed HomeScout checks are shown. Account checks do not by "
                "themselves prove property ownership or agency authority."
            ),
        }

    def _verification_view(
        self, session: Session, case: VerificationCase, *, include_staff: bool
    ) -> VerificationCaseResponse:
        self._expire_case(session, case, date.today())
        evidence_rows = list(
            session.scalars(
                select(VerificationEvidence)
                .where(
                    VerificationEvidence.case_id == case.id,
                    VerificationEvidence.submission_number == case.submission_number,
                )
                .order_by(VerificationEvidence.added_at)
            )
        )
        evidence = []
        for item in evidence_rows:
            document = session.get(PrivateDocument, item.document_id)
            if document is not None:
                evidence.append(
                    {
                        "id": item.id,
                        "document_id": document.id,
                        "filename": document.original_filename,
                        "content_type": document.content_type,
                        "size_bytes": document.size_bytes,
                        "label": item.label,
                        "submission_number": item.submission_number,
                        "download_path": (
                            f"/trust/verifications/{case.id}/evidence/{item.id}/download"
                        ),
                    }
                )
        history_rows = list(
            session.scalars(
                select(VerificationHistory)
                .where(VerificationHistory.case_id == case.id)
                .order_by(VerificationHistory.created_at)
            )
        )
        history = [
            {
                "id": item.id,
                "action": item.action,
                "from_status": item.from_status,
                "to_status": item.to_status,
                "submission_number": item.submission_number,
                "created_at": item.created_at,
            }
            for item in history_rows
        ]
        property_ = session.get(Property, case.property_id) if case.property_id else None
        submission_note = None
        review_note = None
        latest_submission = next(
            (
                item
                for item in reversed(history_rows)
                if item.submission_number == case.submission_number
                and item.action in {"submitted", "resubmitted"}
            ),
            None,
        )
        latest_review = next(
            (
                item
                for item in reversed(history_rows)
                if item.submission_number == case.submission_number
                and item.action in {"approved", "rejected"}
            ),
            None,
        )
        if latest_submission and latest_submission.encrypted_note:
            submission_note = self.cipher.decrypt(
                case.owner_user_id, latest_submission.encrypted_note
            ).get("note")
        if include_staff and latest_review and latest_review.encrypted_note:
            review_note = self.cipher.decrypt(case.owner_user_id, latest_review.encrypted_note).get(
                "note"
            )
        return VerificationCaseResponse(
            id=case.id,
            owner_user_id=case.owner_user_id,
            subject_type=case.subject_type,
            subject_user_id=case.subject_user_id,
            property_id=case.property_id,
            property_title=property_.title if property_ else None,
            status=case.status,
            submission_number=case.submission_number,
            expires_on=case.expires_on,
            submitted_at=case.submitted_at,
            updated_at=case.updated_at,
            evidence=evidence,
            history=history,
            submission_note=submission_note,
            review_note=review_note,
        )

    def _expire_case(self, session: Session, case: VerificationCase, today: date) -> bool:
        if case.status != "approved" or case.expires_on is None or case.expires_on >= today:
            return False
        old_status = case.status
        case.status = "expired"
        case.updated_at = datetime.now(UTC)
        if case.property_id is not None:
            property_ = session.get(Property, case.property_id)
            if property_ is not None and property_.verification_status == "verified":
                property_.verification_status = "expired"
        session.add(
            VerificationHistory(
                case_id=case.id,
                actor_user_id=None,
                action="expired",
                from_status=old_status,
                to_status="expired",
                submission_number=case.submission_number,
                created_at=case.updated_at,
            )
        )
        return True

    def _validate_verification_documents(
        self, session: Session, owner_id: UUID, ids: list[UUID]
    ) -> None:
        if len(ids) != len(set(ids)):
            raise ApiError(
                422, "duplicate_verification_evidence", "Choose each verification document once."
            )
        rows = list(session.scalars(select(PrivateDocument).where(PrivateDocument.id.in_(ids))))
        if len(rows) != len(ids) or any(
            row.owner_user_id != owner_id or row.category != "verification" for row in rows
        ):
            raise self.not_found("Use documents from your account's Verification category.")

    def _replace_verification_evidence(
        self, session: Session, case: VerificationCase, owner_id: UUID, ids: list[UUID]
    ) -> None:
        docs = {
            row.id: row
            for row in session.scalars(select(PrivateDocument).where(PrivateDocument.id.in_(ids)))
        }
        for document_id in ids:
            doc = docs[document_id]
            session.add(
                VerificationEvidence(
                    case_id=case.id,
                    document_id=document_id,
                    submission_number=case.submission_number,
                    label=doc.original_filename,
                )
            )

    def _property_report_view(
        self, session: Session, row: PropertyReport, prop: Property | None
    ) -> PropertyReportResponse:
        return PropertyReportResponse(
            id=row.id,
            property_id=row.property_id,
            property_title=prop.title if prop else "Listing",
            reason=row.reason,
            details=self._report_details(row.reporter_user_id, row.encrypted_details, row.details),
            status=row.status,
            evidence_document_ids=self._evidence_ids(session, "listing", row.id),
            updated_at=row.updated_at,
            resolution_message=row.resolution_message,
            created_at=row.created_at,
        )

    def _report_details(
        self, owner_id: UUID, encrypted: bytes | None, legacy: str | None
    ) -> str | None:
        return self.cipher.decrypt(owner_id, encrypted).get("details") if encrypted else legacy

    def _validate_evidence_documents(
        self, session: Session, owner_id: UUID, ids: list[UUID]
    ) -> None:
        if len(ids) != len(set(ids)):
            raise ApiError(422, "duplicate_report_evidence", "Choose each evidence document once.")
        docs = (
            list(session.scalars(select(PrivateDocument).where(PrivateDocument.id.in_(ids))))
            if ids
            else []
        )
        if len(docs) != len(ids) or any(document.owner_user_id != owner_id for document in docs):
            raise self.not_found("Evidence must be selected from your private documents.")

    @staticmethod
    def _link_report_evidence(
        session: Session, report_type: str, report_id: UUID, owner_id: UUID, ids: list[UUID]
    ) -> None:
        for document_id in ids:
            session.add(
                TrustReportEvidence(
                    listing_report_id=report_id if report_type == "listing" else None,
                    incident_report_id=report_id if report_type == "incident" else None,
                    document_id=document_id,
                    owner_user_id=owner_id,
                )
            )

    @staticmethod
    def _evidence_ids(session: Session, report_type: str, report_id: UUID) -> list[UUID]:
        column = (
            TrustReportEvidence.listing_report_id
            if report_type == "listing"
            else TrustReportEvidence.incident_report_id
        )
        return list(
            session.scalars(
                select(TrustReportEvidence.document_id)
                .where(column == report_id)
                .order_by(TrustReportEvidence.created_at)
            )
        )

    def _listing_signals(self, session: Session, prop: Property) -> list[dict[str, str]]:
        signals: list[dict[str, str]] = []
        if prop.address:
            normalized = prop.address.strip().casefold()
            duplicates = list(
                session.scalars(
                    select(Property.id)
                    .where(
                        Property.id != prop.id,
                        Property.is_demo.is_(False),
                        Property.town_id == prop.town_id,
                        func.lower(func.trim(Property.address)) == normalized,
                    )
                    .limit(4)
                )
            )
            if duplicates:
                signals.append(
                    {
                        "code": "exact_address_match",
                        "message": (
                            "Another listing uses the same normalized address in this "
                            "town. Check whether the listings refer to the same unit."
                        ),
                    }
                )
        peers = list(
            session.scalars(
                select(Property.rent_amount)
                .where(
                    Property.id != prop.id,
                    Property.is_demo.is_(False),
                    Property.listing_status == "published",
                    Property.availability_status == "available",
                    Property.moderation_status == "clear",
                    Property.county_id == prop.county_id,
                    Property.property_type == prop.property_type,
                    Property.unit_type == prop.unit_type,
                    Property.rent_frequency == prop.rent_frequency,
                )
                .limit(101)
            )
        )
        if len(peers) >= 4:
            center = Decimal(str(median(peers)))
            ratio = prop.rent_amount / center if center else Decimal("1")
            if ratio < Decimal("0.3") or ratio > Decimal("3"):
                signals.append(
                    {
                        "code": "rent_outlier_for_comparable_listings",
                        "message": (
                            "Rent is far from the median of at least four comparable "
                            "available listings. This is a review signal only; it does "
                            "not establish fraud or price accuracy."
                        ),
                    }
                )
        return signals

    @staticmethod
    def _listing_history(session: Session, report_id: UUID) -> list[dict[str, Any]]:
        return [
            {
                "action": row.action,
                "public_message": row.public_message,
                "created_at": row.created_at,
            }
            for row in session.scalars(
                select(PropertyReportReview)
                .where(PropertyReportReview.report_id == report_id)
                .order_by(PropertyReportReview.created_at)
            )
        ]

    @staticmethod
    def _incident_history(session: Session, report_id: UUID) -> list[dict[str, Any]]:
        return [
            {"action": row.action, "created_at": row.created_at}
            for row in session.scalars(
                select(SafetyIncidentHistory)
                .where(SafetyIncidentHistory.report_id == report_id)
                .order_by(SafetyIncidentHistory.created_at)
            )
        ]

    def _safety_report_view(
        self, session: Session, row: SafetyIncidentReport, *, include_details: bool
    ) -> SafetyReportResponse:
        details = (
            self.cipher.decrypt(row.owner_user_id, row.encrypted_details).get("details")
            if include_details
            else None
        )
        return SafetyReportResponse(
            id=row.id,
            viewing_id=row.viewing_id,
            property_id=row.property_id,
            category=row.category,
            details=details,
            status=row.status,
            evidence_document_ids=self._evidence_ids(session, "incident", row.id),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _viewing_response(
        self, session: Session, row: SafeViewing, viewer_id: UUID
    ) -> ViewingResponse:
        is_owner = row.owner_user_id == viewer_id
        if not is_owner and (
            row.shared_with_user_id != viewer_id or row.details_share_consented_at is None
        ):
            raise self.not_found("The viewing details were not shared with this account.")
        data = self.cipher.decrypt(row.owner_user_id, row.encrypted_data)
        prop = session.get(Property, row.property_id) if row.property_id else None
        return ViewingResponse(
            id=row.id,
            owner_user_id=row.owner_user_id,
            property_id=row.property_id,
            property_title=prop.title if prop else None,
            shared_with_user_id=row.shared_with_user_id,
            details_share_consented=row.details_share_consented_at is not None,
            title=data["title"],
            starts_at=row.starts_at,
            meeting_point=data["meeting_point"],
            trusted_contact_name=data["trusted_contact_name"],
            trusted_contact_phone=data["trusted_contact_phone"],
            notes=data.get("notes"),
            status=row.status,
            checked_in_at=row.checked_in_at,
            checked_out_at=row.checked_out_at,
            is_owner=is_owner,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _can_manage_property(self, session: Session, user_id: UUID, prop: Property) -> bool:
        if user_id in {
            prop.owner_user_id,
            prop.authorized_agent_user_id,
            prop.property_manager_user_id,
        }:
            return True
        return (
            session.scalar(
                select(PropertyListingMandate.agent_user_id).where(
                    PropertyListingMandate.owner_user_id == prop.owner_user_id,
                    PropertyListingMandate.agent_user_id == user_id,
                    PropertyListingMandate.is_active.is_(True),
                )
            )
            is not None
        )

    def _require_verification_reviewer(self, session: Session, user_id: UUID, action: str) -> None:
        code = f"verification:{action}:assigned"
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code=code,
            resource_scope_type="administrative_workflow",
            resource_scope_id="verification",
        )

    def _require_moderation_view(self, session: Session, user_id: UUID) -> None:
        codes = ("moderation:view:reported", "moderation:view:assigned")
        if not any(
            self.authorization.has_permission(
                session,
                user_id=user_id,
                permission_code=code,
                resource_scope_type="moderation",
                resource_scope_id="reports",
            )
            for code in codes
        ):
            raise ApiError(
                403, "permission_denied", "You are not authorized to view the moderation queue."
            )

    def _require_moderation_action(self, session: Session, user_id: UUID, action: str) -> None:
        self._require_moderation_view(session, user_id)
        if action == "escalated":
            code = "escalation:create:assigned"
        elif action in {"resolved", "dismissed"}:
            code = (
                "moderation:approve:reported"
                if action == "resolved"
                else "moderation:reject:reported"
            )
        else:
            code = "moderation:approve:reported"
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code=code,
            resource_scope_type="moderation",
            resource_scope_id="reports",
        )

    def _validate_share_target(
        self, session: Session, owner_id: UUID, target_id: UUID | None
    ) -> None:
        if target_id is None:
            return
        target = session.get(UserAccount, target_id)
        if target is None or target.status != "active" or target_id == owner_id:
            raise self.not_found(
                "Choose a different active HomeScout account as the trusted contact."
            )

    @staticmethod
    def _require_active_user(session: Session, user_id: UUID) -> None:
        user = session.get(UserAccount, user_id)
        if user is None or user.status != "active":
            raise ApiError(
                403, "active_account_required", "An active HomeScout account is required."
            )

    @staticmethod
    def not_found(
        message: str = "The requested trust and safety record was not found.",
    ) -> ApiError:
        return ApiError(404, "trust_record_not_found", message)
