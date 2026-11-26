"""Owner-scoped reads for HomeScout personal hub resources."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.marketplace import PropertyAlert, PropertySearchHistory, SavedProperty
from app.models.notification import InAppNotification
from app.models.personal_hub import (
    AccountDeletionRequest,
    CollectionShare,
    ManualRecord,
    PersonalActivity,
    PrivateDocument,
    SavedCollection,
    SavedHubItem,
    ScheduleEntry,
    SupportTicket,
    UserPreference,
)


class PersonalHubDataAccess:
    def preferences(self, session: Session, user_id: UUID) -> UserPreference | None:
        return session.get(UserPreference, user_id)

    def saved_items(self, session: Session, user_id: UUID) -> list[SavedHubItem]:
        return list(
            session.scalars(
                select(SavedHubItem)
                .where(SavedHubItem.owner_user_id == user_id)
                .order_by(SavedHubItem.created_at.desc())
                .limit(500)
            )
        )

    def collections(self, session: Session, user_id: UUID) -> list[SavedCollection]:
        return list(
            session.scalars(
                select(SavedCollection)
                .outerjoin(CollectionShare, CollectionShare.collection_id == SavedCollection.id)
                .where(
                    or_(
                        SavedCollection.owner_user_id == user_id,
                        CollectionShare.shared_with_user_id == user_id,
                    )
                )
                .order_by(SavedCollection.updated_at.desc())
                .limit(200)
            ).unique()
        )

    def collection_items(self, session: Session, collection_id: UUID) -> list[SavedHubItem]:
        return list(
            session.scalars(
                select(SavedHubItem)
                .where(SavedHubItem.collection_id == collection_id)
                .order_by(SavedHubItem.created_at.desc())
                .limit(500)
            )
        )

    def collection_shares(self, session: Session, collection_id: UUID) -> list[CollectionShare]:
        return list(
            session.scalars(
                select(CollectionShare)
                .where(CollectionShare.collection_id == collection_id)
                .order_by(CollectionShare.created_at)
            )
        )

    def activity(
        self, session: Session, user_id: UUID, event_type: str | None, limit: int
    ) -> list[PersonalActivity]:
        query = select(PersonalActivity).where(PersonalActivity.owner_user_id == user_id)
        if event_type:
            query = query.where(PersonalActivity.event_type == event_type)
        return list(
            session.scalars(query.order_by(PersonalActivity.created_at.desc()).limit(limit))
        )

    def schedule(self, session: Session, user_id: UUID, after, before) -> list[ScheduleEntry]:
        query = select(ScheduleEntry).where(ScheduleEntry.owner_user_id == user_id)
        if after is not None:
            query = query.where(ScheduleEntry.starts_at >= after)
        if before is not None:
            query = query.where(ScheduleEntry.starts_at < before)
        return list(session.scalars(query.order_by(ScheduleEntry.starts_at).limit(500)))

    def notifications(
        self, session: Session, user_id: UUID, category: str | None, unread_only: bool
    ) -> list[InAppNotification]:
        query = select(InAppNotification).where(
            InAppNotification.recipient_user_id == user_id,
            InAppNotification.dismissed_at.is_(None),
        )
        if category:
            query = query.where(InAppNotification.category == category)
        if unread_only:
            query = query.where(InAppNotification.read_at.is_(None))
        return list(session.scalars(query.order_by(InAppNotification.created_at.desc()).limit(200)))

    def manual_records(self, session: Session, user_id: UUID) -> list[ManualRecord]:
        return list(
            session.scalars(
                select(ManualRecord)
                .where(ManualRecord.owner_user_id == user_id)
                .order_by(ManualRecord.record_date.desc())
                .limit(500)
            )
        )

    def marketplace_saves(self, session: Session, user_id: UUID) -> list[SavedProperty]:
        return list(
            session.scalars(
                select(SavedProperty)
                .where(SavedProperty.user_id == user_id)
                .order_by(SavedProperty.created_at.desc())
                .limit(500)
            )
        )

    def search_history(self, session: Session, user_id: UUID) -> list[PropertySearchHistory]:
        return list(
            session.scalars(
                select(PropertySearchHistory)
                .where(PropertySearchHistory.user_id == user_id)
                .order_by(PropertySearchHistory.created_at.desc())
                .limit(200)
            )
        )

    def alerts(self, session: Session, user_id: UUID) -> list[PropertyAlert]:
        return list(
            session.scalars(
                select(PropertyAlert)
                .where(PropertyAlert.user_id == user_id)
                .order_by(PropertyAlert.created_at.desc())
                .limit(200)
            )
        )

    def notifications_for_export(self, session: Session, user_id: UUID) -> list[InAppNotification]:
        return list(
            session.scalars(
                select(InAppNotification)
                .where(InAppNotification.recipient_user_id == user_id)
                .order_by(InAppNotification.created_at.desc())
                .limit(200)
            )
        )

    def documents(self, session: Session, user_id: UUID) -> list[PrivateDocument]:
        return list(
            session.scalars(
                select(PrivateDocument)
                .where(PrivateDocument.owner_user_id == user_id)
                .order_by(PrivateDocument.uploaded_at.desc())
                .limit(200)
            )
        )

    def tickets(self, session: Session, user_id: UUID) -> list[SupportTicket]:
        return list(
            session.scalars(
                select(SupportTicket)
                .options(selectinload(SupportTicket.messages))
                .where(SupportTicket.owner_user_id == user_id)
                .order_by(SupportTicket.updated_at.desc())
                .limit(100)
            )
        )

    def deletion_requests(self, session: Session, user_id: UUID) -> list[AccountDeletionRequest]:
        return list(
            session.scalars(
                select(AccountDeletionRequest)
                .where(AccountDeletionRequest.owner_user_id == user_id)
                .order_by(AccountDeletionRequest.created_at.desc())
                .limit(20)
            )
        )
