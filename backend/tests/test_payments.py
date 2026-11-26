"""Phase 12 transaction, Daraja callback, and access-control coverage."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pydantic import SecretStr
from sqlalchemy import select

from app.models.payments import PaymentCallbackEvent, PaymentTransaction
from app.models.services import (
    ServiceBooking,
    ServiceOffering,
    ServiceOrder,
    ServiceProviderProfile,
)
from app.models.user import UserAccount
from app.services.daraja import StkPushResult, StkQueryResult
from app.services.payments import normalize_kenyan_phone
from tests.helpers import create_authenticated_user


class FakeDaraja:
    def __init__(self) -> None:
        self.push_count = 0
        self.query_count = 0
        self.query_result = StkQueryResult("0", "0", "checkout-phase12", None)

    def start_stk_push(self, **_kwargs) -> StkPushResult:
        self.push_count += 1
        return StkPushResult("0", "checkout-phase12", "merchant-phase12")

    def query_stk(self, *, checkout_request_id: str) -> StkQueryResult:
        self.query_count += 1
        assert checkout_request_id == "checkout-phase12"
        return self.query_result


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _enable_sandbox_payments(client, daraja: FakeDaraja) -> None:
    settings = client.app.state.settings
    settings.mpesa_enabled = True
    settings.mpesa_environment = "sandbox"
    settings.mpesa_consumer_key = SecretStr("sandbox-consumer-key")
    settings.mpesa_consumer_secret = SecretStr("sandbox-consumer-secret")
    settings.mpesa_business_shortcode = "174379"
    settings.mpesa_passkey = SecretStr("sandbox-passkey")
    settings.mpesa_callback_base_url = "https://payments.homescout.example"
    settings.mpesa_phone_hash_key = SecretStr("test-payment-hmac-key-is-32-bytes-long")
    client.app.state.daraja_client = daraja


def _accepted_fixed_order(client, *, suffix: str = "one") -> tuple[str, str, str, str]:
    tenant_token = create_authenticated_user(
        client, role_code="tenant", email=f"payment-tenant-{suffix}@example.com"
    )
    provider_token = create_authenticated_user(
        client, role_code="service_provider", email=f"payment-provider-{suffix}@example.com"
    )
    with client.app.state.session_factory() as session:
        tenant = session.scalar(
            select(UserAccount).where(UserAccount.email == f"payment-tenant-{suffix}@example.com")
        )
        provider = session.scalar(
            select(UserAccount).where(UserAccount.email == f"payment-provider-{suffix}@example.com")
        )
        assert tenant and provider
        profile = ServiceProviderProfile(
            provider_user_id=provider.id,
            public_name="Nairobi Moving Co.",
            description="Local moving service.",
            is_published=True,
        )
        offering = ServiceOffering(
            provider_user_id=provider.id,
            title="Apartment moving service",
            category="movers",
            description="A fixed-price local move.",
            pricing_model="fixed",
            price_amount=Decimal("15000"),
            currency="KES",
            availability_schedule={},
            is_active=True,
        )
        session.add_all([profile, offering])
        session.flush()
        booking = ServiceBooking(
            offering_id=offering.id,
            customer_user_id=tenant.id,
            provider_user_id=provider.id,
            requested_at=datetime.now(UTC) + timedelta(days=3),
            timezone="Africa/Nairobi",
            request_details="Moving from Kilimani.",
            status="accepted",
            accepted_at=datetime.now(UTC),
        )
        session.add(booking)
        session.flush()
        order = ServiceOrder(
            booking_id=booking.id,
            customer_user_id=tenant.id,
            provider_user_id=provider.id,
            offering_title_snapshot=offering.title,
            category_snapshot=offering.category,
            estimated_amount_kes=Decimal("15000"),
            pricing_model_snapshot="fixed",
            status="accepted",
        )
        session.add(order)
        session.commit()
        booking_id, order_id = str(booking.id), str(order.id)
    return tenant_token, provider_token, booking_id, order_id


def _request_payment(client, token: str, order_id: str, key: str = "phase12-idempotency-0001"):
    return client.post(
        "/api/v1/payments/service-bookings",
        headers={**_headers(token), "Idempotency-Key": key},
        json={"service_order_id": order_id, "phone_number": "+254712345678"},
    )


def _success_callback(*, merchant_id: str = "merchant-phase12", amount: int = 15_000) -> dict:
    return {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": merchant_id,
                "CheckoutRequestID": "checkout-phase12",
                "ResultCode": 0,
                "ResultDesc": "Processed",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": amount},
                        {"Name": "MpesaReceiptNumber", "Value": "QWE1234567"},
                        {"Name": "TransactionDate", "Value": 20261124103045},
                        {"Name": "PhoneNumber", "Value": 254712345678},
                    ]
                },
            }
        }
    }


def test_payment_is_disabled_by_default_and_does_not_create_attempt(client) -> None:
    tenant_token, _provider, _booking_id, order_id = _accepted_fixed_order(client)
    config = client.get("/api/v1/payments/configuration")
    assert config.status_code == 200
    assert config.json()["mode"] == "disabled"
    assert config.json()["enabled"] is False

    response = _request_payment(client, tenant_token, order_id)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "payments_unavailable"
    with client.app.state.session_factory() as session:
        assert session.scalar(select(PaymentTransaction.id)) is None


def test_fixed_service_order_payment_is_idempotent_and_provider_view_is_redacted(client) -> None:
    tenant_token, provider_token, _booking_id, order_id = _accepted_fixed_order(client)
    daraja = FakeDaraja()
    _enable_sandbox_payments(client, daraja)

    first = _request_payment(client, tenant_token, order_id)
    repeated = _request_payment(client, tenant_token, order_id)
    assert first.status_code == repeated.status_code == 200, first.text
    assert first.json()["status"] == "pending"
    assert first.json()["environment"] == "sandbox"
    assert first.json()["phone_masked"] == "•••• 5678"
    assert first.json()["id"] == repeated.json()["id"]
    assert daraja.push_count == 1

    provider_history = client.get(
        "/api/v1/payments/provider-orders", headers=_headers(provider_token)
    )
    assert provider_history.status_code == 200
    record = provider_history.json()[0]
    assert record["payment_status"] == "pending"
    assert "receipt_number" not in record
    assert "phone" not in str(record).lower()

    cancelled = client.patch(
        f"/api/v1/services/bookings/{_booking_id}",
        headers=_headers(tenant_token),
        json={"action": "cancel"},
    )
    assert cancelled.status_code == 409
    assert cancelled.json()["error"]["code"] == "payment_must_be_resolved_before_cancellation"


def test_verified_callback_is_idempotent_and_saves_only_private_phone_digest(client) -> None:
    tenant_token, _provider_token, _booking_id, order_id = _accepted_fixed_order(client)
    daraja = FakeDaraja()
    _enable_sandbox_payments(client, daraja)
    initiated = _request_payment(client, tenant_token, order_id)
    assert initiated.status_code == 200

    callback = _success_callback()
    first = client.post("/api/v1/payments/daraja/callback", json=callback)
    repeated = client.post("/api/v1/payments/daraja/callback", json=callback)
    assert first.status_code == repeated.status_code == 200
    assert daraja.query_count == 1

    history = client.get("/api/v1/payments/me", headers=_headers(tenant_token))
    assert history.status_code == 200
    assert history.json()[0]["status"] == "successful"
    assert history.json()[0]["receipt_number"] == "QWE1234567"
    with client.app.state.session_factory() as session:
        transaction = session.scalar(select(PaymentTransaction))
        event = session.scalar(select(PaymentCallbackEvent))
        assert transaction is not None and event is not None
        assert transaction.payer_phone_hmac != "254712345678"
        assert event.callback_phone_hmac == transaction.payer_phone_hmac
        assert event.receipt_candidate == "QWE1234567"
        assert event.processing_status == "processed"


def test_callback_reference_mismatch_is_ignored_and_reconciliation_stays_pending(client) -> None:
    tenant_token, _provider_token, _booking_id, order_id = _accepted_fixed_order(client)
    daraja = FakeDaraja()
    daraja.query_result = StkQueryResult("0", None, "checkout-phase12", None)
    _enable_sandbox_payments(client, daraja)
    initiated = _request_payment(client, tenant_token, order_id)
    assert initiated.status_code == 200

    mismatch = client.post(
        "/api/v1/payments/daraja/callback",
        json=_success_callback(merchant_id="other-merchant"),
    )
    assert mismatch.status_code == 200
    assert daraja.query_count == 0
    status = client.post(
        f"/api/v1/payments/{initiated.json()['id']}/reconcile",
        headers=_headers(tenant_token),
    )
    assert status.status_code == 200
    assert status.json()["status"] == "pending"
    assert status.json()["receipt_number"] is None
    assert daraja.query_count == 1


def test_provider_confirmed_cancellation_is_terminal_without_fabricated_receipt(client) -> None:
    tenant_token, _provider_token, _booking_id, order_id = _accepted_fixed_order(client)
    daraja = FakeDaraja()
    daraja.query_result = StkQueryResult("0", "1032", "checkout-phase12", None)
    _enable_sandbox_payments(client, daraja)
    initiated = _request_payment(client, tenant_token, order_id)
    assert initiated.status_code == 200

    callback = _success_callback()
    callback["Body"]["stkCallback"]["ResultCode"] = 1032
    callback["Body"]["stkCallback"]["ResultDesc"] = "Request cancelled"
    response = client.post("/api/v1/payments/daraja/callback", json=callback)
    assert response.status_code == 200
    history = client.get("/api/v1/payments/me", headers=_headers(tenant_token))
    assert history.json()[0]["status"] == "cancelled"
    assert history.json()[0]["receipt_number"] is None


def test_payment_history_is_owner_scoped_and_phone_input_is_normalized(client) -> None:
    tenant_token, _provider_token, _booking_id, order_id = _accepted_fixed_order(client)
    other_tenant = create_authenticated_user(
        client, role_code="tenant", email="payment-other-tenant@example.com"
    )
    _enable_sandbox_payments(client, FakeDaraja())
    initiated = _request_payment(client, tenant_token, order_id)
    assert initiated.status_code == 200
    hidden = client.get(
        f"/api/v1/payments/{initiated.json()['id']}", headers=_headers(other_tenant)
    )
    assert hidden.status_code == 403
    assert normalize_kenyan_phone("0712 345 678") == "254712345678"
    assert normalize_kenyan_phone("+254112345678") == "254112345678"
