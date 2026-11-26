"""Phase 8 SmartRent privacy, planning, records, learning, and goal workflows."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.core.errors import ApiError
from app.models.smartrent import FinanceProfile, HousingFinancialRecord, SavingsGoal
from app.services.finance_calculations import (
    assess_finances,
    monthly_income_amount,
    simulate_rent_choice,
    simulate_savings,
    utility_summary,
)
from app.services.smartrent import SmartRentService
from tests.helpers import create_authenticated_user
from tests.test_marketplace import _publish_listing


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _profile(**updates) -> dict[str, object]:
    return {
        "income_amount": 95000,
        "income_frequency": "monthly",
        "income_pattern": "variable",
        "recent_monthly_income": [80000, 90000, 95000],
        "monthly_expenses": 24000,
        "monthly_obligations": 8000,
        "current_savings": 30000,
        "target_monthly_rent": 35000,
        "expected_move_in_total": 70000,
        "monthly_utility_budget": 4500,
        "household_size": 2,
        "has_payslip": False,
        **updates,
    }


def test_planning_calculation_methods_are_deterministic_and_not_credit_decisions() -> None:
    assert monthly_income_amount(Decimal("5000"), "weekly") == Decimal("21666.67")
    result = assess_finances(
        {
            "income_amount": "100000",
            "income_frequency": "monthly",
            "income_pattern": "seasonal",
            "recent_monthly_income": [],
            "monthly_expenses": "25000",
            "monthly_obligations": "5000",
            "current_savings": "20000",
            "target_monthly_rent": "20000",
            "expected_move_in_total": "50000",
            "has_payslip": False,
        }
    )
    assert result["conservative_monthly_income"] == Decimal("65000.00")
    assert result["affordability"] == "stretch"
    assert result["readiness_index"] in range(101)
    assert "not a credit score" in result["disclaimer"]
    assert "automatic property eligibility rule" in result["disclaimer"]

    simulated = simulate_savings(Decimal("30000"), Decimal("5000"), Decimal("5000"), 5)
    assert simulated["projected_total"] == Decimal("30000.00")
    assert simulated["will_reach_target"] is True
    costs = utility_summary([Decimal("1000"), Decimal("4000"), Decimal("2000")])
    assert costs["median"] == Decimal("2000.00")
    assert costs["evidence"] == "estimated_from_user_entered_amounts"


def test_income_normalization_and_surplus_components_are_transparent() -> None:
    assert monthly_income_amount(Decimal("120000"), "annual") == Decimal("10000.00")
    assert monthly_income_amount(Decimal("1000"), "daily", work_days_per_week=3) == Decimal(
        "13000.00"
    )
    result = assess_finances(
        {
            "income_amount": "60000",
            "income_frequency": "monthly",
            "income_pattern": "steady",
            "recent_monthly_income": [],
            "additional_income_sources": [
                {"label": "Annual contract", "amount": "12000", "frequency": "annual"},
                {
                    "label": "Weekend shifts",
                    "amount": "1000",
                    "frequency": "daily",
                    "work_days_per_week": 3,
                },
            ],
            "monthly_expenses": "20000",
            "monthly_obligations": "5000",
            "current_savings": "10000",
            "target_monthly_rent": "18000",
            "monthly_utility_budget": "3000",
            "monthly_transport_cost": "4000",
            "monthly_housing_other_costs": "1000",
            "expected_move_in_total": "50000",
        }
    )
    assert result["monthly_income_before_conservative_adjustment"] == Decimal("74000.00")
    assert result["conservative_monthly_income"] == Decimal("74000.00")
    assert result["non_housing_committed_costs"] == Decimal("25000.00")
    assert result["housing_costs_excluding_rent"] == Decimal("8000.00")
    assert result["total_monthly_housing_cost"] == Decimal("26000.00")
    assert result["monthly_surplus_or_deficit"] == Decimal("23000.00")
    assert result["rent_to_income_percent"] == Decimal("24.32")
    assert len(result["income_source_breakdown"]) == 3


def test_rent_choice_simulator_accounts_for_move_cost_and_validates_inputs() -> None:
    result = simulate_rent_choice(Decimal("50000"), Decimal("42000"), Decimal("24000"), months=12)
    assert result["monthly_difference"] == Decimal("8000.00")
    assert result["break_even_month"] == 3
    assert result["net_savings_after_move_cost"] == Decimal("72000.00")
    assert result["is_lower_cost_over_period"] is True


def test_rentscore_includes_itemized_transport_and_housing_costs() -> None:
    result = assess_finances(
        _profile(
            monthly_expenses=20000,
            monthly_obligations=5000,
            monthly_utility_budget=4000,
            monthly_transport_cost=6000,
            monthly_housing_other_costs=2000,
            target_monthly_rent=25000,
        )
    )
    assert result["monthly_committed_costs"] == Decimal("37000.00")
    assert result["disposable_before_rent"] == Decimal("43000.00")
    assert result["remaining_after_target_rent"] == Decimal("18000.00")


def test_finance_profile_is_encrypted_owner_scoped_and_payslip_optional(client) -> None:
    owner = create_authenticated_user(
        client, role_code="tenant", email="finance-private@example.com"
    )
    other = create_authenticated_user(client, role_code="tenant", email="finance-other@example.com")
    owner_headers = _headers(owner)
    other_headers = _headers(other)

    saved = client.put("/api/v1/finance/profile", headers=owner_headers, json=_profile())
    assert saved.status_code == 200, saved.text
    assessment = client.get("/api/v1/finance/rent-score", headers=owner_headers)
    assert assessment.status_code == 200
    assert Decimal(assessment.json()["suggested_monthly_budget"]) > 0
    assert assessment.json()["disclaimer"].startswith("RentScore is a housing-planning index")
    assert (
        client.get("/api/v1/finance/profile", headers=other_headers).json()["is_configured"]
        is False
    )
    assert client.get("/api/v1/finance/records", headers=other_headers).json() == []

    me = client.get("/api/v1/auth/me", headers=owner_headers).json()
    row = client.app.state.session_factory()
    try:
        stored = row.get(FinanceProfile, UUID(me["id"]))
        assert stored is not None
        assert b"95000" not in stored.encrypted_data
        assert b"monthly_expenses" not in stored.encrypted_data
    finally:
        row.close()


def test_finance_assessment_preview_uses_same_rules_without_saving(client) -> None:
    token = create_authenticated_user(
        client, role_code="tenant", email="finance-preview@example.com"
    )
    headers = _headers(token)

    preview = client.post(
        "/api/v1/finance/assessment/preview",
        headers=headers,
        json=_profile(target_monthly_rent=24000),
    )

    assert preview.status_code == 200, preview.text
    result = preview.json()
    assert Decimal(result["conservative_monthly_income"]) == Decimal("80000.00")
    assert result["affordability"] == "comfortable"
    assert "not a credit score" in result["disclaimer"]
    assert client.get("/api/v1/finance/profile", headers=headers).json()["is_configured"] is False

    unauthenticated = client.post(
        "/api/v1/finance/assessment/preview", json=_profile(target_monthly_rent=24000)
    )
    assert unauthenticated.status_code == 401


def test_move_in_savings_sharing_and_manual_payment_records(client) -> None:
    owner = create_authenticated_user(client, role_code="tenant", email="goal-owner@example.com")
    member = create_authenticated_user(client, role_code="tenant", email="goal-member@example.com")
    owner_headers, member_headers = _headers(owner), _headers(member)
    member_id = client.get("/api/v1/auth/me", headers=member_headers).json()["id"]

    plan = client.post(
        "/api/v1/finance/move-in/plans",
        headers=owner_headers,
        json={
            "title": "Kilimani move",
            "rent_amount": 32000,
            "deposit_amount": 32000,
            "rent_evidence": "listing",
            "deposit_evidence": "estimated",
            "costs": [{"category": "moving", "amount": 8500, "evidence": "estimated"}],
        },
    )
    assert plan.status_code == 201, plan.text
    assert Decimal(plan.json()["total_move_in_cost"]) == Decimal("72500.00")
    assert plan.json()["rent_evidence"] == "listing"
    assert plan.json()["deposit_evidence"] == "estimated"
    updated_plan = client.patch(
        f"/api/v1/finance/move-in/plans/{plan.json()['id']}",
        headers=owner_headers,
        json={"title": "Updated move", "deposit_amount": 28000, "rent_evidence": "estimated"},
    )
    assert updated_plan.status_code == 200
    assert updated_plan.json()["rent_evidence"] == "estimated"
    assert client.get("/api/v1/finance/move-in/plans", headers=member_headers).json() == []

    goal = client.post(
        "/api/v1/finance/savings/goals",
        headers=owner_headers,
        json={
            "title": "Moving fund",
            "target_amount": 50000,
            "initial_saved_amount": 5000,
            "target_date": "2027-01-31",
            "description": "Private target",
        },
    )
    assert goal.status_code == 201, goal.text
    assert Decimal(goal.json()["initial_saved_amount"]) == Decimal("5000.00")
    assert Decimal(goal.json()["remaining_amount"]) == Decimal("45000.00")
    goal_id = goal.json()["id"]
    edited_goal = client.patch(
        f"/api/v1/finance/savings/goals/{goal_id}",
        headers=owner_headers,
        json={"title": "Updated moving fund", "target_amount": 60000, "target_date": None},
    )
    assert edited_goal.status_code == 200
    assert edited_goal.json()["title"] == "Updated moving fund"
    assert Decimal(edited_goal.json()["target_amount"]) == Decimal("60000")
    assert edited_goal.json()["target_date"] is None
    assert client.get("/api/v1/finance/savings/goals", headers=member_headers).json() == []
    denied = client.post(
        f"/api/v1/finance/savings/goals/{goal_id}/contributions",
        headers=member_headers,
        json={"amount": 1000},
    )
    assert denied.status_code == 404

    shared = client.post(
        f"/api/v1/finance/savings/goals/{goal_id}/shares",
        headers=owner_headers,
        json={"user_id": member_id, "can_contribute": True},
    )
    assert shared.status_code == 201
    visible = client.get("/api/v1/finance/savings/goals", headers=member_headers)
    assert len(visible.json()) == 1
    assert visible.json()[0]["is_virtual_tracker"] is True
    contribution = client.post(
        f"/api/v1/finance/savings/goals/{goal_id}/contributions",
        headers=member_headers,
        json={"amount": 12000, "notes": "Manual tracker entry", "request_id": str(uuid4())},
    )
    assert contribution.status_code == 201, contribution.text
    assert Decimal(contribution.json()["current_amount"]) == Decimal("17000.00")
    assert (
        len(
            client.get(
                f"/api/v1/finance/savings/goals/{goal_id}/contributions", headers=owner_headers
            ).json()
        )
        == 1
    )
    client.delete(
        f"/api/v1/finance/savings/goals/{goal_id}/shares/{member_id}", headers=owner_headers
    )
    assert client.get("/api/v1/finance/savings/goals", headers=member_headers).json() == []

    receipt = client.post(
        "/api/v1/hub/documents?category=receipt&filename=rent-receipt.pdf",
        headers={**owner_headers, "Content-Type": "application/octet-stream"},
        content=b"%PDF-1.4\nprivate receipt placeholder",
    )
    assert receipt.status_code == 201, receipt.text
    cross_account_receipt = client.post(
        "/api/v1/finance/records",
        headers=member_headers,
        json={
            "category": "receipt",
            "title": "Receipt should be private",
            "amount": 100,
            "record_date": "2026-11-05T10:00:00+03:00",
            "private_document_id": receipt.json()["id"],
        },
    )
    assert cross_account_receipt.status_code == 404
    record = client.post(
        "/api/v1/finance/records",
        headers=owner_headers,
        json={
            "category": "rent",
            "title": "November rent note",
            "amount": 32000,
            "record_date": "2026-11-05T10:00:00+03:00",
            "reference": "Manual note only",
            "payment_method": "bank_transfer",
            "notes": "Paid from my monthly housing budget",
            "private_document_id": receipt.json()["id"],
        },
    )
    assert record.status_code == 201
    assert record.json()["payment_status"] == "not_confirmed_by_homescout"
    assert record.json()["payment_method"] == "bank_transfer"
    assert record.json()["notes"] == "Paid from my monthly housing budget"
    assert len(client.get("/api/v1/finance/records", headers=owner_headers).json()) == 1
    invalid_method = client.post(
        "/api/v1/finance/records",
        headers=owner_headers,
        json={
            "category": "rent",
            "title": "Invalid payment channel",
            "amount": 100,
            "record_date": "2026-11-05T10:00:00+03:00",
            "payment_method": "crypto",
        },
    )
    assert invalid_method.status_code == 422

    session = client.app.state.session_factory()
    try:
        record_row = session.scalar(select(HousingFinancialRecord))
        goal_row = session.scalar(select(SavingsGoal))
        assert record_row is not None and b"November rent note" not in record_row.encrypted_data
        assert goal_row is not None and b"Moving fund" not in goal_row.encrypted_data
    finally:
        session.close()


def test_finance_dashboard_excludes_receipt_values_from_monthly_costs(client) -> None:
    owner = create_authenticated_user(client, role_code="tenant", email="finance-chart@example.com")
    headers = _headers(owner)
    for category, title in (("rent", "November rent note"), ("receipt", "Rent receipt copy")):
        response = client.post(
            "/api/v1/finance/records",
            headers=headers,
            json={
                "category": category,
                "title": title,
                "amount": 32000,
                "record_date": "2026-11-05T10:00:00+03:00",
            },
        )
        assert response.status_code == 201, response.text

    dashboard = client.get("/api/v1/finance/dashboard", headers=headers)
    assert dashboard.status_code == 200, dashboard.text
    assert Decimal(str(dashboard.json()["expense_totals_by_month"]["2026-11"])) == Decimal("32000")


def test_finance_dashboard_has_real_budget_totals_and_user_scheduled_expenses(client) -> None:
    owner = create_authenticated_user(
        client, role_code="tenant", email="finance-dashboard-v4@example.com"
    )
    headers = _headers(owner)
    now = datetime.now(ZoneInfo("Africa/Nairobi"))
    current_month_record = now.replace(day=1, hour=10, minute=0, second=0, microsecond=0)
    next_month_due = (now.date() + timedelta(days=35)).isoformat()

    saved_profile = client.put(
        "/api/v1/finance/profile",
        headers=headers,
        json=_profile(
            income_amount=100000,
            income_pattern="steady",
            recent_monthly_income=[],
            monthly_expenses=20000,
            monthly_obligations=5000,
            target_monthly_rent=30000,
            monthly_utility_budget=4000,
            monthly_transport_cost=5000,
            monthly_housing_other_costs=1000,
            budget_categories=[
                {"category": "rent", "monthly_limit": 35000},
                {"category": "utilities", "monthly_limit": 4000},
            ],
        ),
    )
    assert saved_profile.status_code == 200, saved_profile.text
    assert len(saved_profile.json()["budget_categories"]) == 2

    for category, title, amount in (
        ("rent", "Rent note", 30000),
        ("utilities", "Power bill note", 5000),
    ):
        response = client.post(
            "/api/v1/finance/records",
            headers=headers,
            json={
                "category": category,
                "title": title,
                "amount": amount,
                "record_date": current_month_record.isoformat(),
            },
        )
        assert response.status_code == 201, response.text

    planned = client.post(
        "/api/v1/finance/records",
        headers=headers,
        json={
            "category": "internet",
            "title": "Internet bill",
            "amount": 2500,
            "record_date": f"{next_month_due}T10:00:00+03:00",
            "due_date": next_month_due,
        },
    )
    assert planned.status_code == 201, planned.text

    dashboard = client.get("/api/v1/finance/dashboard", headers=headers)
    assert dashboard.status_code == 200, dashboard.text
    result = dashboard.json()
    overview = result["financial_overview"]
    assert Decimal(str(overview["estimated_monthly_income"])) == Decimal("100000.00")
    assert Decimal(str(overview["estimated_monthly_housing_expenditure"])) == Decimal("40000.00")
    assert Decimal(str(overview["estimated_monthly_remaining_balance"])) == Decimal("35000.00")
    assert Decimal(
        str(result["expense_totals_by_month"][current_month_record.strftime("%Y-%m")])
    ) == Decimal("35000")
    category_map = {item["category"]: item for item in result["monthly_budget"]["categories"]}
    assert Decimal(str(category_map["rent"]["remaining"])) == Decimal("5000.00")
    assert category_map["utilities"]["over_limit"] is True
    assert Decimal(str(category_map["utilities"]["remaining"])) == Decimal("-1000.00")
    assert len(result["upcoming_expenses"]) == 1
    assert result["upcoming_expenses"][0]["title"] == "Internet bill"
    assert result["upcoming_expenses"][0]["payment_confirmed"] is False
    assert any("above its monthly limit" in item for item in result["insights"])


def test_finance_record_removal_is_owner_scoped(client) -> None:
    owner = create_authenticated_user(
        client, role_code="tenant", email="finance-record-owner@example.com"
    )
    other = create_authenticated_user(
        client, role_code="tenant", email="finance-record-other@example.com"
    )
    headers, other_headers = _headers(owner), _headers(other)
    saved = client.post(
        "/api/v1/finance/records",
        headers=headers,
        json={
            "category": "expense",
            "title": "Household expense note",
            "amount": 1800,
            "record_date": datetime.now(ZoneInfo("Africa/Nairobi")).isoformat(),
        },
    )
    assert saved.status_code == 201, saved.text
    record_id = saved.json()["id"]

    forbidden = client.delete(f"/api/v1/finance/records/{record_id}", headers=other_headers)
    assert forbidden.status_code == 404
    assert len(client.get("/api/v1/finance/records", headers=headers).json()) == 1

    deleted = client.delete(f"/api/v1/finance/records/{record_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/v1/finance/records", headers=headers).json() == []


def test_finance_rejects_duplicate_budget_categories_and_receipt_due_dates(client) -> None:
    owner = create_authenticated_user(
        client, role_code="tenant", email="finance-budget-validation@example.com"
    )
    headers = _headers(owner)
    duplicate_budgets = client.put(
        "/api/v1/finance/profile",
        headers=headers,
        json=_profile(
            budget_categories=[
                {"category": "rent", "monthly_limit": 30000},
                {"category": "rent", "monthly_limit": 35000},
            ]
        ),
    )
    assert duplicate_budgets.status_code == 422

    receipt_reminder = client.post(
        "/api/v1/finance/records",
        headers=headers,
        json={
            "category": "receipt",
            "title": "Receipt copy",
            "amount": 100,
            "record_date": datetime.now(ZoneInfo("Africa/Nairobi")).isoformat(),
            "due_date": (
                datetime.now(ZoneInfo("Africa/Nairobi")).date() + timedelta(days=3)
            ).isoformat(),
        },
    )
    assert receipt_reminder.status_code == 422


def test_simulators_utilities_literacy_lease_and_alert_privacy(client) -> None:
    owner = create_authenticated_user(client, role_code="tenant", email="finance-tools@example.com")
    other = create_authenticated_user(
        client, role_code="tenant", email="finance-tools-other@example.com"
    )
    headers, other_headers = _headers(owner), _headers(other)

    simulation = client.post(
        "/api/v1/finance/savings/simulate",
        headers=headers,
        json={
            "target_amount": 60000,
            "current_savings": 10000,
            "monthly_contribution": 10000,
            "months": 6,
        },
    )
    assert simulation.status_code == 200
    assert simulation.json()["will_reach_target"] is True
    assert simulation.json()["is_virtual_tracker"] is True
    utilities = client.post(
        "/api/v1/finance/utilities/estimate",
        headers=headers,
        json={"monthly_user_entries": [1000, 1500, 2000]},
    )
    assert utilities.status_code == 200
    assert utilities.json()["sample_count"] == 3
    assert "not a utility quote" in utilities.json()["disclaimer"]
    breakdown = client.post(
        "/api/v1/finance/utilities/estimate",
        headers=headers,
        json={
            "monthly_by_category": {
                "water": 1200,
                "electricity": 2000,
                "internet": 2500,
                "cooking_gas": 900,
                "waste_collection": 300,
                "other": 100,
            }
        },
    )
    assert breakdown.status_code == 200, breakdown.text
    assert Decimal(breakdown.json()["monthly_total"]) == Decimal("7000.00")
    assert Decimal(breakdown.json()["monthly_by_category"]["internet"]) == Decimal("2500.00")

    lessons = client.get("/api/v1/finance/lessons", headers=headers)
    assert lessons.status_code == 200 and len(lessons.json()["items"]) >= 10
    quiz = client.post(
        "/api/v1/finance/lessons/mpesa-safety/quiz",
        headers=headers,
        json={"answers": [1]},
    )
    assert quiz.status_code == 200 and quiz.json()["completed"] is True
    assert client.get("/api/v1/finance/lessons/progress", headers=other_headers).json() == []

    lease = client.post(
        "/api/v1/finance/lease-guardian",
        headers=headers,
        json={
            "title": "New lease notes",
            "lease_start": "2027-01-01",
            "lease_end": "2027-12-31",
            "monthly_rent": 41000,
            "deposit_amount": 41000,
            "obligations": [{"title": "Water bill", "user_question": "Is this shared?"}],
            "private_notes": "Ask for a written breakdown.",
        },
    )
    assert lease.status_code == 201
    assert "not legal advice" in lease.json()["disclaimer"]
    assert client.get("/api/v1/finance/lease-guardian", headers=other_headers).json() == []
    updated_lease = client.patch(
        f"/api/v1/finance/lease-guardian/{lease.json()['id']}",
        headers=headers,
        json={
            "lease_start": None,
            "lease_end": "2028-01-31",
            "obligations": [
                {
                    "title": "Water bill",
                    "plain_language_note": "Shared with the upstairs unit",
                    "user_question": "How is the bill split?",
                }
            ],
        },
    )
    assert updated_lease.status_code == 200, updated_lease.text
    assert updated_lease.json()["lease_start"] is None
    assert updated_lease.json()["lease_end"] == "2028-01-31"
    assert (
        updated_lease.json()["obligations"][0]["plain_language_note"]
        == "Shared with the upstairs unit"
    )
    assert (
        client.patch(
            f"/api/v1/finance/lease-guardian/{lease.json()['id']}",
            headers=headers,
            json={"lease_start": "2027-01-01", "lease_end": "2026-01-01"},
        ).status_code
        == 422
    )

    client.put("/api/v1/finance/profile", headers=headers, json=_profile())
    alerts = client.get("/api/v1/finance/alerts", headers=headers)
    assert alerts.status_code == 200 and alerts.json()
    assert client.get("/api/v1/finance/alerts", headers=other_headers).json() == []
    read = client.post(f"/api/v1/finance/alerts/{alerts.json()[0]['id']}/read", headers=headers)
    assert read.status_code == 200 and read.json()["is_read"] is True


def test_budget_discovery_comparison_and_cost_change_alert(client) -> None:
    landlord = create_authenticated_user(
        client, role_code="landlord", email="finance-property-owner@example.com"
    )
    tenant = create_authenticated_user(
        client, role_code="tenant", email="finance-property-renter@example.com"
    )
    first = _publish_listing(client, landlord, title="Phase eight first home", rent=27000)
    second = _publish_listing(client, landlord, title="Phase eight second home", rent=35000)
    headers = _headers(tenant)
    client.put("/api/v1/finance/profile", headers=headers, json=_profile(target_monthly_rent=35000))

    discovery = client.get("/api/v1/finance/discovery", headers=headers)
    assert discovery.status_code == 200
    assert discovery.json()["private"] is True
    assert all(item["rent_frequency"] == "monthly_equivalent" for item in discovery.json()["items"])

    comparison = client.post(
        "/api/v1/finance/comparisons",
        headers=headers,
        json={
            "title": "Two viewing options",
            "property_ids": [first["id"], second["id"]],
            "additional_monthly_costs": {
                first["id"]: {"transport": 4000, "water": 1200, "parking": 3000},
                second["id"]: {"utilities": 3500},
            },
            "one_time_costs": {first["id"]: {"moving": 8000}},
        },
    )
    assert comparison.status_code == 201, comparison.text
    assert len(comparison.json()["properties"]) == 2
    compared_by_id = {item["property_id"]: item for item in comparison.json()["properties"]}
    assert Decimal(compared_by_id[first["id"]]["user_entered_move_in_costs"]) == Decimal("8000")
    assert Decimal(compared_by_id[first["id"]]["known_monthly_cost_subtotal"]) > 0
    assert compared_by_id[first["id"]]["is_total_monthly_cost_complete"] is False
    assert "electricity" in compared_by_id[first["id"]]["missing_monthly_cost_categories"]
    assert compared_by_id[first["id"]]["is_total_move_in_cost_complete"] is False
    assert Decimal(compared_by_id[first["id"]]["monthly_costs"]["water"]) == Decimal("1200")
    assert Decimal(compared_by_id[first["id"]]["monthly_costs"]["parking"]) == Decimal("3000")

    owner_headers = _headers(landlord)
    updated = client.patch(
        f"/api/v1/properties/{first['id']}",
        headers=owner_headers,
        json={"rent_amount": 29000},
    )
    assert updated.status_code == 200, updated.text
    current = client.get("/api/v1/finance/comparisons", headers=headers)
    assert current.status_code == 200
    alerts = client.get("/api/v1/finance/alerts", headers=headers).json()
    assert any("compared listing cost changed" in item["title"] for item in alerts)


def test_savings_contribution_request_is_retry_safe_and_rejects_key_reuse(client) -> None:
    token = create_authenticated_user(
        client, role_code="tenant", email="goal-idempotent@example.com"
    )
    headers = _headers(token)
    goal = client.post(
        "/api/v1/finance/savings/goals",
        headers=headers,
        json={"title": "Moving fund", "target_amount": 2500, "planned_monthly_contribution": 500},
    )
    assert goal.status_code == 201, goal.text
    assert Decimal(goal.json()["planned_monthly_contribution"]) == Decimal("500.00")
    assert goal.json()["estimated_months_to_completion"] == 5
    goal_id = goal.json()["id"]
    request_id = str(uuid4())
    url = f"/api/v1/finance/savings/goals/{goal_id}/contributions"
    payload = {"amount": 2500, "notes": "Monthly transfer noted", "request_id": request_id}
    first = client.post(url, headers=headers, json=payload)
    retry = client.post(url, headers=headers, json=payload)
    assert first.status_code == 201, first.text
    assert retry.status_code == 201, retry.text
    assert Decimal(retry.json()["current_amount"]) == Decimal("2500.00")
    assert retry.json()["status"] == "completed"
    contributions = client.get(
        f"/api/v1/finance/savings/goals/{goal_id}/contributions", headers=headers
    )
    assert len(contributions.json()) == 1
    conflict = client.post(url, headers=headers, json=payload | {"amount": 2600})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "contribution_request_reused"


def test_rent_choice_simulator_api_returns_input_based_projection(client) -> None:
    token = create_authenticated_user(client, role_code="tenant", email="rent-choice@example.com")
    response = client.post(
        "/api/v1/finance/rent-choice/simulate",
        headers=_headers(token),
        json={
            "current_monthly_housing_cost": 40000,
            "alternative_monthly_housing_cost": 35000,
            "one_time_moving_cost": 10000,
            "months": 6,
        },
    )
    assert response.status_code == 200, response.text
    assert Decimal(response.json()["net_savings_after_move_cost"]) == Decimal("20000")
    invalid = client.post(
        "/api/v1/finance/rent-choice/simulate",
        headers=_headers(token),
        json={
            "current_monthly_housing_cost": 0,
            "alternative_monthly_housing_cost": 35000,
            "months": 6,
        },
    )
    assert invalid.status_code == 422


def test_missing_encryption_key_does_not_disable_stateless_calculations() -> None:
    service = SmartRentService(Settings(finance_encryption_key=None))
    result = service.simulate_rent_choice(Decimal("40000"), Decimal("35000"), Decimal("10000"), 6)
    assert result["net_savings_after_move_cost"] == Decimal("20000.00")
    with pytest.raises(ApiError) as failure:
        _ = service.cipher
    assert failure.value.status_code == 503
    assert failure.value.code == "finance_encryption_not_configured"


def test_api_requires_auth_and_reports_capability_limits(client) -> None:
    assert client.get("/api/v1/finance/assessment").status_code == 401
    response = client.get("/api/v1/finance/capabilities")
    assert response.status_code == 200
    states = {item["name"]: item["status"] for item in response.json()["items"]}
    assert states["Budget coach"] == "rule_based_preview"
    assert states["Savings vault"] == "virtual_tracker"
    assert states["Rent payment record"] == "manual_record_only"
