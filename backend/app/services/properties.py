"""Ownership-checked draft workflows and published property discovery reads."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.data_access.properties import PropertyDataAccess
from app.models.access_control import Role, UserRoleAssignment
from app.models.audit import AuditEvent
from app.models.marketplace import PropertyListingMandate
from app.models.property import Property, PropertyAmenity, PropertyMedia
from app.models.user import UserAccount
from app.schemas.properties import (
    AvailabilityUpdate,
    ListingAgentAssignment,
    PropertyCreateRequest,
    PropertyListResponse,
    PropertyLocationResponse,
    PropertyMediaInput,
    PropertyMediaResponse,
    PropertyPatchRequest,
    PropertyResponse,
)
from app.services.authorization import AuthorizationService
from app.services.locations import LocationService
from app.services.media_storage import EXTENSIONS, LocalMediaStorage


class PropertyService:
    def __init__(self) -> None:
        self.data = PropertyDataAccess()
        self.authorization = AuthorizationService()
        self.locations = LocationService()

    def list_public(
        self,
        session: Session,
        *,
        county_id: UUID | None,
        town_id: UUID | None,
        neighbourhood_id: UUID | None,
        property_type: str | None,
        unit_type: str | None,
        bedrooms: int | None,
        bedrooms_min: int | None,
        furnishing: str | None,
        verified_only: bool,
        rent_min: int | None,
        rent_max: int | None,
        query: str | None = None,
        amenities: list[str] | None = None,
        sort_by: str = "newest",
        south: float | None,
        west: float | None,
        north: float | None,
        east: float | None,
        include_demo: bool,
        limit: int,
        offset: int,
    ) -> PropertyListResponse:
        properties, total = self.data.list_public(
            session,
            county_id=county_id,
            town_id=town_id,
            neighbourhood_id=neighbourhood_id,
            property_type=property_type,
            unit_type=unit_type,
            bedrooms=bedrooms,
            bedrooms_min=bedrooms_min,
            furnishing=furnishing,
            verified_only=verified_only,
            rent_min=rent_min,
            rent_max=rent_max,
            query=query,
            amenities=amenities or [],
            sort_by=sort_by,
            south=south,
            west=west,
            north=north,
            east=east,
            include_demo=include_demo,
            limit=limit,
            offset=offset,
        )
        return PropertyListResponse(
            items=[self._response(property_) for property_ in properties],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_public(
        self, session: Session, property_id: UUID, *, include_demo: bool
    ) -> PropertyResponse:
        property_ = self.data.list_public_by_id(session, property_id, include_demo=include_demo)
        if property_ is None:
            raise ApiError(404, "property_not_found", "The requested property was not found.")
        return self._response(property_)

    def list_owned(self, session: Session, *, user_id: UUID) -> list[PropertyResponse]:
        rows = self.data.list_accessible(session, user_id)
        visible = []
        for row in rows:
            if row.owner_user_id == user_id:
                permission, owner = "property:view:owned", row.owner_user_id
            elif row.authorized_agent_user_id == user_id:
                permission, owner = "listing:view:assigned", None
            else:
                permission, owner = "property:view:assigned", None
            if self.authorization.has_permission(
                session,
                user_id=user_id,
                permission_code=permission,
                resource_owner_id=owner,
                resource_scope_type="property",
                resource_scope_id=str(row.id),
            ):
                visible.append(self._response(row))
        return visible

    def create_draft(
        self,
        session: Session,
        *,
        user_id: UUID,
        request: PropertyCreateRequest,
        request_id: str | None = None,
    ) -> PropertyResponse:
        owner_user_id = request.owner_user_id or user_id
        authorized_agent_user_id = None
        if owner_user_id == user_id:
            self.authorization.require_permission(
                session,
                user_id=user_id,
                permission_code="property:create:self",
                resource_owner_id=user_id,
            )
        else:
            self.authorization.require_permission(
                session,
                user_id=user_id,
                permission_code="listing:create:assigned",
                resource_scope_type="portfolio",
                resource_scope_id=str(owner_user_id),
            )
            mandate = session.get(PropertyListingMandate, (owner_user_id, user_id))
            if mandate is None or not mandate.is_active:
                raise ApiError(
                    403, "listing_mandate_required", "The property owner has not authorized you."
                )
            authorized_agent_user_id = user_id
        self.locations.validate_hierarchy(
            session,
            county_id=request.county_id,
            town_id=request.town_id,
            neighbourhood_id=request.neighbourhood_id,
        )
        values = request.model_dump(exclude={"media", "owner_user_id"})
        property_ = Property(
            **values,
            owner_user_id=owner_user_id,
            authorized_agent_user_id=authorized_agent_user_id,
            currency="KES",
            verification_status="not_submitted",
            availability_status="unknown",
            listing_status="draft",
            is_demo=False,
            media=[self._media_model(item) for item in request.media],
            amenity_records=[PropertyAmenity(amenity=item) for item in request.amenities],
        )
        session.add(property_)
        try:
            session.flush()
            session.add(
                AuditEvent(
                    actor_user_id=user_id,
                    event_type="property.draft_created",
                    subject_type="property",
                    subject_id=str(property_.id),
                    request_id=request_id,
                    metadata_json={"county_id": str(property_.county_id)},
                )
            )
            session.commit()
        except IntegrityError:
            session.rollback()
            raise ApiError(
                422,
                "invalid_property_references",
                "Property references could not be saved. Check its location and media fields.",
            ) from None
        saved = self.data.get(session, property_.id)
        assert saved is not None
        return self._response(saved)

    def update_draft(
        self,
        session: Session,
        *,
        user_id: UUID,
        property_id: UUID,
        request: PropertyPatchRequest,
        request_id: str | None = None,
    ) -> PropertyResponse:
        property_ = self.data.get(session, property_id)
        if property_ is None or property_.is_demo:
            raise ApiError(404, "property_not_found", "The requested property was not found.")
        if property_.listing_status in {"archived", "rejected"}:
            raise ApiError(
                409,
                "property_not_editable",
                "Archived or rejected properties cannot be edited.",
            )
        self._require_listing_permission(session, user_id, property_, "edit")

        merged = self._current_values(property_)
        supplied = request.model_dump(exclude_unset=True)
        merged.update(supplied)
        media_was_supplied = "media" in supplied
        merged["media"] = supplied.get("media", [])
        validated = PropertyCreateRequest.model_validate(merged)
        self.locations.validate_hierarchy(
            session,
            county_id=validated.county_id,
            town_id=validated.town_id,
            neighbourhood_id=validated.neighbourhood_id,
        )
        values = validated.model_dump(exclude={"media"})
        for name, value in values.items():
            setattr(property_, name, value)
        if media_was_supplied:
            property_.media = [self._media_model(item) for item in validated.media]
        if "amenities" in supplied:
            property_.amenity_records = [
                PropertyAmenity(amenity=item) for item in validated.amenities
            ]

        try:
            session.flush()
            session.add(
                AuditEvent(
                    actor_user_id=user_id,
                    event_type="property.listing_updated",
                    subject_type="property",
                    subject_id=str(property_.id),
                    request_id=request_id,
                    metadata_json={"changed_fields": sorted(supplied.keys())},
                )
            )
            session.commit()
        except IntegrityError:
            session.rollback()
            raise ApiError(
                422,
                "invalid_property_references",
                "Property references could not be saved. Check its location and media fields.",
            ) from None
        saved = self.data.get(session, property_.id)
        assert saved is not None
        return self._response(saved)

    def assign_listing_party(
        self,
        session: Session,
        *,
        user_id: UUID,
        property_id: UUID,
        assignment: ListingAgentAssignment,
        request_id: str | None = None,
    ) -> PropertyResponse:
        property_ = self._owned_property(session, user_id, property_id)
        self._require_listing_permission(session, user_id, property_, "assign")
        party_id = assignment.agent_user_id or assignment.manager_user_id
        role_code = "real_estate_agent" if assignment.agent_user_id else "property_manager"
        party = session.scalar(select(UserAccount).where(UserAccount.id == party_id))
        has_role = session.scalar(
            select(UserRoleAssignment.user_id)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .where(
                UserRoleAssignment.user_id == party_id,
                Role.code == role_code,
                party.status == "active" if party else False,
            )
            .limit(1)
        )
        if party is None or has_role is None:
            raise ApiError(
                422,
                "listing_party_not_eligible",
                "The selected account does not have an active authorized role.",
            )
        if assignment.agent_user_id is not None:
            property_.authorized_agent_user_id = assignment.agent_user_id
        else:
            property_.property_manager_user_id = assignment.manager_user_id
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type="property.listing_party_assigned",
                subject_type="property",
                subject_id=str(property_.id),
                request_id=request_id,
                metadata_json={"role": role_code},
            )
        )
        session.commit()
        saved = self.data.get(session, property_.id)
        assert saved is not None
        return self._response(saved)

    def set_availability(
        self,
        session: Session,
        *,
        user_id: UUID,
        property_id: UUID,
        request: AvailabilityUpdate,
        request_id: str | None = None,
    ) -> PropertyResponse:
        property_ = self._visible_property(session, property_id)
        self._require_listing_permission(session, user_id, property_, "edit")
        if property_.is_demo or property_.listing_status in {"archived", "rejected"}:
            raise ApiError(409, "property_not_editable", "This listing cannot change availability.")
        property_.availability_status = request.availability_status
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type="property.availability_updated",
                subject_type="property",
                subject_id=str(property_.id),
                request_id=request_id,
                metadata_json={"availability_status": request.availability_status},
            )
        )
        session.commit()
        saved = self.data.get(session, property_.id)
        assert saved is not None
        return self._response(saved)

    def publish(
        self, session: Session, *, user_id: UUID, property_id: UUID, request_id: str | None = None
    ) -> PropertyResponse:
        property_ = self._visible_property(session, property_id)
        self._require_listing_permission(session, user_id, property_, "publish")
        if property_.is_demo:
            raise ApiError(
                409, "demo_listing_not_publishable", "Demo listings cannot be published."
            )
        if property_.availability_status != "available":
            raise ApiError(
                409, "listing_not_available", "Mark the listing available before publishing."
            )
        if property_.moderation_status != "clear":
            raise ApiError(
                409,
                "listing_moderation_hold",
                "This listing cannot be published while a moderation hold is active.",
            )
        if not any(
            item.media_type == "image" and not item.is_illustrative for item in property_.media
        ):
            raise ApiError(
                409, "listing_image_required", "Add at least one listing photo before publishing."
            )
        if property_.listing_status in {"archived", "rejected"}:
            raise ApiError(409, "listing_not_publishable", "This listing cannot be published.")
        property_.listing_status = "published"
        property_.published_at = property_.published_at or datetime.now(UTC)
        property_.archived_at = None
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type="property.listing_published",
                subject_type="property",
                subject_id=str(property_.id),
                request_id=request_id,
                metadata_json={"verification_status": property_.verification_status},
            )
        )
        session.commit()
        saved = self.data.get(session, property_.id)
        assert saved is not None
        return self._response(saved)

    def archive(
        self, session: Session, *, user_id: UUID, property_id: UUID, request_id: str | None = None
    ) -> PropertyResponse:
        property_ = self._visible_property(session, property_id)
        self._require_listing_permission(session, user_id, property_, "archive")
        if property_.is_demo:
            raise ApiError(409, "demo_listing_not_archivable", "Demo listings cannot be managed.")
        property_.listing_status = "archived"
        property_.archived_at = datetime.now(UTC)
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type="property.listing_archived",
                subject_type="property",
                subject_id=str(property_.id),
                request_id=request_id,
                metadata_json={},
            )
        )
        session.commit()
        saved = self.data.get(session, property_.id)
        assert saved is not None
        return self._response(saved)

    def delete_draft(
        self,
        session: Session,
        *,
        user_id: UUID,
        property_id: UUID,
        storage: LocalMediaStorage,
        request_id: str | None = None,
    ) -> None:
        property_ = self._owned_property(session, user_id, property_id)
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code="listing:delete:owned",
            resource_owner_id=property_.owner_user_id,
            resource_scope_type="property",
            resource_scope_id=str(property_.id),
        )
        if property_.listing_status != "draft" or property_.is_demo:
            raise ApiError(409, "listing_delete_not_allowed", "Only draft listings can be deleted.")
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type="property.draft_deleted",
                subject_type="property",
                subject_id=str(property_.id),
                request_id=request_id,
                metadata_json={},
            )
        )
        storage_keys = [item.storage_key for item in property_.media if item.storage_key]
        session.delete(property_)
        session.commit()
        for storage_key in storage_keys:
            storage.delete(storage_key)

    def get_preview(
        self, session: Session, *, user_id: UUID, property_id: UUID
    ) -> PropertyResponse:
        property_ = self._visible_property(session, property_id)
        self._require_listing_permission(session, user_id, property_, "view")
        return self._response(property_)

    def assert_can_edit_listing(
        self, session: Session, *, user_id: UUID, property_id: UUID
    ) -> None:
        property_ = self._visible_property(session, property_id)
        self._require_listing_permission(session, user_id, property_, "edit")
        if property_.listing_status in {"archived", "rejected"}:
            raise ApiError(409, "property_not_editable", "This listing cannot accept changes.")

    def upload_image(
        self,
        session: Session,
        *,
        user_id: UUID,
        property_id: UUID,
        contents: bytes,
        mime_type: str,
        alt_text: str | None,
        storage: LocalMediaStorage,
        request_id: str | None = None,
    ) -> PropertyMediaResponse:
        property_ = self._visible_property(session, property_id)
        self._require_listing_permission(session, user_id, property_, "edit")
        if property_.listing_status in {"archived", "rejected"}:
            raise ApiError(409, "property_not_editable", "This listing cannot accept photos.")
        if mime_type not in EXTENSIONS or not contents:
            raise ApiError(415, "unsupported_image", "Upload a JPEG, PNG, or WebP image.")
        image_count = sum(item.media_type == "image" for item in property_.media)
        if image_count >= 20:
            raise ApiError(422, "image_limit_reached", "A listing can include at most 20 images.")
        media_id = uuid4()
        storage_key = f"{media_id.hex}{EXTENSIONS[mime_type]}"
        storage.put(storage_key, contents)
        position = max((item.position for item in property_.media), default=-1) + 1
        item = PropertyMedia(
            id=media_id,
            property_id=property_.id,
            media_type="image",
            url=f"/api/v1/properties/media/{media_id}",
            storage_key=storage_key,
            mime_type=mime_type,
            byte_size=len(contents),
            alt_text=alt_text,
            position=position,
            is_illustrative=False,
        )
        session.add(item)
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type="property.image_uploaded",
                subject_type="property",
                subject_id=str(property_.id),
                request_id=request_id,
                metadata_json={"media_id": str(media_id), "mime_type": mime_type},
            )
        )
        try:
            session.commit()
        except Exception:
            session.rollback()
            storage.delete(storage_key)
            raise
        return PropertyMediaResponse(
            id=item.id,
            media_type="image",
            url=item.url,
            alt_text=item.alt_text,
            caption=None,
            position=item.position,
            is_illustrative=False,
            source_credit=None,
            mime_type=item.mime_type,
            byte_size=item.byte_size,
        )

    def delete_media(
        self,
        session: Session,
        *,
        user_id: UUID,
        property_id: UUID,
        media_id: UUID,
        storage: LocalMediaStorage,
        request_id: str | None = None,
    ) -> None:
        property_ = self._visible_property(session, property_id)
        self._require_listing_permission(session, user_id, property_, "edit")
        item = next((media for media in property_.media if media.id == media_id), None)
        if item is None:
            raise ApiError(404, "media_not_found", "The requested listing image was not found.")
        storage_key = item.storage_key
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type="property.image_deleted",
                subject_type="property",
                subject_id=str(property_.id),
                request_id=request_id,
                metadata_json={"media_id": str(media_id)},
            )
        )
        session.delete(item)
        session.commit()
        if storage_key:
            storage.delete(storage_key)

    def _visible_property(self, session: Session, property_id: UUID) -> Property:
        property_ = self.data.get(session, property_id)
        if property_ is None or property_.is_demo:
            raise ApiError(404, "property_not_found", "The requested property was not found.")
        return property_

    def _owned_property(self, session: Session, user_id: UUID, property_id: UUID) -> Property:
        property_ = self._visible_property(session, property_id)
        if property_.owner_user_id != user_id:
            raise ApiError(404, "property_not_found", "The requested property was not found.")
        return property_

    def _require_listing_permission(
        self, session: Session, user_id: UUID, property_: Property, action: str
    ) -> None:
        if action == "view":
            if property_.owner_user_id == user_id:
                permission = "property:view:owned"
            elif property_.authorized_agent_user_id == user_id:
                permission = "listing:view:assigned"
            elif property_.property_manager_user_id == user_id:
                permission = "property:view:assigned"
            else:
                raise ApiError(404, "property_not_found", "The requested property was not found.")
            self.authorization.require_permission(
                session,
                user_id=user_id,
                permission_code=permission,
                resource_owner_id=property_.owner_user_id
                if permission.endswith(":owned")
                else None,
                resource_scope_type="property",
                resource_scope_id=str(property_.id),
            )
            return
        if property_.owner_user_id == user_id:
            permission = f"listing:{action}:owned"
            owner_id = property_.owner_user_id
        elif user_id in {property_.authorized_agent_user_id, property_.property_manager_user_id}:
            permission = f"listing:{action}:assigned"
            owner_id = None
        else:
            raise ApiError(404, "property_not_found", "The requested property was not found.")
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code=permission,
            resource_owner_id=owner_id,
            resource_scope_type="property",
            resource_scope_id=str(property_.id),
        )

    @staticmethod
    def _current_values(property_: Property) -> dict[str, object]:
        fields = set(PropertyCreateRequest.model_fields) - {"media"}
        values = {name: getattr(property_, name) for name in fields}
        values["media"] = [
            {
                "media_type": item.media_type,
                "url": item.url,
                "alt_text": item.alt_text,
                "caption": item.caption,
                "position": item.position,
                "is_illustrative": item.is_illustrative,
                "source_credit": item.source_credit,
            }
            for item in property_.media
        ]
        return values

    @staticmethod
    def _media_model(item: PropertyMediaInput) -> PropertyMedia:
        return PropertyMedia(
            media_type=item.media_type,
            url=str(item.url),
            alt_text=item.alt_text,
            caption=item.caption,
            position=item.position,
            is_illustrative=item.is_illustrative,
            source_credit=item.source_credit,
        )

    @staticmethod
    def _response(property_: Property) -> PropertyResponse:
        return PropertyResponse(
            id=property_.id,
            title=property_.title,
            description=property_.description,
            property_type=property_.property_type,
            accommodation_type=property_.accommodation_type,
            unit_type=property_.unit_type,
            rent_amount=property_.rent_amount,
            currency=property_.currency,
            rent_frequency=property_.rent_frequency,
            deposit_amount=property_.deposit_amount,
            bedrooms=property_.bedrooms,
            bathrooms=property_.bathrooms,
            size_sqm=property_.size_sqm,
            parking_available=property_.parking_available,
            parking_spaces=property_.parking_spaces,
            furnishing=property_.furnishing,
            pet_policy=property_.pet_policy,
            water_availability=property_.water_availability,
            electricity_available=property_.electricity_available,
            internet_available=property_.internet_available,
            security_features=property_.security_features,
            amenities=property_.amenities,
            location=PropertyLocationResponse(
                county_id=property_.county.id,
                county_name=property_.county.name,
                town_id=property_.town.id,
                town_name=property_.town.name,
                neighbourhood_id=property_.neighbourhood.id if property_.neighbourhood else None,
                neighbourhood_name=(
                    property_.neighbourhood.name if property_.neighbourhood else None
                ),
            ),
            address=property_.address,
            latitude=property_.latitude,
            longitude=property_.longitude,
            coordinate_source=property_.coordinate_source,
            owner_user_id=property_.owner_user_id,
            authorized_agent_user_id=property_.authorized_agent_user_id,
            property_manager_user_id=property_.property_manager_user_id,
            verification_status=property_.verification_status,
            availability_status=property_.availability_status,
            listing_status=property_.listing_status,
            is_demo=property_.is_demo,
            demo_disclaimer=property_.demo_disclaimer,
            media=property_.media,
            created_at=property_.created_at,
            updated_at=property_.updated_at,
            published_at=property_.published_at,
            archived_at=property_.archived_at,
        )
