"""Data access for saved listings, alerts, search history, and enquiries."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.marketplace import (
    PropertyAlert,
    PropertyEnquiry,
    PropertyReport,
    PropertySearchHistory,
    SavedProperty,
)
from app.models.property import Property


class MarketplaceDataAccess:
    def saved_properties(
        self, session: Session, user_id: UUID, *, include_demo: bool = False
    ) -> list[Property]:
        public = (
            (Property.is_demo.is_(False))
            & (Property.listing_status == "published")
            & (Property.availability_status == "available")
        )
        visible = or_(public, Property.is_demo.is_(True)) if include_demo else public
        statement = (
            select(Property)
            .join(SavedProperty, SavedProperty.property_id == Property.id)
            .where(
                SavedProperty.user_id == user_id,
                visible,
                Property.moderation_status == "clear",
            )
            .order_by(SavedProperty.created_at.desc(), Property.id)
        )
        return list(session.scalars(statement))

    def histories(self, session: Session, user_id: UUID, limit: int) -> list[PropertySearchHistory]:
        return list(
            session.scalars(
                select(PropertySearchHistory)
                .where(PropertySearchHistory.user_id == user_id)
                .order_by(PropertySearchHistory.created_at.desc())
                .limit(limit)
            )
        )

    def alerts(self, session: Session, user_id: UUID) -> list[PropertyAlert]:
        return list(
            session.scalars(
                select(PropertyAlert)
                .where(PropertyAlert.user_id == user_id)
                .order_by(PropertyAlert.created_at.desc())
            )
        )

    def received_enquiries(self, session: Session, user_id: UUID) -> list[PropertyEnquiry]:
        statement = (
            select(PropertyEnquiry)
            .join(Property, Property.id == PropertyEnquiry.property_id)
            .where(
                or_(
                    Property.owner_user_id == user_id,
                    Property.authorized_agent_user_id == user_id,
                    Property.property_manager_user_id == user_id,
                )
            )
            .order_by(PropertyEnquiry.created_at.desc())
            .limit(200)
        )
        return list(session.scalars(statement))

    def sent_enquiries(self, session: Session, user_id: UUID) -> list[PropertyEnquiry]:
        return list(
            session.scalars(
                select(PropertyEnquiry)
                .where(PropertyEnquiry.sender_user_id == user_id)
                .order_by(PropertyEnquiry.created_at.desc())
                .limit(200)
            )
        )

    def reports_by_user(self, session: Session, user_id: UUID) -> list[PropertyReport]:
        return list(
            session.scalars(
                select(PropertyReport)
                .where(PropertyReport.reporter_user_id == user_id)
                .order_by(PropertyReport.created_at.desc())
            )
        )


__all__ = ["MarketplaceDataAccess"]
