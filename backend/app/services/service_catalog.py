"""Provider profiles, service listings, location search, media, and reviews."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.audit import AuditEvent
from app.models.location import County, Town
from app.models.services import (
    ServiceArea,
    ServiceOffering,
    ServiceProviderImage,
    ServiceProviderProfile,
    ServiceReview,
)
from app.models.trust import VerificationCase
from app.models.user import UserAccount
from app.schemas.services import (
    ProviderImageResponse,
    ProviderProfileResponse,
    ProviderProfileSave,
    ServiceOfferingResponse,
    ServiceOfferingSave,
    ServiceReviewResponse,
)
from app.services.authorization import AuthorizationService
from app.services.media_storage import LocalMediaStorage


class ServiceCatalogService:
    def __init__(self) -> None:
        self.authorization = AuthorizationService()

    def save_profile(
        self, session: Session, *, user_id: UUID, body: ProviderProfileSave
    ) -> ProviderProfileResponse:
        self._require_provider(session, user_id, "service:edit:self")
        row = session.scalar(
            select(ServiceProviderProfile).where(ServiceProviderProfile.provider_user_id == user_id)
        )
        if row is None:
            row = ServiceProviderProfile(provider_user_id=user_id, public_name=body.public_name)
            session.add(row)
            session.flush()
        if body.is_published and not session.scalar(
            select(ServiceOffering.id)
            .where(ServiceOffering.provider_user_id == user_id, ServiceOffering.is_active.is_(True))
            .limit(1)
        ):
            raise ApiError(
                409,
                "active_service_required",
                "Add an active service before publishing your provider profile.",
            )
        row.public_name = body.public_name
        row.description = body.description
        row.availability_note = body.availability_note
        row.is_published = body.is_published
        row.updated_at = datetime.now(UTC)
        self._audit(
            session, user_id, "service.provider_profile_updated", "service_provider", str(row.id)
        )
        session.commit()
        return self._profile_response(session, row)

    def my_profile(self, session: Session, *, user_id: UUID) -> ProviderProfileResponse | None:
        self._require_provider(session, user_id, "service:view:self")
        row = session.scalar(
            select(ServiceProviderProfile).where(ServiceProviderProfile.provider_user_id == user_id)
        )
        return self._profile_response(session, row) if row else None

    def public_profile(
        self, session: Session, *, provider_user_id: UUID
    ) -> ProviderProfileResponse:
        row = session.scalar(
            select(ServiceProviderProfile)
            .where(
                ServiceProviderProfile.provider_user_id == provider_user_id,
                ServiceProviderProfile.is_published.is_(True),
                UserAccount.status == "active",
            )
            .join(UserAccount, UserAccount.id == ServiceProviderProfile.provider_user_id)
        )
        if row is None or not session.scalar(
            select(ServiceOffering.id)
            .where(
                ServiceOffering.provider_user_id == provider_user_id,
                ServiceOffering.is_active.is_(True),
            )
            .limit(1)
        ):
            raise self._not_found()
        return self._profile_response(session, row)

    def save_offering(
        self,
        session: Session,
        *,
        user_id: UUID,
        offering_id: UUID | None,
        body: ServiceOfferingSave,
    ) -> ServiceOfferingResponse:
        profile = session.scalar(
            select(ServiceProviderProfile).where(ServiceProviderProfile.provider_user_id == user_id)
        )
        if profile is None:
            raise ApiError(
                409,
                "provider_profile_required",
                "Create your provider profile before adding services.",
            )
        self._require_provider(
            session, user_id, "service:create:self" if offering_id is None else "service:edit:self"
        )
        self._validate_service_areas(session, body)
        row = session.get(ServiceOffering, offering_id) if offering_id else None
        if offering_id is not None and (row is None or row.provider_user_id != user_id):
            raise self._not_found()
        if row is None:
            row = ServiceOffering(
                provider_user_id=user_id,
                title=body.title,
                category=body.category,
                description=body.description,
                pricing_model=body.pricing_model,
            )
            session.add(row)
        row.title = body.title
        row.category = body.category
        row.description = body.description
        row.pricing_model = body.pricing_model
        row.price_amount = body.price_amount
        row.currency = "KES"
        row.estimated_duration_minutes = body.estimated_duration_minutes
        row.availability_schedule = body.availability_schedule
        row.is_active = body.is_active
        row.updated_at = datetime.now(UTC)
        for area in session.scalars(select(ServiceArea).where(ServiceArea.offering_id == row.id)):
            session.delete(area)
        session.flush()
        session.add_all(
            [
                ServiceArea(offering_id=row.id, county_id=area.county_id, town_id=area.town_id)
                for area in body.service_areas
            ]
        )
        self._audit(session, user_id, "service.offering_saved", "service_offering", str(row.id))
        session.commit()
        return self._offering_response(session, row)

    def my_offerings(self, session: Session, *, user_id: UUID) -> list[ServiceOfferingResponse]:
        self._require_provider(session, user_id, "service:view:self")
        rows = session.scalars(
            select(ServiceOffering)
            .where(ServiceOffering.provider_user_id == user_id)
            .order_by(ServiceOffering.created_at.desc())
        )
        return [self._offering_response(session, row) for row in rows]

    def search_offerings(
        self,
        session: Session,
        *,
        query: str | None,
        category: str | None,
        county_id: UUID | None,
        town_id: UUID | None,
        min_price: float | None,
        max_price: float | None,
        verified_only: bool,
        sort: str,
        limit: int,
        offset: int,
    ) -> list[ServiceOfferingResponse]:
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ApiError(422, "invalid_price_range", "Minimum price cannot exceed maximum price.")
        statement = (
            select(ServiceOffering)
            .join(
                ServiceProviderProfile,
                ServiceProviderProfile.provider_user_id == ServiceOffering.provider_user_id,
            )
            .join(UserAccount, UserAccount.id == ServiceOffering.provider_user_id)
            .where(
                ServiceOffering.is_active.is_(True),
                ServiceProviderProfile.is_published.is_(True),
                UserAccount.status == "active",
            )
        )
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    ServiceOffering.title.ilike(pattern),
                    ServiceOffering.description.ilike(pattern),
                    ServiceProviderProfile.public_name.ilike(pattern),
                )
            )
        if category:
            statement = statement.where(ServiceOffering.category == category)
        if min_price is not None:
            statement = statement.where(ServiceOffering.price_amount >= min_price)
        if max_price is not None:
            statement = statement.where(ServiceOffering.price_amount <= max_price)
        if county_id is not None or town_id is not None:
            statement = statement.join(ServiceArea, ServiceArea.offering_id == ServiceOffering.id)
            if town_id is not None:
                statement = statement.where(ServiceArea.town_id == town_id)
            elif county_id is not None:
                statement = statement.where(ServiceArea.county_id == county_id)
        rows = list(session.scalars(statement.distinct().limit(300)))
        if verified_only:
            rows = [
                row
                for row in rows
                if self._verification_status(session, row.provider_user_id) == "verified"
            ]
        if sort == "price_low":
            rows.sort(
                key=lambda row: (row.price_amount is None, row.price_amount or 0, row.created_at)
            )
        elif sort == "price_high":
            rows.sort(
                key=lambda row: (row.price_amount is None, -(row.price_amount or 0), row.created_at)
            )
        else:
            rows.sort(key=lambda row: row.created_at, reverse=True)
        return [self._offering_response(session, row) for row in rows[offset : offset + limit]]

    def compare(
        self, session: Session, *, service_ids: list[UUID]
    ) -> list[ServiceOfferingResponse]:
        if not 2 <= len(service_ids) <= 5 or len(service_ids) != len(set(service_ids)):
            raise ApiError(
                422,
                "invalid_service_comparison",
                "Compare between two and five different services.",
            )
        rows = [self.public_offering(session, service_id=service_id) for service_id in service_ids]
        return [self._offering_response(session, row) for row in rows]

    def public_offering(self, session: Session, *, service_id: UUID) -> ServiceOffering:
        row = session.scalar(
            select(ServiceOffering)
            .join(
                ServiceProviderProfile,
                ServiceProviderProfile.provider_user_id == ServiceOffering.provider_user_id,
            )
            .join(UserAccount, UserAccount.id == ServiceOffering.provider_user_id)
            .where(
                ServiceOffering.id == service_id,
                ServiceOffering.is_active.is_(True),
                ServiceProviderProfile.is_published.is_(True),
                UserAccount.status == "active",
            )
        )
        if row is None:
            raise self._not_found()
        return row

    def reviews(self, session: Session, *, service_id: UUID) -> list[ServiceReviewResponse]:
        self.public_offering(session, service_id=service_id)
        rows = session.scalars(
            select(ServiceReview)
            .where(
                ServiceReview.offering_id == service_id,
                ServiceReview.moderation_status == "clear",
            )
            .order_by(ServiceReview.created_at.desc())
            .limit(100)
        )
        return [ServiceReviewResponse.model_validate(row) for row in rows]

    def upload_image(
        self,
        session: Session,
        *,
        user_id: UUID,
        contents: bytes,
        mime_type: str,
        filename: str,
        caption: str | None,
        storage: LocalMediaStorage,
    ) -> ProviderImageResponse:
        self._require_provider(session, user_id, "service:edit:self")
        profile = session.scalar(
            select(ServiceProviderProfile).where(ServiceProviderProfile.provider_user_id == user_id)
        )
        if profile is None:
            raise ApiError(
                409,
                "provider_profile_required",
                "Create your provider profile before adding images.",
            )
        count = (
            session.scalar(
                select(func.count())
                .select_from(ServiceProviderImage)
                .where(ServiceProviderImage.provider_user_id == user_id)
            )
            or 0
        )
        if count >= 12:
            raise ApiError(
                409, "provider_image_limit", "A provider profile can have up to 12 images."
            )
        key = (
            uuid4().hex
            + {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[mime_type]
        )
        row = ServiceProviderImage(
            provider_user_id=user_id,
            storage_key=key,
            filename=filename[:180],
            content_type=mime_type,
            size_bytes=len(contents),
            caption=caption,
        )
        storage.put(key, contents)
        session.add(row)
        try:
            session.flush()
            self._audit(
                session,
                user_id,
                "service.provider_image_uploaded",
                "service_provider",
                str(profile.id),
            )
            session.commit()
        except Exception:
            session.rollback()
            storage.delete(key)
            raise
        return self._image_response(row)

    def image(
        self,
        session: Session,
        *,
        provider_user_id: UUID,
        image_id: UUID,
        storage: LocalMediaStorage,
    ) -> tuple[ServiceProviderImage, Path]:
        self.public_profile(session, provider_user_id=provider_user_id)
        profile = session.scalar(
            select(ServiceProviderProfile).where(
                ServiceProviderProfile.provider_user_id == provider_user_id,
                ServiceProviderProfile.is_published.is_(True),
            )
        )
        row = session.get(ServiceProviderImage, image_id)
        if profile is None or row is None or row.provider_user_id != provider_user_id:
            raise self._not_found()
        path = storage.get(row.storage_key)
        if path is None:
            raise self._not_found()
        return row, path

    def delete_image(
        self, session: Session, *, user_id: UUID, image_id: UUID, storage: LocalMediaStorage
    ) -> None:
        self._require_provider(session, user_id, "service:edit:self")
        row = session.get(ServiceProviderImage, image_id)
        if row is None or row.provider_user_id != user_id:
            raise self._not_found()
        key = row.storage_key
        session.delete(row)
        session.commit()
        storage.delete(key)

    def _validate_service_areas(self, session: Session, body: ServiceOfferingSave) -> None:
        for area in body.service_areas:
            if area.county_id is not None:
                county = session.get(County, area.county_id)
                if county is None or not county.is_active:
                    raise ApiError(422, "location_not_found", "Choose a valid Kenyan county.")
            if area.town_id is not None:
                town = session.get(Town, area.town_id)
                if town is None or town.county_id != area.county_id or not town.is_active:
                    raise ApiError(
                        422, "location_not_found", "Choose a town within the selected county."
                    )

    def _profile_response(
        self, session: Session, row: ServiceProviderProfile
    ) -> ProviderProfileResponse:
        offers = list(
            session.scalars(
                select(ServiceOffering).where(
                    ServiceOffering.provider_user_id == row.provider_user_id
                )
            )
        )
        areas = []
        for area in session.scalars(
            select(ServiceArea).where(
                ServiceArea.offering_id.in_([offer.id for offer in offers]) if offers else False
            )
        ):
            county = session.get(County, area.county_id) if area.county_id else None
            town = session.get(Town, area.town_id) if area.town_id else None
            areas.append(
                {
                    "county_id": str(area.county_id) if area.county_id else None,
                    "county_name": county.name if county else None,
                    "town_id": str(area.town_id) if area.town_id else None,
                    "town_name": town.name if town else None,
                }
            )
        images = list(
            session.scalars(
                select(ServiceProviderImage.id)
                .where(ServiceProviderImage.provider_user_id == row.provider_user_id)
                .order_by(ServiceProviderImage.created_at)
            )
        )
        reviews = list(
            session.scalars(
                select(ServiceReview.rating).where(
                    ServiceReview.provider_user_id == row.provider_user_id
                )
            )
        )
        return ProviderProfileResponse(
            id=row.id,
            provider_user_id=row.provider_user_id,
            public_name=row.public_name,
            description=row.description,
            availability_note=row.availability_note,
            is_published=row.is_published,
            verification_status=self._verification_status(session, row.provider_user_id),
            service_areas=areas,
            image_ids=images,
            average_rating=round(sum(reviews) / len(reviews), 2) if reviews else None,
            review_count=len(reviews),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _offering_response(self, session: Session, row: ServiceOffering) -> ServiceOfferingResponse:
        profile = session.scalar(
            select(ServiceProviderProfile).where(
                ServiceProviderProfile.provider_user_id == row.provider_user_id
            )
        )
        if profile is None:
            raise self._not_found()
        areas = []
        for area in session.scalars(select(ServiceArea).where(ServiceArea.offering_id == row.id)):
            county = session.get(County, area.county_id) if area.county_id else None
            town = session.get(Town, area.town_id) if area.town_id else None
            areas.append(
                {
                    "county_id": str(area.county_id) if area.county_id else None,
                    "county_name": county.name if county else None,
                    "town_id": str(area.town_id) if area.town_id else None,
                    "town_name": town.name if town else None,
                }
            )
        reviews = list(
            session.scalars(select(ServiceReview.rating).where(ServiceReview.offering_id == row.id))
        )
        return ServiceOfferingResponse(
            id=row.id,
            provider_user_id=row.provider_user_id,
            provider_name=profile.public_name,
            provider_verification_status=self._verification_status(session, row.provider_user_id),
            title=row.title,
            category=row.category,
            description=row.description,
            pricing_model=row.pricing_model,
            price_amount=row.price_amount,
            currency="KES",
            estimated_duration_minutes=row.estimated_duration_minutes,
            availability_schedule=row.availability_schedule,
            service_areas=areas,
            average_rating=round(sum(reviews) / len(reviews), 2) if reviews else None,
            review_count=len(reviews),
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _verification_status(self, session: Session, provider_user_id: UUID) -> str:
        case = session.scalar(
            select(VerificationCase)
            .where(
                VerificationCase.subject_type == "service_provider",
                VerificationCase.subject_user_id == provider_user_id,
            )
            .order_by(VerificationCase.updated_at.desc())
            .limit(1)
        )
        if case is None:
            return "not_submitted"
        if (
            case.status == "approved"
            and case.expires_on is not None
            and case.expires_on < date.today()
        ):
            return "expired"
        return case.status

    def _require_provider(self, session: Session, user_id: UUID, permission: str) -> None:
        self.authorization.require_permission(
            session, user_id=user_id, permission_code=permission, resource_owner_id=user_id
        )
        account = session.get(UserAccount, user_id)
        if account is None or account.status != "active":
            raise ApiError(
                403, "active_account_required", "An active service-provider account is required."
            )

    @staticmethod
    def _image_response(row: ServiceProviderImage) -> ProviderImageResponse:
        return ProviderImageResponse(
            id=row.id,
            provider_user_id=row.provider_user_id,
            filename=row.filename,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            caption=row.caption,
            url=f"/api/v1/services/providers/{row.provider_user_id}/images/{row.id}",
            created_at=row.created_at,
        )

    @staticmethod
    def _audit(
        session: Session, actor_id: UUID, event: str, subject_type: str, subject_id: str
    ) -> None:
        session.add(
            AuditEvent(
                actor_user_id=actor_id,
                event_type=event,
                subject_type=subject_type,
                subject_id=subject_id,
                metadata_json={},
            )
        )

    @staticmethod
    def _not_found() -> ApiError:
        return ApiError(404, "service_not_found", "The requested service was not found.")
