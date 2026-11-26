"""Audited platform operations with explicit authorization and data minimization."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import ApiError
from app.models.access_control import Role, UserRoleAssignment
from app.models.audit import AuditEvent
from app.models.auth import AuthSession
from app.models.location import County, Neighbourhood, Town
from app.models.marketplace import PropertyReport
from app.models.personal_hub import (
    SupportMessage,
    SupportTicket,
    SupportTicketAction,
)
from app.models.phase10 import ConversationMessage, MessageReport
from app.models.property import Property
from app.models.services import ServiceOffering, ServiceProviderProfile, ServiceReview
from app.models.settings import ApplicationSetting
from app.models.trust import SafetyIncidentReport, VerificationCase
from app.models.user import UserAccount
from app.services.audit import AuditService
from app.services.authorization import AuthorizationService
from app.services.passwords import password_service

SUPPORT_CATEGORIES = (
    "account",
    "property",
    "safety",
    "privacy",
    "technical",
    "feedback",
    "other",
)
ALLOWED_SETTINGS = {
    "support.allow_new_tickets": (True, "Allow users to open support tickets"),
    "moderation.require_internal_note": (False, "Require a staff note for moderation decisions"),
}
SAFE_AUDIT_METADATA_KEYS = {
    "action",
    "category",
    "listing_action",
    "location_type",
    "offering_id",
    "priority",
    "provider_id",
    "reason",
    "role_code",
    "scope_type",
    "status",
    "ticket_id",
    "ticket_status",
}


class PlatformOperationsService:
    def __init__(self) -> None:
        self.authorization = AuthorizationService()
        self.audit = AuditService()

    @staticmethod
    def not_found(message: str = "The requested operations record was not found.") -> ApiError:
        return ApiError(404, "operations_record_not_found", message)

    def overview(self, session: Session) -> dict[str, int]:
        """Count operational records only; no transaction or personal finance data is read."""

        def count(model, *conditions) -> int:
            statement = select(func.count()).select_from(model)
            if conditions:
                statement = statement.where(*conditions)
            return int(session.scalar(statement) or 0)

        non_demo = Property.is_demo.is_(False)
        unresolved = ("received", "in_review", "escalated")
        return {
            "users_total": count(UserAccount),
            "users_active": count(UserAccount, UserAccount.status == "active"),
            "users_suspended": count(UserAccount, UserAccount.status == "suspended"),
            "listings_total": count(Property, non_demo),
            "listings_review": count(
                Property, non_demo, Property.moderation_status == "under_review"
            ),
            "listings_removed": count(Property, non_demo, Property.moderation_status == "removed"),
            "verifications_pending": count(VerificationCase, VerificationCase.status == "pending"),
            "listing_reports_open": count(PropertyReport, PropertyReport.status.in_(unresolved)),
            "safety_reports_open": count(
                SafetyIncidentReport, SafetyIncidentReport.status.in_(unresolved)
            ),
            "message_reports_open": count(MessageReport, MessageReport.status == "received"),
            "service_reviews_total": count(ServiceReview),
            "service_reviews_pending": count(
                ServiceReview, ServiceReview.moderation_status == "under_review"
            ),
            "service_reviews_removed": count(
                ServiceReview, ServiceReview.moderation_status == "removed"
            ),
            "support_open": count(SupportTicket, SupportTicket.status == "open"),
            "support_waiting": count(SupportTicket, SupportTicket.status == "waiting"),
            "providers_published": count(
                ServiceProviderProfile, ServiceProviderProfile.is_published.is_(True)
            ),
            "services_active": count(ServiceOffering, ServiceOffering.is_active.is_(True)),
            "counties_active": count(County, County.is_active.is_(True)),
            "towns_active": count(Town, Town.is_active.is_(True)),
            "neighbourhoods_active": count(Neighbourhood, Neighbourhood.is_active.is_(True)),
        }

    def users(
        self, session: Session, *, query: str = "", status: str | None = None, limit: int = 30
    ) -> list[dict[str, object]]:
        statement = select(UserAccount).options(joinedload(UserAccount.profile))
        if query.strip():
            cleaned = query.strip().lower().replace("%", "\\%").replace("_", "\\_")
            needle = f"{cleaned}%"
            statement = statement.where(
                or_(
                    func.lower(UserAccount.email).like(needle, escape="\\"),
                    UserAccount.phone_number.like(f"{cleaned}%", escape="\\"),
                )
            )
        if status:
            statement = statement.where(UserAccount.status == status)
        rows = session.scalars(statement.order_by(UserAccount.created_at.desc()).limit(limit)).all()
        return [
            {
                "id": row.id,
                "email": row.email,
                "status": row.status,
                "roles": self.authorization.role_codes(session, row.id),
                "requested_role_code": row.profile.requested_role_code if row.profile else None,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    def update_account_status(
        self,
        session: Session,
        *,
        actor_id: UUID,
        target_id: UUID,
        status: str,
        current_password: str,
        reason: str,
        request_id: str | None,
    ) -> dict[str, object]:
        actor = session.get(UserAccount, actor_id)
        target = session.get(UserAccount, target_id)
        if (
            actor is None
            or not actor.password_hash
            or not password_service.verify(actor.password_hash, current_password)
        ):
            raise ApiError(401, "reauthentication_required", "Confirm your password to continue.")
        if target is None:
            raise self.not_found("The account was not found.")
        if actor_id == target_id:
            raise ApiError(
                403, "self_account_restriction_forbidden", "You cannot restrict your own account."
            )
        if target.status == "closed":
            raise ApiError(
                409, "closed_account_immutable", "A closed account cannot be reactivated here."
            )
        roles = self.authorization.role_codes(session, target_id)
        if set(roles).intersection({"admin", "moderator", "super_admin"}):
            self.authorization.require_permission(
                session,
                user_id=actor_id,
                permission_code="security:manage:global",
                resource_scope_type="global",
                resource_scope_id="*",
            )
        if target.status == status:
            return {"id": target.id, "status": target.status}
        if status == "suspended" and "super_admin" in roles:
            super_admin = session.scalar(select(Role).where(Role.code == "super_admin"))
            other_active = session.scalar(
                select(func.count())
                .select_from(UserRoleAssignment)
                .join(UserAccount, UserAccount.id == UserRoleAssignment.user_id)
                .where(
                    UserAccount.status == "active",
                    UserAccount.id != target_id,
                    UserRoleAssignment.role_id == super_admin.id if super_admin else False,
                )
            )
            if not other_active:
                raise ApiError(
                    409,
                    "last_super_admin_required",
                    "The last active Super Admin cannot be suspended.",
                )
        prior_status = target.status
        target.status = status
        if status == "suspended":
            session.execute(
                update(AuthSession)
                .where(AuthSession.user_id == target_id, AuthSession.revoked_at.is_(None))
                .values(revoked_at=datetime.now(UTC))
            )
        self.audit.record(
            session,
            event_type="admin.account_status_changed",
            actor_user_id=actor_id,
            subject_type="user_account",
            subject_id=str(target_id),
            request_id=request_id,
            metadata={"status": status},
        )
        session.add(
            AuditEvent(
                actor_user_id=actor_id,
                event_type="admin.account_restriction_reason_recorded",
                subject_type="user_account",
                subject_id=str(target_id),
                request_id=request_id,
                metadata_json={
                    "status": status,
                    "prior_status": prior_status,
                    "reason": self._safe_reason(reason),
                },
            )
        )
        session.commit()
        return {"id": target.id, "status": target.status}

    def listings(
        self, session: Session, *, status: str | None = None, query: str = "", limit: int = 50
    ) -> list[dict[str, object]]:
        statement = (
            select(Property)
            .options(joinedload(Property.county), joinedload(Property.town))
            .where(Property.is_demo.is_(False))
        )
        if status:
            statement = statement.where(Property.moderation_status == status)
        if query.strip():
            statement = statement.where(
                func.lower(Property.title).like(f"%{query.strip().lower()}%")
            )
        rows = session.scalars(statement.order_by(Property.updated_at.desc()).limit(limit)).unique()
        result = []
        for row in rows:
            result.append(
                {
                    "id": row.id,
                    "title": row.title,
                    "rent_kes": row.rent_amount,
                    "county": row.county.name if row.county else None,
                    "town": row.town.name if row.town else None,
                    "owner_user_id": row.owner_user_id,
                    "listing_status": row.listing_status,
                    "moderation_status": row.moderation_status,
                    "verification_status": row.verification_status,
                    "availability_status": row.availability_status,
                    "reported_count": int(
                        session.scalar(
                            select(func.count())
                            .select_from(PropertyReport)
                            .where(PropertyReport.property_id == row.id)
                        )
                        or 0
                    ),
                    "updated_at": row.updated_at,
                }
            )
        return result

    def update_listing_moderation(
        self,
        session: Session,
        *,
        actor_id: UUID,
        property_id: UUID,
        status: str,
        reason: str,
        request_id: str | None,
    ) -> dict[str, object]:
        row = session.scalar(
            select(Property).where(Property.id == property_id, Property.is_demo.is_(False))
        )
        if row is None:
            raise self.not_found("The non-demo listing was not found.")
        row.moderation_status = status
        self.audit.record(
            session,
            event_type="admin.listing_moderation_changed",
            actor_user_id=actor_id,
            subject_type="property",
            subject_id=str(row.id),
            request_id=request_id,
            metadata={"status": status},
        )
        session.add(
            AuditEvent(
                actor_user_id=actor_id,
                event_type="admin.listing_reason_recorded",
                subject_type="property",
                subject_id=str(row.id),
                request_id=request_id,
                metadata_json={"status": status, "reason": self._safe_reason(reason)},
            )
        )
        session.commit()
        return {"id": row.id, "moderation_status": row.moderation_status}

    def service_reviews(
        self, session: Session, *, status: str | None = None, limit: int = 100
    ) -> list[dict[str, object]]:
        statement = (
            select(ServiceReview, ServiceOffering.title)
            .join(ServiceOffering, ServiceOffering.id == ServiceReview.offering_id)
            .order_by(ServiceReview.created_at.desc())
            .limit(limit)
        )
        if status:
            statement = statement.where(ServiceReview.moderation_status == status)
        return [
            {
                "id": review.id,
                "offering_id": review.offering_id,
                "offering_title": offering_title,
                "reviewer_user_id": review.reviewer_user_id,
                "rating": review.rating,
                "review_text": review.review_text,
                "moderation_status": review.moderation_status,
                "created_at": review.created_at,
            }
            for review, offering_title in session.execute(statement).all()
        ]

    def update_service_review_moderation(
        self,
        session: Session,
        *,
        actor_id: UUID,
        review_id: UUID,
        status: str,
        reason: str,
        request_id: str | None,
    ) -> dict[str, object]:
        review = session.get(ServiceReview, review_id)
        if review is None:
            raise self.not_found("The service review was not found.")
        review.moderation_status = status
        self.audit.record(
            session,
            event_type="admin.service_review_moderation_changed",
            actor_user_id=actor_id,
            subject_type="service_review",
            subject_id=str(review.id),
            request_id=request_id,
            metadata={"status": status},
        )
        session.add(
            AuditEvent(
                actor_user_id=actor_id,
                event_type="admin.service_review_reason_recorded",
                subject_type="service_review",
                subject_id=str(review.id),
                request_id=request_id,
                metadata_json={"status": status, "reason": self._safe_reason(reason)},
            )
        )
        session.commit()
        return {"id": review.id, "moderation_status": review.moderation_status}

    def providers(self, session: Session, *, limit: int = 50) -> list[dict[str, object]]:
        profiles = session.scalars(
            select(ServiceProviderProfile)
            .order_by(ServiceProviderProfile.updated_at.desc())
            .limit(limit)
        ).all()
        return [
            {
                "id": profile.id,
                "provider_user_id": profile.provider_user_id,
                "public_name": profile.public_name,
                "is_published": profile.is_published,
                "active_offerings": int(
                    session.scalar(
                        select(func.count())
                        .select_from(ServiceOffering)
                        .where(
                            ServiceOffering.provider_user_id == profile.provider_user_id,
                            ServiceOffering.is_active.is_(True),
                        )
                    )
                    or 0
                ),
                "updated_at": profile.updated_at,
            }
            for profile in profiles
        ]

    def update_provider_publication(
        self,
        session: Session,
        *,
        actor_id: UUID,
        provider_id: UUID,
        published: bool,
        reason: str,
        request_id: str | None,
    ) -> dict[str, object]:
        row = session.scalar(
            select(ServiceProviderProfile).where(
                ServiceProviderProfile.provider_user_id == provider_id
            )
        )
        if row is None:
            raise self.not_found("The service provider profile was not found.")
        row.is_published = published
        self.audit.record(
            session,
            event_type="admin.provider_publication_changed",
            actor_user_id=actor_id,
            subject_type="service_provider_profile",
            subject_id=str(row.id),
            request_id=request_id,
            metadata={"status": "published" if published else "paused"},
        )
        session.add(
            AuditEvent(
                actor_user_id=actor_id,
                event_type="admin.provider_reason_recorded",
                subject_type="service_provider_profile",
                subject_id=str(row.id),
                request_id=request_id,
                metadata_json={"reason": self._safe_reason(reason)},
            )
        )
        session.commit()
        return {"provider_user_id": provider_id, "is_published": row.is_published}

    def update_offering_status(
        self,
        session: Session,
        *,
        actor_id: UUID,
        offering_id: UUID,
        active: bool,
        reason: str,
        request_id: str | None,
    ) -> dict[str, object]:
        row = session.get(ServiceOffering, offering_id)
        if row is None:
            raise self.not_found("The service offering was not found.")
        row.is_active = active
        self.audit.record(
            session,
            event_type="admin.service_offering_status_changed",
            actor_user_id=actor_id,
            subject_type="service_offering",
            subject_id=str(row.id),
            request_id=request_id,
            metadata={"status": "active" if active else "paused"},
        )
        session.add(
            AuditEvent(
                actor_user_id=actor_id,
                event_type="admin.service_offering_reason_recorded",
                subject_type="service_offering",
                subject_id=str(row.id),
                request_id=request_id,
                metadata_json={"reason": self._safe_reason(reason)},
            )
        )
        session.commit()
        return {"id": row.id, "is_active": row.is_active}

    def locations(self, session: Session) -> list[dict[str, object]]:
        counties = session.scalars(select(County).order_by(County.name)).all()
        return (
            [
                {
                    "type": "county",
                    "id": county.id,
                    "name": county.name,
                    "parent": None,
                    "is_active": county.is_active,
                }
                for county in counties
            ]
            + [
                {
                    "type": "town",
                    "id": row.id,
                    "name": row.name,
                    "parent": row.county_id,
                    "is_active": row.is_active,
                }
                for row in session.scalars(select(Town).order_by(Town.name))
            ]
            + [
                {
                    "type": "neighbourhood",
                    "id": row.id,
                    "name": row.name,
                    "parent": row.town_id,
                    "is_active": row.is_active,
                }
                for row in session.scalars(select(Neighbourhood).order_by(Neighbourhood.name))
            ]
        )

    def update_location_status(
        self,
        session: Session,
        *,
        actor_id: UUID,
        location_type: str,
        location_id: UUID,
        active: bool,
        reason: str,
        request_id: str | None,
    ) -> dict[str, object]:
        model = {"county": County, "town": Town, "neighbourhood": Neighbourhood}.get(location_type)
        if model is None:
            raise ApiError(422, "invalid_location_type", "Choose a county, town, or neighbourhood.")
        row = session.get(model, location_id)
        if row is None:
            raise self.not_found("The location was not found.")
        if active and location_type == "town":
            parent = session.get(County, row.county_id)
            if parent is None or not parent.is_active:
                raise ApiError(409, "inactive_parent_location", "Activate the parent county first.")
        elif active and location_type == "neighbourhood":
            parent = session.get(Town, row.town_id)
            if parent is None or not parent.is_active:
                raise ApiError(409, "inactive_parent_location", "Activate the parent town first.")
        if (
            not active
            and location_type == "county"
            and session.scalar(
                select(Town.id)
                .where(Town.county_id == location_id, Town.is_active.is_(True))
                .limit(1)
            )
        ):
            raise ApiError(
                409, "active_child_locations", "Deactivate active towns before this county."
            )
        if (
            not active
            and location_type == "town"
            and session.scalar(
                select(Neighbourhood.id)
                .where(Neighbourhood.town_id == location_id, Neighbourhood.is_active.is_(True))
                .limit(1)
            )
        ):
            raise ApiError(
                409, "active_child_locations", "Deactivate active neighbourhoods before this town."
            )
        row.is_active = active
        self.audit.record(
            session,
            event_type="admin.location_status_changed",
            actor_user_id=actor_id,
            subject_type=location_type,
            subject_id=str(location_id),
            request_id=request_id,
            metadata={"location_type": location_type, "status": "active" if active else "inactive"},
        )
        session.add(
            AuditEvent(
                actor_user_id=actor_id,
                event_type="admin.location_reason_recorded",
                subject_type=location_type,
                subject_id=str(location_id),
                request_id=request_id,
                metadata_json={"reason": self._safe_reason(reason)},
            )
        )
        session.commit()
        return {"id": location_id, "type": location_type, "is_active": active}

    def support_tickets(
        self, session: Session, *, status: str | None, limit: int = 50
    ) -> list[dict[str, object]]:
        statement = select(SupportTicket).options(joinedload(SupportTicket.messages))
        if status:
            statement = statement.where(SupportTicket.status == status)
        rows = session.scalars(
            statement.order_by(SupportTicket.updated_at.desc()).limit(limit)
        ).unique()
        return [
            self._support_ticket_response(
                session, row, include_history=False, include_messages=False
            )
            for row in rows
        ]

    def support_ticket(
        self, session: Session, *, actor_id: UUID, ticket_id: UUID
    ) -> dict[str, object]:
        row = session.scalar(
            select(SupportTicket)
            .options(joinedload(SupportTicket.messages), selectinload(SupportTicket.actions))
            .where(SupportTicket.id == ticket_id)
        )
        if row is None:
            raise self.not_found("The support ticket was not found.")
        self.audit.record(
            session,
            event_type="admin.support_ticket_viewed",
            actor_user_id=actor_id,
            subject_type="support_ticket",
            subject_id=str(ticket_id),
        )
        session.commit()
        return self._support_ticket_response(
            session, row, include_history=True, include_messages=True
        )

    def update_support_ticket(
        self,
        session: Session,
        *,
        actor_id: UUID,
        ticket_id: UUID,
        values: dict[str, object],
        request_id: str | None,
    ) -> dict[str, object]:
        row = session.get(SupportTicket, ticket_id)
        if row is None:
            raise self.not_found("The support ticket was not found.")
        changes: dict[str, object] = {}
        for field in ("status", "priority", "assigned_to_user_id"):
            if field in values and values[field] is not None:
                value = values[field]
                if field == "assigned_to_user_id":
                    assignee = session.get(UserAccount, value)
                    if (
                        assignee is None
                        or assignee.status != "active"
                        or not self.authorization.has_permission(
                            session,
                            user_id=assignee.id,
                            permission_code="support:manage:assigned",
                            resource_scope_type="administrative_workflow",
                            resource_scope_id="support",
                        )
                    ):
                        raise ApiError(
                            422,
                            "invalid_support_assignee",
                            "Choose an active support administrator.",
                        )
                previous = getattr(row, field)
                setattr(row, field, value)
                if previous != value:
                    changes[field] = str(value) if field == "assigned_to_user_id" else value
        if values.get("escalate") is True and row.escalated_at is None:
            row.escalated_at = datetime.now(UTC)
            changes["escalated_at"] = row.escalated_at.isoformat()
        elif values.get("escalate") is False:
            row.escalated_at = None
            changes["escalated_at"] = None
        if not changes:
            raise ApiError(
                422, "empty_support_update", "Choose at least one support ticket change."
            )
        note = str(values.get("note") or "").strip() or None
        action_note = "; ".join(f"{key}={value}" for key, value in changes.items())
        if note:
            action_note = f"{action_note}; staff note: {note}" if action_note else note
        row.actions.append(
            SupportTicketAction(
                actor_user_id=actor_id,
                action="workflow_changed",
                note=action_note[:1000],
            )
        )
        self.audit.record(
            session,
            event_type="admin.support_ticket_updated",
            actor_user_id=actor_id,
            subject_type="support_ticket",
            subject_id=str(ticket_id),
            request_id=request_id,
            metadata={"ticket_status": row.status, "priority": row.priority},
        )
        session.commit()
        session.refresh(row)
        return {
            "id": row.id,
            "status": row.status,
            "priority": row.priority,
            "assigned_to_user_id": row.assigned_to_user_id,
            "escalated_at": row.escalated_at,
        }

    def reply_support_ticket(
        self,
        session: Session,
        *,
        actor_id: UUID,
        ticket_id: UUID,
        body: str,
        request_id: str | None,
    ) -> dict[str, object]:
        row = session.get(SupportTicket, ticket_id)
        if row is None:
            raise self.not_found("The support ticket was not found.")
        if row.status == "closed":
            raise ApiError(409, "ticket_closed", "Reopen the ticket before replying.")
        row.messages.append(SupportMessage(sender_user_id=actor_id, body=body.strip()))
        row.status = "waiting"
        row.actions.append(SupportTicketAction(actor_user_id=actor_id, action="staff_reply"))
        self.audit.record(
            session,
            event_type="admin.support_reply_sent",
            actor_user_id=actor_id,
            subject_type="support_ticket",
            subject_id=str(ticket_id),
            request_id=request_id,
            metadata={"ticket_status": "waiting"},
        )
        session.commit()
        return {"id": row.id, "status": row.status, "message_sent": True}

    def categories(self, session: Session) -> list[dict[str, object]]:
        return [
            {
                "type": "support",
                "code": code,
                "is_active": self._setting_value(session, f"category.support.{code}", True),
            }
            for code in SUPPORT_CATEGORIES
        ]

    def update_category(
        self, session: Session, *, actor_id: UUID, code: str, active: bool, request_id: str | None
    ) -> dict[str, object]:
        if code not in SUPPORT_CATEGORIES:
            raise self.not_found("The support category is not configurable.")
        self._set_setting(session, f"category.support.{code}", active)
        self.audit.record(
            session,
            event_type="admin.support_category_changed",
            actor_user_id=actor_id,
            subject_type="support_category",
            subject_id=code,
            request_id=request_id,
            metadata={"status": "active" if active else "inactive", "category": code},
        )
        session.commit()
        return {"type": "support", "code": code, "is_active": active}

    def settings(self, session: Session) -> list[dict[str, object]]:
        return [
            {
                "key": key,
                "description": description,
                "value": self._setting_value(session, key, default),
            }
            for key, (default, description) in ALLOWED_SETTINGS.items()
        ]

    def update_setting(
        self, session: Session, *, actor_id: UUID, key: str, value: bool, request_id: str | None
    ) -> dict[str, object]:
        if key not in ALLOWED_SETTINGS:
            raise self.not_found("That setting is not managed by this operations console.")
        self._set_setting(session, key, value)
        self.audit.record(
            session,
            event_type="admin.setting_changed",
            actor_user_id=actor_id,
            subject_type="application_setting",
            subject_id=key,
            request_id=request_id,
            metadata={"status": "enabled" if value else "disabled"},
        )
        session.commit()
        return {"key": key, "value": value}

    def audit_events(
        self, session: Session, *, limit: int = 50, offset: int = 0
    ) -> list[dict[str, object]]:
        rows = session.scalars(
            select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).offset(offset).limit(limit)
        )
        result = []
        for row in rows:
            safe_metadata = {
                key: value
                for key, value in (row.metadata_json or {}).items()
                if key in SAFE_AUDIT_METADATA_KEYS
                and isinstance(value, (str, int, float, bool, type(None)))
            }
            result.append(
                {
                    "id": row.id,
                    "actor_user_id": row.actor_user_id,
                    "event_type": row.event_type,
                    "subject_type": row.subject_type,
                    "subject_id": row.subject_id,
                    "metadata": safe_metadata,
                    "occurred_at": row.occurred_at,
                }
            )
        return result

    def message_reports(self, session: Session, *, limit: int = 50) -> list[dict[str, object]]:
        rows = session.execute(
            select(MessageReport, ConversationMessage)
            .join(ConversationMessage, ConversationMessage.id == MessageReport.message_id)
            .where(MessageReport.status == "received")
            .order_by(MessageReport.created_at.asc())
            .limit(limit)
        )
        return [
            {
                "id": report.id,
                "message_id": report.message_id,
                "reporter_user_id": report.reporter_user_id,
                "sender_user_id": message.sender_user_id,
                "category": report.category,
                "details": report.details,
                "status": report.status,
                "message_deleted": message.deleted_at is not None,
                "created_at": report.created_at,
            }
            for report, message in rows
        ]

    def review_message_report(
        self,
        session: Session,
        *,
        actor_id: UUID,
        report_id: UUID,
        status: str,
        remove_message: bool,
        reason: str,
        request_id: str | None,
    ) -> dict[str, object]:
        row = session.get(MessageReport, report_id)
        if row is None:
            raise self.not_found("The message report was not found.")
        message = session.get(ConversationMessage, row.message_id)
        if message is None:
            raise self.not_found("The reported message was not found.")
        if row.status == "closed":
            raise ApiError(409, "report_closed", "This report is already closed.")
        row.status = status
        if remove_message:
            message.deleted_at = datetime.now(UTC)
        self.audit.record(
            session,
            event_type="admin.message_report_reviewed",
            actor_user_id=actor_id,
            subject_type="message_report",
            subject_id=str(report_id),
            request_id=request_id,
            metadata={
                "status": status,
                "action": "message_removed" if remove_message else "reviewed",
            },
        )
        session.add(
            AuditEvent(
                actor_user_id=actor_id,
                event_type="admin.message_report_reason_recorded",
                subject_type="message_report",
                subject_id=str(report_id),
                request_id=request_id,
                metadata_json={"reason": self._safe_reason(reason)},
            )
        )
        session.commit()
        return {"id": row.id, "status": row.status, "message_removed": remove_message}

    def message_report_detail(
        self,
        session: Session,
        *,
        actor_id: UUID,
        report_id: UUID,
        cipher,
    ) -> dict[str, object]:
        row = session.get(MessageReport, report_id)
        if row is None:
            raise self.not_found("The message report was not found.")
        message = session.get(ConversationMessage, row.message_id)
        if message is None:
            raise self.not_found("The reported message was not found.")
        body = (
            "[Message removed by moderation]"
            if message.deleted_at is not None
            else cipher.decrypt_message(
                message.conversation_id,
                message.id,
                message.sender_user_id,
                message.encrypted_body,
            )
        )
        self.audit.record(
            session,
            event_type="admin.reported_message_viewed",
            actor_user_id=actor_id,
            subject_type="message_report",
            subject_id=str(report_id),
            metadata={"category": row.category},
        )
        session.commit()
        return {
            "id": row.id,
            "message_id": message.id,
            "sender_user_id": message.sender_user_id,
            "reporter_user_id": row.reporter_user_id,
            "category": row.category,
            "details": row.details,
            "status": row.status,
            "message_body": body,
            "created_at": row.created_at,
        }

    @staticmethod
    def _setting_value(session: Session, key: str, default: bool) -> bool:
        row = session.get(ApplicationSetting, key)
        return bool(row.value.get("value", default)) if row else default

    @staticmethod
    def _set_setting(session: Session, key: str, value: bool) -> None:
        row = session.get(ApplicationSetting, key)
        if row is None:
            row = ApplicationSetting(key=key, value={"value": value})
            session.add(row)
        else:
            row.value = {"value": value}

    @staticmethod
    def _safe_reason(value: str) -> str:
        """Keep action context while redacting common direct contact identifiers."""

        reason = re.sub(r"[\r\n\t]+", " ", value).strip()
        reason = re.sub(
            r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
            "[contact redacted]",
            reason,
            flags=re.I,
        )
        reason = re.sub(r"\+?\d[\d ()-]{5,}\d", "[contact redacted]", reason)
        return reason[:500]

    def _support_ticket_response(
        self,
        session: Session,
        row: SupportTicket,
        *,
        include_history: bool,
        include_messages: bool,
    ) -> dict[str, object]:
        owner = session.get(UserAccount, row.owner_user_id)
        result: dict[str, object] = {
            "id": row.id,
            "owner_user_id": row.owner_user_id,
            "owner_email": owner.email if owner else None,
            "subject": row.subject,
            "category": row.category,
            "status": row.status,
            "priority": row.priority,
            "assigned_to_user_id": row.assigned_to_user_id,
            "escalated_at": row.escalated_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "messages": [
                {
                    "id": message.id,
                    "sender_user_id": message.sender_user_id,
                    "body": message.body,
                    "created_at": message.created_at,
                }
                for message in row.messages
            ]
            if include_messages
            else [],
        }
        if include_history:
            result["actions"] = [
                {
                    "id": action.id,
                    "actor_user_id": action.actor_user_id,
                    "action": action.action,
                    "note": action.note,
                    "created_at": action.created_at,
                }
                for action in row.actions
            ]
        else:
            result["actions"] = []
        return result
