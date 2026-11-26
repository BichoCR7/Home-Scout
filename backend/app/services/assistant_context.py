"""Build explicitly selected, owner-authorized facts for Assistant provider requests."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings
from app.core.errors import ApiError
from app.models.location import County, Neighbourhood, Town
from app.models.marketplace import SavedProperty
from app.models.personal_hub import ScheduleEntry
from app.models.phase10 import (
    CollaborationGroup,
    CollaborationGroupMember,
    ScheduledViewing,
    SharedProperty,
    SharedSearch,
)
from app.models.property import Property
from app.models.services import MovePlan, MovePlanTask, ServiceBooking
from app.models.smartrent import MoveInPlan, SavingsGoal
from app.schemas.assistant import AssistantContextProperty, AssistantMessageRequest
from app.services.smartrent import SmartRentService

_RENT_LIMIT = re.compile(
    r"\b(?:under|below|less than|up to|maximum|max|budget(?: of)?)\s*"
    r"(?:ksh|kes)?\s*([\d,]+)\s*(k)?\b",
    re.IGNORECASE,
)
_BEDROOM_COUNT = re.compile(r"\b([0-9]{1,2})\s*[- ]?(?:bedrooms?|beds?|br)\b", re.IGNORECASE)


@dataclass(slots=True)
class AssistantContext:
    text: str = "No private account data was selected for this request."
    properties: list[AssistantContextProperty] = field(default_factory=list)
    property_ids: list[str] = field(default_factory=list)


class AssistantContextBuilder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build(
        self,
        session: Session,
        *,
        user_id: UUID,
        request: AssistantMessageRequest,
    ) -> AssistantContext:
        facts: list[str] = []
        listings: dict[UUID, Property] = {}

        selected_ids = list(request.compare_property_ids)
        if request.property_id:
            selected_ids.append(request.property_id)
        if selected_ids:
            rows = self._public_properties(session, selected_ids)
            if len(rows) != len(set(selected_ids)):
                raise ApiError(
                    404,
                    "assistant_property_not_available",
                    "One of the selected homes is not currently available as a public listing.",
                )
            listings.update((row.id, row) for row in rows)
            facts.append("Homes the user explicitly selected:")
            facts.extend(self._property_fact(row) for row in rows)

        if request.include_saved_properties:
            saved = list(
                session.scalars(
                    select(Property)
                    .join(SavedProperty, SavedProperty.property_id == Property.id)
                    .options(
                        joinedload(Property.county),
                        joinedload(Property.town),
                        joinedload(Property.neighbourhood),
                    )
                    .where(
                        SavedProperty.user_id == user_id,
                        Property.is_demo.is_(False),
                        Property.moderation_status == "clear",
                        Property.listing_status == "published",
                        Property.availability_status == "available",
                    )
                    .order_by(SavedProperty.created_at.desc())
                    .limit(5)
                )
            )
            listings.update((row.id, row) for row in saved)
            facts.append("Currently public and available homes saved by this user:")
            facts.extend(self._property_fact(row) for row in saved)

        search_results = self._search_from_message(session, request.text)
        if search_results:
            listings.update((row.id, row) for row in search_results)
            facts.append("Public listing records matching parsed search details at request time:")
            facts.extend(self._property_fact(row) for row in search_results)
        elif request.intent in {"property_search", "neighbourhood_discovery"}:
            facts.append(
                "No matching public HomeScout listings were found. "
                "This database result does not prove no homes exist in that area."
            )

        if request.include_finance_context:
            if not self.settings.finance_encryption_key:
                raise ApiError(
                    409,
                    "assistant_finance_context_unavailable",
                    "Your private finance profile is not configured for secure access.",
                )
            finance = SmartRentService(self.settings)
            profile = finance.profile_response(session, user_id)
            if profile["is_configured"]:
                assessment = finance.assessment(session, user_id)
                facts.append(
                    "User-owned SmartRent planning summary, explicitly selected by the user: "
                    f"conservative_monthly_income_kes={assessment['conservative_monthly_income']}; "
                    f"monthly_expenses_kes={assessment['monthly_expenses']}; "
                    f"monthly_obligations_kes={assessment['monthly_obligations']}; "
                    f"suggested_monthly_budget_kes={assessment['suggested_monthly_budget']}; "
                    f"target_monthly_rent_kes={assessment['target_monthly_rent']}; "
                    f"remaining_after_target_rent_kes={assessment['remaining_after_target_rent']}; "
                    f"planning_band={assessment['affordability']}; "
                    f"readiness_index={assessment['readiness_index']}; "
                    f"readiness_label={assessment['readiness_label']}. "
                    "RentScore/readiness is a user-input planning index, not a credit score, "
                    "lending decision, eligibility result, or promise."
                )
                goals = session.scalars(
                    select(SavingsGoal)
                    .where(SavingsGoal.owner_user_id == user_id)
                    .order_by(SavingsGoal.updated_at.desc())
                    .limit(5)
                ).all()
                if goals:
                    facts.append("The user's own saved housing savings goals:")
                    for goal in goals:
                        goal_data = finance.cipher.decrypt(user_id, goal.encrypted_data)
                        facts.append(
                            f"title={goal_data.get('title', 'Savings goal')}; "
                            f"target_kes={goal_data.get('target_amount')}; status={goal.status}"
                        )
            else:
                facts.append(
                    "The user has not configured a SmartRent profile. Do not infer income, "
                    "budget, savings, or affordability."
                )
            move_in_plans = session.scalars(
                select(MoveInPlan)
                .where(MoveInPlan.owner_user_id == user_id)
                .order_by(MoveInPlan.updated_at.desc())
                .limit(5)
            ).all()
            if move_in_plans:
                facts.append("The user's own saved move-in cost plans:")
                facts.extend(
                    f"plan={plan.id}; data={finance.cipher.decrypt(user_id, plan.encrypted_data)}"
                    for plan in move_in_plans
                )

        if request.include_schedule_context:
            facts.extend(self._schedule_facts(session, user_id))

        if request.include_work_context:
            facts.extend(self._work_facts(session, user_id))

        if request.shared_group_id:
            facts.extend(
                self._shared_group_facts(session, user_id, request.shared_group_id, listings)
            )

        facts.append(
            "These records are factual snapshots only. Never infer or promise future availability, "
            "property verification, booking confirmation, payment status, service completion, "
            "or neighbourhood statistics."
        )
        properties = [self._property_response(row) for row in listings.values()]
        return AssistantContext(
            text="\n".join(facts),
            properties=properties,
            property_ids=[str(item.id) for item in properties],
        )

    @staticmethod
    def _public_condition():
        return (
            Property.is_demo.is_(False),
            Property.moderation_status == "clear",
            Property.listing_status == "published",
            Property.availability_status == "available",
        )

    def _public_properties(self, session: Session, ids: list[UUID]) -> list[Property]:
        unique_ids = list(dict.fromkeys(ids))
        return list(
            session.scalars(
                select(Property)
                .options(
                    joinedload(Property.county),
                    joinedload(Property.town),
                    joinedload(Property.neighbourhood),
                )
                .where(Property.id.in_(unique_ids), *self._public_condition())
            )
        )

    def _search_from_message(self, session: Session, text: str) -> list[Property]:
        folded = text.casefold()
        location_conditions = []
        for model, _column, id_column in (
            (Neighbourhood, Neighbourhood.name, Property.neighbourhood_id),
            (Town, Town.name, Property.town_id),
            (County, County.name, Property.county_id),
        ):
            locations = session.scalars(select(model).where(model.is_active.is_(True))).all()
            matches = [location for location in locations if location.name.casefold() in folded]
            if matches:
                match = max(matches, key=lambda location: len(location.name))
                location_conditions.append(id_column == match.id)
                break

        conditions = list(self._public_condition())
        if location_conditions:
            conditions.extend(location_conditions)
        rent_match = _RENT_LIMIT.search(text)
        if rent_match:
            rent = Decimal(rent_match.group(1).replace(",", ""))
            if rent_match.group(2):
                rent *= 1000
            conditions.append(Property.rent_amount <= rent)
        bedroom_match = _BEDROOM_COUNT.search(text)
        if bedroom_match:
            conditions.append(Property.bedrooms == int(bedroom_match.group(1)))
        lowered = folded
        if "bedsitter" in lowered:
            conditions.append(Property.unit_type == "bedsitter")
        elif "studio" in lowered:
            conditions.append(Property.unit_type == "studio")
        for keyword, value in (
            ("apartment", "apartment"),
            ("maisonette", "maisonette"),
            ("townhouse", "townhouse"),
            ("villa", "villa"),
            ("house", "house"),
        ):
            if keyword in lowered:
                conditions.append(Property.property_type == value)
                break
        if (
            not location_conditions
            and not rent_match
            and not bedroom_match
            and not any(
                item in lowered
                for item in (
                    "bedsitter",
                    "studio",
                    "apartment",
                    "maisonette",
                    "townhouse",
                    "villa",
                    "house",
                )
            )
        ):
            return []
        return list(
            session.scalars(
                select(Property)
                .options(
                    joinedload(Property.county),
                    joinedload(Property.town),
                    joinedload(Property.neighbourhood),
                )
                .where(*conditions)
                .order_by(Property.rent_amount.asc(), Property.id)
                .limit(5)
            )
        )

    def _schedule_facts(self, session: Session, user_id: UUID) -> list[str]:
        now = datetime.now(UTC)
        schedule = session.scalars(
            select(ScheduleEntry)
            .where(
                ScheduleEntry.owner_user_id == user_id,
                ScheduleEntry.status == "planned",
                ScheduleEntry.starts_at >= now - timedelta(days=1),
                ScheduleEntry.starts_at <= now + timedelta(days=30),
            )
            .order_by(ScheduleEntry.starts_at)
            .limit(12)
        ).all()
        viewings = session.scalars(
            select(ScheduledViewing)
            .where(
                or_(
                    ScheduledViewing.requester_user_id == user_id,
                    ScheduledViewing.host_user_id == user_id,
                ),
                ScheduledViewing.status.in_(("requested", "confirmed", "reschedule_proposed")),
                ScheduledViewing.requested_at >= now - timedelta(days=1),
                ScheduledViewing.requested_at <= now + timedelta(days=30),
            )
            .order_by(ScheduledViewing.requested_at)
            .limit(12)
        ).all()
        facts = ["Upcoming user-owned schedule entries:"]
        facts.extend(
            f"{row.category}, {row.title}, {row.starts_at.isoformat()}, "
            f"status={row.status}, timezone={row.timezone}"
            for row in schedule
        )
        facts.append("Viewings where this user is a participant:")
        facts.extend(
            f"Viewing status={row.status}, requested_at={row.requested_at.isoformat()}, "
            f"timezone={row.timezone}"
            for row in viewings
        )
        if not schedule and not viewings:
            facts.append(
                "No upcoming user-owned schedule entries or participant viewings were found."
            )
        return facts

    def _shared_group_facts(
        self,
        session: Session,
        user_id: UUID,
        group_id: UUID,
        listings: dict[UUID, Property],
    ) -> list[str]:
        membership = session.get(CollaborationGroupMember, (group_id, user_id))
        if membership is None or membership.status != "active":
            raise ApiError(
                404, "assistant_shared_group_not_found", "That shared search is not available."
            )
        group_name = session.scalar(
            select(CollaborationGroup.name).where(CollaborationGroup.id == group_id)
        )
        searches = session.scalars(
            select(SharedSearch)
            .where(SharedSearch.group_id == group_id)
            .order_by(SharedSearch.updated_at.desc())
            .limit(5)
        ).all()
        facts = [
            "Shared housing-search context explicitly selected by an active group member: "
            f"{group_name or 'Shared search'}."
        ]
        facts.extend(f"Shared search filters: {item.filters}" for item in searches)
        property_ids = list(
            session.scalars(
                select(SharedProperty.property_id)
                .where(SharedProperty.group_id == group_id)
                .order_by(SharedProperty.created_at.desc())
                .limit(5)
            )
        )
        rows = self._public_properties(session, property_ids) if property_ids else []
        listings.update((row.id, row) for row in rows)
        if rows:
            facts.append("Currently public and available homes shared with this group:")
            facts.extend(self._property_fact(row) for row in rows)
        else:
            facts.append("This group has no currently public and available shared home records.")
        facts.append(
            "Private group conversations, private journals, and member profiles were not included."
        )
        return facts

    def _work_facts(self, session: Session, user_id: UUID) -> list[str]:
        owned_or_assigned = session.scalars(
            select(Property)
            .options(
                joinedload(Property.county),
                joinedload(Property.town),
                joinedload(Property.neighbourhood),
            )
            .where(
                Property.is_demo.is_(False),
                or_(
                    Property.owner_user_id == user_id,
                    Property.authorized_agent_user_id == user_id,
                    Property.property_manager_user_id == user_id,
                ),
            )
            .order_by(Property.updated_at.desc())
            .limit(5)
        ).all()
        facts = ["The user's own or explicitly assigned listing work:"]
        facts.extend(
            f"property_id={row.id}; title={row.title}; rent_kes={row.rent_amount}; "
            f"listing_status={row.listing_status}; availability={row.availability_status}; "
            f"review_status={row.verification_status}; location={self._location(row)}"
            for row in owned_or_assigned
        )

        plans = session.scalars(
            select(MovePlan)
            .where(MovePlan.owner_user_id == user_id)
            .order_by(MovePlan.move_date)
            .limit(5)
        ).all()
        facts.append("The user's private moving plans and tasks:")
        if plans:
            plan_ids = [plan.id for plan in plans]
            tasks = session.scalars(
                select(MovePlanTask)
                .where(MovePlanTask.move_plan_id.in_(plan_ids))
                .order_by(MovePlanTask.due_date)
                .limit(30)
            ).all()
            for plan in plans:
                facts.append(
                    f"plan={plan.title}; move_date={plan.move_date}; "
                    f"target_budget_kes={plan.target_budget_kes}; "
                    f"tasks="
                    + "; ".join(
                        f"{task.title} ({task.category}, {task.status}, due={task.due_date})"
                        for task in tasks
                        if task.move_plan_id == plan.id
                    )
                )
        else:
            facts.append("No personal moving plans were found.")

        bookings = session.scalars(
            select(ServiceBooking)
            .where(
                or_(
                    ServiceBooking.customer_user_id == user_id,
                    ServiceBooking.provider_user_id == user_id,
                )
            )
            .order_by(ServiceBooking.requested_at.desc())
            .limit(10)
        ).all()
        facts.append("Service bookings where the user is the customer or provider:")
        if bookings:
            facts.extend(
                f"booking_id={row.id}; status={row.status}; "
                f"requested_at={row.requested_at.isoformat()}; timezone={row.timezone}; "
                "service_request="
                f"{row.request_details if row.customer_user_id == user_id else 'omitted'}"
                for row in bookings
            )
        else:
            facts.append("No participant service bookings were found.")
        facts.append(
            "Only owned or assigned listings and participant bookings were included. "
            "Private messages and other customers' booking details were excluded."
        )
        return facts

    @staticmethod
    def _property_fact(row: Property) -> str:
        location = AssistantContextBuilder._location(row)
        return (
            f"property_id={row.id}; title={row.title}; "
            f"rent=KSh {row.rent_amount} per {row.rent_frequency}; "
            f"location={location}; bedrooms={row.bedrooms}; bathrooms={row.bathrooms}; "
            f"property_type={row.property_type}; furnishing={row.furnishing}; "
            f"amenities={', '.join(row.amenities or [])}; "
            f"stored_verification_status={row.verification_status}; "
            f"stored_availability_status={row.availability_status}."
        )

    @staticmethod
    def _location(row: Property) -> str:
        return ", ".join(
            part
            for part in (
                row.neighbourhood.name if row.neighbourhood else None,
                row.town.name if row.town else None,
                row.county.name if row.county else None,
            )
            if part
        )

    @classmethod
    def _property_response(cls, row: Property) -> AssistantContextProperty:
        return AssistantContextProperty(
            id=row.id,
            title=row.title,
            rent_amount_kes=str(row.rent_amount),
            rent_frequency=row.rent_frequency,
            location=cls._location(row),
            bedrooms=row.bedrooms,
            bathrooms=str(row.bathrooms),
            verification_status=row.verification_status,
            availability_status=row.availability_status,
        )
