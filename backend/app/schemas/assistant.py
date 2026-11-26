"""Validated HomeScout Assistant request and response contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

AssistantIntent = Literal[
    "general",
    "property_search",
    "property_explanation",
    "property_comparison",
    "budget_planning",
    "affordability_explanation",
    "move_in_costs",
    "savings_planning",
    "financial_literacy",
    "viewing_preparation",
    "lease_explanation",
    "scam_awareness",
    "neighbourhood_discovery",
    "moving_planning",
    "schedule_assistance",
    "app_navigation",
    "landlord_listing_assistance",
    "agent_workflow_assistance",
    "service_provider_assistance",
    "property_manager_assistance",
    "shared_house_hunting",
    "irregular_income_budgeting",
    "rentscore_explanation",
    "property_cost_explanation",
]


class AssistantConfigurationResponse(BaseModel):
    available: bool
    provider_label: str
    consent_version: str
    privacy_notice: str
    disabled_message: str | None = None


class AssistantPrivacyResponse(BaseModel):
    provider_processing_allowed: bool
    consent_version: str
    updated_at: datetime | None = None
    ai_available: bool
    at_rest_encryption_configured: bool


class AssistantPrivacyUpdate(BaseModel):
    provider_processing_allowed: bool


class AssistantMessageRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None
    intent: AssistantIntent = "general"
    property_id: UUID | None = None
    compare_property_ids: list[UUID] = Field(default_factory=list, max_length=5)
    include_finance_context: bool = False
    include_saved_properties: bool = False
    include_schedule_context: bool = False
    include_work_context: bool = False
    shared_group_id: UUID | None = None

    @field_validator("text")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Message cannot be blank.")
        return clean

    @field_validator("compare_property_ids")
    @classmethod
    def validate_compare_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Choose different property records.")
        return value


class AssistantRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)

    @field_validator("title")
    @classmethod
    def reject_blank_title(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Conversation title cannot be blank.")
        return clean


class AssistantConversationResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class AssistantMessageResponse(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    text: str
    context_property_ids: list[str] = Field(default_factory=list)
    created_at: datetime


class AssistantConversationDetailResponse(AssistantConversationResponse):
    messages: list[AssistantMessageResponse] = Field(default_factory=list)


class AssistantContextProperty(BaseModel):
    id: UUID
    title: str
    rent_amount_kes: str
    rent_frequency: str
    location: str
    bedrooms: int
    bathrooms: str
    verification_status: str
    availability_status: str


class AssistantMessageResult(BaseModel):
    conversation: AssistantConversationResponse
    user_message: AssistantMessageResponse
    assistant_message: AssistantMessageResponse
    context_properties: list[AssistantContextProperty] = Field(default_factory=list)
