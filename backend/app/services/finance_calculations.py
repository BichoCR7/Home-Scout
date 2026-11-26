"""Deterministic SmartRent calculations with visible, non-credit heuristics."""

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal
from typing import Any

MONEY = Decimal("0.01")
ZERO = Decimal("0")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY)


def monthly_income_amount(amount: Decimal, frequency: str, work_days_per_week: int = 5) -> Decimal:
    """Normalize user-entered pay to a month using an explicit daily work schedule."""
    factor = {
        "daily": Decimal(work_days_per_week * 52) / Decimal(12),
        "weekly": Decimal(52) / Decimal(12),
        "biweekly": Decimal(26) / Decimal(12),
        "twice_monthly": Decimal(2),
        "monthly": Decimal(1),
        "annual": Decimal(1) / Decimal(12),
    }[frequency]
    return _money(amount * factor)


def assess_finances(profile: dict[str, Any]) -> dict[str, Any]:
    main_income = monthly_income_amount(
        Decimal(str(profile["income_amount"])),
        profile["income_frequency"],
        int(profile.get("income_work_days_per_week", 5)),
    )
    income_sources = [
        {
            "label": "Primary income",
            "amount": _money(Decimal(str(profile["income_amount"]))),
            "frequency": profile["income_frequency"],
            "monthly_equivalent": main_income,
        }
    ]
    for source in profile.get("additional_income_sources", []):
        source_amount = Decimal(str(source["amount"]))
        source_monthly = monthly_income_amount(
            source_amount,
            source["frequency"],
            int(source.get("work_days_per_week", 5)),
        )
        income_sources.append(
            {
                "label": source["label"],
                "amount": _money(source_amount),
                "frequency": source["frequency"],
                "monthly_equivalent": source_monthly,
            }
        )
    income = sum((source["monthly_equivalent"] for source in income_sources), ZERO)
    recent = [Decimal(str(value)) for value in profile.get("recent_monthly_income", [])]
    pattern = profile["income_pattern"]
    if recent:
        conservative_income = min(recent)
        income_basis = (
            "lowest of the monthly income amounts you entered; these totals take precedence "
            "over normalized recurring sources to avoid double counting"
        )
    else:
        factor = {
            "steady": Decimal("1.0"),
            "variable": Decimal("0.8"),
            "seasonal": Decimal("0.65"),
        }[pattern]
        conservative_income = _money(income * factor)
        income_basis = {
            "steady": "monthly equivalent of all entered recurring income sources",
            "variable": "80% planning factor applied to all recurring monthly income equivalents",
            "seasonal": "65% planning factor applied to all recurring monthly income equivalents",
        }[pattern]

    expenses = Decimal(str(profile["monthly_expenses"]))
    obligations = Decimal(str(profile["monthly_obligations"]))
    savings = Decimal(str(profile["current_savings"]))
    rent = Decimal(str(profile["target_monthly_rent"]))
    move_in = Decimal(str(profile["expected_move_in_total"]))
    utilities = Decimal(str(profile.get("monthly_utility_budget") or "0"))
    transport = Decimal(str(profile.get("monthly_transport_cost") or "0"))
    other_housing = Decimal(str(profile.get("monthly_housing_other_costs") or "0"))
    non_housing_committed = expenses + obligations
    housing_excluding_rent = utilities + transport + other_housing
    total_housing = rent + housing_excluding_rent
    committed_costs = expenses + obligations + utilities + transport + other_housing
    disposable = max(ZERO, conservative_income - committed_costs)
    suggested = min(conservative_income * Decimal("0.30"), disposable * Decimal("0.80"))
    remaining = conservative_income - committed_costs - rent

    if conservative_income <= ZERO or rent <= ZERO:
        affordability = "not_enough_data"
    elif rent <= suggested and remaining >= ZERO:
        affordability = "comfortable"
    elif rent <= conservative_income * Decimal("0.30") and remaining >= ZERO:
        affordability = "review"
    elif rent <= conservative_income * Decimal("0.40") and remaining >= ZERO:
        affordability = "stretch"
    else:
        affordability = "tight"

    coverage = min(Decimal(100), savings / move_in * 100) if move_in > ZERO else ZERO
    if conservative_income <= ZERO:
        index = 0
        readiness = "not_enough_data"
    else:
        rent_load = rent / conservative_income if rent > ZERO else Decimal("1")
        rent_component = max(ZERO, min(Decimal(1), Decimal(1) - rent_load / Decimal("0.5")))
        cash_after_rent = max(ZERO, remaining) / conservative_income
        cash_component = min(Decimal(1), cash_after_rent / Decimal("0.5"))
        move_in_component = coverage / Decimal(100)
        index = int(
            (rent_component * 35 + cash_component * 35 + move_in_component * 30).quantize(
                Decimal("1"), rounding=ROUND_CEILING
            )
        )
        readiness = "prepared" if index >= 75 else "getting_ready" if index >= 45 else "building"

    suggestions: list[str] = []
    if pattern != "steady" and not recent:
        suggestions.append(
            "Adding at least three recent monthly income amounts can replace "
            "the default variability factor."
        )
    if rent > suggested and suggested > ZERO:
        suggestions.append(
            "Try a lower rent ceiling or add more recent income and expense "
            "details before deciding."
        )
    if move_in <= ZERO:
        suggestions.append(
            "Add a move-in estimate to see how your entered savings compare with upfront costs."
        )
    elif savings < move_in:
        suggestions.append(
            f"Your entered savings are KSh {_money(move_in - savings)} below the move-in estimate."
        )
    if remaining < ZERO:
        suggestions.append(
            "Your entered rent and monthly costs exceed the conservative income estimate; "
            "review the figures or compare a lower-cost option."
        )
    if profile.get("has_payslip") is False:
        suggestions.append(
            "No payslip is required here; results use only the figures you chose to enter."
        )
    if not suggestions:
        suggestions.append(
            "Keep your estimate current and compare the full monthly and "
            "move-in costs before choosing."
        )

    return {
        "conservative_monthly_income": _money(conservative_income),
        "monthly_income_before_conservative_adjustment": _money(income),
        "income_source_breakdown": income_sources,
        "monthly_expenses": _money(expenses),
        "monthly_obligations": _money(obligations),
        "monthly_utility_budget": _money(utilities),
        "monthly_transport_cost": _money(transport),
        "monthly_housing_other_costs": _money(other_housing),
        "monthly_committed_costs": _money(committed_costs),
        "non_housing_committed_costs": _money(non_housing_committed),
        "housing_costs_excluding_rent": _money(housing_excluding_rent),
        "total_monthly_housing_cost": _money(total_housing),
        "rent_to_income_percent": (
            _money(rent / conservative_income * Decimal(100))
            if conservative_income > ZERO
            else None
        ),
        "housing_cost_to_income_percent": (
            _money(total_housing / conservative_income * Decimal(100))
            if conservative_income > ZERO
            else None
        ),
        "disposable_before_rent": _money(disposable),
        "suggested_monthly_budget": _money(suggested),
        "target_monthly_rent": _money(rent),
        "remaining_after_target_rent": _money(remaining),
        "monthly_surplus_or_deficit": _money(remaining),
        "affordability": affordability,
        "readiness_index": index,
        "readiness_label": readiness,
        "move_in_savings_coverage_percent": int(coverage.quantize(Decimal("1"))),
        "method": (
            "Daily pay uses the workdays/week you entered (default 5); weekly uses 52 weeks/year, "
            "biweekly uses 26 periods/year, twice-monthly uses 2 periods/month, and annual pay "
            "is divided by 12. Without recent "
            "monthly amounts, variable income uses 80% and seasonal income uses "
            "65%. Suggested rent is the lower of 30% of conservative monthly "
            "income and 80% of income remaining after entered expenses, "
            "obligations, utilities, transport, and other housing costs. The "
            "readiness index weights rent load 35%, remaining "
            "cash flow 35%, and entered savings coverage of entered move-in costs "
            "30%. These are planning heuristics, not lending, credit, eligibility, "
            "or listing-rejection rules."
        ),
        "explanations": [
            f"Income basis: {income_basis}.",
            "All amounts are user-entered KES values.",
        ],
        "suggestions": suggestions,
        "disclaimer": (
            "RentScore is a housing-planning index, not a credit score, "
            "creditworthiness assessment, loan decision, or automatic property "
            "eligibility rule. Estimates use only your inputs."
        ),
    }


