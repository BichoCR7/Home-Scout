"""Host-confirmed viewing requests and private, consent-shareable journal records."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.notification import InAppNotification
from app.models.personal_hub import PrivateDocument, ScheduleEntry
from app.models.phase10 import (
    ScheduledViewing,
    ViewingHistory,
    ViewingJournal,
    ViewingJournalMedia,
    ViewingJournalShare,
)
from app.models.property import Property
from app.models.trust import SafeViewing
from app.models.user import UserAccount
from app.schemas.phase10 import (
    JournalShareCreate,
    ViewingAction,
    ViewingJournalCreate,
    ViewingJournalResponse,
    ViewingRequestCreate,
    ViewingResponse,
)
from app.services.authorization import AuthorizationService
from app.services.phase10_cipher import Phase10Cipher

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}


class ViewingService:
    def __init__(self, cipher: Phase10Cipher) -> None:
        self.cipher = cipher
        self.authorization = AuthorizationService()

    def request_viewing(
        self,
        session: Session,
        user_id: UUID,
        body: ViewingRequestCreate,
        *,
        request_id: str | None = None,
    ) -> ViewingResponse:
        self._permission(session, user_id, "viewing:create:self", "user", str(user_id))
        property_ = self._public_property(session, body.property_id)
        if property_ is None:
            raise ApiError(404, "property_not_found", "The available property was not found.")
        host_id = (
            property_.authorized_agent_user_id
            or property_.property_manager_user_id
            or property_.owner_user_id
        )
        if host_id == user_id:
            raise ApiError(
                409, "own_listing_viewing", "You cannot request a viewing for your own listing."
            )
        requested_at = body.requested_at.astimezone(UTC)
        now = datetime.now(UTC)
        if requested_at < now + timedelta(hours=1) or requested_at > now + timedelta(days=365):
            raise ApiError(
                422,
                "viewing_time_out_of_range",
                "Choose a viewing time at least one hour from now and within one year.",
            )
        safe_viewing_id = None
        if body.safe_viewing_id is not None:
            safe_plan = session.get(SafeViewing, body.safe_viewing_id)
            if (
                safe_plan is None
                or safe_plan.owner_user_id != user_id
                or safe_plan.property_id != property_.id
                or safe_plan.status == "cancelled"
            ):
                raise ApiError(404, "safe_viewing_not_found", "The safety plan was not found.")
            safe_viewing_id = safe_plan.id
        row = ScheduledViewing(
            property_id=property_.id,
            requester_user_id=user_id,
            host_user_id=host_id,
            requested_at=requested_at,
            timezone=body.timezone,
            request_message=body.message,
            safe_viewing_id=safe_viewing_id,
            status="requested",
        )
        session.add(row)
        session.flush()
        session.add(
            ViewingHistory(
                viewing_id=row.id,
                actor_user_id=user_id,
                action="requested",
                from_status=None,
                to_status="requested",
                note=body.message,
            )
        )
        session.add(
            InAppNotification(
                recipient_user_id=host_id,
                category="viewing_request",
                title="Viewing request received",
                body="A HomeScout member requested a time to see your listing.",
                target_path="/collaboration?tab=Viewings",
            )
        )
        session.commit()
        return self._viewing_response(session, row, user_id)

    def calendar(
        self,
        session: Session,
        user_id: UUID,
        *,
        start: datetime | None,
        end: datetime | None,
        status_filter: str | None = None,
    ) -> list[ViewingResponse]:
        self._permission(session, user_id, "viewing:view:participant", "user", str(user_id))
        statement = select(ScheduledViewing).where(
            or_(
                ScheduledViewing.requester_user_id == user_id,
                ScheduledViewing.host_user_id == user_id,
            )
        )
        if start is not None:
            statement = statement.where(ScheduledViewing.requested_at >= start.astimezone(UTC))
        if end is not None:
            statement = statement.where(ScheduledViewing.requested_at <= end.astimezone(UTC))
        if status_filter:
            statement = statement.where(ScheduledViewing.status == status_filter)
        rows = session.scalars(statement.order_by(ScheduledViewing.requested_at.desc()).limit(200))
        return [self._viewing_response(session, row, user_id) for row in rows]

    def viewing_action(
        self,
        session: Session,
        user_id: UUID,
        viewing_id: UUID,
        body: ViewingAction,
        *,
        request_id: str | None = None,
    ) -> ViewingResponse:
        row = session.get(ScheduledViewing, viewing_id)
        if row is None or user_id not in {row.requester_user_id, row.host_user_id}:
            raise self.not_found("The viewing was not found.")
        self._permission(session, user_id, "viewing:view:participant", "user", str(user_id))
        host = user_id == row.host_user_id
        requester = user_id == row.requester_user_id
        property_ = session.get(Property, row.property_id)
        if host and property_ is not None:
            self._permission(
                session,
                user_id,
                "viewing:manage:assigned",
                "property",
                str(property_.id),
            )
        now = datetime.now(UTC)
        old_status = row.status
        action = body.action
        if action == "confirm":
            self._require_host(host)
            if row.status != "requested":
                raise ApiError(
                    409, "viewing_not_confirmable", "Only a pending request can be confirmed."
                )
            row.status = "confirmed"
            row.confirmed_at = now
            recipient_id = row.requester_user_id
        elif action == "propose_reschedule":
            self._require_host(host)
            if row.status not in {"requested", "confirmed"}:
                raise ApiError(
                    409,
                    "viewing_not_reschedulable",
                    "This viewing cannot be rescheduled in its current state.",
                )
            proposed = body.proposed_at.astimezone(UTC) if body.proposed_at else None
            if (
                proposed is None
                or proposed < now + timedelta(hours=1)
                or proposed > now + timedelta(days=365)
            ):
                raise ApiError(
                    422,
                    "viewing_time_out_of_range",
                    "Choose a proposed time at least one hour from now and within one year.",
                )
            row.proposed_at = proposed
            row.status = "reschedule_proposed"
            row.host_message = body.note
            recipient_id = row.requester_user_id
        elif action == "accept_reschedule":
            self._require_requester(requester)
            if row.status != "reschedule_proposed" or row.proposed_at is None:
                raise ApiError(
                    409, "no_reschedule_to_accept", "There is no proposed time to accept."
                )
            row.requested_at = row.proposed_at
            row.proposed_at = None
            row.status = "confirmed"
            row.confirmed_at = now
            row.host_message = None
            recipient_id = row.host_user_id
        elif action == "decline":
            self._require_host(host)
            if row.status not in {"requested", "reschedule_proposed"}:
                raise ApiError(
                    409, "viewing_not_declineable", "This viewing can no longer be declined."
                )
            row.status = "declined"
            row.host_message = body.note
            recipient_id = row.requester_user_id
        elif action == "cancel":
            if row.status not in {"requested", "confirmed", "reschedule_proposed"}:
                raise ApiError(
                    409, "viewing_not_cancellable", "This viewing can no longer be cancelled."
                )
            row.status = "cancelled"
            row.host_message = body.note if host else row.host_message
            recipient_id = row.requester_user_id if host else row.host_user_id
        else:
            self._require_host(host)
            if row.status != "confirmed" or row.requested_at > now:
                raise ApiError(
                    409,
                    "viewing_not_complete",
                    "Only a confirmed viewing after its scheduled time can be completed.",
                )
            row.status = "completed"
            recipient_id = row.requester_user_id
        row.updated_at = now
        session.add(
            ViewingHistory(
                viewing_id=row.id,
                actor_user_id=user_id,
                action=action,
                from_status=old_status,
                to_status=row.status,
                note=body.note,
            )
        )
        session.add(
            InAppNotification(
                recipient_user_id=recipient_id,
                category="viewing_update",
                title="Viewing updated",
                body="A HomeScout viewing request has a status update.",
                target_path="/collaboration?tab=Viewings",
            )
        )
        self._sync_schedule_entries(
            session, row, property_title=property_.title if property_ else "Home viewing"
        )
        session.commit()
        return self._viewing_response(session, row, user_id)

    def create_journal(
        self,
        session: Session,
        user_id: UUID,
        body: ViewingJournalCreate,
    ) -> ViewingJournalResponse:
        property_ = session.get(Property, body.property_id)
        if property_ is None:
            raise self.not_found("The property was not found.")
        viewing = None
        if body.viewing_id is not None:
            viewing = session.get(ScheduledViewing, body.viewing_id)
            if viewing is None or user_id not in {viewing.requester_user_id, viewing.host_user_id}:
                raise self.not_found("The viewing was not found.")
            if viewing.property_id != property_.id:
                raise ApiError(
                    422, "journal_property_mismatch", "The journal property must match its viewing."
                )
            if viewing.status not in {"confirmed", "completed", "cancelled"}:
                raise ApiError(
                    409,
                    "viewing_not_started",
                    "A journal can be linked after a viewing is confirmed.",
                )
        if body.viewing_id is None and self._public_property(session, property_.id) is None:
            raise self.not_found("The public property was not found.")
        self._validate_photos(session, user_id, body.photo_document_ids)
        row = ViewingJournal(
            owner_user_id=user_id,
            property_id=property_.id,
            viewing_id=viewing.id if viewing else None,
            title=body.title,
            encrypted_data=b"",
        )
        session.add(row)
        session.flush()
        row.encrypted_data = self._encrypt_journal(user_id, row, body)
        for document_id in body.photo_document_ids:
            session.add(ViewingJournalMedia(journal_id=row.id, document_id=document_id))
        session.commit()
        return self._journal_response(session, row, can_edit=True)

    def update_journal(
        self,
        session: Session,
        user_id: UUID,
        journal_id: UUID,
        body: ViewingJournalCreate,
    ) -> ViewingJournalResponse:
        row = session.get(ViewingJournal, journal_id)
        if row is None or row.owner_user_id != user_id:
            raise self.not_found("The journal was not found.")
        property_ = session.get(Property, body.property_id)
        if property_ is None:
            raise self.not_found("The property was not found.")
        if body.viewing_id is not None:
            viewing = session.get(ScheduledViewing, body.viewing_id)
            if (
                viewing is None
                or user_id not in {viewing.requester_user_id, viewing.host_user_id}
                or viewing.property_id != property_.id
                or viewing.status not in {"confirmed", "completed", "cancelled"}
            ):
                raise ApiError(
                    422, "invalid_journal_viewing", "Choose a confirmed viewing for this property."
                )
        if body.viewing_id is None and self._public_property(session, property_.id) is None:
            raise self.not_found("The public property was not found.")
        self._validate_photos(session, user_id, body.photo_document_ids)
        row.property_id = property_.id
        row.viewing_id = body.viewing_id
        row.title = body.title
        row.encrypted_data = self._encrypt_journal(user_id, row, body)
        row.updated_at = datetime.now(UTC)
        for media in list(
            session.scalars(
                select(ViewingJournalMedia).where(ViewingJournalMedia.journal_id == row.id)
            )
        ):
            session.delete(media)
        for document_id in body.photo_document_ids:
            session.add(ViewingJournalMedia(journal_id=row.id, document_id=document_id))
        session.commit()
        return self._journal_response(session, row, can_edit=True)

    def journals(self, session: Session, user_id: UUID) -> list[ViewingJournalResponse]:
        rows = list(
            session.scalars(
                select(ViewingJournal)
                .outerjoin(ViewingJournalShare, ViewingJournalShare.journal_id == ViewingJournal.id)
                .where(
                    or_(
                        ViewingJournal.owner_user_id == user_id,
                        and_(
                            ViewingJournalShare.shared_with_user_id == user_id,
                            ViewingJournalShare.revoked_at.is_(None),
                        ),
                    )
                )
                .order_by(ViewingJournal.updated_at.desc())
            )
        )
        return [
            self._journal_response(session, row, can_edit=row.owner_user_id == user_id)
            for row in rows
        ]

    def journal(self, session: Session, user_id: UUID, journal_id: UUID) -> ViewingJournalResponse:
        row = session.get(ViewingJournal, journal_id)
        if row is None:
            raise self.not_found("The journal was not found.")
        can_edit = row.owner_user_id == user_id
        if not can_edit:
            share = session.get(ViewingJournalShare, (row.id, user_id))
            if share is None or share.revoked_at is not None:
                raise self.not_found("The journal was not found.")
        return self._journal_response(session, row, can_edit=can_edit)

    def share_journal(
        self, session: Session, user_id: UUID, journal_id: UUID, body: JournalShareCreate
    ) -> None:
        row = session.get(ViewingJournal, journal_id)
        account = session.get(UserAccount, body.recipient_user_id)
        if row is None or row.owner_user_id != user_id:
            raise self.not_found("The journal was not found.")
        if body.recipient_user_id == user_id or account is None or account.status != "active":
            raise ApiError(
                422,
                "invalid_journal_recipient",
                "Choose an active HomeScout account to share with.",
            )
        share = session.get(ViewingJournalShare, (journal_id, body.recipient_user_id))
        if share is None:
            session.add(
                ViewingJournalShare(
                    journal_id=journal_id,
                    shared_with_user_id=body.recipient_user_id,
                )
            )
        else:
            share.shared_at = datetime.now(UTC)
            share.revoked_at = None
        session.add(
            InAppNotification(
                recipient_user_id=body.recipient_user_id,
                category="viewing_journal_share",
                title="Viewing journal shared",
                body="A HomeScout member explicitly shared a private viewing journal with you.",
                target_path="/collaboration?tab=Journal",
            )
        )
        session.commit()

    def revoke_journal_share(
        self, session: Session, user_id: UUID, journal_id: UUID, recipient_id: UUID
    ) -> None:
        row = session.get(ViewingJournal, journal_id)
        share = session.get(ViewingJournalShare, (journal_id, recipient_id))
        if (
            row is None
            or row.owner_user_id != user_id
            or share is None
            or share.revoked_at is not None
        ):
            raise self.not_found("The journal share was not found.")
        share.revoked_at = datetime.now(UTC)
        session.commit()

    def journal_photo(
        self, session: Session, user_id: UUID, journal_id: UUID, document_id: UUID
    ) -> PrivateDocument:
        row = session.get(ViewingJournal, journal_id)
        if row is None:
            raise self.not_found("The journal photo was not found.")
        if row.owner_user_id != user_id:
            share = session.get(ViewingJournalShare, (journal_id, user_id))
            if share is None or share.revoked_at is not None:
                raise self.not_found("The journal photo was not found.")
        linked = session.scalar(
            select(ViewingJournalMedia.id).where(
                ViewingJournalMedia.journal_id == journal_id,
                ViewingJournalMedia.document_id == document_id,
            )
        )
        document = session.get(PrivateDocument, document_id)
        if (
            linked is None
            or document is None
            or document.owner_user_id != row.owner_user_id
            or document.content_type not in ALLOWED_PHOTO_TYPES
            or document.storage_encrypted
        ):
            raise self.not_found("The journal photo was not found.")
        return document

    def _viewing_response(
        self, session: Session, row: ScheduledViewing, viewer_id: UUID
    ) -> ViewingResponse:
        property_ = session.get(Property, row.property_id)
        events = list(
            session.scalars(
                select(ViewingHistory)
                .where(ViewingHistory.viewing_id == row.id)
                .order_by(ViewingHistory.created_at)
            )
        )
        return ViewingResponse(
            id=row.id,
            property_id=row.property_id,
            property_title=property_.title if property_ else "Listing",
            requester_user_id=row.requester_user_id,
            host_user_id=row.host_user_id,
            requested_at=row.requested_at,
            proposed_at=row.proposed_at,
            confirmed_at=row.confirmed_at,
            timezone=row.timezone,
            request_message=row.request_message,
            host_message=row.host_message,
            status=row.status,
            is_requester=viewer_id == row.requester_user_id,
            history=[
                {
                    "action": item.action,
                    "from_status": item.from_status,
                    "to_status": item.to_status,
                    "note": item.note,
                    "created_at": item.created_at,
                }
                for item in events
            ],
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _journal_response(
        self, session: Session, row: ViewingJournal, *, can_edit: bool
    ) -> ViewingJournalResponse:
        payload = self.cipher.decrypt_json(
            "viewing_journal", row.owner_user_id, row.id, row.encrypted_data
        )
        property_ = session.get(Property, row.property_id)
        document_ids = list(
            session.scalars(
                select(ViewingJournalMedia.document_id).where(
                    ViewingJournalMedia.journal_id == row.id
                )
            )
        )
        return ViewingJournalResponse(
            id=row.id,
            property_id=row.property_id,
            property_title=property_.title if property_ else "Listing",
            viewing_id=row.viewing_id,
            title=row.title,
            notes=payload.get("notes"),
            pros=payload.get("pros", []),
            cons=payload.get("cons", []),
            rating=payload.get("rating"),
            checklist=payload.get("checklist", {}),
            follow_up_at=payload.get("follow_up_at"),
            photo_document_ids=document_ids,
            owner_user_id=row.owner_user_id,
            can_edit=can_edit,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _encrypt_journal(
        self, user_id: UUID, row: ViewingJournal, body: ViewingJournalCreate
    ) -> bytes:
        return self.cipher.encrypt_json(
            "viewing_journal",
            user_id,
            row.id,
            {
                "notes": body.notes,
                "pros": body.pros,
                "cons": body.cons,
                "rating": body.rating,
                "checklist": body.checklist,
                "follow_up_at": body.follow_up_at,
            },
        )

    @staticmethod
    def _validate_photos(session: Session, user_id: UUID, document_ids: list[UUID]) -> None:
        if len(document_ids) != len(set(document_ids)):
            raise ApiError(422, "duplicate_journal_photo", "Choose each photo once.")
        if not document_ids:
            return
        documents = list(
            session.scalars(select(PrivateDocument).where(PrivateDocument.id.in_(document_ids)))
        )
        if len(documents) != len(document_ids) or any(
            document.owner_user_id != user_id
            or document.category == "verification"
            or document.storage_encrypted
            or document.content_type not in ALLOWED_PHOTO_TYPES
            for document in documents
        ):
            raise ApiError(
                422,
                "invalid_journal_photo",
                "Use image files already stored in your private documents.",
            )

    def _permission(
        self, session: Session, user_id: UUID, code: str, scope: str, scope_id: str
    ) -> None:
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code=code,
            resource_owner_id=user_id if code.endswith(":self") else None,
            resource_scope_type=scope,
            resource_scope_id=scope_id,
        )

    @staticmethod
    def _sync_schedule_entries(
        session: Session, row: ScheduledViewing, *, property_title: str
    ) -> None:
        marker = f"HomeScout viewing:{row.id}"
        for owner_id in {row.requester_user_id, row.host_user_id}:
            entry = session.scalar(
                select(ScheduleEntry).where(
                    ScheduleEntry.owner_user_id == owner_id,
                    ScheduleEntry.description == marker,
                )
            )
            if row.status == "confirmed":
                if entry is None:
                    entry = ScheduleEntry(
                        owner_user_id=owner_id,
                        title=f"Viewing: {property_title}"[:160],
                        description=marker,
                        category="viewing",
                        starts_at=row.requested_at,
                        timezone=row.timezone,
                        reminder_minutes=60,
                        status="planned",
                    )
                    session.add(entry)
                else:
                    entry.starts_at = row.requested_at
                    entry.status = "planned"
                    entry.updated_at = datetime.now(UTC)
            elif entry is not None and row.status in {"cancelled", "declined", "completed"}:
                entry.status = "done" if row.status == "completed" else "cancelled"
                entry.updated_at = datetime.now(UTC)

    @staticmethod
    def _require_host(host: bool) -> None:
        if not host:
            raise ApiError(
                403,
                "viewing_host_action_required",
                "Only the listing contact can perform this action.",
            )

    @staticmethod
    def _require_requester(requester: bool) -> None:
        if not requester:
            raise ApiError(
                403,
                "viewing_requester_action_required",
                "Only the person who requested the viewing can accept this time.",
            )

    @staticmethod
    def _public_property(session: Session, property_id: UUID) -> Property | None:
        return session.scalar(
            select(Property).where(
                Property.id == property_id,
                Property.listing_status == "published",
                Property.availability_status == "available",
                Property.moderation_status == "clear",
                Property.is_demo.is_(False),
            )
        )

    @staticmethod
    def not_found(message: str) -> ApiError:
        return ApiError(404, "viewing_not_found", message)
