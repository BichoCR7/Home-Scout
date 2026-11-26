"""Phase 9 verification, moderation, evidence privacy, and viewing safety tests."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID

from app.models.marketplace import PropertyReport, PropertyReportReview
from app.models.personal_hub import PrivateDocument
from app.models.property import Property
from app.models.trust import (
    SafetyIncidentReport,
    SafeViewing,
    VerificationCase,
    VerificationHistory,
)
from tests.helpers import create_authenticated_user
from tests.test_marketplace import PNG_1X1, _publish_listing


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _upload_verification_document(client, token: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/hub/documents?category=verification&filename=identity-evidence.png",
        headers={**_headers(token), "Content-Type": "image/png"},
        content=PNG_1X1,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_manual_verification_encrypted_evidence_history_and_expiry(client) -> None:
    landlord = create_authenticated_user(
        client, role_code="landlord", email="verification-owner@example.com"
    )
    reviewer = create_authenticated_user(
        client, role_code="admin", email="verification-reviewer@example.com"
    )
    tenant = create_authenticated_user(
        client, role_code="tenant", email="verification-tenant@example.com"
    )
    listing = _publish_listing(client, landlord, title="Verification test home", rent=52_000)
    document = _upload_verification_document(client, landlord)
    document_id = UUID(document["id"])

    with client.app.state.session_factory() as session:
        stored_document = session.get(PrivateDocument, document_id)
        assert stored_document is not None
        assert stored_document.storage_encrypted is True
        encrypted_path = (
            client.app.state.settings.private_document_storage_dir / stored_document.storage_key
        )
        assert Path(encrypted_path).read_bytes() != PNG_1X1

    owner_download = client.get(
        f"/api/v1/hub/documents/{document_id}/download", headers=_headers(landlord)
    )
    assert owner_download.status_code == 200
    assert owner_download.content == PNG_1X1

    submitted = client.post(
        "/api/v1/trust/verifications",
        headers=_headers(landlord),
        json={
            "subject_type": "landlord",
            "evidence_document_ids": [str(document_id)],
            "submission_note": "Please review this identity evidence.",
        },
    )
    assert submitted.status_code == 201, submitted.text
    case_id = submitted.json()["id"]
    assert submitted.json()["status"] == "pending"
    assert submitted.json()["history"][0]["action"] == "submitted"

    denied = client.get("/api/v1/trust/verifications/queue", headers=_headers(tenant))
    assert denied.status_code == 403
    queue = client.get("/api/v1/trust/verifications/queue", headers=_headers(reviewer))
    assert queue.status_code == 200
    assert queue.json()[0]["evidence"][0]["document_id"] == str(document_id)
    evidence_id = queue.json()[0]["evidence"][0]["id"]

    reviewer_download = client.get(
        f"/api/v1/trust/verifications/{case_id}/evidence/{evidence_id}/download",
        headers=_headers(reviewer),
    )
    assert reviewer_download.status_code == 200
    assert reviewer_download.content == PNG_1X1

    approved = client.post(
        f"/api/v1/trust/verifications/{case_id}/review",
        headers=_headers(reviewer),
        json={
            "decision": "approved",
            "expires_on": (date.today() + timedelta(days=20)).isoformat(),
        },
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["history"][-1]["action"] == "approved"

    indicators = client.get(f"/api/v1/trust/indicators/{listing['id']}")
    assert indicators.status_code == 200
    assert indicators.json()["listing_contact_account_check"] == "approved"
    assert indicators.json()["authorized_agent_account_check"] == "not_verified"
    assert indicators.json()["property_verification"] == "not_submitted"
    assert indicators.json()["trust_score"] is None
    assert indicators.json()["review_count"] == 0

    with client.app.state.session_factory() as session:
        case = session.get(VerificationCase, UUID(case_id))
        assert case is not None
        case.expires_on = date.today() - timedelta(days=1)
        session.commit()
    expired = client.get("/api/v1/trust/verifications/mine", headers=_headers(landlord))
    assert expired.status_code == 200
    assert expired.json()[0]["status"] == "expired"
    with client.app.state.session_factory() as session:
        actions = list(
            session.query(VerificationHistory.action)
            .filter(VerificationHistory.case_id == UUID(case_id))
            .all()
        )
        assert [item[0] for item in actions] == ["submitted", "approved", "expired"]

    request_again = client.post(
        "/api/v1/trust/verifications",
        headers=_headers(landlord),
        json={"subject_type": "landlord", "evidence_document_ids": [str(document_id)]},
    )
    assert request_again.status_code == 201
    assert request_again.json()["submission_number"] == 2
    assert request_again.json()["history"][-1]["action"] == "resubmitted"


def test_verification_submission_rejects_duplicate_evidence_documents(client) -> None:
    landlord = create_authenticated_user(
        client, role_code="landlord", email="duplicate-verification-evidence@example.com"
    )
    document = _upload_verification_document(client, landlord)
    response = client.post(
        "/api/v1/trust/verifications",
        headers=_headers(landlord),
        json={
            "subject_type": "landlord",
            "evidence_document_ids": [document["id"], document["id"]],
        },
    )
    assert response.status_code == 422
    assert client.get("/api/v1/trust/verifications/mine", headers=_headers(landlord)).json() == []


def test_listing_reports_moderation_evidence_and_manual_visibility_action(client) -> None:
    landlord = create_authenticated_user(
        client, role_code="landlord", email="moderation-property-owner@example.com"
    )
    renter = create_authenticated_user(
        client, role_code="tenant", email="moderation-renter@example.com"
    )
    moderator = create_authenticated_user(
        client, role_code="moderator", email="trust-moderator@example.com"
    )
    listing = _publish_listing(client, landlord, title="Reported Kilimani home", rent=42_000)
    evidence = _upload_verification_document(client, renter)
    report = client.post(
        f"/api/v1/marketplace/properties/{listing['id']}/reports",
        headers=_headers(renter),
        json={
            "reason": "suspected_scam",
            "details": "The contact asked me for a deposit before a viewing.",
            "evidence_document_ids": [evidence["id"]],
        },
    )
    assert report.status_code == 201, report.text
    report_id = UUID(report.json()["id"])
    assert report.json()["status"] == "received"
    assert client.get(f"/api/v1/properties/{listing['id']}").status_code == 200

    with client.app.state.session_factory() as session:
        stored = session.get(PropertyReport, report_id)
        assert stored is not None
        assert stored.details is None
        assert stored.encrypted_details is not None
        assert b"deposit" not in stored.encrypted_details

    denied = client.get("/api/v1/trust/moderation/queue", headers=_headers(renter))
    assert denied.status_code == 403
    queue = client.get("/api/v1/trust/moderation/queue", headers=_headers(moderator))
    assert queue.status_code == 200
    row = next(item for item in queue.json() if item["id"] == str(report_id))
    assert row["details"] == "The contact asked me for a deposit before a viewing."
    assert row["evidence_document_ids"] == [evidence["id"]]

    downloaded = client.get(
        f"/api/v1/trust/moderation/listing/{report_id}/evidence/{evidence['id']}/download",
        headers=_headers(moderator),
    )
    assert downloaded.status_code == 200
    assert downloaded.content == PNG_1X1

    reviewed = client.post(
        f"/api/v1/trust/moderation/listing/{report_id}/review",
        headers=_headers(moderator),
        json={
            "action": "resolved",
            "internal_note": "Listing details are being checked.",
            "public_message": "We reviewed your report and temporarily hid the listing.",
            "listing_action": "hide",
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "resolved"
    assert client.get(f"/api/v1/properties/{listing['id']}").status_code == 404

    reporter_status = client.get("/api/v1/trust/listing-reports/mine", headers=_headers(renter))
    assert reporter_status.status_code == 200
    assert reporter_status.json()[0]["status"] == "resolved"
    assert "temporarily hid" in reporter_status.json()[0]["resolution_message"]
    with client.app.state.session_factory() as session:
        assert session.get(Property, UUID(listing["id"])).moderation_status == "under_review"
        reviews = list(session.query(PropertyReportReview).filter_by(report_id=report_id).all())
        assert len(reviews) == 1
        assert reviews[0].action == "resolved"
        assert reviews[0].internal_note == "Listing details are being checked."


def test_safe_viewing_private_consent_and_safety_report_review(client) -> None:
    owner = create_authenticated_user(client, role_code="tenant", email="viewing-owner@example.com")
    trusted_person = create_authenticated_user(
        client, role_code="tenant", email="viewing-contact@example.com"
    )
    unrelated = create_authenticated_user(
        client, role_code="tenant", email="viewing-unrelated@example.com"
    )
    moderator = create_authenticated_user(
        client, role_code="moderator", email="viewing-moderator@example.com"
    )
    contact_id = client.get("/api/v1/auth/me", headers=_headers(trusted_person)).json()["id"]
    starts_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    created = client.post(
        "/api/v1/trust/viewings",
        headers=_headers(owner),
        json={
            "title": "Viewing on Ngong Road",
            "starts_at": starts_at,
            "meeting_point": "Outside the main gate",
            "trusted_contact_name": "Trusted contact",
            "trusted_contact_phone": "+254700111222",
            "notes": "Ask about written lease terms.",
            "share_with_user_id": contact_id,
            "consent_to_share_details": True,
        },
    )
    assert created.status_code == 201, created.text
    viewing_id = UUID(created.json()["id"])
    assert created.json()["details_share_consented"] is True
    assert created.json()["trusted_contact_phone"] == "+254700111222"

    with client.app.state.session_factory() as session:
        stored_viewing = session.get(SafeViewing, viewing_id)
        assert stored_viewing is not None
        assert b"Ngong Road" not in stored_viewing.encrypted_data
        assert b"+254700111222" not in stored_viewing.encrypted_data

    shared = client.get("/api/v1/trust/viewings", headers=_headers(trusted_person))
    assert shared.status_code == 200
    assert shared.json()[0]["meeting_point"] == "Outside the main gate"
    private = client.get("/api/v1/trust/viewings", headers=_headers(unrelated))
    assert private.status_code == 200
    assert private.json() == []

    check_in = client.post(f"/api/v1/trust/viewings/{viewing_id}/check-in", headers=_headers(owner))
    assert check_in.status_code == 200
    assert check_in.json()["status"] == "checked_in"
    check_out = client.post(
        f"/api/v1/trust/viewings/{viewing_id}/check-out", headers=_headers(owner)
    )
    assert check_out.status_code == 200
    assert check_out.json()["status"] == "checked_out"

    incident = client.post(
        "/api/v1/trust/safety-reports",
        headers=_headers(owner),
        json={
            "category": "pressure_or_threat",
            "viewing_id": str(viewing_id),
            "details": "The listing contact pressured me to pay a deposit.",
        },
    )
    assert incident.status_code == 201, incident.text
    incident_id = UUID(incident.json()["id"])
    assert incident.json()["status"] == "received"
    with client.app.state.session_factory() as session:
        record = session.get(SafetyIncidentReport, incident_id)
        assert record is not None
        assert b"pressured" not in record.encrypted_details

    review = client.post(
        f"/api/v1/trust/moderation/safety_incident/{incident_id}/review",
        headers=_headers(moderator),
        json={"action": "in_review", "internal_note": "Requesting additional context."},
    )
    assert review.status_code == 200
    own_reports = client.get("/api/v1/trust/safety-reports/mine", headers=_headers(owner))
    assert own_reports.status_code == 200
    assert own_reports.json()[0]["status"] == "in_review"
    assert own_reports.json()[0]["details"] == "The listing contact pressured me to pay a deposit."
    assert client.get("/api/v1/trust/safety-reports/mine", headers=_headers(unrelated)).json() == []
