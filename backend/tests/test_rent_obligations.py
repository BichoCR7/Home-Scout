"""Phase 5 private rent obligations and user-reported external payments."""

from uuid import UUID, uuid4

from sqlalchemy import select

from app.models.smartrent import RentObligation, RentPaymentRecord
from tests.helpers import create_authenticated_user


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_obligation(client, token: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/finance/rent-obligations",
        headers=_headers(token),
        json={
            "title": "Kilimani rent · December",
            "amount_kes": "30000.00",
            "due_date": "2026-12-01",
            "property_reference": "Kilimani apartment",
            "notes": "Personal reminder only",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_rent_obligation_and_partial_external_payment_reports_are_private_and_idempotent(client):
    token = create_authenticated_user(
        client, role_code="tenant", email="rent-obligation-owner@example.com"
    )
    other_token = create_authenticated_user(
        client, role_code="tenant", email="rent-obligation-other@example.com"
    )
    obligation = _create_obligation(client, token)
    assert obligation["lease_verified"] is False
    assert obligation["payment_status"] == "not_confirmed_by_homescout"
    assert obligation["remaining_based_on_reports_kes"] == "30000.00"

    request_id = str(uuid4())
    partial = {
        "amount_kes": "10000.00",
        "payment_method": "mpesa",
        "paid_on": "2026-11-24",
        "reference": "private-reference-1",
        "notes": "Manual note only",
        "request_id": request_id,
    }
    saved = client.post(
        f"/api/v1/finance/rent-obligations/{obligation['id']}/payments",
        headers=_headers(token),
        json=partial,
    )
    assert saved.status_code == 201, saved.text
    payload = saved.json()
    assert payload["reported_total_kes"] == "10000.00"
    assert payload["remaining_based_on_reports_kes"] == "20000.00"
    assert payload["payment_report_state"] == "partial_payment_reported_not_verified"
    assert payload["payments"][0]["report_status"] == "reported_by_user"
    assert payload["payments"][0]["provider_confirmed"] is False
    assert payload["payments"][0]["money_moved_by_homescout"] is False

    repeated = client.post(
        f"/api/v1/finance/rent-obligations/{obligation['id']}/payments",
        headers=_headers(token),
        json=partial,
    )
    assert repeated.status_code == 201
    assert repeated.json()["reported_total_kes"] == "10000.00"

    full = client.post(
        f"/api/v1/finance/rent-obligations/{obligation['id']}/payments",
        headers=_headers(token),
        json={
            "amount_kes": "20000.00",
            "payment_method": "bank_transfer",
            "paid_on": "2026-11-25",
            "request_id": str(uuid4()),
        },
    )
    assert full.status_code == 201
    assert full.json()["remaining_based_on_reports_kes"] == "0.00"
    assert full.json()["payment_report_state"] == "amount_fully_reported_not_verified"
    assert full.json()["payment_status"] == "not_confirmed_by_homescout"

    inconsistent_edit = client.put(
        f"/api/v1/finance/rent-obligations/{obligation['id']}",
        headers=_headers(token),
        json={
            "title": "Rent below reported payments",
            "amount_kes": "29999.00",
            "due_date": "2026-12-01",
            "property_reference": "Kilimani apartment",
            "notes": None,
            "status": "open",
        },
    )
    assert inconsistent_edit.status_code == 409
    assert inconsistent_edit.json()["error"]["code"] == "rent_obligation_below_reported_payments"

    over_balance = client.post(
        f"/api/v1/finance/rent-obligations/{obligation['id']}/payments",
        headers=_headers(token),
        json={
            "amount_kes": "1.00",
            "payment_method": "cash",
            "paid_on": "2026-11-25",
            "request_id": str(uuid4()),
        },
    )
    assert over_balance.status_code == 409
    assert over_balance.json()["error"]["code"] == "rent_report_exceeds_balance"

    assert (
        client.get("/api/v1/finance/rent-obligations", headers=_headers(other_token)).json() == []
    )
    assert (
        client.delete(
            f"/api/v1/finance/rent-obligations/{obligation['id']}", headers=_headers(other_token)
        ).status_code
        == 404
    )

    with client.app.state.session_factory() as session:
        obligation_row = session.get(RentObligation, UUID(obligation["id"]))
        payment_row = session.scalar(select(RentPaymentRecord))
        assert obligation_row is not None and payment_row is not None
        assert b"30000" not in obligation_row.encrypted_data
        assert b"private-reference-1" not in payment_row.encrypted_data


def test_rent_obligation_edit_cancel_delete_and_payment_option_disclosures(client):
    token = create_authenticated_user(
        client, role_code="tenant", email="rent-obligation-lifecycle@example.com"
    )
    obligation = _create_obligation(client, token)
    updated = client.put(
        f"/api/v1/finance/rent-obligations/{obligation['id']}",
        headers=_headers(token),
        json={
            "title": "Revised rent due",
            "amount_kes": "32000.00",
            "due_date": "2026-12-03",
            "property_reference": "Kilimani apartment",
            "notes": None,
            "status": "cancelled",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["amount_kes"] == "32000.00"
    assert updated.json()["status"] == "cancelled"
    assert (
        client.delete(
            f"/api/v1/finance/rent-obligations/{obligation['id']}", headers=_headers(token)
        ).status_code
        == 204
    )

    methods = client.get("/api/v1/payments/configuration").json()["methods"]
    by_code = {item["code"]: item for item in methods}
    assert by_code["mpesa"]["live_rent_checkout"] is False
    assert by_code["visa"]["status"] == "not_configured"
    assert by_code["mastercard"]["status"] == "not_configured"
    assert by_code["paypal"]["status"] == "not_configured"
    assert by_code["bank_transfer"]["status"] == "manual_record_only"
