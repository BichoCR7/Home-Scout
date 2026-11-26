"""Owner-scoped data access for SmartRent records."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

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


class SmartRentDataAccess:
    def profile(self, session: Session, user_id: UUID) -> FinanceProfile | None:
        return session.get(FinanceProfile, user_id)

    def plans(self, session: Session, user_id: UUID) -> list[MoveInPlan]:
        return list(
            session.scalars(
                select(MoveInPlan)
                .where(MoveInPlan.owner_user_id == user_id)
                .order_by(MoveInPlan.updated_at.desc())
                .limit(100)
            )
        )

    def goal(self, session: Session, goal_id: UUID) -> SavingsGoal | None:
        return session.get(SavingsGoal, goal_id)

    def accessible_goals(self, session: Session, user_id: UUID) -> list[SavingsGoal]:
        statement = (
            select(SavingsGoal)
            .outerjoin(SavingsGoalShare, SavingsGoalShare.goal_id == SavingsGoal.id)
            .where(
                or_(
                    SavingsGoal.owner_user_id == user_id,
                    SavingsGoalShare.shared_with_user_id == user_id,
                )
            )
            .order_by(SavingsGoal.updated_at.desc())
            .limit(100)
        )
        return list(session.scalars(statement).unique())

    def contributions(self, session: Session, goal_id: UUID) -> list[SavingsContribution]:
        return list(
            session.scalars(
                select(SavingsContribution)
                .where(SavingsContribution.goal_id == goal_id)
                .order_by(SavingsContribution.created_at.asc())
                .limit(500)
            )
        )

    def goal_shares(self, session: Session, goal_id: UUID) -> list[SavingsGoalShare]:
        return list(
            session.scalars(
                select(SavingsGoalShare)
                .where(SavingsGoalShare.goal_id == goal_id)
                .order_by(SavingsGoalShare.created_at.asc())
            )
        )

    def records(self, session: Session, user_id: UUID) -> list[HousingFinancialRecord]:
        return list(
            session.scalars(
                select(HousingFinancialRecord)
                .where(HousingFinancialRecord.owner_user_id == user_id)
                .order_by(HousingFinancialRecord.created_at.desc())
                .limit(500)
            )
        )

    def rent_obligations(self, session: Session, user_id: UUID) -> list[RentObligation]:
        return list(
            session.scalars(
                select(RentObligation)
                .where(RentObligation.owner_user_id == user_id)
                .order_by(RentObligation.due_date.asc(), RentObligation.created_at.desc())
                .limit(200)
            )
        )

    def rent_obligation(
        self, session: Session, user_id: UUID, obligation_id: UUID
    ) -> RentObligation | None:
        return session.scalar(
            select(RentObligation).where(
                RentObligation.id == obligation_id,
                RentObligation.owner_user_id == user_id,
            )
        )

    def rent_payment_records(
        self, session: Session, user_id: UUID, obligation_id: UUID | None = None
    ) -> list[RentPaymentRecord]:
        statement = select(RentPaymentRecord).where(RentPaymentRecord.owner_user_id == user_id)
        if obligation_id is not None:
            statement = statement.where(RentPaymentRecord.obligation_id == obligation_id)
        return list(
            session.scalars(statement.order_by(RentPaymentRecord.created_at.desc()).limit(500))
        )

    def rent_payment_by_request(
        self, session: Session, user_id: UUID, request_id: UUID
    ) -> RentPaymentRecord | None:
        return session.scalar(
            select(RentPaymentRecord).where(
                RentPaymentRecord.owner_user_id == user_id,
                RentPaymentRecord.request_id == request_id,
            )
        )

    def rent_payment_record(
        self, session: Session, user_id: UUID, record_id: UUID
    ) -> RentPaymentRecord | None:
        return session.scalar(
            select(RentPaymentRecord).where(
                RentPaymentRecord.id == record_id,
                RentPaymentRecord.owner_user_id == user_id,
            )
        )

    def lesson_progress(self, session: Session, user_id: UUID) -> list[FinancialLessonProgress]:
        return list(
            session.scalars(
                select(FinancialLessonProgress)
                .where(FinancialLessonProgress.user_id == user_id)
                .order_by(FinancialLessonProgress.updated_at.desc())
            )
        )

    def comparisons(self, session: Session, user_id: UUID) -> list[TrueCostComparison]:
        return list(
            session.scalars(
                select(TrueCostComparison)
                .where(TrueCostComparison.owner_user_id == user_id)
                .order_by(TrueCostComparison.updated_at.desc())
                .limit(100)
            )
        )

    def leases(self, session: Session, user_id: UUID) -> list[LeaseGuardianRecord]:
        return list(
            session.scalars(
                select(LeaseGuardianRecord)
                .where(LeaseGuardianRecord.owner_user_id == user_id)
                .order_by(LeaseGuardianRecord.updated_at.desc())
                .limit(100)
            )
        )

    def alerts(self, session: Session, user_id: UUID) -> list[FinanceAlert]:
        return list(
            session.scalars(
                select(FinanceAlert)
                .where(FinanceAlert.owner_user_id == user_id)
                .order_by(FinanceAlert.created_at.desc())
                .limit(100)
            )
        )
