"""M-Pesa payment attempts and deduplicated callback evidence."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    __table_args__ = (
        CheckConstraint("currency = 'KES'", name="payment_currency_kes"),
        CheckConstraint("amount_kes > 0", name="payment_amount_positive"),
        CheckConstraint("payment_purpose = 'service_booking'", name="payment_purpose_allowed"),
        CheckConstraint(
            "status IN ('initiated','pending','successful','failed','cancelled','expired',"
            "'reversed')",
            name="payment_status",
        ),
        CheckConstraint("environment IN ('sandbox','production')", name="payment_environment"),
        Index("ix_payment_transactions_user_created", "payer_user_id", "created_at"),
        Index("ix_payment_transactions_status_updated", "status", "updated_at"),
        Index(
            "uq_payment_transactions_user_idempotency",
            "payer_user_id",
            "idempotency_key_hash",
            unique=True,
        ),
        Index(
            "uq_payment_transactions_order_in_flight",
            "service_order_id",
            unique=True,
            sqlite_where=text("status IN ('initiated','pending')"),
            postgresql_where=text("status IN ('initiated','pending')"),
        ),
        Index(
            "uq_payment_transactions_order_success",
            "service_order_id",
            unique=True,
            sqlite_where=text("status = 'successful'"),
            postgresql_where=text("status = 'successful'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payer_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    service_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("service_orders.id", ondelete="RESTRICT"), nullable=False
    )
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payment_purpose: Mapped[str] = mapped_column(String(40), nullable=False)
    amount_kes: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="initiated")
    environment: Mapped[str] = mapped_column(String(12), nullable=False)
    payer_phone_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    payer_phone_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    merchant_request_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    checkout_request_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    receipt_number: Mapped[str | None] = mapped_column(String(32), unique=True)
    provider_result_code: Mapped[str | None] = mapped_column(String(24))
    failure_code: Mapped[str | None] = mapped_column(String(64))
    submission_unknown: Mapped[bool] = mapped_column(nullable=False, default=False)
    reconciliation_attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    last_reconciliation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class PaymentCallbackEvent(Base):
    __tablename__ = "payment_callback_events"
    __table_args__ = (
        CheckConstraint(
            "processing_status IN ('pending','processed','rejected')",
            name="payment_callback_processing_status",
        ),
        Index("ix_payment_callback_events_transaction", "transaction_id", "received_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payment_transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    checkout_request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    callback_result_code: Mapped[str] = mapped_column(String(24), nullable=False)
    callback_amount_kes: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    callback_phone_hmac: Mapped[str | None] = mapped_column(String(64))
    receipt_candidate: Mapped[str | None] = mapped_column(String(32))
    transaction_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending")
    process_code: Mapped[str | None] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
