"""Persistence queries for payment transactions and callback evidence."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.payments import PaymentCallbackEvent, PaymentTransaction
from app.models.services import ServiceOrder


def payment_by_idempotency(
    session: Session, *, user_id: UUID, key_hash: str
) -> PaymentTransaction | None:
    return session.scalar(
        select(PaymentTransaction).where(
            PaymentTransaction.payer_user_id == user_id,
            PaymentTransaction.idempotency_key_hash == key_hash,
        )
    )


def payment_for_order(
    session: Session, *, service_order_id: UUID, statuses: tuple[str, ...] | None = None
) -> PaymentTransaction | None:
    statement = select(PaymentTransaction).where(
        PaymentTransaction.service_order_id == service_order_id
    )
    if statuses:
        statement = statement.where(PaymentTransaction.status.in_(statuses))
    return session.scalar(statement.order_by(PaymentTransaction.created_at.desc()))


def payment_by_checkout_id(session: Session, checkout_id: str) -> PaymentTransaction | None:
    return session.scalar(
        select(PaymentTransaction).where(PaymentTransaction.checkout_request_id == checkout_id)
    )


def payment_by_id(session: Session, transaction_id: UUID) -> PaymentTransaction | None:
    return session.get(PaymentTransaction, transaction_id)


def payment_history(
    session: Session, *, user_id: UUID, limit: int = 100
) -> list[PaymentTransaction]:
    return list(
        session.scalars(
            select(PaymentTransaction)
            .where(PaymentTransaction.payer_user_id == user_id)
            .order_by(PaymentTransaction.created_at.desc())
            .limit(limit)
        )
    )


def provider_payment_orders(
    session: Session, *, provider_user_id: UUID, limit: int = 100
) -> list[tuple[ServiceOrder, PaymentTransaction | None]]:
    latest_payment_id = (
        select(PaymentTransaction.id)
        .where(PaymentTransaction.service_order_id == ServiceOrder.id)
        .order_by(PaymentTransaction.created_at.desc())
        .limit(1)
        .correlate(ServiceOrder)
        .scalar_subquery()
    )
    rows = session.execute(
        select(ServiceOrder, PaymentTransaction)
        .outerjoin(PaymentTransaction, PaymentTransaction.id == latest_payment_id)
        .where(ServiceOrder.provider_user_id == provider_user_id)
        .order_by(ServiceOrder.created_at.desc())
        .limit(limit)
    )
    return [(order, transaction) for order, transaction in rows]


def payment_reconciliation_queue(
    session: Session, *, older_than: datetime, limit: int = 200
) -> list[PaymentTransaction]:
    return list(
        session.scalars(
            select(PaymentTransaction)
            .where(
                PaymentTransaction.status.in_(("initiated", "pending")),
                or_(
                    PaymentTransaction.last_reconciliation_at.is_(None),
                    PaymentTransaction.last_reconciliation_at < older_than,
                ),
            )
            .order_by(PaymentTransaction.created_at.asc())
            .limit(limit)
        )
    )


def callback_event_by_digest(session: Session, digest: str) -> PaymentCallbackEvent | None:
    return session.scalar(
        select(PaymentCallbackEvent).where(PaymentCallbackEvent.payload_digest == digest)
    )
