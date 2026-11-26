"""Private SmartRent workflows and explainable housing-finance planning."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_CEILING, Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import Settings
from app.core.errors import ApiError
from app.data_access.smartrent import SmartRentDataAccess
from app.models.personal_hub import PrivateDocument
from app.models.property import Property
from app.models.smartrent import (
    FinanceAlert,
    FinanceProfile,
    FinancialLessonProgress,
    HousingFinancialRecord,
    LeaseGuardianRecord,
    MoveInPlan,
    RentObligation,
    RentPaymentRecord,
    SavingsContribution,
    SavingsGoal,
    SavingsGoalShare,
    TrueCostComparison,
)
from app.models.user import UserAccount
from app.schemas.smartrent import (
    FinanceProfileInput,
    HousingRecordCreate,
    LeaseGuardianCreate,
    LeaseGuardianUpdate,
    MoveInPlanCreate,
    MoveInPlanUpdate,
    RentObligationCreate,
    RentObligationUpdate,
    RentPaymentReportCreate,
    SavingsContributionCreate,
    SavingsGoalCreate,
    SavingsGoalShareCreate,
    SavingsGoalUpdate,
    TrueCostComparisonCreate,
)
from app.services.finance_calculations import (
    assess_finances,
    simulate_rent_choice,
    simulate_savings,
    utility_summary,
)
from app.services.finance_cipher import FinanceCipher
from app.services.financial_literacy import LESSONS, public_lesson

ZERO = Decimal("0")
MONEY = Decimal("0.01")
NOT_CREDIT = (
    "Planning estimate only. This is not a credit score, lending decision, eligibility test, "
    "or automatic listing-rejection rule."
)
VIRTUAL_SAVINGS = "Virtual tracker only. HomeScout does not hold, receive, or transfer these funds."
NO_LEGAL_ADVICE = (
    "This organizer is not legal advice and does not interpret or approve an agreement."
)


class SmartRentService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cipher: FinanceCipher | None = None
        self.data = SmartRentDataAccess()

    @property
    def cipher(self) -> FinanceCipher:
        """Initialize encryption only for workflows that read or persist private data.

        A missing finance key must not disable stateless calculations, public-data
        discovery, or learning endpoints that do not need encrypted finance storage.
        Persistence still fails closed through FinanceCipher when it is required.
        """
        if self._cipher is None:
            self._cipher = FinanceCipher(self.settings)
        return self._cipher

    @staticmethod
    def not_found() -> ApiError:
        return ApiError(
            404, "finance_record_not_found", "The requested private finance record was not found."
        )

    def _profile_payload(self, session: Session, user_id: UUID) -> dict[str, Any]:
        row = self.data.profile(session, user_id)
        if row is None:
            return {
                "income_amount": "0",
                "income_frequency": "monthly",
                "income_work_days_per_week": 5,
                "additional_income_sources": [],
                "income_pattern": "steady",
                "recent_monthly_income": [],
                "monthly_expenses": "0",
                "monthly_obligations": "0",
                "current_savings": "0",
                "target_monthly_rent": "0",
                "expected_move_in_total": "0",
                "monthly_utility_budget": None,
                "monthly_transport_cost": "0",
                "monthly_housing_other_costs": "0",
                "budget_categories": [],
                "household_size": 1,
                "has_payslip": False,
            }
        payload = self.cipher.decrypt(user_id, row.encrypted_data)
        payload.setdefault("budget_categories", [])
        return payload

    def profile_response(self, session: Session, user_id: UUID) -> dict[str, Any]:
        row = self.data.profile(session, user_id)
        return self._profile_payload(session, user_id) | {
            "updated_at": row.updated_at if row else None,
            "is_configured": row is not None,
        }

    def save_profile(
        self, session: Session, user_id: UUID, body: FinanceProfileInput
    ) -> dict[str, Any]:
        payload = body.model_dump(mode="json")
        row = self.data.profile(session, user_id)
        if row is None:
            row = FinanceProfile(
                user_id=user_id, encrypted_data=self.cipher.encrypt(user_id, payload)
            )
            session.add(row)
        else:
            row.encrypted_data = self.cipher.encrypt(user_id, payload)
        session.flush()
        assessment = assess_finances(payload)
        self._maybe_budget_alert(session, user_id, payload, assessment)
        session.commit()
        return self.profile_response(session, user_id)

    def assessment(self, session: Session, user_id: UUID) -> dict[str, Any]:
        return assess_finances(self._profile_payload(session, user_id))

    @staticmethod
    def preview_assessment(body: FinanceProfileInput) -> dict[str, Any]:
        """Calculate a private, non-persisting preview using the saved-profile rules."""
        return assess_finances(body.model_dump(mode="json"))

    def coach(self, session: Session, user_id: UUID) -> dict[str, Any]:
        assessment = self.assessment(session, user_id)
        return {
            "mode": "rule_based_preview",
            "connected_to_ai_provider": False,
            "messages": assessment["suggestions"][:3],
            "budget": assessment["suggested_monthly_budget"],
            "disclaimer": (
                "This preview uses transparent rules and your own entries; "
                "no AI provider is connected."
            ),
        }

    def create_plan(
        self, session: Session, user_id: UUID, body: MoveInPlanCreate
    ) -> dict[str, Any]:
        payload = body.model_dump(mode="json")
        listing = None
        if body.property_id:
            listing = self._public_property(session, body.property_id)
            if listing is None:
                raise ApiError(
                    404, "public_property_not_found", "Choose an available public property."
                )
            if body.rent_amount is None:
                payload["rent_amount"] = str(self._monthly_rent(listing))
                payload["rent_evidence"] = "listing"
            if body.deposit_amount is None and listing.deposit_amount is not None:
                payload["deposit_amount"] = str(listing.deposit_amount)
                payload["deposit_evidence"] = "listing"
        row = MoveInPlan(
            owner_user_id=user_id,
            property_id=body.property_id,
            encrypted_data=self.cipher.encrypt(user_id, payload),
        )
        session.add(row)
        session.commit()
        return self._plan_view(row)

    def list_plans(self, session: Session, user_id: UUID) -> list[dict[str, Any]]:
        return [self._plan_view(row) for row in self.data.plans(session, user_id)]

    def update_plan(
        self, session: Session, user_id: UUID, plan_id: UUID, body: MoveInPlanUpdate
    ) -> dict[str, Any]:
        row = session.scalar(
            select(MoveInPlan).where(MoveInPlan.id == plan_id, MoveInPlan.owner_user_id == user_id)
        )
        if row is None:
            raise self.not_found()
        payload = self.cipher.decrypt(user_id, row.encrypted_data)
        for key, value in body.model_dump(mode="json", exclude_unset=True).items():
            if value is not None:
                payload[key] = value
        row.encrypted_data = self.cipher.encrypt(user_id, payload)
        session.commit()
        return self._plan_view(row)

    def delete_plan(self, session: Session, user_id: UUID, plan_id: UUID) -> None:
        row = session.scalar(
            select(MoveInPlan).where(MoveInPlan.id == plan_id, MoveInPlan.owner_user_id == user_id)
        )
        if row is None:
            raise self.not_found()
        session.delete(row)
        session.commit()

    def _plan_view(self, row: MoveInPlan) -> dict[str, Any]:
        payload = self.cipher.decrypt(row.owner_user_id, row.encrypted_data)
        rent = Decimal(payload["rent_amount"]) if payload.get("rent_amount") else ZERO
        deposit = Decimal(payload["deposit_amount"]) if payload.get("deposit_amount") else ZERO
        costs = payload.get("costs", [])
        other = sum((Decimal(line["amount"]) for line in costs), ZERO)
        return payload | {
            "id": row.id,
            "total_move_in_cost": (rent + deposit + other).quantize(MONEY),
            "monthly_rent": rent.quantize(MONEY),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "disclaimer": (
                "Listing figures reflect the listing when selected; "
                "confirm all figures with the provider."
            ),
        }

    def create_goal(
        self, session: Session, user_id: UUID, body: SavingsGoalCreate
    ) -> dict[str, Any]:
        payload = body.model_dump(mode="json") | {"manual_contributions_total": "0"}
        row = SavingsGoal(
            owner_user_id=user_id,
            encrypted_data=self.cipher.encrypt(user_id, payload),
        )
        session.add(row)
        session.commit()
        return self._goal_view(session, row, user_id)

    def list_goals(self, session: Session, user_id: UUID) -> list[dict[str, Any]]:
        return [
            self._goal_view(session, row, user_id)
            for row in self.data.accessible_goals(session, user_id)
        ]

    def update_goal(
        self, session: Session, user_id: UUID, goal_id: UUID, body: SavingsGoalUpdate
    ) -> dict[str, Any]:
        row = session.scalar(
            select(SavingsGoal).where(
                SavingsGoal.id == goal_id, SavingsGoal.owner_user_id == user_id
            )
        )
        if row is None:
            raise self.not_found()
        payload = self.cipher.decrypt(user_id, row.encrypted_data)
        for key, value in body.model_dump(mode="json", exclude_unset=True).items():
            if value is not None or key == "target_date":
                payload[key] = value
        row.status = payload.get("status", row.status)
        row.encrypted_data = self.cipher.encrypt(user_id, payload)
        session.commit()
        return self._goal_view(session, row, user_id)

    def delete_goal(self, session: Session, user_id: UUID, goal_id: UUID) -> None:
        row = session.scalar(
            select(SavingsGoal).where(
                SavingsGoal.id == goal_id, SavingsGoal.owner_user_id == user_id
            )
        )
        if row is None:
            raise self.not_found()
        session.delete(row)
        session.commit()

    def _require_goal_access(
        self, session: Session, goal_id: UUID, user_id: UUID, *, contribution: bool = False
    ) -> SavingsGoal:
        row = self.data.goal(session, goal_id)
        if row is None:
            raise self.not_found()
        if row.owner_user_id == user_id:
            return row
        share = session.get(SavingsGoalShare, (goal_id, user_id))
        if share is None or (contribution and not share.can_contribute):
            raise self.not_found()
        return row

    def contribute(
        self,
        session: Session,
        user_id: UUID,
        goal_id: UUID,
        body: SavingsContributionCreate,
    ) -> dict[str, Any]:
        goal = self._require_goal_access(session, goal_id, user_id, contribution=True)
        payload = body.model_dump(mode="json")
        existing = None
        if body.request_id is not None:
            existing = session.scalar(
                select(SavingsContribution).where(
                    SavingsContribution.goal_id == goal_id,
                    SavingsContribution.contributor_user_id == user_id,
                    SavingsContribution.request_id == body.request_id,
                )
            )
        if existing is not None:
            recorded = self.cipher.decrypt(existing.contributor_user_id, existing.encrypted_data)
            if recorded.get("amount") != payload.get("amount") or recorded.get(
                "notes"
            ) != payload.get("notes"):
                raise ApiError(
                    409,
                    "contribution_request_reused",
                    "This contribution retry key was already used for different details.",
                )
            return self._goal_view(session, goal, user_id)
        if goal.status != "open":
            raise ApiError(
                409, "goal_not_open", "Contributions can only be recorded on an open goal."
            )
        row = SavingsContribution(
            goal_id=goal_id,
            contributor_user_id=user_id,
            request_id=body.request_id,
            encrypted_data=self.cipher.encrypt(user_id, payload),
        )
        session.add(row)
        try:
            session.flush()
        except IntegrityError as error:
            session.rollback()
            if body.request_id is None:
                raise
            goal = self._require_goal_access(session, goal_id, user_id, contribution=True)
            existing = session.scalar(
                select(SavingsContribution).where(
                    SavingsContribution.goal_id == goal_id,
                    SavingsContribution.contributor_user_id == user_id,
                    SavingsContribution.request_id == body.request_id,
                )
            )
            if existing is None:
                raise error
            recorded = self.cipher.decrypt(existing.contributor_user_id, existing.encrypted_data)
            if recorded.get("amount") != payload.get("amount") or recorded.get(
                "notes"
            ) != payload.get("notes"):
                raise ApiError(
                    409,
                    "contribution_request_reused",
                    "This contribution retry key was already used for different details.",
                ) from error
            return self._goal_view(session, goal, user_id)
        view = self._goal_view(session, goal, user_id)
        self._goal_milestone_alert(session, goal, view)
        session.commit()
        return self._goal_view(session, goal, user_id)

    def goal_contributions(
        self, session: Session, user_id: UUID, goal_id: UUID
    ) -> list[dict[str, Any]]:
        self._require_goal_access(session, goal_id, user_id)
        return [
            self.cipher.decrypt(row.contributor_user_id, row.encrypted_data)
            | {
                "contributor_id": row.contributor_user_id,
                "recorded_at": row.created_at,
                "status": "manually_recorded",
            }
            for row in self.data.contributions(session, goal_id)
        ]

    def share_goal(
        self, session: Session, owner_id: UUID, goal_id: UUID, body: SavingsGoalShareCreate
    ) -> dict[str, Any]:
        goal = session.scalar(
            select(SavingsGoal).where(
                SavingsGoal.id == goal_id, SavingsGoal.owner_user_id == owner_id
            )
        )
        if goal is None or body.user_id == owner_id:
            raise self.not_found()
        if session.get(UserAccount, body.user_id) is None:
            raise ApiError(
                404, "share_member_not_found", "That HomeScout account could not be found."
            )
        share = session.get(SavingsGoalShare, (goal_id, body.user_id))
        if share is None:
            share = SavingsGoalShare(
                goal_id=goal_id,
                shared_with_user_id=body.user_id,
                can_contribute=body.can_contribute,
            )
            session.add(share)
        else:
            share.can_contribute = body.can_contribute
        session.commit()
        return {"goal_id": goal_id, "user_id": body.user_id, "can_contribute": body.can_contribute}

    def unshare_goal(
        self, session: Session, owner_id: UUID, goal_id: UUID, member_id: UUID
    ) -> None:
        goal = session.scalar(
            select(SavingsGoal).where(
                SavingsGoal.id == goal_id, SavingsGoal.owner_user_id == owner_id
            )
        )
        if goal is None:
            raise self.not_found()
        share = session.get(SavingsGoalShare, (goal_id, member_id))
        if share is not None:
            session.delete(share)
            session.commit()

    def _goal_view(self, session: Session, row: SavingsGoal, viewer_id: UUID) -> dict[str, Any]:
        owner_view = row.owner_user_id == viewer_id
        payload = self.cipher.decrypt(row.owner_user_id, row.encrypted_data)
        target = Decimal(payload["target_amount"])
        contributions = self.data.contributions(session, row.id)
        contribution_total = sum(
            (
                Decimal(
                    self.cipher.decrypt(item.contributor_user_id, item.encrypted_data)["amount"]
                )
                for item in contributions
            ),
            ZERO,
        )
        initial_savings = Decimal(payload.get("initial_saved_amount", "0"))
        current = initial_savings + contribution_total
        progress = min(Decimal(100), current / target * 100) if target > ZERO else ZERO
        shares = self.data.goal_shares(session, row.id) if owner_view else []
        if row.status == "open" and current >= target:
            row.status = "completed"
        return payload | {
            "id": row.id,
            "owner_user_id": row.owner_user_id,
            "status": row.status,
            "current_amount": current.quantize(MONEY),
            "initial_saved_amount": initial_savings.quantize(MONEY),
            "remaining_amount": max(ZERO, target - current).quantize(MONEY),
            "progress_percent": int(progress),
            "required_monthly_contribution": self._required_savings(payload, current),
            "required_weekly_contribution": self._required_weekly_savings(payload, current),
            "planned_monthly_contribution": Decimal(
                payload.get("planned_monthly_contribution", "0")
            ).quantize(MONEY),
            "estimated_completion_date": self._estimated_completion_date(payload, current),
            "estimated_months_to_completion": self._estimated_months_to_completion(
                payload, current
            ),
            "members": [
                {"user_id": share.shared_with_user_id, "can_contribute": share.can_contribute}
                for share in shares
            ],
            "is_owner": owner_view,
            "is_virtual_tracker": True,
            "disclaimer": VIRTUAL_SAVINGS,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def _required_savings(payload: dict[str, Any], current: Decimal) -> Decimal | None:
        target = Decimal(payload["target_amount"])
        deadline = payload.get("target_date")
        if not deadline:
            return None
        days = (date.fromisoformat(deadline) - date.today()).days
        months = max(1, (days + 29) // 30)
        return (max(ZERO, target - current) / months).quantize(MONEY)

    @staticmethod
    def _required_weekly_savings(payload: dict[str, Any], current: Decimal) -> Decimal | None:
        target = Decimal(payload["target_amount"])
        deadline = payload.get("target_date")
        if not deadline:
            return None
        days = (date.fromisoformat(deadline) - date.today()).days
        weeks = max(1, (days + 6) // 7)
        return (max(ZERO, target - current) / weeks).quantize(MONEY)

    @staticmethod
    def _estimated_months_to_completion(payload: dict[str, Any], current: Decimal) -> int | None:
        planned = Decimal(payload.get("planned_monthly_contribution", "0"))
        if planned <= ZERO:
            return None
        remaining = max(ZERO, Decimal(payload["target_amount"]) - current)
        return (
            int((remaining / planned).to_integral_value(rounding=ROUND_CEILING)) if remaining else 0
        )

    @classmethod
    def _estimated_completion_date(cls, payload: dict[str, Any], current: Decimal) -> date | None:
        months = cls._estimated_months_to_completion(payload, current)
        return date.today() + timedelta(days=months * 30) if months is not None else None

    def simulate(
        self, target: Decimal, current: Decimal, monthly: Decimal, months: int
    ) -> dict[str, Any]:
        return simulate_savings(target, current, monthly, months)

    def simulate_rent_choice(
        self,
        current_monthly_housing_cost: Decimal,
        alternative_monthly_housing_cost: Decimal,
        one_time_moving_cost: Decimal,
        months: int,
    ) -> dict[str, Any]:
        return simulate_rent_choice(
            current_monthly_housing_cost,
            alternative_monthly_housing_cost,
            one_time_moving_cost,
            months,
        )

    def create_record(
        self, session: Session, user_id: UUID, body: HousingRecordCreate
    ) -> dict[str, Any]:
        if body.private_document_id:
            document = session.scalar(
                select(PrivateDocument).where(
                    PrivateDocument.id == body.private_document_id,
                    PrivateDocument.owner_user_id == user_id,
                )
            )
            if document is None:
                raise ApiError(
                    404, "private_receipt_not_found", "Choose a private document in your account."
                )
        payload = body.model_dump(mode="json") | {
            "evidence": "user_entered",
            "payment_status": "not_confirmed_by_homescout",
        }
        row = HousingFinancialRecord(
            owner_user_id=user_id,
            encrypted_data=self.cipher.encrypt(user_id, payload),
        )
        session.add(row)
        session.flush()
        profile = self._profile_payload(session, user_id)
        self._maybe_budget_alert(session, user_id, profile, assess_finances(profile))
        session.commit()
        return self._record_view(row)

    def list_records(self, session: Session, user_id: UUID) -> list[dict[str, Any]]:
        return [self._record_view(row) for row in self.data.records(session, user_id)]

    def delete_record(self, session: Session, user_id: UUID, record_id: UUID) -> None:
        row = session.scalar(
            select(HousingFinancialRecord).where(
                HousingFinancialRecord.id == record_id,
                HousingFinancialRecord.owner_user_id == user_id,
            )
        )
        if row is None:
            raise self.not_found()
        session.delete(row)
        session.commit()

    def _record_view(self, row: HousingFinancialRecord) -> dict[str, Any]:
        return self.cipher.decrypt(row.owner_user_id, row.encrypted_data) | {
            "id": row.id,
            "recorded_at": row.created_at,
            "evidence": "user_entered",
        }

    def list_rent_obligations(self, session: Session, user_id: UUID) -> list[dict[str, Any]]:
        return [
            self._rent_obligation_view(session, user_id, row)
            for row in self.data.rent_obligations(session, user_id)
        ]

    def create_rent_obligation(
        self, session: Session, user_id: UUID, body: RentObligationCreate
    ) -> dict[str, Any]:
        if body.property_id:
            self._require_public_property(session, body.property_id)
        payload = body.model_dump(mode="json", exclude={"property_id"}) | {
            "currency": "KES",
            "source": "user_entered",
            "lease_verified": False,
            "payment_status": "not_confirmed_by_homescout",
        }
        row = RentObligation(
            owner_user_id=user_id,
            property_id=body.property_id,
            encrypted_data=self.cipher.encrypt(user_id, payload),
            due_date=body.due_date,
            status="open",
        )
        session.add(row)
        session.commit()
        return self._rent_obligation_view(session, user_id, row)

    def update_rent_obligation(
        self,
        session: Session,
        user_id: UUID,
        obligation_id: UUID,
        body: RentObligationUpdate,
    ) -> dict[str, Any]:
        row = self.data.rent_obligation(session, user_id, obligation_id)
        if row is None:
            raise self.not_found()
        if body.property_id:
            self._require_public_property(session, body.property_id)
        reported_total = sum(
            (
                Decimal(str(self.cipher.decrypt(user_id, item.encrypted_data)["amount_kes"]))
                for item in self.data.rent_payment_records(session, user_id, obligation_id)
            ),
            ZERO,
        )
        if body.amount_kes < reported_total:
            raise ApiError(
                409,
                "rent_obligation_below_reported_payments",
                (
                    "The reminder amount cannot be lower than payment amounts you have "
                    "already reported."
                ),
            )
        payload = body.model_dump(mode="json", exclude={"property_id", "status"}) | {
            "currency": "KES",
            "source": "user_entered",
            "lease_verified": False,
            "payment_status": "not_confirmed_by_homescout",
        }
        row.encrypted_data = self.cipher.encrypt(user_id, payload)
        row.property_id = body.property_id
        row.due_date = body.due_date
        row.status = body.status
        session.commit()
        return self._rent_obligation_view(session, user_id, row)

    def delete_rent_obligation(self, session: Session, user_id: UUID, obligation_id: UUID) -> None:
        row = self.data.rent_obligation(session, user_id, obligation_id)
        if row is None:
            raise self.not_found()
        session.delete(row)
        session.commit()

    def create_rent_payment_report(
        self,
        session: Session,
        user_id: UUID,
        obligation_id: UUID,
        body: RentPaymentReportCreate,
    ) -> dict[str, Any]:
        existing = self.data.rent_payment_by_request(session, user_id, body.request_id)
        payload = body.model_dump(mode="json", exclude={"request_id"}) | {
            "report_status": "reported_by_user",
            "provider_confirmed": False,
            "money_moved_by_homescout": False,
        }
        if existing:
            existing_payload = self.cipher.decrypt(user_id, existing.encrypted_data)
            if existing.obligation_id != obligation_id or existing_payload != payload:
                raise ApiError(
                    409,
                    "rent_payment_request_reused",
                    "This request identifier was already used for a different rent record.",
                )
            return self._rent_obligation_view(
                session,
                user_id,
                self.data.rent_obligation(session, user_id, obligation_id),
            )

        obligation = session.scalar(
            select(RentObligation)
            .where(
                RentObligation.id == obligation_id,
                RentObligation.owner_user_id == user_id,
            )
            .with_for_update()
        )
        if obligation is None:
            raise self.not_found()
        if obligation.status != "open":
            raise ApiError(
                409, "rent_obligation_closed", "Reopen this rent item before adding a report."
            )
        obligation_payload = self.cipher.decrypt(user_id, obligation.encrypted_data)
        amount_due = Decimal(str(obligation_payload["amount_kes"]))
        current_total = sum(
            (
                Decimal(str(self.cipher.decrypt(user_id, item.encrypted_data)["amount_kes"]))
                for item in self.data.rent_payment_records(session, user_id, obligation_id)
            ),
            ZERO,
        )
        if body.amount_kes > amount_due - current_total:
            raise ApiError(
                409,
                "rent_report_exceeds_balance",
                "The amount is higher than the remaining balance in this rent item.",
            )

        row = RentPaymentRecord(
            owner_user_id=user_id,
            obligation_id=obligation_id,
            request_id=body.request_id,
            encrypted_data=self.cipher.encrypt(user_id, payload),
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            repeated = self.data.rent_payment_by_request(session, user_id, body.request_id)
            if repeated and repeated.obligation_id == obligation_id:
                repeated_payload = self.cipher.decrypt(user_id, repeated.encrypted_data)
                if repeated_payload == payload:
                    return self._rent_obligation_view(
                        session,
                        user_id,
                        self.data.rent_obligation(session, user_id, obligation_id),
                    )
            raise ApiError(
                409, "rent_payment_conflict", "That rent payment report could not be saved twice."
            ) from error
        return self._rent_obligation_view(session, user_id, obligation)

    def delete_rent_payment_report(self, session: Session, user_id: UUID, record_id: UUID) -> None:
        row = self.data.rent_payment_record(session, user_id, record_id)
        if row is None:
            raise self.not_found()
        session.delete(row)
        session.commit()

    def _rent_obligation_view(
        self, session: Session, user_id: UUID, row: RentObligation | None
    ) -> dict[str, Any]:
        if row is None:
            raise self.not_found()
        payload = self.cipher.decrypt(user_id, row.encrypted_data)
        payment_rows = self.data.rent_payment_records(session, user_id, row.id)
        payments = [
            self.cipher.decrypt(user_id, payment.encrypted_data)
            | {"id": payment.id, "recorded_at": payment.created_at}
            for payment in payment_rows
        ]
        amount_due = Decimal(str(payload["amount_kes"]))
        reported_total = sum(
            (Decimal(str(payment["amount_kes"])) for payment in payments), ZERO
        ).quantize(MONEY)
        remaining = max(ZERO, amount_due - reported_total).quantize(MONEY)
        if reported_total == ZERO:
            report_state = "no_payment_reported"
        elif remaining == ZERO:
            report_state = "amount_fully_reported_not_verified"
        else:
            report_state = "partial_payment_reported_not_verified"
        return payload | {
            "id": row.id,
            "property_id": row.property_id,
            "due_date": row.due_date,
            "status": row.status,
            "reported_total_kes": reported_total,
            "remaining_based_on_reports_kes": remaining,
            "payment_report_state": report_state,
            "payments": payments,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def _require_public_property(session: Session, property_id: UUID) -> Property:
        row = session.scalar(
            select(Property).where(
                Property.id == property_id,
                Property.listing_status == "published",
                Property.availability_status == "available",
                Property.moderation_status == "clear",
                Property.is_demo.is_(False),
            )
        )
        if row is None:
            raise ApiError(404, "property_not_found", "The published property was not found.")
        return row

    def lessons(self, session: Session, user_id: UUID) -> dict[str, Any]:
        progress = {row.lesson_slug: row for row in self.data.lesson_progress(session, user_id)}
        return {
            "items": [
                public_lesson(lesson)
                | {
                    "progress": (
                        {
                            "best_score": progress[lesson["slug"]].best_score,
                            "attempts": progress[lesson["slug"]].attempts,
                            "completed_at": progress[lesson["slug"]].completed_at,
                        }
                        if lesson["slug"] in progress
                        else None
                    )
                }
                for lesson in LESSONS
            ],
            "completed_count": sum(1 for item in progress.values() if item.completed_at),
            "achievement": "Housing basics learner"
            if any(item.completed_at for item in progress.values())
            else None,
        }

    def submit_quiz(
        self, session: Session, user_id: UUID, slug: str, answers: list[int]
    ) -> dict[str, Any]:
        lesson = next((item for item in LESSONS if item["slug"] == slug), None)
        if lesson is None:
            raise self.not_found()
        quiz = lesson["quiz"]
        if len(answers) != 1:
            raise ApiError(
                422, "invalid_quiz_answers", "Answer the single question shown for this lesson."
            )
        score = 100 if answers[0] == quiz["correct"] else 0
        row = session.scalar(
            select(FinancialLessonProgress).where(
                FinancialLessonProgress.user_id == user_id,
                FinancialLessonProgress.lesson_slug == slug,
            )
        )
        now = datetime.now(UTC)
        if row is None:
            row = FinancialLessonProgress(
                user_id=user_id,
                lesson_slug=slug,
                best_score=score,
                attempts=1,
                completed_at=now if score == 100 else None,
            )
            session.add(row)
        else:
            row.attempts += 1
            row.best_score = max(row.best_score, score)
            if score == 100 and row.completed_at is None:
                row.completed_at = now
        session.commit()
        return {
            "score": score,
            "correct": score == 100,
            "explanation": quiz["explanation"],
            "completed": row.completed_at is not None,
            "attempts": row.attempts,
        }

    def create_comparison(
        self, session: Session, user_id: UUID, body: TrueCostComparisonCreate
    ) -> dict[str, Any]:
        properties = self._comparison_properties(session, body.property_ids)
        if len(properties) != len(body.property_ids):
            raise ApiError(
                422,
                "comparison_requires_live_properties",
                "Compare currently available, non-demo listings only.",
            )
        payload = {
            "title": body.title,
            "property_ids": [str(item) for item in body.property_ids],
            "monthly_costs": {
                key: {name: str(value) for name, value in costs.items()}
                for key, costs in body.additional_monthly_costs.items()
            },
            "one_time_costs": {
                key: {name: str(value) for name, value in costs.items()}
                for key, costs in body.one_time_costs.items()
            },
            "properties": [self._property_snapshot(item) for item in properties],
        }
        row = TrueCostComparison(
            owner_user_id=user_id,
            encrypted_data=self.cipher.encrypt(user_id, payload),
        )
        session.add(row)
        session.commit()
        return self._comparison_view(row)

    def list_comparisons(self, session: Session, user_id: UUID) -> list[dict[str, Any]]:
        rows = self.data.comparisons(session, user_id)
        for row in rows:
            self._detect_cost_changes(session, user_id, row)
        if rows:
            session.commit()
        return [self._comparison_view(row) for row in rows]

    def delete_comparison(self, session: Session, user_id: UUID, comparison_id: UUID) -> None:
        row = session.scalar(
            select(TrueCostComparison).where(
                TrueCostComparison.id == comparison_id,
                TrueCostComparison.owner_user_id == user_id,
            )
        )
        if row is None:
            raise self.not_found()
        session.delete(row)
        session.commit()

    def _comparison_view(self, row: TrueCostComparison) -> dict[str, Any]:
        payload = self.cipher.decrypt(row.owner_user_id, row.encrypted_data)
        monthly = payload["monthly_costs"]
        one_time = payload["one_time_costs"]
        results = []
        for prop in payload["properties"]:
            pid = prop["id"]
            extra_monthly = sum((Decimal(value) for value in monthly.get(pid, {}).values()), ZERO)
            move_once = sum((Decimal(value) for value in one_time.get(pid, {}).values()), ZERO)
            rent = Decimal(prop["monthly_rent"])
            entered_monthly = monthly.get(pid, {})
            entered_one_time = one_time.get(pid, {})
            missing_monthly = sorted(
                {
                    "utilities",
                    "water",
                    "electricity",
                    "gas",
                    "waste_collection",
                    "transport",
                    "internet",
                    "parking",
                    "other",
                }
                - set(entered_monthly)
            )
            missing_one_time = sorted(
                {"moving", "agent_fee", "furniture", "essentials", "other"} - set(entered_one_time)
            )
            deposit = Decimal(prop["deposit"]) if prop.get("deposit") is not None else None
            known_move_in = rent + (deposit or ZERO) + move_once
            results.append(
                {
                    "property_id": pid,
                    "title": prop["title"],
                    "location": prop["location"],
                    "monthly_rent": rent,
                    "deposit": deposit,
                    "deposit_evidence": "listing" if deposit is not None else "not_provided",
                    "monthly_costs": {"rent": rent}
                    | {name: Decimal(value) for name, value in entered_monthly.items()},
                    "total_monthly_cost": (rent + extra_monthly).quantize(MONEY),
                    "known_monthly_cost_subtotal": (rent + extra_monthly).quantize(MONEY),
                    "missing_monthly_cost_categories": missing_monthly,
                    "is_total_monthly_cost_complete": not missing_monthly,
                    "user_entered_move_in_costs": move_once.quantize(MONEY),
                    "known_move_in_cost_subtotal": known_move_in.quantize(MONEY),
                    "missing_move_in_cost_categories": (
                        ([] if deposit is not None else ["deposit"]) + missing_one_time
                    ),
                    "is_total_move_in_cost_complete": deposit is not None and not missing_one_time,
                    "listing_rent_frequency": prop["rent_frequency"],
                    "rent_source": "current listing; confirm with the provider",
                }
            )
        return {
            "id": row.id,
            "title": payload["title"],
            "properties": results,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "disclaimer": (
                "Monthly and move-in figures are known-cost subtotals until all listed missing "
                "categories are entered. Unprovided costs are not treated as zero. Confirm costs "
                "with the property contact."
            ),
        }

    def _detect_cost_changes(
        self, session: Session, user_id: UUID, row: TrueCostComparison
    ) -> None:
        payload = self.cipher.decrypt(user_id, row.encrypted_data)
        current = {
            str(item.id): item
            for item in self._comparison_properties(
                session, [UUID(pid) for pid in payload["property_ids"]]
            )
        }
        for snapshot in payload["properties"]:
            prop = current.get(snapshot["id"])
            if prop is None:
                continue
            new_rent = self._monthly_rent(prop)
            old_rent = Decimal(snapshot["monthly_rent"])
            new_deposit = str(prop.deposit_amount) if prop.deposit_amount is not None else None
            old_deposit = snapshot.get("deposit")
            if new_rent != old_rent or new_deposit != old_deposit:
                change_key = (
                    f"property-cost:{row.id}:{prop.id}:{new_rent}:{new_deposit or 'unknown'}"
                )
                self._alert(
                    session,
                    user_id,
                    change_key,
                    "A compared listing cost changed",
                    f"{prop.title} now shows monthly rent KSh {new_rent}; "
                    "review the listing before deciding.",
                    {
                        "comparison_id": str(row.id),
                        "property_id": str(prop.id),
                        "old_rent": str(old_rent),
                        "new_rent": str(new_rent),
                        "old_deposit": old_deposit,
                        "new_deposit": new_deposit,
                    },
                )

    def utility_estimate(
        self,
        values: list[Decimal] | None,
        by_category: dict[str, Decimal],
    ) -> dict[str, Any]:
        historical = utility_summary(values) if values else None
        total = sum(by_category.values(), ZERO)
        result = {
            "history_summary": historical,
            "monthly_by_category": {
                category: amount.quantize(MONEY) for category, amount in by_category.items()
            },
            "monthly_total": total.quantize(MONEY),
            "evidence": "estimated_from_user_entered_amounts",
            "disclaimer": (
                "Category amounts are your estimates. Historical summaries use only "
                "amounts you entered; these are not provider quotes or future bills."
            ),
        }
        if historical:
            result.update(historical)
        return result

    def create_lease(
        self, session: Session, user_id: UUID, body: LeaseGuardianCreate
    ) -> dict[str, Any]:
        payload = body.model_dump(mode="json")
        row = LeaseGuardianRecord(
            owner_user_id=user_id,
            property_id=body.property_id,
            encrypted_data=self.cipher.encrypt(user_id, payload),
        )
        session.add(row)
        session.commit()
        return self._lease_view(row)

    def list_leases(self, session: Session, user_id: UUID) -> list[dict[str, Any]]:
        return [self._lease_view(row) for row in self.data.leases(session, user_id)]

    def update_lease(
        self, session: Session, user_id: UUID, lease_id: UUID, body: LeaseGuardianUpdate
    ) -> dict[str, Any]:
        row = session.scalar(
            select(LeaseGuardianRecord).where(
                LeaseGuardianRecord.id == lease_id,
                LeaseGuardianRecord.owner_user_id == user_id,
            )
        )
        if row is None:
            raise self.not_found()
        payload = self.cipher.decrypt(user_id, row.encrypted_data)
        for key, value in body.model_dump(mode="json", exclude_unset=True).items():
            if value is not None or key in {
                "lease_start",
                "lease_end",
                "monthly_rent",
                "deposit_amount",
                "obligations",
                "private_notes",
            }:
                payload[key] = value
        if (
            payload.get("lease_start")
            and payload.get("lease_end")
            and payload["lease_end"] < payload["lease_start"]
        ):
            raise ApiError(
                422, "invalid_lease_dates", "Lease end date must be on or after the start date."
            )
        row.encrypted_data = self.cipher.encrypt(user_id, payload)
        session.commit()
        return self._lease_view(row)

    def delete_lease(self, session: Session, user_id: UUID, lease_id: UUID) -> None:
        row = session.scalar(
            select(LeaseGuardianRecord).where(
                LeaseGuardianRecord.id == lease_id,
                LeaseGuardianRecord.owner_user_id == user_id,
            )
        )
        if row is None:
            raise self.not_found()
        session.delete(row)
        session.commit()

    def _lease_view(self, row: LeaseGuardianRecord) -> dict[str, Any]:
        return self.cipher.decrypt(row.owner_user_id, row.encrypted_data) | {
            "id": row.id,
            "updated_at": row.updated_at,
            "disclaimer": NO_LEGAL_ADVICE,
        }

    def dashboard(self, session: Session, user_id: UUID) -> dict[str, Any]:
        assessment = self.assessment(session, user_id)
        profile = self._profile_payload(session, user_id)
        plans = self.list_plans(session, user_id)
        goals = self.list_goals(session, user_id)
        records = self.list_records(session, user_id)
        lessons = self.lessons(session, user_id)
        alerts = self.list_alerts(session, user_id)
        today = datetime.now(ZoneInfo("Africa/Nairobi")).date()
        current_month = today.strftime("%Y-%m")
        monthly_expenses = {}
        current_category_spend: dict[str, Decimal] = {}
        upcoming_expenses = []
        for item in records:
            category = item.get("category")
            if category == "receipt":
                continue
            if item.get("due_date"):
                due_date = date.fromisoformat(item["due_date"])
                if due_date >= today:
                    upcoming_expenses.append(
                        {
                            "id": item["id"],
                            "title": item["title"],
                            "category": category,
                            "amount": Decimal(item["amount"]).quantize(MONEY),
                            "due_date": due_date,
                            "evidence": "user_entered_plan",
                            "payment_confirmed": False,
                        }
                    )
                # A future-due item is a plan, never recorded spending or payment evidence.
                continue
            recorded_date = datetime.fromisoformat(item["record_date"].replace("Z", "+00:00"))
            local_date = recorded_date.astimezone(ZoneInfo("Africa/Nairobi")).date()
            month = local_date.strftime("%Y-%m")
            amount = Decimal(item["amount"])
            monthly_expenses[month] = monthly_expenses.get(month, ZERO) + amount
            if month == current_month:
                current_category_spend[category] = (
                    current_category_spend.get(category, ZERO) + amount
                )

        upcoming_expenses.sort(key=lambda item: (item["due_date"], item["title"].casefold()))
        upcoming_expenses = upcoming_expenses[:10]
        budget_categories = []
        for item in profile.get("budget_categories", []):
            category = item["category"]
            limit = Decimal(item["monthly_limit"]).quantize(MONEY)
            spent = current_category_spend.get(category, ZERO).quantize(MONEY)
            budget_categories.append(
                {
                    "category": category,
                    "monthly_limit": limit,
                    "recorded_this_month": spent,
                    "remaining": (limit - spent).quantize(MONEY),
                    "over_limit": spent > limit,
                }
            )
        budget_categories.sort(key=lambda item: item["category"])
        budget_total = sum((item["monthly_limit"] for item in budget_categories), ZERO).quantize(
            MONEY
        )
        recorded_budget_total = sum(
            (item["recorded_this_month"] for item in budget_categories), ZERO
        ).quantize(MONEY)
        income = Decimal(assessment["conservative_monthly_income"])
        remaining_balance = Decimal(assessment["monthly_surplus_or_deficit"])
        total_expenses = (income - remaining_balance).quantize(MONEY)
        insights = list(assessment["suggestions"])
        exceeded = [item for item in budget_categories if item["over_limit"]]
        if exceeded:
            insight = exceeded[0]
            insights.append(
                f"Your recorded {insight['category'].replace('_', ' ')} spending is "
                f"KSh {abs(insight['remaining'])} above its monthly limit."
            )
        elif not budget_categories:
            insights.append(
                "Add monthly category limits to track recorded spending against your plan."
            )
        if profile.get("monthly_utility_budget") is not None and not current_category_spend.get(
            "utilities"
        ):
            insights.append(
                f"No utility expense note is recorded for {current_month}; your housing "
                "estimate uses the monthly utility amount you entered."
            )
        if upcoming_expenses:
            item = upcoming_expenses[0]
            insights.append(
                f"You planned KSh {item['amount']} for {item['title']} on "
                f"{item['due_date'].isoformat()}. This is a reminder only, "
                "not a payment confirmation."
            )
        return {
            "assessment": assessment,
            "financial_overview": {
                "period": current_month,
                "estimated_monthly_income": income.quantize(MONEY),
                "estimated_monthly_expenses": total_expenses,
                "estimated_monthly_housing_expenditure": Decimal(
                    assessment["total_monthly_housing_cost"]
                ).quantize(MONEY),
                "estimated_monthly_remaining_balance": remaining_balance.quantize(MONEY),
                "affordability": assessment["affordability"],
                "basis": "saved_user_inputs_and_transparent_planning_calculation",
            },
            "monthly_budget": {
                "period": current_month,
                "monthly_limit_total": budget_total,
                "recorded_spending_in_budget_categories": recorded_budget_total,
                "categories": budget_categories,
                "basis": "user_entered_limits_and_private_manual_records",
            },
            "upcoming_expenses": upcoming_expenses,
            "insights": insights[:8],
            "move_in_plan_count": len(plans),
            "lowest_move_in_estimate": min(
                (item["total_move_in_cost"] for item in plans), default=None
            ),
            "savings_goals": goals,
            "expense_totals_by_month": monthly_expenses,
            "record_count": len(records),
            "comparison_count": len(self.data.comparisons(session, user_id)),
            "literacy_completed_count": lessons["completed_count"],
            "alerts": alerts[:5],
            "privacy_notice": (
                "Your financial profile and assessments are visible only to your signed-in account."
            ),
        }

    def budget_discovery(self, session: Session, user_id: UUID, limit: int = 30) -> dict[str, Any]:
        assessment = self.assessment(session, user_id)
        budget = assessment["suggested_monthly_budget"]
        statement = (
            select(Property)
            .options(
                joinedload(Property.county),
                joinedload(Property.town),
                joinedload(Property.neighbourhood),
                selectinload(Property.media),
            )
            .where(
                Property.is_demo.is_(False),
                Property.listing_status == "published",
                Property.availability_status == "available",
            )
            .order_by(Property.rent_amount.asc(), Property.id)
            .limit(250)
        )
        properties = list(session.scalars(statement).unique())
        matches = [prop for prop in properties if self._monthly_rent(prop) <= budget]
        return {
            "suggested_monthly_budget": budget,
            "items": [
                {
                    "id": prop.id,
                    "title": prop.title,
                    "rent_amount": self._monthly_rent(prop),
                    "currency": "KES",
                    "rent_frequency": "monthly_equivalent",
                    "location": ", ".join(
                        part
                        for part in [
                            getattr(prop.neighbourhood, "name", None),
                            getattr(prop.town, "name", None),
                            getattr(prop.county, "name", None),
                        ]
                        if part
                    ),
                    "bedrooms": prop.bedrooms,
                    "verification_status": prop.verification_status,
                    "image_url": next(
                        (
                            media.url
                            for media in prop.media
                            if media.media_type == "image" and not media.is_illustrative
                        ),
                        None,
                    ),
                    "why_recommended": (
                        "Current available listing rent is at or below your "
                        "suggested monthly budget."
                    ),
                }
                for prop in matches[: max(1, min(limit, 60))]
            ],
            "result_count": min(len(matches), max(1, min(limit, 60))),
            "private": True,
            "disclaimer": NOT_CREDIT,
        }

    def _comparison_properties(self, session: Session, ids: list[UUID]) -> list[Property]:
        if not ids:
            return []
        statement = (
            select(Property)
            .options(
                joinedload(Property.county),
                joinedload(Property.town),
                joinedload(Property.neighbourhood),
                selectinload(Property.media),
            )
            .where(
                Property.id.in_(ids),
                Property.is_demo.is_(False),
                Property.listing_status == "published",
                Property.availability_status == "available",
            )
        )
        return list(session.scalars(statement).unique())

    @staticmethod
    def _public_property(session: Session, property_id: UUID) -> Property | None:
        return session.scalar(
            select(Property)
            .options(
                joinedload(Property.county),
                joinedload(Property.town),
                joinedload(Property.neighbourhood),
            )
            .where(
                Property.id == property_id,
                Property.is_demo.is_(False),
                Property.listing_status == "published",
                Property.availability_status == "available",
            )
        )

    @staticmethod
    def _monthly_rent(prop: Property) -> Decimal:
        amount = Decimal(prop.rent_amount)
        factor = {
            "daily": Decimal(365) / Decimal(12),
            "weekly": Decimal(52) / Decimal(12),
            "monthly": Decimal(1),
        }[prop.rent_frequency]
        return (amount * factor).quantize(MONEY)

    def _property_snapshot(self, prop: Property) -> dict[str, Any]:
        return {
            "id": str(prop.id),
            "title": prop.title,
            "location": ", ".join(
                part
                for part in [
                    getattr(prop.neighbourhood, "name", None),
                    getattr(prop.town, "name", None),
                    getattr(prop.county, "name", None),
                ]
                if part
            ),
            "monthly_rent": str(self._monthly_rent(prop)),
            "deposit": str(prop.deposit_amount) if prop.deposit_amount is not None else None,
            "rent_frequency": prop.rent_frequency,
        }

    def list_alerts(self, session: Session, user_id: UUID) -> list[dict[str, Any]]:
        self._goal_deadline_alerts(session, user_id)
        rows = self.data.alerts(session, user_id)
        if rows:
            session.commit()
        return [
            self.cipher.decrypt(user_id, row.encrypted_data)
            | {
                "id": row.id,
                "created_at": row.created_at,
                "read_at": row.read_at,
                "is_read": row.read_at is not None,
            }
            for row in rows
        ]

    def mark_alert_read(self, session: Session, user_id: UUID, alert_id: UUID) -> dict[str, Any]:
        row = session.scalar(
            select(FinanceAlert).where(
                FinanceAlert.id == alert_id, FinanceAlert.owner_user_id == user_id
            )
        )
        if row is None:
            raise self.not_found()
        row.read_at = row.read_at or datetime.now(UTC)
        session.commit()
        return self.cipher.decrypt(user_id, row.encrypted_data) | {
            "id": row.id,
            "created_at": row.created_at,
            "read_at": row.read_at,
            "is_read": True,
        }

    def _maybe_budget_alert(
        self, session: Session, user_id: UUID, profile: dict[str, Any], assessment: dict[str, Any]
    ) -> None:
        budget = Decimal(str(profile.get("target_monthly_rent", 0)))
        conservative_income = Decimal(str(assessment["conservative_monthly_income"]))
        if budget > ZERO and budget > Decimal(str(assessment["suggested_monthly_budget"])):
            self._alert(
                session,
                user_id,
                f"budget-exceeded:{budget}:{conservative_income}",
                "Your rent target is above your suggested budget",
                f"Your entered target is KSh {budget}; your current planning "
                f"estimate is KSh {assessment['suggested_monthly_budget']}. "
                "Review your assumptions.",
                {
                    "target_monthly_rent": str(budget),
                    "suggested_monthly_budget": str(assessment["suggested_monthly_budget"]),
                },
            )

    def _goal_milestone_alert(
        self, session: Session, goal: SavingsGoal, view: dict[str, Any]
    ) -> None:
        percent = int(view["progress_percent"])
        milestone = (percent // 25) * 25
        if milestone >= 25:
            self._alert(
                session,
                goal.owner_user_id,
                f"savings-milestone:{goal.id}:{milestone}",
                "A moving-goal milestone was reached",
                f"{view['title']} is {milestone}% of its manually tracked target.",
                {"goal_id": str(goal.id), "milestone_percent": milestone},
            )

    def _goal_deadline_alerts(self, session: Session, user_id: UUID) -> None:
        for row in self.data.accessible_goals(session, user_id):
            if row.owner_user_id != user_id or row.status != "open":
                continue
            payload = self.cipher.decrypt(row.owner_user_id, row.encrypted_data)
            deadline = payload.get("target_date")
            if deadline and date.today() <= date.fromisoformat(
                deadline
            ) <= date.today() + timedelta(days=7):
                self._alert(
                    session,
                    user_id,
                    f"goal-reminder:{row.id}:{deadline}",
                    "A moving-goal date is coming up",
                    f"Review your virtual tracker for {payload['title']} before {deadline}.",
                    {"goal_id": str(row.id), "target_date": deadline},
                )

    def _alert(
        self,
        session: Session,
        owner_id: UUID,
        key: str,
        title: str,
        message: str,
        details: dict[str, Any],
    ) -> None:
        # alert_key is indexed for idempotency, so never store user-entered amounts in it.
        safe_key = hashlib.sha256(key.encode("utf-8")).hexdigest()
        existing = session.scalar(
            select(FinanceAlert).where(
                FinanceAlert.owner_user_id == owner_id, FinanceAlert.alert_key == safe_key
            )
        )
        if existing is None:
            session.add(
                FinanceAlert(
                    owner_user_id=owner_id,
                    alert_key=safe_key,
                    encrypted_data=self.cipher.encrypt(
                        owner_id, {"title": title, "message": message, "details": details}
                    ),
                )
            )
