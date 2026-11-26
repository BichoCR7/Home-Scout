"""Property-resident maintenance requests with manager/provider access checks."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.audit import AuditEvent
from app.models.location import County, Town
from app.models.personal_hub import PrivateDocument
from app.models.property import Property
from app.models.services import (
    MaintenanceHistory,
    MaintenanceRequest,
    MaintenanceRequestPhoto,
    PropertyResidentAccess,
    ServiceArea,
)
from app.models.user import UserAccount
from app.schemas.services import (
    MaintenanceAction,
    MaintenanceAssignment,
    MaintenanceCreate,
    MaintenanceResponse,
    ResidentAccessCreate,
    ResidentAccessResponse,
    ResidentPropertyResponse,
)
from app.services.authorization import AuthorizationService
from app.services.service_catalog import ServiceCatalogService

MAINTENANCE_TO_SERVICE_CATEGORY = {
    "plumbing": {"plumbers", "home_maintenance", "handymen"},
    "electrical": {"electricians", "home_maintenance", "handymen"},
    "cleaning": {"cleaners", "home_maintenance"},
    "internet": {"internet_providers", "home_maintenance"},
    "appliance": {"home_maintenance", "handymen"},
    "structural": {"home_maintenance", "handymen"},
    "other": {"home_maintenance", "handymen", "other"},
}


class MaintenanceService:
    def __init__(self) -> None:
        self.authorization = AuthorizationService()
        self.catalog = ServiceCatalogService()

    def grant_resident(
        self, session: Session, *, manager_id: UUID, property_id: UUID, body: ResidentAccessCreate
    ) -> ResidentAccessResponse:
        property_ = self._managed_property(session, manager_id, property_id)
        if body.resident_user_id == manager_id:
            raise ApiError(
                422, "invalid_resident", "A property manager cannot add themselves as a resident."
            )
        resident = session.get(UserAccount, body.resident_user_id)
        roles = (
            set(self.authorization.role_codes(session, body.resident_user_id))
            if resident
            else set()
        )
        if (
            resident is None
            or resident.status != "active"
            or not roles.intersection({"tenant", "roommate"})
        ):
            raise ApiError(
                422, "resident_account_required", "Choose an active tenant or roommate account."
            )
        row = session.scalar(
            select(PropertyResidentAccess).where(
                PropertyResidentAccess.property_id == property_.id,
                PropertyResidentAccess.resident_user_id == resident.id,
            )
        )
        if row is None:
            row = PropertyResidentAccess(
                property_id=property_.id,
                resident_user_id=resident.id,
                granted_by_user_id=manager_id,
                status="active",
            )
            session.add(row)
        else:
            row.status = "active"
            row.granted_by_user_id = manager_id
            row.granted_at = datetime.now(UTC)
            row.revoked_at = None
        self._audit(
            session,
            manager_id,
            "maintenance.resident_access_granted",
            property_.id,
            {"resident_user_id": str(resident.id)},
        )
        session.commit()
        return ResidentAccessResponse.model_validate(row)

    def revoke_resident(
        self, session: Session, *, manager_id: UUID, property_id: UUID, resident_user_id: UUID
    ) -> ResidentAccessResponse:
        property_ = self._managed_property(session, manager_id, property_id)
        row = session.scalar(
            select(PropertyResidentAccess).where(
                PropertyResidentAccess.property_id == property_.id,
                PropertyResidentAccess.resident_user_id == resident_user_id,
            )
        )
        if row is None:
            raise self._not_found()
        row.status = "revoked"
        row.revoked_at = datetime.now(UTC)
        self._audit(
            session,
            manager_id,
            "maintenance.resident_access_revoked",
            property_.id,
            {"resident_user_id": str(resident_user_id)},
        )
        session.commit()
        return ResidentAccessResponse.model_validate(row)

    def residents(
        self, session: Session, *, manager_id: UUID, property_id: UUID
    ) -> list[ResidentAccessResponse]:
        property_ = self._managed_property(session, manager_id, property_id)
        rows = session.scalars(
            select(PropertyResidentAccess)
            .where(PropertyResidentAccess.property_id == property_.id)
            .order_by(PropertyResidentAccess.granted_at.desc())
        )
        return [ResidentAccessResponse.model_validate(row) for row in rows]

    def resident_properties(
        self, session: Session, *, resident_id: UUID
    ) -> list[ResidentPropertyResponse]:
        self.authorization.require_permission(
            session,
            user_id=resident_id,
            permission_code="maintenance:view:self",
            resource_owner_id=resident_id,
        )
        rows = session.execute(
            select(Property, Town, County)
            .join(PropertyResidentAccess, PropertyResidentAccess.property_id == Property.id)
            .join(Town, (Town.id == Property.town_id) & (Town.county_id == Property.county_id))
            .join(County, County.id == Property.county_id)
            .where(
                PropertyResidentAccess.resident_user_id == resident_id,
                PropertyResidentAccess.status == "active",
                Property.is_demo.is_(False),
            )
            .order_by(Property.title)
        )
        return [
            ResidentPropertyResponse(
                id=property_.id,
                title=property_.title,
                location=f"{town.name}, {county.name}",
            )
            for property_, town, county in rows
        ]

    def create(
        self, session: Session, *, user_id: UUID, body: MaintenanceCreate
    ) -> MaintenanceResponse:
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code="maintenance:create:self",
            resource_owner_id=user_id,
        )
        property_ = self._resident_property(session, user_id, body.property_id)
        documents: list[PrivateDocument] = []
        for document_id in body.photo_document_ids:
            document = session.get(PrivateDocument, document_id)
            if (
                document is None
                or document.owner_user_id != user_id
                or not document.content_type.startswith("image/")
                or document.storage_encrypted
            ):
                raise ApiError(
                    422,
                    "maintenance_photo_invalid",
                    "Use an image from your own unencrypted private documents.",
                )
            documents.append(document)
        assigned_manager = property_.property_manager_user_id or property_.owner_user_id
        row = MaintenanceRequest(
            property_id=property_.id,
            resident_user_id=user_id,
            assigned_manager_user_id=assigned_manager,
            category=body.category,
            description=body.description,
            priority=body.priority,
            status="submitted",
        )
        session.add(row)
        session.flush()
        session.add_all(
            [
                MaintenanceRequestPhoto(request_id=row.id, document_id=document.id)
                for document in documents
            ]
        )
        session.add(
            MaintenanceHistory(
                request_id=row.id, actor_user_id=user_id, action="submitted", note=None
            )
        )
        self._audit(
            session,
            user_id,
            "maintenance.request_created",
            row.id,
            {"property_id": str(property_.id), "category": row.category},
        )
        session.commit()
        return self._response(session, row)

    def list_for_user(self, session: Session, *, user_id: UUID) -> list[MaintenanceResponse]:
        rows = session.scalars(
            select(MaintenanceRequest)
            .where(
                (MaintenanceRequest.resident_user_id == user_id)
                | (MaintenanceRequest.assigned_manager_user_id == user_id)
                | (MaintenanceRequest.assigned_provider_user_id == user_id)
            )
            .order_by(MaintenanceRequest.created_at.desc())
            .limit(200)
        )
        visible = []
        for row in rows:
            try:
                self._authorize_request(session, user_id, row)
            except ApiError:
                continue
            visible.append(self._response(session, row))
        if not visible and not self.authorization.permission_codes(session, user_id):
            raise ApiError(
                403, "permission_denied", "You are not authorized to view maintenance requests."
            )
        return visible

    def get(self, session: Session, *, user_id: UUID, request_id: UUID) -> MaintenanceResponse:
        row = session.get(MaintenanceRequest, request_id)
        if row is None:
            raise self._not_found()
        self._authorize_request(session, user_id, row)
        return self._response(session, row)

    def assign(
        self,
        session: Session,
        *,
        manager_id: UUID,
        request_id: UUID,
        body: MaintenanceAssignment,
        request_id_header: str | None = None,
    ) -> MaintenanceResponse:
        row = session.get(MaintenanceRequest, request_id)
        if row is None:
            raise self._not_found()
        property_ = self._managed_property(session, manager_id, row.property_id)
        if row.status in {"completed", "cancelled"}:
            raise ApiError(
                409, "maintenance_closed", "A closed maintenance request cannot be reassigned."
            )
        if (body.provider_user_id is None) != (body.offering_id is None):
            raise ApiError(
                422,
                "provider_assignment_incomplete",
                "Select both a provider account and one of their services.",
            )
        if body.provider_user_id is not None and body.offering_id is not None:
            offer = self.catalog.public_offering(session, service_id=body.offering_id)
            areas = list(
                session.scalars(select(ServiceArea).where(ServiceArea.offering_id == offer.id))
            )
            area_matches = any(
                area.town_id == property_.town_id
                or (area.town_id is None and area.county_id == property_.county_id)
                for area in areas
            )
            if (
                offer.provider_user_id != body.provider_user_id
                or offer.category not in MAINTENANCE_TO_SERVICE_CATEGORY[row.category]
                or not area_matches
            ):
                raise ApiError(
                    422,
                    "provider_not_eligible",
                    "Choose an active provider whose service matches this request and area.",
                )
            row.assigned_provider_user_id = body.provider_user_id
            row.assigned_offering_id = offer.id
            row.status = "assigned"
            row.assigned_manager_user_id = manager_id
            session.add(
                MaintenanceHistory(
                    request_id=row.id,
                    actor_user_id=manager_id,
                    action="provider_assigned",
                    note=f"Assigned service {offer.title}.",
                )
            )
        else:
            row.assigned_provider_user_id = None
            row.assigned_offering_id = None
            row.status = "submitted"
            session.add(
                MaintenanceHistory(
                    request_id=row.id,
                    actor_user_id=manager_id,
                    action="provider_unassigned",
                    note=None,
                )
            )
        row.updated_at = datetime.now(UTC)
        self._audit(
            session,
            manager_id,
            "maintenance.assignment_changed",
            row.id,
            {"provider_user_id": str(body.provider_user_id) if body.provider_user_id else None},
        )
        session.commit()
        return self._response(session, row)

    def act(
        self, session: Session, *, user_id: UUID, request_id: UUID, body: MaintenanceAction
    ) -> MaintenanceResponse:
        row = session.get(MaintenanceRequest, request_id)
        if row is None:
            raise self._not_found()
        self._authorize_request(session, user_id, row)
        is_manager = self._can_manage(session, user_id, session.get(Property, row.property_id))
        is_provider = row.assigned_provider_user_id == user_id
        is_resident = row.resident_user_id == user_id
        if body.action in {"start", "complete"} and not (is_provider or is_manager):
            raise self._not_found()
        if body.action == "cancel" and not (is_resident or is_manager):
            raise self._not_found()
        now = datetime.now(UTC)
        if body.action == "start":
            if row.status != "assigned":
                raise ApiError(
                    409, "maintenance_status_conflict", "Only an assigned request can be started."
                )
            row.status = "in_progress"
        elif body.action == "complete":
            if row.status not in {"assigned", "in_progress"} or not body.note:
                raise ApiError(
                    409,
                    "maintenance_completion_required",
                    "An assigned request and a completion note are required.",
                )
            row.status = "completed"
            row.completion_record = body.note.strip()
            row.completed_at = now
        else:
            if row.status in {"completed", "cancelled"} or (
                is_resident and row.status != "submitted"
            ):
                raise ApiError(
                    409, "maintenance_status_conflict", "This request cannot be cancelled now."
                )
            row.status = "cancelled"
        row.updated_at = now
        session.add(
            MaintenanceHistory(
                request_id=row.id,
                actor_user_id=user_id,
                action=body.action,
                note=body.note.strip() if body.note else None,
            )
        )
        self._audit(session, user_id, f"maintenance.{body.action}", row.id, {})
        recipient = (
            row.resident_user_id
            if user_id != row.resident_user_id
            else row.assigned_manager_user_id
        )
        from app.models.notification import InAppNotification

        session.add(
            InAppNotification(
                recipient_user_id=recipient,
                category="maintenance",
                title="Maintenance request updated",
                body=f"Request status: {row.status.replace('_', ' ')}.",
                target_path="/services?tab=Maintenance",
            )
        )
        session.commit()
        return self._response(session, row)

    def photo_document(
        self, session: Session, *, user_id: UUID, request_id: UUID, document_id: UUID
    ) -> PrivateDocument:
        row = session.get(MaintenanceRequest, request_id)
        if row is None:
            raise self._not_found()
        self._authorize_request(session, user_id, row)
        link = session.scalar(
            select(MaintenanceRequestPhoto).where(
                MaintenanceRequestPhoto.request_id == request_id,
                MaintenanceRequestPhoto.document_id == document_id,
            )
        )
        document = session.get(PrivateDocument, document_id) if link else None
        if document is None or document.storage_encrypted:
            raise self._not_found()
        self._audit(
            session, user_id, "maintenance.photo_viewed", row.id, {"document_id": str(document_id)}
        )
        session.commit()
        return document

    def _authorize_request(self, session: Session, user_id: UUID, row: MaintenanceRequest) -> None:
        if row.resident_user_id == user_id:
            self.authorization.require_permission(
                session,
                user_id=user_id,
                permission_code="maintenance:view:self",
                resource_owner_id=user_id,
            )
            self._resident_property(session, user_id, row.property_id)
            return
        if row.assigned_provider_user_id == user_id:
            self.authorization.require_permission(
                session,
                user_id=user_id,
                permission_code="maintenance:view:assigned",
                resource_scope_type="property",
                resource_scope_id=str(row.property_id),
            )
            return
        property_ = session.get(Property, row.property_id)
        self._managed_property(session, user_id, property_)

    def _managed_property(
        self, session: Session, manager_id: UUID, property_id: UUID | Property
    ) -> Property:
        property_ = (
            property_id if isinstance(property_id, Property) else session.get(Property, property_id)
        )
        if (
            property_ is None
            or property_.is_demo
            or not self._can_manage(session, manager_id, property_)
        ):
            raise ApiError(
                404, "property_not_found", "The property is not assigned to this manager."
            )
        self.authorization.require_permission(
            session,
            user_id=manager_id,
            permission_code="maintenance:manage:assigned",
            resource_scope_type="property",
            resource_scope_id=str(property_.id),
        )
        return property_

    def _can_manage(self, session: Session, user_id: UUID, property_: Property | None) -> bool:
        if property_ is None:
            return False
        return user_id in {
            property_.owner_user_id,
            property_.property_manager_user_id,
            property_.authorized_agent_user_id,
        }

    @staticmethod
    def _resident_property(session: Session, resident_id: UUID, property_id: UUID) -> Property:
        property_ = session.get(Property, property_id)
        access = session.scalar(
            select(PropertyResidentAccess).where(
                PropertyResidentAccess.property_id == property_id,
                PropertyResidentAccess.resident_user_id == resident_id,
                PropertyResidentAccess.status == "active",
            )
        )
        if property_ is None or property_.is_demo or access is None:
            raise ApiError(
                404,
                "property_not_found",
                "The requested property is not available to this account.",
            )
        return property_

    def _response(self, session: Session, row: MaintenanceRequest) -> MaintenanceResponse:
        property_ = session.get(Property, row.property_id)
        photos = list(
            session.scalars(
                select(MaintenanceRequestPhoto.document_id).where(
                    MaintenanceRequestPhoto.request_id == row.id
                )
            )
        )
        history = [
            {
                "id": str(item.id),
                "action": item.action,
                "note": item.note,
                "created_at": item.created_at,
            }
            for item in session.scalars(
                select(MaintenanceHistory)
                .where(MaintenanceHistory.request_id == row.id)
                .order_by(MaintenanceHistory.created_at)
            )
        ]
        return MaintenanceResponse(
            id=row.id,
            property_id=row.property_id,
            property_title=property_.title if property_ else "Unavailable property",
            resident_user_id=row.resident_user_id,
            assigned_manager_user_id=row.assigned_manager_user_id,
            assigned_provider_user_id=row.assigned_provider_user_id,
            assigned_offering_id=row.assigned_offering_id,
            category=row.category,
            description=row.description,
            priority=row.priority,
            status=row.status,
            completion_record=row.completion_record,
            photo_document_ids=photos,
            history=history,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _audit(
        session: Session, actor_id: UUID, event: str, subject_id: UUID, metadata: dict[str, object]
    ) -> None:
        session.add(
            AuditEvent(
                actor_user_id=actor_id,
                event_type=event,
                subject_type="property"
                if event.startswith("maintenance.resident_access_")
                else "maintenance_request",
                subject_id=str(subject_id),
                metadata_json=metadata,
            )
        )

    @staticmethod
    def _not_found() -> ApiError:
        return ApiError(
            404, "maintenance_not_found", "The requested maintenance record was not found."
        )
