"""Marketplace workflows with ownership, visibility, and role checks."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.data_access.marketplace import MarketplaceDataAccess
from app.data_access.properties import PropertyDataAccess
from app.models.audit import AuditEvent
from app.models.marketplace import (
    PropertyAlert,
    PropertyEnquiry,
    PropertyListingMandate,
    PropertyReport,
    PropertySearchHistory,
    SavedProperty,
)
from app.models.personal_hub import PersonalActivity
from app.schemas.marketplace import (
    PropertyAlertCreate,
    PropertyAlertResponse,
    PropertyEnquiryCreate,
    PropertyEnquiryResponse,
    PropertyEnquiryStatusUpdate,
    PropertyReportCreate,
    PropertyReportResponse,
    SearchFilters,
    SearchHistoryCreate,
    SearchHistoryResponse,
)
from app.schemas.properties import (
    ListingMandateCreate,
    ListingMandateResponse,
    PropertyListResponse,
    PropertyResponse,
)
from app.services.authorization import AuthorizationService
from app.services.properties import PropertyService


class MarketplaceService:
    def __init__(self) -> None:
        self.data = MarketplaceDataAccess()
        self.properties = PropertyDataAccess()
        self.property_service = PropertyService()
        self.authorization = AuthorizationService()

    def save(
        self, session: Session, *, user_id: UUID, property_id: UUID, include_demo: bool = False
    ) -> None:
        self._require_user_permission(session, user_id, "property:save:self")
        property_ = self.properties.list_public_by_id(
            session, property_id, include_demo=include_demo
        )
        if property_ is None:
            raise self._property_not_found()
        existing = session.get(SavedProperty, (user_id, property_id))
        if existing is None:
            session.add(SavedProperty(user_id=user_id, property_id=property_id))
            self._track_activity(
                session,
                user_id,
                "saved_item",
                f"Saved {property_.title}",
                target_path=f"/property/{property_id}",
            )
            session.commit()

    def unsave(self, session: Session, *, user_id: UUID, property_id: UUID) -> None:
        self._require_user_permission(session, user_id, "property:save:self")
        existing = session.get(SavedProperty, (user_id, property_id))
        if existing is not None:
            session.delete(existing)
            session.commit()

    def saved(
        self, session: Session, *, user_id: UUID, include_demo: bool = False
    ) -> PropertyListResponse:
        self._require_user_permission(session, user_id, "property:save:self")
        items = [
            self.property_service._response(row)
            for row in self.data.saved_properties(session, user_id, include_demo=include_demo)
        ]
        return PropertyListResponse(items=items, total=len(items), limit=len(items) or 20, offset=0)

    def compare(
        self,
        session: Session,
        *,
        user_id: UUID,
        property_ids: list[UUID],
        include_demo: bool = False,
    ) -> list[PropertyResponse]:
        self._require_user_permission(session, user_id, "property:compare:public", public=True)
        if not 2 <= len(property_ids) <= 4 or len(set(property_ids)) != len(property_ids):
            raise ApiError(422, "invalid_comparison", "Choose two to four different properties.")
        items = [
            self.properties.list_public_by_id(session, property_id, include_demo=include_demo)
            for property_id in property_ids
        ]
        if any(item is None for item in items):
            raise self._property_not_found()
        titles = [item.title for item in items if item is not None]
        self._track_activity(
            session,
            user_id,
            "comparison",
            "Compared properties",
            details=" · ".join(titles)[:500],
            target_path="/discover",
        )
        session.commit()
        return [self.property_service._response(item) for item in items if item is not None]

    def record_search(
        self, session: Session, *, user_id: UUID, request: SearchHistoryCreate
    ) -> SearchHistoryResponse:
        self._require_user_permission(session, user_id, "search:history:self")
        row = PropertySearchHistory(
            user_id=user_id,
            filters=request.filters.model_dump(mode="json", exclude_none=True),
            result_count=request.result_count,
        )
        session.add(row)
        self._track_activity(
            session,
            user_id,
            "search",
            "Searched properties",
            details=request.filters.query,
            target_path="/discover",
        )
        session.flush()
        old_ids = session.scalars(
            select(PropertySearchHistory.id)
            .where(PropertySearchHistory.user_id == user_id)
            .order_by(PropertySearchHistory.created_at.desc())
            .offset(30)
        ).all()
        if old_ids:
            session.execute(
                delete(PropertySearchHistory).where(PropertySearchHistory.id.in_(old_ids))
            )
        session.commit()
        return SearchHistoryResponse(
            id=row.id,
            filters=SearchFilters.model_validate(row.filters),
            result_count=row.result_count,
            created_at=row.created_at,
        )

    def history(
        self, session: Session, *, user_id: UUID, limit: int
    ) -> list[SearchHistoryResponse]:
        self._require_user_permission(session, user_id, "search:history:self")
        return [
            SearchHistoryResponse(
                id=row.id,
                filters=SearchFilters.model_validate(row.filters),
                result_count=row.result_count,
                created_at=row.created_at,
            )
            for row in self.data.histories(session, user_id, limit)
        ]

    def create_alert(
        self, session: Session, *, user_id: UUID, request: PropertyAlertCreate
    ) -> PropertyAlertResponse:
        self._require_user_permission(session, user_id, "alert:manage:self")
        active_count = (
            session.scalar(
                select(func.count())
                .select_from(PropertyAlert)
                .where(PropertyAlert.user_id == user_id, PropertyAlert.is_active.is_(True))
            )
            or 0
        )
        if active_count >= 20:
            raise ApiError(
                409, "alert_limit_reached", "You can keep up to 20 active search alerts."
            )
        row = PropertyAlert(
            user_id=user_id,
            filters=request.filters.model_dump(mode="json", exclude_none=True),
        )
        session.add(row)
        session.commit()
        return self._alert_response(row)

    def alerts(self, session: Session, *, user_id: UUID) -> list[PropertyAlertResponse]:
        self._require_user_permission(session, user_id, "alert:manage:self")
        return [self._alert_response(row) for row in self.data.alerts(session, user_id)]

    def delete_alert(self, session: Session, *, user_id: UUID, alert_id: UUID) -> None:
        self._require_user_permission(session, user_id, "alert:manage:self")
        row = session.get(PropertyAlert, alert_id)
        if row is None or row.user_id != user_id:
            raise ApiError(404, "alert_not_found", "The requested alert was not found.")
        session.delete(row)
        session.commit()

    def create_listing_mandate(
        self,
        session: Session,
        *,
        owner_user_id: UUID,
        request: ListingMandateCreate,
        request_id: str | None = None,
    ) -> ListingMandateResponse:
        self.authorization.require_permission(
            session,
            user_id=owner_user_id,
            permission_code="listing:assign:owned",
            resource_owner_id=owner_user_id,
            resource_scope_type="portfolio",
            resource_scope_id=str(owner_user_id),
        )
        if request.agent_user_id == owner_user_id:
            raise ApiError(422, "invalid_listing_agent", "You cannot appoint yourself as an agent.")
        from app.models.access_control import Role, UserRoleAssignment
        from app.models.user import UserAccount

        agent = session.scalar(select(UserAccount).where(UserAccount.id == request.agent_user_id))
        has_role = session.scalar(
            select(UserRoleAssignment.user_id)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .where(
                UserRoleAssignment.user_id == request.agent_user_id,
                Role.code == "real_estate_agent",
            )
            .limit(1)
        )
        if agent is None or agent.status != "active" or has_role is None:
            raise ApiError(
                422,
                "listing_agent_not_eligible",
                "Choose an active account with an approved agent role.",
            )
        row = session.get(PropertyListingMandate, (owner_user_id, request.agent_user_id))
        if row is None:
            row = PropertyListingMandate(
                owner_user_id=owner_user_id, agent_user_id=request.agent_user_id, is_active=True
            )
            session.add(row)
        else:
            row.is_active = True
            row.revoked_at = None
        session.add(
            AuditEvent(
                actor_user_id=owner_user_id,
                event_type="property.listing_mandate_granted",
                subject_type="listing_mandate",
                subject_id=f"{owner_user_id}:{request.agent_user_id}",
                request_id=request_id,
                metadata_json={},
            )
        )
        session.commit()
        return self._mandate_response(row)

    def listing_mandates(self, session: Session, *, user_id: UUID) -> list[ListingMandateResponse]:
        rows = session.scalars(
            select(PropertyListingMandate)
            .where(
                PropertyListingMandate.is_active.is_(True),
                or_(
                    PropertyListingMandate.agent_user_id == user_id,
                    PropertyListingMandate.owner_user_id == user_id,
                ),
            )
            .order_by(PropertyListingMandate.created_at.desc())
        )
        return [self._mandate_response(row) for row in rows]

    def revoke_listing_mandate(
        self,
        session: Session,
        *,
        owner_user_id: UUID,
        agent_user_id: UUID,
        request_id: str | None = None,
    ) -> None:
        self.authorization.require_permission(
            session,
            user_id=owner_user_id,
            permission_code="listing:assign:owned",
            resource_owner_id=owner_user_id,
            resource_scope_type="portfolio",
            resource_scope_id=str(owner_user_id),
        )
        row = session.get(PropertyListingMandate, (owner_user_id, agent_user_id))
        if row is None or not row.is_active:
            raise ApiError(
                404, "listing_mandate_not_found", "The listing authorization was not found."
            )
        row.is_active = False
        row.revoked_at = datetime.now(UTC)
        from app.models.property import Property

        for property_ in session.scalars(
            select(Property).where(
                Property.owner_user_id == owner_user_id,
                Property.authorized_agent_user_id == agent_user_id,
            )
        ):
            property_.authorized_agent_user_id = None
        session.add(
            AuditEvent(
                actor_user_id=owner_user_id,
                event_type="property.listing_mandate_revoked",
                subject_type="listing_mandate",
                subject_id=f"{owner_user_id}:{agent_user_id}",
                request_id=request_id,
                metadata_json={},
            )
        )
        session.commit()

    def create_enquiry(
        self,
        session: Session,
        *,
        user_id: UUID,
        property_id: UUID,
        request: PropertyEnquiryCreate,
        request_id: str | None = None,
    ) -> PropertyEnquiryResponse:
        self._require_user_permission(session, user_id, "enquiry:create:self")
        property_ = self.properties.list_public_by_id(session, property_id, include_demo=False)
        if property_ is None:
            raise self._property_not_found()
        if property_.owner_user_id == user_id:
            raise ApiError(
                409, "self_enquiry_not_allowed", "You cannot enquire about your own listing."
            )
        recipient_id = (
            property_.authorized_agent_user_id
            or property_.property_manager_user_id
            or property_.owner_user_id
        )
        row = PropertyEnquiry(
            property_id=property_.id,
            sender_user_id=user_id,
            recipient_user_id=recipient_id,
            message=request.message,
            status="new",
        )
        session.add(row)
        session.flush()
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type="property.enquiry_created",
                subject_type="property",
                subject_id=str(property_.id),
                request_id=request_id,
                metadata_json={"enquiry_id": str(row.id)},
            )
        )
        self._track_activity(
            session,
            user_id,
            "message",
            f"Enquired about {property_.title}",
            details="An enquiry was sent to the listing contact.",
            target_path=f"/property/{property_.id}",
        )
        session.commit()
        return self._enquiry_response(row, property_.title)

    def received_enquiries(
        self, session: Session, *, user_id: UUID
    ) -> list[PropertyEnquiryResponse]:
        rows = []
        for enquiry in self.data.received_enquiries(session, user_id):
            property_ = self.properties.get(session, enquiry.property_id)
            if property_ is None:
                continue
            self._require_enquiry_access(session, user_id, property_, "view")
            rows.append(self._enquiry_response(enquiry, property_.title))
        return rows

    def sent_enquiries(self, session: Session, *, user_id: UUID) -> list[PropertyEnquiryResponse]:
        results = []
        for row in self.data.sent_enquiries(session, user_id):
            property_ = self.properties.get(session, row.property_id)
            results.append(self._enquiry_response(row, property_.title if property_ else "Listing"))
        return results

    def report_property(
        self,
        session: Session,
        *,
        user_id: UUID,
        property_id: UUID,
        request: PropertyReportCreate,
        request_id: str | None = None,
    ) -> PropertyReportResponse:
        self._require_user_permission(session, user_id, "property:report:self")
        property_ = self.properties.list_public_by_id(session, property_id, include_demo=False)
        if property_ is None:
            raise self._property_not_found()
        if property_.owner_user_id == user_id:
            raise ApiError(
                409, "own_listing_report_not_allowed", "You cannot report your own listing."
            )
        already_reported = session.scalar(
            select(PropertyReport.id).where(
                PropertyReport.property_id == property_id,
                PropertyReport.reporter_user_id == user_id,
            )
        )
        if already_reported is not None:
            raise ApiError(
                409, "listing_already_reported", "You have already reported this listing."
            )
        row = PropertyReport(
            property_id=property_id,
            reporter_user_id=user_id,
            reason=request.reason,
            details=request.details,
            status="received",
        )
        session.add(row)
        session.flush()
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type="property.report_submitted",
                subject_type="property",
                subject_id=str(property_id),
                request_id=request_id,
                metadata_json={"report_id": str(row.id), "reason": row.reason},
            )
        )
        self._track_activity(
            session,
            user_id,
            "report",
            f"Reported {property_.title}",
            details="The report was recorded for review.",
            target_path=f"/property/{property_.id}",
        )
        session.commit()
        return self._report_response(row, property_.title)

    def reports_by_user(self, session: Session, *, user_id: UUID) -> list[PropertyReportResponse]:
        self._require_user_permission(session, user_id, "property:report:self")
        results = []
        for row in self.data.reports_by_user(session, user_id):
            property_ = self.properties.get(session, row.property_id)
            results.append(self._report_response(row, property_.title if property_ else "Listing"))
        return results

    def update_enquiry(
        self,
        session: Session,
        *,
        user_id: UUID,
        enquiry_id: UUID,
        request: PropertyEnquiryStatusUpdate,
        request_id: str | None = None,
    ) -> PropertyEnquiryResponse:
        row = session.get(PropertyEnquiry, enquiry_id)
        property_ = self.properties.get(session, row.property_id) if row else None
        if row is None or property_ is None:
            raise ApiError(404, "enquiry_not_found", "The requested enquiry was not found.")
        self._require_enquiry_access(session, user_id, property_, "manage")
        if row.status == "closed" and request.status != "closed":
            raise ApiError(409, "enquiry_already_closed", "A closed enquiry cannot be reopened.")
        row.status = request.status
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type="property.enquiry_status_updated",
                subject_type="property_enquiry",
                subject_id=str(row.id),
                request_id=request_id,
                metadata_json={"status": row.status},
            )
        )
        session.commit()
        return self._enquiry_response(row, property_.title)

    def similar(self, session: Session, *, property_id: UUID, limit: int) -> PropertyListResponse:
        target = self.properties.list_public_by_id(session, property_id, include_demo=False)
        if target is None:
            raise self._property_not_found()
        results, _ = self.properties.list_public(
            session,
            county_id=target.county_id,
            town_id=target.town_id,
            neighbourhood_id=target.neighbourhood_id,
            property_type=target.property_type,
            unit_type=None,
            bedrooms=None,
            bedrooms_min=None,
            furnishing=None,
            verified_only=False,
            rent_min=None,
            rent_max=None,
            query=None,
            amenities=[],
            sort_by="newest",
            south=None,
            west=None,
            north=None,
            east=None,
            include_demo=False,
            limit=limit + 1,
            offset=0,
        )
        items = [row for row in results if row.id != target.id][:limit]
        return PropertyListResponse(
            items=[self.property_service._response(row) for row in items],
            total=len(items),
            limit=limit,
            offset=0,
        )

    @staticmethod
    def _track_activity(
        session: Session,
        user_id: UUID,
        event_type: str,
        title: str,
        *,
        details: str | None = None,
        target_path: str | None = None,
    ) -> None:
        session.add(
            PersonalActivity(
                owner_user_id=user_id,
                event_type=event_type,
                title=title[:180],
                details=details[:500] if details else None,
                target_path=target_path,
            )
        )

    def _require_user_permission(
        self, session: Session, user_id: UUID, permission_code: str, *, public: bool = False
    ) -> None:
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code=permission_code,
            resource_owner_id=user_id if permission_code.endswith(":self") else None,
            resource_scope_type="public" if public else "user",
            resource_scope_id="*" if public else str(user_id),
        )

    def _require_enquiry_access(
        self, session: Session, user_id: UUID, property_, action: str
    ) -> None:
        if user_id not in {
            property_.owner_user_id,
            property_.authorized_agent_user_id,
            property_.property_manager_user_id,
        }:
            raise ApiError(404, "enquiry_not_found", "The requested enquiry was not found.")
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code=f"enquiry:{action}:assigned",
            resource_scope_type="property",
            resource_scope_id=str(property_.id),
        )

    @staticmethod
    def _alert_response(row: PropertyAlert) -> PropertyAlertResponse:
        return PropertyAlertResponse(
            id=row.id,
            filters=SearchFilters.model_validate(row.filters),
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _mandate_response(row: PropertyListingMandate) -> ListingMandateResponse:
        return ListingMandateResponse(
            owner_user_id=row.owner_user_id,
            agent_user_id=row.agent_user_id,
            is_active=row.is_active,
            created_at=row.created_at,
        )

    @staticmethod
    def _enquiry_response(row: PropertyEnquiry, property_title: str) -> PropertyEnquiryResponse:
        return PropertyEnquiryResponse(
            id=row.id,
            property_id=row.property_id,
            property_title=property_title,
            sender_user_id=row.sender_user_id,
            recipient_user_id=row.recipient_user_id,
            message=row.message,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _report_response(row: PropertyReport, property_title: str) -> PropertyReportResponse:
        return PropertyReportResponse(
            id=row.id,
            property_id=row.property_id,
            property_title=property_title,
            reason=row.reason,
            details=row.details,
            status=row.status,
            created_at=row.created_at,
        )

    @staticmethod
    def _property_not_found() -> ApiError:
        return ApiError(404, "property_not_found", "The requested property was not found.")
