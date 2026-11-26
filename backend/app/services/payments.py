"""Backend-first Daraja payment orchestration and transaction access."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ApiError
from app.data_access.payments import (
    callback_event_by_digest,
    payment_by_checkout_id,
    payment_by_id,
    payment_by_idempotency,
    payment_for_order,
    payment_history,
    payment_reconciliation_queue,
    provider_payment_orders,
)
from app.models.payments import PaymentCallbackEvent, PaymentTransaction
from app.models.services import ServiceOrder
from app.schemas.payments import (
    DarajaCallbackEnvelope,
    PaymentConfigurationResponse,
    PaymentMethodAvailability,
    PaymentTransactionResponse,
    ProviderPaymentOrderResponse,
)
from app.services.audit import AuditService
from app.services.daraja import DarajaClient, DarajaError, StkQueryResult

logger = logging.getLogger("homescout.payments")
PHONE_PATTERN = re.compile(r"^254(?:1|7)\d{8}$")
RECEIPT_PATTERN = re.compile(r"^[A-Z0-9]{8,32}$")
MAX_STK_AMOUNT_KES = 9_999_999


class PaymentsService:
    def __init__(self, settings: Settings, daraja: DarajaClient) -> None:
        self.settings = settings
        self.daraja = daraja
        self.audit = AuditService()

    def configuration(self) -> PaymentConfigurationResponse:
        enabled = self.settings.mpesa_enabled
        mode = self.settings.mpesa_environment if enabled else "disabled"
        if not enabled:
            message = "M-Pesa payments are not configured. No payment has been attempted."
        elif mode == "sandbox":
            message = "Sandbox mode is enabled. Any prompts are test transactions only."
        else:
            message = "M-Pesa service payments are enabled for approved service bookings."
        return PaymentConfigurationResponse(
            enabled=enabled,
            mode=mode,
            available_purposes=["service_booking"] if enabled else [],
            message=message,
            methods=[
                PaymentMethodAvailability(
                    code="mpesa",
                    label="M-Pesa",
                    status="service_only" if enabled else "not_configured",
                    live_rent_checkout=False,
                    message=(
                        "Configured only for eligible HomeScout service bookings. "
                        "Rent checkout is unavailable."
                        if enabled
                        else "Not configured. No rent payment can be initiated."
                    ),
                ),
                PaymentMethodAvailability(
                    code="visa",
                    label="Visa",
                    status="not_configured",
                    message=(
                        "Card checkout is not configured. Never enter card details into HomeScout."
                    ),
                ),
                PaymentMethodAvailability(
                    code="mastercard",
                    label="Mastercard",
                    status="not_configured",
                    message=(
                        "Card checkout is not configured. Never enter card details into HomeScout."
                    ),
                ),
                PaymentMethodAvailability(
                    code="paypal",
                    label="PayPal",
                    status="not_configured",
                    message="PayPal checkout is not configured.",
                ),
                PaymentMethodAvailability(
                    code="bank_transfer",
                    label="Bank transfer",
                    status="manual_record_only",
                    live_rent_checkout=False,
                    message=(
                        "Record an external transfer you made; HomeScout does not initiate "
                        "or verify it."
                    ),
                ),
                PaymentMethodAvailability(
                    code="cash",
                    label="Cash",
                    status="manual_record_only",
                    live_rent_checkout=False,
                    message="Keep a private record of a cash payment; it remains unverified.",
                ),
                PaymentMethodAvailability(
                    code="other",
                    label="Other method",
                    status="manual_record_only",
                    live_rent_checkout=False,
                    message="Save a private note about an external payment; it remains unverified.",
                ),
            ],
        )

    def initiate(
        self,
        session: Session,
        *,
        payer_user_id: UUID,
        service_order_id: UUID,
        phone_number: str,
        idempotency_key: str,
        callback_base_url: str | None,
        request_id: str | None,
    ) -> PaymentTransactionResponse:
        self._require_enabled()
        if not callback_base_url:
            raise self._unavailable()
        canonical_phone = normalize_kenyan_phone(phone_number)
        phone_digest = self._phone_digest(canonical_phone)
        idempotency_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()

        existing = payment_by_idempotency(session, user_id=payer_user_id, key_hash=idempotency_hash)
        if existing:
            if (
                existing.service_order_id != service_order_id
                or existing.payer_phone_hmac != phone_digest
            ):
                raise ApiError(
                    409,
                    "idempotency_key_reused",
                    "This request key was already used for a different payment request.",
                )
            return payment_response(existing, self.settings)

        order = session.scalar(select(ServiceOrder).where(ServiceOrder.id == service_order_id))
        if order is None or order.customer_user_id != payer_user_id:
            raise ApiError(404, "service_order_not_found", "The service order was not found.")
        if order.status != "accepted":
            raise ApiError(
                409,
                "service_order_not_payable",
                "A service provider must accept this booking before payment can be requested.",
            )
        amount = order.estimated_amount_kes
        if (
            order.pricing_model_snapshot != "fixed"
            or amount is None
            or amount <= 0
            or amount != amount.to_integral_value()
            or amount > MAX_STK_AMOUNT_KES
        ):
            raise ApiError(
                409,
                "fixed_price_required",
                "Only an accepted service order with a fixed whole-KES price can use STK Push.",
            )
        previous = payment_for_order(session, service_order_id=service_order_id)
        if previous and previous.status in {"initiated", "pending", "successful"}:
            raise ApiError(
                409,
                "payment_already_exists",
                "This service order already has a pending or completed payment.",
            )

        transaction = PaymentTransaction(
            payer_user_id=payer_user_id,
            service_order_id=service_order_id,
            idempotency_key_hash=idempotency_hash,
            payment_purpose="service_booking",
            amount_kes=amount,
            currency="KES",
            status="initiated",
            environment=self.settings.mpesa_environment,
            payer_phone_hmac=phone_digest,
            payer_phone_last4=canonical_phone[-4:],
            submission_unknown=True,
            initiated_at=datetime.now(UTC),
        )
        session.add(transaction)
        try:
            session.flush()
            self.audit.record(
                session,
                event_type="payment.initiated",
                actor_user_id=payer_user_id,
                subject_type="payment_transaction",
                subject_id=str(transaction.id),
                request_id=request_id,
                metadata={"purpose": "service_booking", "amount_kes": int(amount)},
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            reused = payment_by_idempotency(
                session, user_id=payer_user_id, key_hash=idempotency_hash
            )
            if (
                reused
                and reused.service_order_id == service_order_id
                and reused.payer_phone_hmac == phone_digest
            ):
                return payment_response(reused, self.settings)
            raise ApiError(
                409,
                "payment_request_conflict",
                "A payment request is already active for this service order.",
            ) from error

        # Commit a pending, ambiguous attempt before network I/O. A duplicate client call cannot
        # send a second STK prompt if this process stops after Safaricom receives the request.
        transaction.status = "pending"
        transaction.updated_at = datetime.now(UTC)
        self._audit_status(session, transaction, payer_user_id, request_id)
        session.commit()
        callback_url = f"{callback_base_url.rstrip('/')}/api/v1/payments/daraja/callback"
        try:
            result = self.daraja.start_stk_push(
                amount_kes=amount,
                phone_number=canonical_phone,
                service_order_id=service_order_id,
                callback_url=callback_url,
            )
        except DarajaError as error:
            transaction.failure_code = error.code
            transaction.submission_unknown = error.submission_unknown
            transaction.status = "pending" if error.submission_unknown else "failed"
            transaction.updated_at = datetime.now(UTC)
            self._audit_status(session, transaction, payer_user_id, request_id)
            session.commit()
            return payment_response(transaction, self.settings)

        if result.error_code or result.response_code != "0":
            transaction.status = "failed"
            transaction.failure_code = result.error_code or "provider_rejected_request"
            transaction.submission_unknown = False
            transaction.updated_at = datetime.now(UTC)
            self._audit_status(session, transaction, payer_user_id, request_id)
        else:
            transaction.checkout_request_id = result.checkout_request_id
            transaction.merchant_request_id = result.merchant_request_id
            transaction.submission_unknown = False
            transaction.updated_at = datetime.now(UTC)
            self._audit_status(session, transaction, payer_user_id, request_id)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            logger.error("payment_provider_reference_conflict transaction_id=%s", transaction.id)
            transaction = payment_by_id(session, transaction.id) or transaction
            transaction.status = "pending"
            transaction.submission_unknown = True
            transaction.failure_code = "provider_reference_conflict"
            session.commit()
        return payment_response(transaction, self.settings)

    def handle_callback(
        self,
        session: Session,
        *,
        callback: DarajaCallbackEnvelope,
        request_id: str | None,
    ) -> None:
        parsed = callback.body.stk_callback
        transaction = payment_by_checkout_id(session, parsed.checkout_request_id)
        if transaction is None:
            logger.info("daraja_callback_unknown_checkout request_id=%s", request_id or "-")
            return
        if transaction.merchant_request_id != parsed.merchant_request_id:
            logger.warning("daraja_callback_reference_mismatch transaction_id=%s", transaction.id)
            return
        if transaction.status not in {"initiated", "pending"}:
            return
        digest = self._callback_digest(callback.model_dump(by_alias=True, mode="json"))
        event = callback_event_by_digest(session, digest)
        metadata = _callback_metadata(
            parsed.callback_metadata.items if parsed.callback_metadata else []
        )
        amount = _callback_amount(metadata.get("Amount"))
        callback_phone = _optional_phone(metadata.get("PhoneNumber"))
        receipt = _optional_receipt(metadata.get("MpesaReceiptNumber"))
        event_phone_hash = self._phone_digest(callback_phone) if callback_phone else None
        if event is None:
            event = PaymentCallbackEvent(
                transaction_id=transaction.id,
                payload_digest=digest,
                checkout_request_id=parsed.checkout_request_id,
                callback_result_code=str(parsed.result_code),
                callback_amount_kes=amount,
                callback_phone_hmac=event_phone_hash,
                receipt_candidate=receipt,
                transaction_time=_callback_time(metadata.get("TransactionDate")),
                processing_status="pending",
            )
            session.add(event)
            session.commit()
        elif event.processing_status in {"processed", "rejected"}:
            return

        now = datetime.now(UTC)
        cooldown = timedelta(seconds=self.settings.mpesa_reconciliation_cooldown_seconds)
        if (
            transaction.last_reconciliation_at
            and now - _as_utc(transaction.last_reconciliation_at) < cooldown
        ):
            event.process_code = "reconciliation_cooldown"
            session.commit()
            return
        transaction.last_reconciliation_at = now
        transaction.reconciliation_attempts += 1
        session.commit()

        try:
            query = self.daraja.query_stk(checkout_request_id=parsed.checkout_request_id)
        except DarajaError as error:
            event.process_code = error.code
            session.commit()
            return

        if not self._query_matches(transaction, query):
            event.processing_status = "rejected"
            event.process_code = "provider_query_mismatch"
            event.processed_at = datetime.now(UTC)
            session.commit()
            return

        provider_result = query.result_code
        callback_matches = (
            parsed.result_code == _integer(provider_result)
            and amount == transaction.amount_kes
            and event_phone_hash == transaction.payer_phone_hmac
        )
        if provider_result == "0" and _is_reversed(query):
            transaction.status = "reversed"
            transaction.provider_result_code = provider_result
            transaction.settled_at = datetime.now(UTC)
            event.processing_status = "processed"
            event.process_code = "provider_reports_reversed"
        elif provider_result == "0":
            # The authenticated status query is authoritative. Callback metadata is only used
            # to attach a receipt when amount and phone match the request we originally made.
            transaction.status = "successful"
            transaction.provider_result_code = provider_result
            transaction.failure_code = None
            transaction.submission_unknown = False
            transaction.settled_at = datetime.now(UTC)
            if callback_matches and receipt:
                transaction.receipt_number = receipt
            event.processing_status = "processed"
            event.process_code = "provider_success_confirmed"
        elif parsed.result_code == _integer(provider_result) and provider_result in {
            "1032",
            "1037",
        }:
            transaction.status = "cancelled" if provider_result == "1032" else "expired"
            transaction.provider_result_code = provider_result
            transaction.failure_code = (
                "payer_cancelled" if provider_result == "1032" else "provider_timeout"
            )
            transaction.submission_unknown = False
            event.processing_status = "processed"
            event.process_code = transaction.failure_code
        elif (
            parsed.result_code == _integer(provider_result)
            and provider_result
            and provider_result != "0"
        ):
            transaction.status = "failed"
            transaction.provider_result_code = provider_result[:24]
            transaction.failure_code = "provider_payment_failed"
            transaction.submission_unknown = False
            event.processing_status = "processed"
            event.process_code = "provider_payment_failed"
        else:
            event.processing_status = "pending"
            event.process_code = "provider_result_pending"
        event.processed_at = datetime.now(UTC) if event.processing_status != "pending" else None
        transaction.updated_at = datetime.now(UTC)
        self._audit_status(session, transaction, None, request_id)
        session.commit()

    def reconcile(
        self,
        session: Session,
        *,
        transaction: PaymentTransaction,
        actor_user_id: UUID,
        request_id: str | None,
    ) -> PaymentTransactionResponse:
        if transaction.status not in {"initiated", "pending"}:
            return payment_response(transaction, self.settings)
        if not transaction.checkout_request_id:
            return payment_response(transaction, self.settings)
        cooldown = timedelta(seconds=self.settings.mpesa_reconciliation_cooldown_seconds)
        now = datetime.now(UTC)
        if (
            transaction.last_reconciliation_at
            and now - _as_utc(transaction.last_reconciliation_at) < cooldown
        ):
            return payment_response(transaction, self.settings)
        transaction.last_reconciliation_at = now
        transaction.reconciliation_attempts += 1
        session.commit()
        try:
            query = self.daraja.query_stk(checkout_request_id=transaction.checkout_request_id)
        except DarajaError as error:
            logger.warning(
                "payment_reconciliation_unavailable transaction_id=%s provider_code=%s",
                transaction.id,
                error.code,
            )
            return payment_response(transaction, self.settings)
        if not self._query_matches(transaction, query):
            transaction.failure_code = "provider_query_mismatch"
            transaction.updated_at = datetime.now(UTC)
            session.commit()
            return payment_response(transaction, self.settings)

        if query.result_code == "0":
            transaction.status = "reversed" if _is_reversed(query) else "successful"
            transaction.provider_result_code = query.result_code
            transaction.failure_code = None
            transaction.submission_unknown = False
            transaction.settled_at = datetime.now(UTC)
        elif query.result_code in {"1032", "1037"}:
            transaction.status = "cancelled" if query.result_code == "1032" else "expired"
            transaction.provider_result_code = query.result_code
            transaction.failure_code = (
                "payer_cancelled" if query.result_code == "1032" else "provider_timeout"
            )
            transaction.submission_unknown = False
        elif query.result_code and query.result_code not in {"0"}:
            transaction.status = "failed"
            transaction.provider_result_code = query.result_code[:24]
            transaction.failure_code = "provider_payment_failed"
            transaction.submission_unknown = False
        else:
            return payment_response(transaction, self.settings)
        transaction.updated_at = datetime.now(UTC)
        self._audit_status(session, transaction, actor_user_id, request_id)
        session.commit()
        return payment_response(transaction, self.settings)

    def history(self, session: Session, *, user_id: UUID) -> list[PaymentTransactionResponse]:
        return [
            payment_response(row, self.settings)
            for row in payment_history(session, user_id=user_id)
        ]

    def provider_orders(
        self, session: Session, *, provider_user_id: UUID
    ) -> list[ProviderPaymentOrderResponse]:
        return [
            ProviderPaymentOrderResponse(
                service_order_id=order.id,
                offering_title=order.offering_title_snapshot,
                amount_kes=order.estimated_amount_kes,
                payment_status=transaction.status if transaction else None,
                created_at=order.created_at,
            )
            for order, transaction in provider_payment_orders(
                session, provider_user_id=provider_user_id
            )
        ]

    def queue(self, session: Session, *, limit: int = 100) -> list[PaymentTransaction]:
        cutoff = datetime.now(UTC) - timedelta(
            seconds=self.settings.mpesa_reconciliation_cooldown_seconds
        )
        return payment_reconciliation_queue(session, older_than=cutoff, limit=limit)

    def _query_matches(self, transaction: PaymentTransaction, query: StkQueryResult) -> bool:
        return (
            query.response_code == "0"
            and query.checkout_request_id == transaction.checkout_request_id
            and query.result_code is not None
        )

    def _phone_digest(self, canonical_phone: str) -> str:
        key = self._phone_key()
        return hmac.new(key, canonical_phone.encode("ascii"), hashlib.sha256).hexdigest()

    def _callback_digest(self, payload: dict[str, Any]) -> str:
        key = self._phone_key()
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def _phone_key(self) -> bytes:
        secret = self.settings.mpesa_phone_hash_key
        if not secret:
            raise self._unavailable()
        return secret.get_secret_value().encode("utf-8")

    def _require_enabled(self) -> None:
        if not self.settings.mpesa_enabled:
            raise self._unavailable()

    @staticmethod
    def _unavailable() -> ApiError:
        return ApiError(
            503,
            "payments_unavailable",
            "M-Pesa payments are not configured. No payment was attempted.",
        )

    def _audit_status(
        self,
        session: Session,
        transaction: PaymentTransaction,
        actor_user_id: UUID | None,
        request_id: str | None,
    ) -> None:
        self.audit.record(
            session,
            event_type=f"payment.status.{transaction.status}",
            actor_user_id=actor_user_id,
            subject_type="payment_transaction",
            subject_id=str(transaction.id),
            request_id=request_id,
            metadata={
                "purpose": transaction.payment_purpose,
                "amount_kes": int(transaction.amount_kes),
                "status": transaction.status,
                "environment": transaction.environment,
            },
        )


def payment_response(
    transaction: PaymentTransaction, settings: Settings
) -> PaymentTransactionResponse:
    return PaymentTransactionResponse(
        id=transaction.id,
        service_order_id=transaction.service_order_id,
        purpose=transaction.payment_purpose,
        amount_kes=transaction.amount_kes,
        currency=transaction.currency,
        status=transaction.status,
        environment=transaction.environment,
        phone_masked=f"•••• {transaction.payer_phone_last4}",
        reference=f"HS-{str(transaction.id).replace('-', '')[:12].upper()}",
        receipt_number=transaction.receipt_number,
        failure_code=transaction.failure_code,
        can_reconcile=(
            settings.mpesa_enabled
            and transaction.status in {"initiated", "pending"}
            and bool(transaction.checkout_request_id)
        ),
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        settled_at=transaction.settled_at,
    )


def normalize_kenyan_phone(value: str) -> str:
    normalized = value.strip().replace(" ", "").replace("-", "")
    if normalized.startswith("+"):
        normalized = normalized[1:]
    if normalized.startswith("0"):
        normalized = "254" + normalized[1:]
    if not PHONE_PATTERN.fullmatch(normalized):
        raise ApiError(422, "invalid_phone_number", "Enter a valid Kenyan mobile number.")
    return normalized


def _callback_metadata(items: list[Any]) -> dict[str, object]:
    result: dict[str, object] = {}
    for item in items:
        if item.name in result:
            # Duplicate keys make the payload ambiguous for receipt data.
            result[item.name] = None
        else:
            result[item.name] = item.value
    return result


def _callback_amount(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        amount = Decimal(str(value))
    except Exception:
        return None
    return amount if amount.is_finite() and amount >= 0 else None


def _optional_phone(value: object) -> str | None:
    if not isinstance(value, (str, int)):
        return None
    try:
        return normalize_kenyan_phone(str(value))
    except ApiError:
        return None


def _optional_receipt(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip().upper()
    return candidate if RECEIPT_PATTERN.fullmatch(candidate) else None


def _callback_time(value: object) -> datetime | None:
    if not isinstance(value, (str, int)):
        return None
    raw = str(value)
    if not re.fullmatch(r"\d{14}", raw):
        return None
    try:
        local = datetime.strptime(raw, "%Y%m%d%H%M%S").replace(tzinfo=ZoneInfo("Africa/Nairobi"))
    except ValueError:
        return None
    return local.astimezone(UTC)


def _integer(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _is_reversed(query: StkQueryResult) -> bool:
    return (query.transaction_status or "").strip().lower() == "reversed"


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
