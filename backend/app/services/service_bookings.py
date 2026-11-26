"""Participant-only booking, order, and completed-service review workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.audit import AuditEvent
from app.models.location import County, Town
from app.models.notification import InAppNotification
from app.models.payments import PaymentTransaction
from app.models.property import Property
from app.models.services import (
    PropertyResidentAccess,
    ServiceBooking,
    ServiceBookingEvent,
    ServiceOffering,
    ServiceOrder,
    ServiceProviderProfile,
    ServiceReview,
)
from app.schemas.services import (
    BookingAction,
    BookingCreate,
    BookingHistoryResponse,
    BookingResponse,
    OrderResponse,
    ServiceReviewCreate,
    ServiceReviewResponse,
)
from app.services.authorization import AuthorizationService
from app.services.service_catalog import ServiceCatalogService


class ServiceBookingService:
    def __init__(self) -> None:
        self.authorization = AuthorizationService()
        self.catalog = ServiceCatalogService()

    def create(
        self,
        session: Session,
        *,
        customer_id: UUID,
        body: BookingCreate,
        request_id: str | None = None,
    ) -> BookingResponse:
        self.authorization.require_permission(
            session,
            user_id=customer_id,
            permission_code="booking:create:self",
            resource_owner_id=customer_id,
        )
        offering = self.catalog.public_offering(session, service_id=body.offering_id)
        try:
            timezone = ZoneInfo(body.timezone)
        except ZoneInfoNotFoundError as error:
            raise ApiError(422, "invalid_timezone", "Choose a supported timezone.") from error
        if body.requested_at.astimezone(UTC) <= datetime.now(UTC):
            raise ApiError(422, "booking_must_be_future", "Choose a future date and time.")
        local_time = body.requested_at.astimezone(timezone)
        if offering.availability_schedule:
            windows = offering.availability_schedule.get(local_time.strftime("%A").lower(), [])
            clock = local_time.strftime("%H:%M")
            if not any(start <= clock < end for start, end in windows):
                raise ApiError(
                    409,
                    "outside_provider_availability",
                    "Choose a time in the provider's listed availability.",
                )
        if body.property_id is not None:
            self._require_resident(session, customer_id, body.property_id)
            self._require_offering_area_for_property(session, offering.id, body.property_id)
        booking = ServiceBooking(
            offering_id=offering.id,
            customer_user_id=customer_id,
            provider_user_id=offering.provider_user_id,
            property_id=body.property_id,
            requested_at=body.requested_at.astimezone(UTC),
            timezone=body.timezone,
            request_details=body.request_details,
            status="pending",
        )
        session.add(booking)
        session.flush()
        # An order record is an auditable request snapshot, not a payment or final quote.
        order = ServiceOrder(
            booking_id=booking.id,
            customer_user_id=customer_id,
            provider_user_id=offering.provider_user_id,
            offering_title_snapshot=offering.title,
            category_snapshot=offering.category,
            estimated_amount_kes=offering.price_amount
            if offering.pricing_model == "fixed"
            else None,
            pricing_model_snapshot=offering.pricing_model,
            status="pending",
        )
        session.add(order)
        self._event(
            session,
            booking,
            customer_id,
            "requested",
            "Service request submitted; awaiting provider response.",
        )
        session.add(
            InAppNotification(
                recipient_user_id=offering.provider_user_id,
                category="service_booking",
                title="New service request",
                body=f"A customer requested {offering.title}. No booking is confirmed yet.",
                target_path=f"/services?bookingId={booking.id}&tab=Bookings",
            )
        )
        self._audit(
            session,
            customer_id,
            "service.booking_requested",
            "service_booking",
            booking.id,
            request_id,
        )
        session.commit()
        return self._booking_response(session, booking, customer_id)

    def list_for_user(self, session: Session, *, user_id: UUID) -> list[BookingResponse]:
        customer_permission = self.authorization.has_permission(
            session, user_id=user_id, permission_code="booking:view:self", resource_owner_id=user_id
        )
        provider_permission = self.authorization.has_permission(
            session,
            user_id=user_id,
            permission_code="booking:view:assigned",
            resource_scope_type="booking",
            resource_scope_id="*",
        )
        if not customer_permission and not provider_permission:
            raise self._denied()
        statement = select(ServiceBooking)
        if customer_permission and provider_permission:
            statement = statement.where(
                (ServiceBooking.customer_user_id == user_id)
                | (ServiceBooking.provider_user_id == user_id)
            )
        elif customer_permission:
            statement = statement.where(ServiceBooking.customer_user_id == user_id)
        else:
            statement = statement.where(ServiceBooking.provider_user_id == user_id)
        rows = session.scalars(statement.order_by(ServiceBooking.created_at.desc()).limit(200))
        return [self._booking_response(session, row, user_id) for row in rows]

    def history(
        self, session: Session, *, user_id: UUID, booking_id: UUID
    ) -> list[BookingHistoryResponse]:
        booking = self._authorized_booking(session, user_id, booking_id)
        return [
            BookingHistoryResponse.model_validate(row)
            for row in session.scalars(
                select(ServiceBookingEvent)
                .where(ServiceBookingEvent.booking_id == booking.id)
                .order_by(ServiceBookingEvent.created_at)
            )
        ]

    def act(
        self,
        session: Session,
        *,
        user_id: UUID,
        booking_id: UUID,
        body: BookingAction,
        request_id: str | None = None,
    ) -> BookingResponse:
        booking = self._authorized_booking(session, user_id, booking_id)
        now = datetime.now(UTC)
        is_provider = booking.provider_user_id == user_id
        if body.action in {"accept", "reject", "propose_reschedule", "complete"}:
            if not is_provider:
                raise self._not_found()
            self.authorization.require_permission(
                session,
                user_id=user_id,
                permission_code="booking:manage:assigned",
                resource_scope_type="booking",
                resource_scope_id=str(booking.id),
            )
        else:
            if is_provider or booking.customer_user_id != user_id:
                raise self._not_found()
        if body.action == "accept":
            if booking.status != "pending":
                raise self._invalid_transition()
            booking.status = "accepted"
            booking.accepted_at = now
            booking.provider_response = body.note
        elif body.action == "reject":
            if booking.status != "pending":
                raise self._invalid_transition()
            booking.status = "rejected"
            booking.provider_response = body.note
        elif body.action == "propose_reschedule":
            if (
                booking.status not in {"pending", "accepted", "rescheduled"}
                or body.proposed_at is None
                or body.proposed_at.astimezone(UTC) <= now
            ):
                raise self._invalid_transition()
            booking.reschedule_return_status = "accepted" if booking.accepted_at else "pending"
            booking.proposed_at = body.proposed_at.astimezone(UTC)
            booking.status = "reschedule_proposed"
            booking.provider_response = body.note
        elif body.action == "accept_reschedule":
            if booking.status != "reschedule_proposed" or booking.proposed_at is None:
                raise self._invalid_transition()
            booking.requested_at = booking.proposed_at
            booking.proposed_at = None
            booking.status = "rescheduled"
            booking.accepted_at = booking.accepted_at or now
            booking.reschedule_return_status = None
        elif body.action == "decline_reschedule":
            if booking.status != "reschedule_proposed":
                raise self._invalid_transition()
            booking.status = booking.reschedule_return_status or "pending"
            booking.proposed_at = None
            booking.reschedule_return_status = None
        elif body.action == "cancel":
            if booking.status not in {"pending", "accepted", "reschedule_proposed", "rescheduled"}:
                raise self._invalid_transition()
            order = session.scalar(
                select(ServiceOrder).where(ServiceOrder.booking_id == booking.id)
            )
            active_payment = (
                session.scalar(
                    select(PaymentTransaction.id).where(
                        PaymentTransaction.service_order_id == order.id,
                        PaymentTransaction.status.in_(("initiated", "pending", "successful")),
                    )
                )
                if order is not None
                else None
            )
            if active_payment is not None:
                raise ApiError(
                    409,
                    "payment_must_be_resolved_before_cancellation",
                    "Check the M-Pesa status before cancelling this service booking.",
                )
            booking.status = "cancelled"
            booking.proposed_at = None
        elif body.action == "complete":
            if booking.status not in {"accepted", "rescheduled"}:
                raise self._invalid_transition()
            booking.status = "completed"
            booking.completed_at = now
        booking.updated_at = now
        if booking.provider_response is None and body.note:
            booking.provider_response = body.note
        order = session.scalar(select(ServiceOrder).where(ServiceOrder.booking_id == booking.id))
        if order:
            order.status = booking.status
            order.updated_at = now
        self._event(session, booking, user_id, body.action, body.note)
        recipient = booking.customer_user_id if is_provider else booking.provider_user_id
        session.add(
            InAppNotification(
                recipient_user_id=recipient,
                category="service_booking",
                title="Service request updated",
                body=f"Request status: {booking.status.replace('_', ' ')}.",
                target_path=f"/services?bookingId={booking.id}&tab=Bookings",
            )
        )
        self._audit(
            session,
            user_id,
            f"service.booking_{body.action}",
            "service_booking",
            booking.id,
            request_id,
        )
        session.commit()
        return self._booking_response(session, booking, user_id)

    def orders(self, session: Session, *, user_id: UUID) -> list[OrderResponse]:
        customer = self.authorization.has_permission(
            session, user_id=user_id, permission_code="booking:view:self", resource_owner_id=user_id
        )
        provider = self.authorization.has_permission(
            session,
            user_id=user_id,
            permission_code="order:view:assigned",
            resource_scope_type="booking",
            resource_scope_id="*",
        )
        if not customer and not provider:
            raise self._denied()
        statement = select(ServiceOrder)
        if customer and provider:
            statement = statement.where(
                (ServiceOrder.customer_user_id == user_id)
                | (ServiceOrder.provider_user_id == user_id)
            )
        elif customer:
            statement = statement.where(ServiceOrder.customer_user_id == user_id)
        else:
            statement = statement.where(ServiceOrder.provider_user_id == user_id)
        return [
            OrderResponse.model_validate(row)
            for row in session.scalars(
                statement.order_by(ServiceOrder.created_at.desc()).limit(200)
            )
        ]

    def create_review(
        self, session: Session, *, user_id: UUID, booking_id: UUID, body: ServiceReviewCreate
    ) -> ServiceReviewResponse:
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code="service_review:create:self",
            resource_owner_id=user_id,
        )
        booking = session.get(ServiceBooking, booking_id)
        if booking is None or booking.customer_user_id != user_id or booking.status != "completed":
            raise self._not_found()
        if session.scalar(select(ServiceReview.id).where(ServiceReview.booking_id == booking.id)):
            raise ApiError(
                409,
                "review_already_submitted",
                "A review has already been submitted for this completed service.",
            )
        review = ServiceReview(
            booking_id=booking.id,
            offering_id=booking.offering_id,
            reviewer_user_id=user_id,
            provider_user_id=booking.provider_user_id,
            rating=body.rating,
            review_text=body.review_text,
        )
        session.add(review)
        self._audit(
            session, user_id, "service.review_submitted", "service_booking", booking.id, None
        )
        session.commit()
        return ServiceReviewResponse.model_validate(review)

    def _authorized_booking(
        self, session: Session, user_id: UUID, booking_id: UUID
    ) -> ServiceBooking:
        row = session.get(ServiceBooking, booking_id)
        if row is None or user_id not in {row.customer_user_id, row.provider_user_id}:
            raise self._not_found()
        if user_id == row.customer_user_id:
            self.authorization.require_permission(
                session,
                user_id=user_id,
                permission_code="booking:view:self",
                resource_owner_id=user_id,
            )
        else:
            self.authorization.require_permission(
                session,
                user_id=user_id,
                permission_code="booking:view:assigned",
                resource_scope_type="booking",
                resource_scope_id=str(row.id),
            )
        return row

    def _booking_response(
        self, session: Session, row: ServiceBooking, viewer_id: UUID
    ) -> BookingResponse:
        offer = session.get(ServiceOffering, row.offering_id)
        profile = session.scalar(
            select(ServiceProviderProfile).where(
                ServiceProviderProfile.provider_user_id == row.provider_user_id
            )
        )
        order = session.scalar(select(ServiceOrder).where(ServiceOrder.booking_id == row.id))
        return BookingResponse(
            id=row.id,
            offering_id=row.offering_id,
            offering_title=offer.title
            if offer
            else (order.offering_title_snapshot if order else "Service"),
            category=offer.category if offer else (order.category_snapshot if order else "other"),
            customer_user_id=row.customer_user_id,
            provider_user_id=row.provider_user_id,
            provider_name=profile.public_name if profile else "Service provider",
            property_id=row.property_id,
            requested_at=row.requested_at,
            proposed_at=row.proposed_at,
            timezone=row.timezone,
            request_details=row.request_details,
            provider_response=row.provider_response,
            status=row.status,
            is_customer=viewer_id == row.customer_user_id,
            order_id=order.id if order else None,
            estimated_amount_kes=order.estimated_amount_kes if order else None,
            currency="KES",
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _require_resident(session: Session, user_id: UUID, property_id: UUID) -> Property:
        property_ = session.get(Property, property_id)
        access = session.scalar(
            select(PropertyResidentAccess).where(
                PropertyResidentAccess.property_id == property_id,
                PropertyResidentAccess.resident_user_id == user_id,
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

    def _require_offering_area_for_property(
        self, session: Session, offering_id: UUID, property_id: UUID
    ) -> None:
        from app.models.services import ServiceArea

        property_ = session.get(Property, property_id)
        county = session.get(County, property_.county_id) if property_ else None
        town = session.get(Town, property_.town_id) if property_ else None
        area = (
            session.scalar(
                select(ServiceArea.id).where(
                    ServiceArea.offering_id == offering_id,
                    (
                        (ServiceArea.town_id == property_.town_id)
                        | (
                            (ServiceArea.town_id.is_(None))
                            & (ServiceArea.county_id == property_.county_id)
                        )
                    ),
                )
            )
            if property_
            else None
        )
        if property_ and (county is None or town is None or area is None):
            raise ApiError(
                422,
                "service_area_mismatch",
                "The provider does not list this property's town or county as a service area.",
            )

    @staticmethod
    def _event(
        session: Session, booking: ServiceBooking, actor_id: UUID, action: str, details: str | None
    ) -> None:
        session.add(
            ServiceBookingEvent(
                booking_id=booking.id, actor_user_id=actor_id, action=action, details=details
            )
        )

    @staticmethod
    def _audit(
        session: Session,
        actor_id: UUID,
        event: str,
        subject_type: str,
        subject_id: UUID,
        request_id: str | None,
    ) -> None:
        session.add(
            AuditEvent(
                actor_user_id=actor_id,
                event_type=event,
                subject_type=subject_type,
                subject_id=str(subject_id),
                request_id=request_id,
                metadata_json={},
            )
        )

    @staticmethod
    def _invalid_transition() -> ApiError:
        return ApiError(
            409,
            "booking_status_conflict",
            "This booking cannot take that action in its current status.",
        )

    @staticmethod
    def _denied() -> ApiError:
        return ApiError(403, "permission_denied", "You are not authorized to view these bookings.")

    @staticmethod
    def _not_found() -> ApiError:
        return ApiError(404, "booking_not_found", "The requested booking was not found.")