def simulate_savings(
    target: Decimal, current: Decimal, monthly: Decimal, months: int
) -> dict[str, Any]:
    if target <= ZERO or current < ZERO or monthly < ZERO or months < 1:
        raise ValueError(
            "Savings amounts must be non-negative, target must be positive, and months must "
            "be at least one."
        )
    remaining = max(ZERO, target - current)
    projected = current + monthly * months
    required = _money(remaining / months) if months > 0 else remaining
    months_to_target = (
        int((remaining / monthly).to_integral_value(rounding=ROUND_CEILING))
        if monthly > ZERO
        else None
    )
    return {
        "target_amount": _money(target),
        "current_savings": _money(current),
        "monthly_contribution": _money(monthly),
        "months": months,
        "projected_total": _money(projected),
        "required_monthly_contribution": required,
        "remaining_amount": _money(remaining),
        "months_to_target": months_to_target,
        "will_reach_target": projected >= target,
        "is_virtual_tracker": True,
        "disclaimer": (
            "This is a virtual tracker only. HomeScout does not hold, receive, "
            "or transfer these funds."
        ),
    }


def simulate_rent_choice(
    current_monthly_housing_cost: Decimal,
    alternative_monthly_housing_cost: Decimal,
    one_time_moving_cost: Decimal,
    months: int,
) -> dict[str, Any]:
    """Compare stated housing costs, without returns, inflation, or unentered costs."""
    if (
        current_monthly_housing_cost <= ZERO
        or alternative_monthly_housing_cost < ZERO
        or one_time_moving_cost < ZERO
        or months < 1
    ):
        raise ValueError(
            "Enter positive current housing cost, non-negative alternative and move costs, "
            "and a period of at least one month."
        )
    monthly_difference = current_monthly_housing_cost - alternative_monthly_housing_cost
    cumulative_difference = monthly_difference * months
    net_savings = cumulative_difference - one_time_moving_cost
    break_even_month = (
        int((one_time_moving_cost / monthly_difference).to_integral_value(rounding=ROUND_CEILING))
        if monthly_difference > ZERO
        else None
    )
    return {
        "months": months,
        "current_monthly_housing_cost": _money(current_monthly_housing_cost),
        "alternative_monthly_housing_cost": _money(alternative_monthly_housing_cost),
        "monthly_difference": _money(monthly_difference),
        "one_time_moving_cost": _money(one_time_moving_cost),
        "current_housing_cost_over_period": _money(current_monthly_housing_cost * months),
        "alternative_cost_over_period_including_move": _money(
            alternative_monthly_housing_cost * months + one_time_moving_cost
        ),
        "net_savings_after_move_cost": _money(net_savings),
        "break_even_month": break_even_month,
        "is_lower_cost_over_period": net_savings >= ZERO,
        "assumptions": [
            "Uses only the monthly housing costs and one-time moving cost you entered.",
            "Assumes costs remain unchanged and excludes unentered fees, rent increases, and "
            "investment returns.",
        ],
        "disclaimer": (
            "An estimate for planning only; it does not guarantee future savings or affordability."
        ),
    }


def utility_summary(values: list[Decimal]) -> dict[str, Any]:
    if not values:
        raise ValueError("Enter at least one monthly utility amount.")
    ordered = sorted(values)
    count = len(ordered)
    middle = count // 2
    median = ordered[middle] if count % 2 else (ordered[middle - 1] + ordered[middle]) / Decimal(2)
    average = sum(ordered, ZERO) / count
    return {
        "sample_count": count,
        "minimum": _money(ordered[0]),
        "maximum": _money(ordered[-1]),
        "median": _money(median),
        "average": _money(average),
        "evidence": "estimated_from_user_entered_amounts",
        "disclaimer": (
            "This summary uses only the monthly amounts you entered; it is not "
            "a utility quote or forecast."
        ),
    }
