"""M-Pesa configuration, service payment history, and Daraja callback routes."""

from __future__ import annotations

import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db
from app.core.errors import ApiError
from app.models.payments import PaymentTransaction
from app.schemas.payments import (
    DarajaCallbackEnvelope,
    PaymentConfigurationResponse,
    PaymentInitiateRequest,
    PaymentReconciliationItem,
    PaymentTransactionResponse,
    ProviderPaymentOrderResponse,
)
from app.services.authentication import AuthenticatedPrincipal
from app.services.authorization import AuthorizationService
from app.services.payments import PaymentsService

router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger("homescout.payments.api")
MAX_CALLBACK_BODY_BYTES = 65_536


def _service(request: Request) -> PaymentsService:
    return PaymentsService(request.app.state.settings, request.app.state.daraja_client)


def _require_permission(session: Session, user_id: UUID, code: str) -> None:
    AuthorizationService().require_permission(
        session,
        user_id=user_id,
        permission_code=code,
        resource_owner_id=user_id if code.endswith(":self") else None,
    )


@router.get("/configuration", response_model=PaymentConfigurationResponse)
def payment_configuration(request: Request) -> PaymentConfigurationResponse:
    return _service(request).configuration()


@router.post("/service-bookings", response_model=PaymentTransactionResponse)
def request_service_payment(
    body: PaymentInitiateRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=16,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ],
) -> PaymentTransactionResponse:
    _require_permission(session, principal.user_id, "payment:create:self")
    return _service(request).initiate(
        session,
        payer_user_id=principal.user_id,
        service_order_id=body.service_order_id,
        phone_number=body.phone_number,
        idempotency_key=idempotency_key,
        callback_base_url=request.app.state.settings.mpesa_callback_base_url,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/me", response_model=list[PaymentTransactionResponse])
def my_payment_history(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[PaymentTransactionResponse]:
    _require_permission(session, principal.user_id, "payment:view:self")
    return _service(request).history(session, user_id=principal.user_id)


@router.get("/provider-orders", response_model=list[ProviderPaymentOrderResponse])
def provider_payment_history(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ProviderPaymentOrderResponse]:
    if not AuthorizationService().has_permission(
        session,
        user_id=principal.user_id,
        permission_code="payment:view:booking_participant",
        resource_scope_type="booking",
        resource_scope_id="*",
    ):
        raise ApiError(403, "permission_denied", "You are not authorized to view these records.")
    return _service(request).provider_orders(session, provider_user_id=principal.user_id)[:limit]


@router.get("/reconciliation-queue", response_model=list[PaymentReconciliationItem])
def reconciliation_queue(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[PaymentReconciliationItem]:
    _require_permission(session, principal.user_id, "payment:reconcile:global")
    return [
        PaymentReconciliationItem(
            id=row.id,
            service_order_id=row.service_order_id,
            amount_kes=row.amount_kes,
            status=row.status,
            environment=row.environment,
            submission_unknown=row.submission_unknown,
            reconciliation_attempts=row.reconciliation_attempts,
            last_reconciliation_at=row.last_reconciliation_at,
            created_at=row.created_at,
        )
        for row in _service(request).queue(session, limit=limit)
    ]


@router.get("/{transaction_id}", response_model=PaymentTransactionResponse)
def get_payment(
    transaction_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PaymentTransactionResponse:
    transaction = session.get(PaymentTransaction, transaction_id)
    if transaction is None:
        raise ApiError(404, "payment_not_found", "The payment record was not found.")
    allowed = (
        transaction.payer_user_id == principal.user_id
        and AuthorizationService().has_permission(
            session,
            user_id=principal.user_id,
            permission_code="payment:view:self",
            resource_owner_id=principal.user_id,
        )
    )
    admin_allowed = AuthorizationService().has_permission(
        session, user_id=principal.user_id, permission_code="payment:view:global"
    )
    if not (allowed or admin_allowed):
        raise ApiError(403, "permission_denied", "You are not authorized to view this payment.")
    return _response(transaction, request)


@router.post("/{transaction_id}/reconcile", response_model=PaymentTransactionResponse)
def reconcile_payment(
    transaction_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PaymentTransactionResponse:
    transaction = session.get(PaymentTransaction, transaction_id)
    if transaction is None:
        raise ApiError(404, "payment_not_found", "The payment record was not found.")
    owner = (
        transaction.payer_user_id == principal.user_id
        and AuthorizationService().has_permission(
            session,
            user_id=principal.user_id,
            permission_code="payment:view:self",
            resource_owner_id=principal.user_id,
        )
    )
    admin = AuthorizationService().has_permission(
        session, user_id=principal.user_id, permission_code="payment:reconcile:global"
    )
    if not (owner or admin):
        raise ApiError(
            403, "permission_denied", "You are not authorized to reconcile this payment."
        )
    return _service(request).reconcile(
        session,
        transaction=transaction,
        actor_user_id=principal.user_id,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/daraja/callback")
async def daraja_callback(request: Request) -> JSONResponse:
    """Accept Daraja's untrusted callback, then verify its checkout server-to-server."""

    ack = {"ResultCode": 0, "ResultDesc": "Accepted"}
    settings = request.app.state.settings
    if not settings.mpesa_enabled:
        return JSONResponse(content=ack)
    try:
        chunks: list[bytes] = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_CALLBACK_BODY_BYTES:
                logger.warning("daraja_callback_oversized")
                return JSONResponse(content=ack)
            chunks.append(chunk)
        raw = b"".join(chunks)
        if size > MAX_CALLBACK_BODY_BYTES:
            logger.warning("daraja_callback_oversized")
            return JSONResponse(content=ack)
        value = json.loads(raw)
        callback = DarajaCallbackEnvelope.model_validate(value)
    except (json.JSONDecodeError, ValidationError, ValueError, TypeError):
        logger.warning(
            "daraja_callback_invalid request_id=%s", getattr(request.state, "request_id", "-")
        )
        return JSONResponse(content=ack)
    session = request.app.state.session_factory()
    try:
        _service(request).handle_callback(
            session,
            callback=callback,
            request_id=getattr(request.state, "request_id", None),
        )
    except Exception as error:
        # Keep provider payloads and exception details out of logs and responses; a callback retry
        # or scheduled transaction query can reconcile the still-pending record.
        logger.error("daraja_callback_processing_failed error_type=%s", type(error).__name__)
        return JSONResponse(
            status_code=503,
            content={"ResultCode": 1, "ResultDesc": "Temporarily unavailable"},
        )
    finally:
        session.close()
    return JSONResponse(content=ack)


def _response(transaction: PaymentTransaction, request: Request) -> PaymentTransactionResponse:
    from app.services.payments import payment_response

    return payment_response(transaction, request.app.state.settings)
