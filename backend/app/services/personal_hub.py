"""Personal hub rules; each private record is queried through its owner scope."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import PurePath
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import ApiError
from app.data_access.personal_hub import PersonalHubDataAccess
from app.data_access.properties import PropertyDataAccess
from app.models.access_control import Role, UserRoleAssignment
from app.models.notification import InAppNotification
from app.models.personal_hub import (
    AccountDeletionRequest,
    CollectionShare,
    ManualRecord,
    PersonalActivity,
    SavedCollection,
    SavedHubItem,
    ScheduleEntry,
    SupportMessage,
    SupportTicket,
    UserPreference,
)
from app.models.settings import ApplicationSetting
from app.models.user import UserAccount, UserProfile
from app.schemas.personal_hub import (
    ActivityCreate,
    CollectionCreate,
    CollectionShareCreate,
    CollectionUpdate,
    DeletionRequestCreate,
    ManualRecordCreate,
    PreferenceUpdate,
    ProfileUpdate,
    SavedItemCreate,
    SavedItemUpdate,
    ScheduleCreate,
    ScheduleUpdate,
    SupportMessageCreate,
    SupportTicketCreate,
)
from app.services.passwords import password_service


class PersonalHubService:
    def __init__(self) -> None:
        self.data = PersonalHubDataAccess()
        self.properties = PropertyDataAccess()

    def profile(self, session: Session, user_id: uuid.UUID) -> tuple[UserAccount, UserPreference]:
        user = session.scalar(
            select(UserAccount)
            .options(joinedload(UserAccount.profile))
            .where(UserAccount.id == user_id)
        )
        if user is None:
            raise self._not_found()
        preference = session.get(UserPreference, user_id)
        if preference is None:
            preference = UserPreference(user_id=user_id)
            session.add(preference)
            session.commit()
        return user, preference

    def update_profile(
        self, session: Session, user_id: uuid.UUID, body: ProfileUpdate
    ) -> tuple[UserAccount, UserPreference]:
        user, preference = self.profile(session, user_id)
        profile = user.profile
        if profile is None:
            profile = UserProfile(user_id=user_id)
            user.profile = profile
        if body.phone_number is not None:
            normalized_phone = re.sub(r"[\s()-]", "", body.phone_number)
            if normalized_phone and not re.fullmatch(r"\+?[0-9]{7,15}", normalized_phone):
                raise ApiError(
                    422,
                    "invalid_phone_number",
                    "Enter 7 to 15 digits, optionally beginning with a plus sign.",
                )
            if normalized_phone and session.scalar(
                select(UserAccount.id).where(
                    UserAccount.phone_number == normalized_phone, UserAccount.id != user_id
                )
            ):
                raise ApiError(
                    409, "phone_in_use", "That phone number is already linked to another account."
                )
            user.phone_number = normalized_phone or None
        for name in ("given_name", "family_name", "preferred_name", "location_label", "bio"):
            value = getattr(body, name)
            if value is not None:
                setattr(profile, name, value.strip() or None)
        session.commit()
        return user, preference

    def preferences(self, session: Session, user_id: uuid.UUID) -> UserPreference:
        preference = session.get(UserPreference, user_id)
        if preference is None:
            preference = UserPreference(user_id=user_id)
            session.add(preference)
            session.commit()
        return preference

    def update_preferences(
        self, session: Session, user_id: uuid.UUID, body: PreferenceUpdate
    ) -> UserPreference:
        preference = self.preferences(session, user_id)
        if body.appearance is not None:
            preference.appearance = body.appearance
        if body.notification_preferences is not None:
            preference.notification_preferences = body.notification_preferences
        if body.accessibility_preferences is not None:
            preference.accessibility_preferences = body.accessibility_preferences
        session.commit()
        return preference

    def set_active_role(
        self, session: Session, user_id: uuid.UUID, role_code: str
    ) -> UserPreference:
        assigned = session.scalar(
            select(Role.code)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(UserRoleAssignment.user_id == user_id, Role.code == role_code)
        )
        if assigned is None:
            raise ApiError(
                403,
                "role_not_assigned",
                "You can switch only to a role already assigned to your account.",
            )
        preference = self.preferences(session, user_id)
        previous_role = preference.active_role_code
        preference.active_role_code = role_code
        if previous_role != role_code:
            session.add(
                PersonalActivity(
                    owner_user_id=user_id,
                    event_type="account",
                    title="Changed active profile",
                    details=f"Active role changed to {role_code.replace('_', ' ')}.",
                    target_path="/hub/profile",
                )
            )
        session.commit()
        return preference

    def save_item(
        self, session: Session, user_id: uuid.UUID, body: SavedItemCreate
    ) -> SavedHubItem:
        if body.kind == "property":
            if (
                body.reference_id is None
                or self.properties.list_public_by_id(session, body.reference_id, include_demo=False)
                is None
            ):
                raise self._not_found("This property is not available to save.")
        if body.collection_id:
            self.require_collection_access(session, user_id, body.collection_id, edit=True)
        row = SavedHubItem(
            owner_user_id=user_id,
            kind=body.kind,
            title=body.title.strip(),
            reference_id=body.reference_id,
            target_path=body.target_path,
            personal_note=body.personal_note,
            collection_id=body.collection_id,
        )
        session.add(row)
        session.add(
            PersonalActivity(
                owner_user_id=user_id,
                event_type="saved_item",
                title=f"Saved {body.kind.replace('_', ' ')}: {body.title.strip()}",
                target_path=body.target_path,
            )
        )
        session.commit()
        session.refresh(row)
        return row

    def update_saved_item(
        self, session: Session, user_id: uuid.UUID, item_id: uuid.UUID, body: SavedItemUpdate
    ) -> SavedHubItem:
        row = session.get(SavedHubItem, item_id)
        if row is None or not self.can_edit_saved_item(session, user_id, row):
            raise self._not_found()
        values = body.model_dump(exclude_unset=True)
        if values.get("collection_id") is not None:
            self.require_collection_access(session, user_id, values["collection_id"], edit=True)
        if row.owner_user_id != user_id and "collection_id" in values:
            raise ApiError(
                403,
                "collection_owner_required",
                "Only the collection owner can move a shared item.",
            )
        for name, value in values.items():
            setattr(row, name, value.strip() if isinstance(value, str) else value)
        session.commit()
        session.refresh(row)
        return row

    def create_collection(
        self, session: Session, user_id: uuid.UUID, body: CollectionCreate
    ) -> SavedCollection:
        row = SavedCollection(
            owner_user_id=user_id, name=body.name.strip(), description=body.description
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    def update_collection(
        self, session: Session, user_id: uuid.UUID, collection_id: uuid.UUID, body: CollectionUpdate
    ) -> SavedCollection:
        row = session.get(SavedCollection, collection_id)
        if row is None or row.owner_user_id != user_id:
            raise self._not_found()
        if body.name is not None:
            row.name = body.name.strip()
        if body.description is not None:
            row.description = body.description
        session.commit()
        session.refresh(row)
        return row

    def share_collection(
        self,
        session: Session,
        user_id: uuid.UUID,
        collection_id: uuid.UUID,
        body: CollectionShareCreate,
    ) -> CollectionShare:
        collection = session.get(SavedCollection, collection_id)
        if collection is None or collection.owner_user_id != user_id:
            raise self._not_found()
        if body.user_id == user_id or session.get(UserAccount, body.user_id) is None:
            raise ApiError(
                422, "invalid_share_recipient", "Choose another existing HomeScout account."
            )
        share = session.get(CollectionShare, (collection_id, body.user_id))
        if share is None:
            share = CollectionShare(
                collection_id=collection_id,
                shared_with_user_id=body.user_id,
                can_edit=body.can_edit,
            )
            session.add(share)
        else:
            share.can_edit = body.can_edit
        session.commit()
        return share

    def require_collection_access(
        self, session: Session, user_id: uuid.UUID, collection_id: uuid.UUID, *, edit: bool = False
    ) -> SavedCollection:
        collection = session.get(SavedCollection, collection_id)
        if collection is None:
            raise self._not_found()
        if collection.owner_user_id == user_id:
            return collection
        share = session.get(CollectionShare, (collection_id, user_id))
        if share is None or (edit and not share.can_edit):
            raise self._not_found()
        return collection

    def can_edit_saved_item(self, session: Session, user_id: uuid.UUID, row: SavedHubItem) -> bool:
        if row.owner_user_id == user_id:
            return True
        if row.collection_id is None:
            return False
        share = session.get(CollectionShare, (row.collection_id, user_id))
        return bool(share and share.can_edit)

    def add_activity(
        self, session: Session, user_id: uuid.UUID, body: ActivityCreate
    ) -> PersonalActivity:
        row = PersonalActivity(
            owner_user_id=user_id,
            event_type=body.event_type,
            title=body.title.strip(),
            details=body.details,
            target_path=body.target_path,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    def create_schedule(
        self, session: Session, user_id: uuid.UUID, body: ScheduleCreate
    ) -> ScheduleEntry:
        self._validate_timezone(body.timezone)
        if body.ends_at and body.ends_at <= body.starts_at:
            raise ApiError(422, "invalid_schedule_range", "End time must be after start time.")
        values = body.model_dump()
        values["starts_at"] = values["starts_at"].astimezone(UTC)
        if values["ends_at"] is not None:
            values["ends_at"] = values["ends_at"].astimezone(UTC)
        row = ScheduleEntry(owner_user_id=user_id, **values)
        session.add(row)
        session.add(
            PersonalActivity(
                owner_user_id=user_id,
                event_type="viewing" if body.category == "viewing" else "account",
                title=f"Added to schedule: {body.title.strip()}",
                details=f"{body.category.replace('_', ' ')} · {body.starts_at.isoformat()}",
                target_path="/hub/schedule",
            )
        )
        session.commit()
        session.refresh(row)
        return row

    def update_schedule(
        self, session: Session, user_id: uuid.UUID, entry_id: uuid.UUID, body: ScheduleUpdate
    ) -> ScheduleEntry:
        row = session.get(ScheduleEntry, entry_id)
        if row is None or row.owner_user_id != user_id:
            raise self._not_found()
        values = body.model_dump(exclude_unset=True)
        if values.get("timezone"):
            self._validate_timezone(values["timezone"])
        starts = values.get("starts_at", row.starts_at)
        ends = values.get("ends_at", row.ends_at)
        if starts is not None and starts.tzinfo is None:
            starts = starts.replace(tzinfo=UTC)
        if ends is not None and ends.tzinfo is None:
            ends = ends.replace(tzinfo=UTC)
        if starts and ends and ends <= starts:
            raise ApiError(422, "invalid_schedule_range", "End time must be after start time.")
        for name, value in values.items():
            if name in {"starts_at", "ends_at"} and value is not None:
                value = value.astimezone(UTC)
            setattr(row, name, value)
        session.commit()
        session.refresh(row)
        return row

    def delete_schedule(self, session: Session, user_id: uuid.UUID, entry_id: uuid.UUID) -> None:
        row = session.get(ScheduleEntry, entry_id)
        if row is None or row.owner_user_id != user_id:
            raise self._not_found()
        session.delete(row)
        session.commit()

    def add_manual_record(
        self, session: Session, user_id: uuid.UUID, body: ManualRecordCreate
    ) -> ManualRecord:
        role_codes = set(
            session.scalars(
                select(Role.code)
                .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
                .where(UserRoleAssignment.user_id == user_id)
            )
        )
        role_categories = {
            "tenant": {"rent", "deposit", "expense", "receipt"},
            "roommate": {"rent", "deposit", "expense", "receipt"},
            "service_provider": {"booking", "order", "expense", "receipt"},
            "landlord": {"viewing", "expense", "receipt", "order"},
            "real_estate_agent": {"viewing", "expense", "receipt", "order"},
            "property_manager": {"viewing", "expense", "receipt", "order"},
            "moderator": set(),
            "admin": set(),
            "super_admin": set(),
        }
        allowed_categories = {"other"}.union(
            *(role_categories.get(code, set()) for code in role_codes)
        )
        if body.category not in allowed_categories:
            raise ApiError(
                403,
                "record_category_not_available",
                "This record category is not available for your assigned account roles.",
            )
        values = body.model_dump()
        values["record_date"] = values["record_date"].astimezone(UTC)
        row = ManualRecord(owner_user_id=user_id, **values, evidence_status="user_entered")
        session.add(row)
        session.add(
            PersonalActivity(
                owner_user_id=user_id,
                event_type="finance",
                title=f"Added a personal {body.category} record",
                details="This record was entered by the account holder.",
                target_path="/hub/records",
            )
        )
        session.commit()
        session.refresh(row)
        return row

    def create_ticket(
        self, session: Session, user_id: uuid.UUID, body: SupportTicketCreate
    ) -> SupportTicket:
        allow_new_tickets = session.get(ApplicationSetting, "support.allow_new_tickets")
        if allow_new_tickets is not None and not allow_new_tickets.value.get("value", True):
            raise ApiError(
                503,
                "support_temporarily_unavailable",
                "New support tickets are temporarily unavailable.",
            )
        category_setting = session.get(ApplicationSetting, f"category.support.{body.category}")
        if category_setting is not None and not category_setting.value.get("value", True):
            raise ApiError(
                422, "support_category_unavailable", "Choose an available support category."
            )
        row = SupportTicket(
            owner_user_id=user_id, subject=body.subject.strip(), category=body.category
        )
        row.messages.append(SupportMessage(sender_user_id=user_id, body=body.message.strip()))
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    def add_ticket_message(
        self, session: Session, user_id: uuid.UUID, ticket_id: uuid.UUID, body: SupportMessageCreate
    ) -> SupportTicket:
        row = session.scalar(
            select(SupportTicket)
            .options(joinedload(SupportTicket.messages))
            .where(SupportTicket.id == ticket_id, SupportTicket.owner_user_id == user_id)
        )
        if row is None:
            raise self._not_found()
        if row.status == "closed":
            raise ApiError(409, "ticket_closed", "This support ticket is closed.")
        row.messages.append(SupportMessage(sender_user_id=user_id, body=body.body.strip()))
        row.status = "open"
        session.commit()
        session.refresh(row)
        return row

    def create_deletion_request(
        self, session: Session, user_id: uuid.UUID, body: DeletionRequestCreate
    ) -> AccountDeletionRequest:
        user = session.get(UserAccount, user_id)
        if user is None or not password_service.verify(user.password_hash, body.current_password):
            raise ApiError(
                403, "reauthentication_failed", "Confirm your current password to continue."
            )
        row = AccountDeletionRequest(owner_user_id=user_id)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    def cancel_deletion_request(
        self, session: Session, user_id: uuid.UUID, request_id: uuid.UUID
    ) -> AccountDeletionRequest:
        row = session.get(AccountDeletionRequest, request_id)
        if row is None or row.owner_user_id != user_id:
            raise self._not_found()
        if row.status == "pending":
            row.status = "cancelled"
            session.commit()
        return row

    def mark_notification(
        self, session: Session, user_id: uuid.UUID, notification_id: uuid.UUID, *, dismiss: bool
    ) -> InAppNotification:
        row = session.get(InAppNotification, notification_id)
        if row is None or row.recipient_user_id != user_id:
            raise self._not_found()
        now = datetime.now(UTC)
        if dismiss:
            row.dismissed_at = row.dismissed_at or now
        else:
            row.read_at = row.read_at or now
        session.commit()
        session.refresh(row)
        return row

    @staticmethod
    def mark_all_notifications_read(session: Session, user_id: uuid.UUID) -> int:
        rows = list(
            session.scalars(
                select(InAppNotification).where(
                    InAppNotification.recipient_user_id == user_id,
                    InAppNotification.dismissed_at.is_(None),
                    InAppNotification.read_at.is_(None),
                )
            )
        )
        now = datetime.now(UTC)
        for row in rows:
            row.read_at = now
        session.commit()
        return len(rows)

    @staticmethod
    def _validate_timezone(name: str) -> None:
        try:
            ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            raise ApiError(
                422, "invalid_timezone", "Choose a supported timezone such as Africa/Nairobi."
            ) from None

    @staticmethod
    def clean_filename(name: str) -> str:
        leaf = PurePath(name.replace("\\", "/")).name
        cleaned = re.sub(r"[^A-Za-z0-9._ -]", "", leaf).strip(" .")
        return (cleaned or "document")[:180]

    @staticmethod
    def _not_found(message: str = "The requested personal hub item was not found.") -> ApiError:
        return ApiError(404, "personal_item_not_found", message)
