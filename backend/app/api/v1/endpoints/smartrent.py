"""Authenticated SmartRent APIs; finance records are private by default."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db, get_settings
from app.core.config import Settings
from app.schemas.smartrent import (
    FinanceAssessmentResponse,
    FinanceProfileInput,
    FinancialLessonQuizRequest,
    HousingRecordCreate,
    LeaseGuardianCreate,
    LeaseGuardianUpdate,
    MoveInPlanCreate,
    MoveInPlanUpdate,
    RentChoiceSimulationRequest,
    RentObligationCreate,
    RentObligationUpdate,
    RentPaymentReportCreate,
    SavingsContributionCreate,
    SavingsGoalCreate,
    SavingsGoalShareCreate,
    SavingsGoalUpdate,
    SavingsSimulationRequest,
    TrueCostComparisonCreate,
    UtilityEstimateRequest,
)
from app.services.authentication import AuthenticatedPrincipal
from app.services.smartrent import SmartRentService

router = APIRouter(prefix="/finance", tags=["SmartRent housing finance"])


def get_smartrent_service(settings: Annotated[Settings, Depends(get_settings)]) -> SmartRentService:
    return SmartRentService(settings)


Service = Annotated[SmartRentService, Depends(get_smartrent_service)]
Principal = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]
Database = Annotated[Session, Depends(get_db)]


@router.get("/capabilities")
def capabilities() -> dict[str, object]:
    names = [
        ("RentScore", "available", "Explainable planning index; not a credit score."),
        ("Budget coach", "rule_based_preview", "No AI provider is connected."),
        ("Move-in planner", "available", "Private KES estimates with evidence labels."),
        ("Savings vault", "virtual_tracker", "No money is held or transferred."),
        ("True cost comparison", "available", "Current listings and user-entered extras."),
        (
            "Rental fraud protection",
            "education_only",
            "Lessons and reminders; no fraud detection service.",
        ),
        ("Literacy academy", "available", "Lessons, quizzes, and progress."),
        (
            "Rent-to-savings simulator",
            "available",
            "Deterministic rent-choice and savings projections from user inputs.",
        ),
        (
            "Income source modeling",
            "available",
            "Annual, daily, weekly, twice-monthly, monthly, and additional income sources.",
        ),
        ("Irregular income mode", "available", "Conservative calculations from entered income."),
        ("Affordability without a payslip", "available", "A payslip is optional."),
        (
            "Financial health check",
            "available",
            "Private readiness planning, not creditworthiness.",
        ),
        ("Budget-based discovery", "available", "Private filter over public available listings."),
        ("Shared moving goals", "available", "Explicitly shared virtual goals only."),
        ("Utility predictor", "user_entries_only", "Summarizes entries; no provider quotes."),
        ("Expense organizer", "available", "Private manually entered housing records."),
        ("Financial dashboard", "available", "Private summary of SmartRent records."),
        ("Housing cost alerts", "in_app_only", "No push or email delivery."),
        ("Rent payment record", "manual_record_only", "Does not confirm or process payments."),
        ("Lease and deposit guardian", "organizer_only", "Not legal advice."),
        (
            "Financial AI interface",
            "preview_only",
            "No model/provider or automated advice is connected.",
        ),
    ]
    return {
        "product": "HomeScout SmartRent",
        "items": [{"name": n, "status": s, "description": d} for n, s, d in names],
    }


@router.get("/dashboard")
def dashboard(principal: Principal, session: Database, service: Service) -> dict[str, object]:
    return service.dashboard(session, principal.user_id)


@router.get("/profile")
def get_profile(principal: Principal, session: Database, service: Service) -> dict[str, object]:
    return service.profile_response(session, principal.user_id)


@router.put("/profile")
def put_profile(
    body: FinanceProfileInput, principal: Principal, session: Database, service: Service
) -> dict[str, object]:
    return service.save_profile(session, principal.user_id, body)


@router.post("/assessment/preview", response_model=FinanceAssessmentResponse)
def preview_assessment(
    body: FinanceProfileInput, principal: Principal, service: Service
) -> dict[str, object]:
    """Return an assessment for entered figures without storing them."""
    del principal
    return service.preview_assessment(body)


@router.get("/assessment")
@router.get("/rent-score")
@router.get("/health-check")
def assessment(principal: Principal, session: Database, service: Service) -> dict[str, object]:
    return service.assessment(session, principal.user_id)


@router.post("/coach")
def budget_coach(principal: Principal, session: Database, service: Service) -> dict[str, object]:
    return service.coach(session, principal.user_id)


@router.get("/discovery")
def discovery(
    principal: Principal, session: Database, service: Service, limit: int = 30
) -> dict[str, object]:
    return service.budget_discovery(session, principal.user_id, limit)


@router.get("/move-in/plans")
def plans(principal: Principal, session: Database, service: Service) -> list[dict[str, object]]:
    return service.list_plans(session, principal.user_id)


@router.post("/move-in/plans", status_code=201)
def create_plan(
    body: MoveInPlanCreate, principal: Principal, session: Database, service: Service
) -> dict[str, object]:
    return service.create_plan(session, principal.user_id, body)


@router.patch("/move-in/plans/{plan_id}")
def update_plan(
    plan_id: UUID, body: MoveInPlanUpdate, principal: Principal, session: Database, service: Service
) -> dict[str, object]:
    return service.update_plan(session, principal.user_id, plan_id, body)


@router.delete("/move-in/plans/{plan_id}", status_code=204)
def delete_plan(
    plan_id: UUID, principal: Principal, session: Database, service: Service
) -> Response:
    service.delete_plan(session, principal.user_id, plan_id)
    return Response(status_code=204)


@router.get("/savings/goals")
def goals(principal: Principal, session: Database, service: Service) -> list[dict[str, object]]:
    return service.list_goals(session, principal.user_id)


@router.post("/savings/goals", status_code=201)
def create_goal(
    body: SavingsGoalCreate, principal: Principal, session: Database, service: Service
) -> dict[str, object]:
    return service.create_goal(session, principal.user_id, body)


@router.patch("/savings/goals/{goal_id}")
def update_goal(
    goal_id: UUID,
    body: SavingsGoalUpdate,
    principal: Principal,
    session: Database,
    service: Service,
) -> dict[str, object]:
    return service.update_goal(session, principal.user_id, goal_id, body)


@router.delete("/savings/goals/{goal_id}", status_code=204)
def delete_goal(
    goal_id: UUID, principal: Principal, session: Database, service: Service
) -> Response:
    service.delete_goal(session, principal.user_id, goal_id)
    return Response(status_code=204)


@router.post("/savings/goals/{goal_id}/contributions", status_code=201)
def contribute(
    goal_id: UUID,
    body: SavingsContributionCreate,
    principal: Principal,
    session: Database,
    service: Service,
) -> dict[str, object]:
    return service.contribute(session, principal.user_id, goal_id, body)


@router.get("/savings/goals/{goal_id}/contributions")
def contributions(
    goal_id: UUID, principal: Principal, session: Database, service: Service
) -> list[dict[str, object]]:
    return service.goal_contributions(session, principal.user_id, goal_id)


@router.post("/savings/goals/{goal_id}/shares", status_code=201)
def share_goal(
    goal_id: UUID,
    body: SavingsGoalShareCreate,
    principal: Principal,
    session: Database,
    service: Service,
) -> dict[str, object]:
    return service.share_goal(session, principal.user_id, goal_id, body)


@router.delete("/savings/goals/{goal_id}/shares/{member_id}", status_code=204)
def unshare_goal(
    goal_id: UUID, member_id: UUID, principal: Principal, session: Database, service: Service
) -> Response:
    service.unshare_goal(session, principal.user_id, goal_id, member_id)
    return Response(status_code=204)


@router.post("/savings/simulate")
def simulate(
    body: SavingsSimulationRequest, principal: Principal, service: Service
) -> dict[str, object]:
    _ = principal
    return service.simulate(
        body.target_amount, body.current_savings, body.monthly_contribution, body.months
    )


@router.post("/rent-choice/simulate")
def simulate_rent_choice(
    body: RentChoiceSimulationRequest, principal: Principal, service: Service
) -> dict[str, object]:
    _ = principal
    return service.simulate_rent_choice(
        body.current_monthly_housing_cost,
        body.alternative_monthly_housing_cost,
        body.one_time_moving_cost,
        body.months,
    )


@router.get("/records")
def records(principal: Principal, session: Database, service: Service) -> list[dict[str, object]]:
    return service.list_records(session, principal.user_id)


@router.post("/records", status_code=201)
def create_record(
    body: HousingRecordCreate, principal: Principal, session: Database, service: Service
) -> dict[str, object]:
    return service.create_record(session, principal.user_id, body)


@router.delete("/records/{record_id}", status_code=204)
def delete_record(
    record_id: UUID, principal: Principal, session: Database, service: Service
) -> Response:
    service.delete_record(session, principal.user_id, record_id)
    return Response(status_code=204)


@router.get("/rent-obligations")
def rent_obligations(
    principal: Principal, session: Database, service: Service
) -> list[dict[str, object]]:
    return service.list_rent_obligations(session, principal.user_id)


@router.post("/rent-obligations", status_code=201)
def create_rent_obligation(
    body: RentObligationCreate, principal: Principal, session: Database, service: Service
) -> dict[str, object]:
    return service.create_rent_obligation(session, principal.user_id, body)


@router.put("/rent-obligations/{obligation_id}")
def update_rent_obligation(
    obligation_id: UUID,
    body: RentObligationUpdate,
    principal: Principal,
    session: Database,
    service: Service,
) -> dict[str, object]:
    return service.update_rent_obligation(session, principal.user_id, obligation_id, body)


@router.delete("/rent-obligations/{obligation_id}", status_code=204)
def delete_rent_obligation(
    obligation_id: UUID, principal: Principal, session: Database, service: Service
) -> Response:
    service.delete_rent_obligation(session, principal.user_id, obligation_id)
    return Response(status_code=204)


@router.post("/rent-obligations/{obligation_id}/payments", status_code=201)
def create_rent_payment_report(
    obligation_id: UUID,
    body: RentPaymentReportCreate,
    principal: Principal,
    session: Database,
    service: Service,
) -> dict[str, object]:
    return service.create_rent_payment_report(session, principal.user_id, obligation_id, body)


@router.delete("/rent-payments/{record_id}", status_code=204)
def delete_rent_payment_report(
    record_id: UUID, principal: Principal, session: Database, service: Service
) -> Response:
    service.delete_rent_payment_report(session, principal.user_id, record_id)
    return Response(status_code=204)


@router.get("/lessons")
def lessons(principal: Principal, session: Database, service: Service) -> dict[str, object]:
    return service.lessons(session, principal.user_id)


@router.get("/lessons/progress")
def lesson_progress(
    principal: Principal, session: Database, service: Service
) -> list[dict[str, object]]:
    return [
        {
            "slug": row.lesson_slug,
            "best_score": row.best_score,
            "attempts": row.attempts,
            "completed_at": row.completed_at,
        }
        for row in service.data.lesson_progress(session, principal.user_id)
    ]


@router.post("/lessons/{slug}/quiz")
def submit_quiz(
    slug: str,
    body: FinancialLessonQuizRequest,
    principal: Principal,
    session: Database,
    service: Service,
) -> dict[str, object]:
    return service.submit_quiz(session, principal.user_id, slug, body.answers)


@router.get("/comparisons")
def comparisons(
    principal: Principal, session: Database, service: Service
) -> list[dict[str, object]]:
    return service.list_comparisons(session, principal.user_id)


@router.post("/comparisons", status_code=201)
def create_comparison(
    body: TrueCostComparisonCreate, principal: Principal, session: Database, service: Service
) -> dict[str, object]:
    return service.create_comparison(session, principal.user_id, body)


@router.delete("/comparisons/{comparison_id}", status_code=204)
def delete_comparison(
    comparison_id: UUID, principal: Principal, session: Database, service: Service
) -> Response:
    service.delete_comparison(session, principal.user_id, comparison_id)
    return Response(status_code=204)


@router.post("/utilities/estimate")
def estimate_utilities(
    body: UtilityEstimateRequest, principal: Principal, service: Service
) -> dict[str, object]:
    _ = principal
    return service.utility_estimate(body.monthly_user_entries, body.monthly_by_category)


@router.get("/lease-guardian")
def leases(principal: Principal, session: Database, service: Service) -> list[dict[str, object]]:
    return service.list_leases(session, principal.user_id)


@router.post("/lease-guardian", status_code=201)
def create_lease(
    body: LeaseGuardianCreate, principal: Principal, session: Database, service: Service
) -> dict[str, object]:
    return service.create_lease(session, principal.user_id, body)


@router.patch("/lease-guardian/{lease_id}")
def update_lease(
    lease_id: UUID,
    body: LeaseGuardianUpdate,
    principal: Principal,
    session: Database,
    service: Service,
) -> dict[str, object]:
    return service.update_lease(session, principal.user_id, lease_id, body)


@router.delete("/lease-guardian/{lease_id}", status_code=204)
def delete_lease(
    lease_id: UUID, principal: Principal, session: Database, service: Service
) -> Response:
    service.delete_lease(session, principal.user_id, lease_id)
    return Response(status_code=204)


@router.get("/alerts")
def alerts(principal: Principal, session: Database, service: Service) -> list[dict[str, object]]:
    return service.list_alerts(session, principal.user_id)


@router.post("/alerts/{alert_id}/read")
def mark_alert_read(
    alert_id: UUID, principal: Principal, session: Database, service: Service
) -> dict[str, object]:
    return service.mark_alert_read(session, principal.user_id, alert_id)
