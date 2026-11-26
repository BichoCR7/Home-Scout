"""Validated M-Pesa and transaction API shapes."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

PaymentStatus = Literal[
    "initiated", "pending", "successful", "failed", "cancelled", "expired", "reversed"
]


class PaymentMethodAvailability(BaseModel):
    code: Literal["mpesa", "visa", "mastercard", "paypal", "bank_transfer", "cash", "other"]
    label: str
    status: Literal["service_only", "not_configured", "manual_record_only"]
    live_rent_checkout: bool = False
    message: str


class PaymentConfigurationResponse(BaseModel):
    enabled: bool
    mode: Literal["disabled", "sandbox", "production"]
    available_purposes: list[str]
    message: str
    methods: list[PaymentMethodAvailability]


class PaymentInitiateRequest(BaseModel):
    service_order_id: UUID
    phone_number: str = Field(min_length=9, max_length=16)

    @field_validator("phone_number")
    @classmethod
    def digits_only(cls, value: str) -> str:
        normalized = value.strip().replace(" ", "").replace("-", "")
        if normalized.startswith("+"):
            normalized = normalized[1:]
        if not normalized.isdigit():
            raise ValueError("Enter a Kenyan mobile number using digits.")
        if normalized.startswith("0"):
            normalized = "254" + normalized[1:]
        if normalized.startswith("254") and len(normalized) in {12}:
            if normalized[3] not in {"1", "7"}:
                raise ValueError("Enter a valid Kenyan mobile number.")
            return normalized
        raise ValueError("Enter a Kenyan mobile number beginning with 01, 07, or 254.")


class PaymentTransactionResponse(BaseModel):
    id: UUID
    service_order_id: UUID
    purpose: str
    amount_kes: Decimal
    currency: str
    status: PaymentStatus
    environment: str
    phone_masked: str
    reference: str | None = None
    receipt_number: str | None = None
    failure_code: str | None = None
    can_reconcile: bool
    created_at: datetime
    updated_at: datetime
    settled_at: datetime | None = None


class ProviderPaymentOrderResponse(BaseModel):
    service_order_id: UUID
    offering_title: str
    amount_kes: Decimal | None
    currency: str = "KES"
    payment_status: PaymentStatus | None
    created_at: datetime


class PaymentReconciliationItem(BaseModel):
    id: UUID
    service_order_id: UUID
    amount_kes: Decimal
    status: PaymentStatus
    environment: str
    submission_unknown: bool
    reconciliation_attempts: int
    last_reconciliation_at: datetime | None
    created_at: datetime


class DarajaCallbackMetadataItem(BaseModel):
    name: str = Field(alias="Name", max_length=80)
    value: str | int | float | None = Field(default=None, alias="Value")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DarajaCallbackMetadata(BaseModel):
    items: list[DarajaCallbackMetadataItem] = Field(alias="Item", max_length=30)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DarajaStkCallback(BaseModel):
    merchant_request_id: str = Field(alias="MerchantRequestID", min_length=1, max_length=128)
    checkout_request_id: str = Field(alias="CheckoutRequestID", min_length=1, max_length=128)
    result_code: int = Field(alias="ResultCode", ge=0, le=99_999)
    result_description: str = Field(alias="ResultDesc", max_length=500)
    callback_metadata: DarajaCallbackMetadata | None = Field(default=None, alias="CallbackMetadata")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DarajaCallbackBody(BaseModel):
    stk_callback: DarajaStkCallback = Field(alias="stkCallback")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DarajaCallbackEnvelope(BaseModel):
    body: DarajaCallbackBody = Field(alias="Body")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DarajaQueryResult(BaseModel):
    response_code: str | None = None
    result_code: str | None = None
    result_description: str | None = None
    checkout_request_id: str | None = None
    transaction_status: str | None = None
    extra_data: dict[str, Any] = Field(default_factory=dict)
