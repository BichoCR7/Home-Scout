"""Validated HomeScout SmartRent finance contracts."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

IncomeFrequency = Literal["daily", "weekly", "biweekly", "twice_monthly", "monthly", "annual"]
IncomePattern = Literal["steady", "variable", "seasonal"]
CostEvidence = Literal["listing", "user_entered", "estimated"]


class AdditionalIncomeSource(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    frequency: IncomeFrequency
    work_days_per_week: int = Field(default=5, ge=1, le=7)


BudgetCategory = Literal[
    "rent", "utilities", "internet", "transport", "household", "debt", "expense", "other"
]


class FinanceBudgetCategory(BaseModel):
    category: BudgetCategory
    monthly_limit: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class FinanceProfileInput(BaseModel):
    income_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    income_frequency: IncomeFrequency = "monthly"
    income_work_days_per_week: int = Field(default=5, ge=1, le=7)
    additional_income_sources: list[AdditionalIncomeSource] = Field(
        default_factory=list, max_length=10
    )
    income_pattern: IncomePattern = "steady"
    recent_monthly_income: list[Decimal] = Field(default_factory=list, max_length=12)
    monthly_expenses: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    monthly_obligations: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=14, decimal_places=2
    )
    current_savings: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    target_monthly_rent: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=14, decimal_places=2
    )
    expected_move_in_total: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=14, decimal_places=2
    )
    monthly_utility_budget: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )
    monthly_transport_cost: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=14, decimal_places=2
    )
    monthly_housing_other_costs: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=14, decimal_places=2
    )
    budget_categories: list[FinanceBudgetCategory] = Field(default_factory=list, max_length=8)
    household_size: int = Field(default=1, ge=1, le=30)
    has_payslip: bool = False

    @field_validator("recent_monthly_income")
    @classmethod
    def validate_recent_income(cls, values: list[Decimal]) -> list[Decimal]:
        if values and len(values) < 3:
            raise ValueError("Enter at least three recent monthly values, or leave this empty.")
        if any(value < 0 or value > Decimal("999999999999.99") for value in values):
            raise ValueError("Recent monthly income values must be non-negative KES amounts.")
        return values

    @model_validator(mode="after")
    def validate_budget_categories(self):
        categories = [item.category for item in self.budget_categories]
        if len(categories) != len(set(categories)):
            raise ValueError("Each monthly budget category can only be added once.")
        return self


class FinanceProfileResponse(FinanceProfileInput):
    updated_at: datetime | None = None
    is_configured: bool = False

    model_config = {"from_attributes": True}


class FinanceAssessmentResponse(BaseModel):
    conservative_monthly_income: Decimal
    monthly_income_before_conservative_adjustment: Decimal
    income_source_breakdown: list[dict[str, object]]
    monthly_expenses: Decimal
    monthly_obligations: Decimal
    monthly_utility_budget: Decimal
    monthly_transport_cost: Decimal
    monthly_housing_other_costs: Decimal
    monthly_committed_costs: Decimal
    non_housing_committed_costs: Decimal
    housing_costs_excluding_rent: Decimal
    total_monthly_housing_cost: Decimal
    rent_to_income_percent: Decimal | None
    housing_cost_to_income_percent: Decimal | None
    monthly_surplus_or_deficit: Decimal
    disposable_before_rent: Decimal
    suggested_monthly_budget: Decimal
    target_monthly_rent: Decimal
    remaining_after_target_rent: Decimal
    affordability: Literal["comfortable", "review", "stretch", "tight", "not_enough_data"]
    readiness_index: int = Field(ge=0, le=100)
    readiness_label: Literal["building", "getting_ready", "prepared", "not_enough_data"]
    move_in_savings_coverage_percent: int = Field(ge=0, le=100)
    method: str
    explanations: list[str]
    suggestions: list[str]
    disclaimer: str


class MoveInCostLine(BaseModel):
    category: Literal[
        "moving",
        "agent_fee",
        "utilities",
        "internet",
        "furniture",
        "essentials",
        "cleaning",
        "transport",
        "other",
    ]
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    evidence: Literal["listing", "user_entered", "estimated"]
    note: str | None = Field(default=None, max_length=300)


class MoveInPlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    property_id: UUID | None = None
    rent_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    deposit_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    rent_evidence: Literal["listing", "user_entered", "estimated"] = "user_entered"
    deposit_evidence: Literal["listing", "user_entered", "estimated"] = "user_entered"
    costs: list[MoveInCostLine] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def require_rent_without_property(self):
        if self.property_id is None and self.rent_amount is None:
            raise ValueError("Enter a rent amount or select a property.")
        return self


class MoveInPlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    costs: list[MoveInCostLine] | None = Field(default=None, max_length=20)
    rent_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    deposit_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    rent_evidence: CostEvidence | None = None
    deposit_evidence: CostEvidence | None = None


class SavingsGoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    initial_saved_amount: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=14, decimal_places=2
    )
    planned_monthly_contribution: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=14, decimal_places=2
    )
    target_date: date | None = None
    description: str | None = Field(default=None, max_length=500)


class SavingsGoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    target_date: date | None = None
    description: str | None = Field(default=None, max_length=500)
    status: Literal["open", "completed", "archived"] | None = None


class SavingsContributionCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=300)
    request_id: UUID | None = None


class SavingsGoalShareCreate(BaseModel):
    user_id: UUID
    can_contribute: bool = False


class SavingsSimulationRequest(BaseModel):
    target_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    current_savings: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    monthly_contribution: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    months: int = Field(ge=1, le=120)


class RentChoiceSimulationRequest(BaseModel):
    current_monthly_housing_cost: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    alternative_monthly_housing_cost: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    one_time_moving_cost: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=14, decimal_places=2
    )
    months: int = Field(ge=1, le=120)


class HousingRecordCreate(BaseModel):
    category: Literal[
        "rent",
        "deposit",
        "utilities",
        "moving",
        "internet",
        "furniture",
        "expense",
        "transport",
        "household",
        "debt",
        "other",
        "receipt",
    ]
    title: str = Field(min_length=1, max_length=140)
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    record_date: datetime
    due_date: date | None = None
    payment_method: Literal["not_recorded", "mpesa", "bank_transfer", "cash", "card", "other"] = (
        "not_recorded"
    )
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)
    private_document_id: UUID | None = None

    @field_validator("record_date")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Record date must include a timezone offset.")
        return value

    @model_validator(mode="after")
    def validate_upcoming_record(self):
        if self.due_date and self.category == "receipt":
            raise ValueError("A receipt attachment cannot be saved as an upcoming expense.")
        return self


class RentObligationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    amount_kes: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    due_date: date
    property_id: UUID | None = None
    property_reference: str | None = Field(default=None, max_length=140)
    notes: str | None = Field(default=None, max_length=1000)


class RentObligationUpdate(RentObligationCreate):
    status: Literal["open", "cancelled"] = "open"


class RentPaymentReportCreate(BaseModel):
    amount_kes: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: Literal["mpesa", "bank_transfer", "cash", "card", "paypal", "other"]
    paid_on: date
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)
    request_id: UUID


class FinancialLessonQuizRequest(BaseModel):
    answers: list[int] = Field(min_length=1, max_length=5)


class TrueCostComparisonCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    property_ids: list[UUID] = Field(min_length=2, max_length=4)
    additional_monthly_costs: dict[str, dict[str, Decimal]] = Field(default_factory=dict)
    one_time_costs: dict[str, dict[str, Decimal]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_comparison_costs(self):
        if len(self.property_ids) != len(set(self.property_ids)):
            raise ValueError("Choose each property only once.")
        categories = {
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
        for values in self.additional_monthly_costs.values():
            if not set(values).issubset(categories):
                raise ValueError(
                    "Use supported utility, transport, internet, parking, or other cost categories."
                )
            if any(amount < 0 for amount in values.values()):
                raise ValueError("Comparison costs must be non-negative KES amounts.")
        for values in self.one_time_costs.values():
            if not set(values).issubset(
                {"moving", "agent_fee", "furniture", "essentials", "other"}
            ):
                raise ValueError(
                    "Only moving, agent fee, furniture, essentials, and other one-time "
                    "costs are supported."
                )
            if any(amount < 0 for amount in values.values()):
                raise ValueError("Comparison costs must be non-negative KES amounts.")
        allowed_ids = {str(property_id) for property_id in self.property_ids}
        if not set(self.additional_monthly_costs).issubset(allowed_ids) or not set(
            self.one_time_costs
        ).issubset(allowed_ids):
            raise ValueError("Additional costs must reference a property in this comparison.")
        return self


class UtilityEstimateRequest(BaseModel):
    monthly_user_entries: list[Decimal] | None = Field(default=None, min_length=1, max_length=24)
    monthly_by_category: dict[str, Decimal] = Field(default_factory=dict)

    @field_validator("monthly_user_entries")
    @classmethod
    def validate_entries(cls, values: list[Decimal] | None) -> list[Decimal] | None:
        if values is not None and any(
            value < 0 or value > Decimal("999999999999.99") for value in values
        ):
            raise ValueError("Utility amounts must be non-negative KES values.")
        return values

    @model_validator(mode="after")
    def require_user_entries_or_categories(self):
        allowed = {"water", "electricity", "internet", "cooking_gas", "waste_collection", "other"}
        if not self.monthly_user_entries and not self.monthly_by_category:
            raise ValueError("Enter past utility totals or itemized monthly costs.")
        if not set(self.monthly_by_category).issubset(allowed):
            raise ValueError(
                "Use water, electricity, internet, cooking gas, waste collection, or other."
            )
        if any(
            value < 0 or value > Decimal("999999999999.99")
            for value in self.monthly_by_category.values()
        ):
            raise ValueError("Utility category amounts must be non-negative KES values.")
        return self


class LeaseObligation(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    plain_language_note: str | None = Field(default=None, max_length=500)
    user_question: str | None = Field(default=None, max_length=500)


class LeaseGuardianCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    property_id: UUID | None = None
    lease_start: date | None = None
    lease_end: date | None = None
    monthly_rent: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    deposit_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    obligations: list[LeaseObligation] = Field(default_factory=list, max_length=30)
    private_notes: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def validate_lease_dates(self):
        if self.lease_start and self.lease_end and self.lease_end < self.lease_start:
            raise ValueError("Lease end date must be on or after the start date.")
        return self


class LeaseGuardianUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    lease_start: date | None = None
    lease_end: date | None = None
    monthly_rent: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    deposit_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    obligations: list[LeaseObligation] | None = Field(default=None, max_length=30)
    private_notes: str | None = Field(default=None, max_length=3000)
