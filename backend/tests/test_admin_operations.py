"""Phase 14 staff operations authorization, privacy, and audit coverage."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.models.audit import AuditEvent
from app.models.auth import AuthSession
from app.models.property import Property
from tests.helpers import create_authenticated_user
from tests.test_marketplace import _publish_listing
from tests.test_services import _published_provider


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_operations_overview_is_restricted_and_contains_only_operational_counts(client) -> None:
    tenant = create_authenticated_user(client, role_code="tenant", email="ops-tenant@example.com")
    admin = create_authenticated_user(client, role_code="admin", email="ops-admin@example.com")

    denied = client.get("/api/v1/admin/operations/overview", headers=_headers(tenant))
    assert denied.status_code == 403

    allowed = client.get("/api/v1/admin/operations/overview", headers=_headers(admin))
    assert allowed.status_code == 200, allowed.text
    payload = allowed.json()
    assert payload["users_total"] >= 2
    assert payload["service_reviews_pending"] == 0
    assert "payments_total" not in payload
    assert "financial_records" not in payload


def test_staff_support_queue_hides_messages_until_audited_ticket_open(client) -> None:
    owner = create_authenticated_user(client, role_code="tenant", email="ticket-owner@example.com")
    admin = create_authenticated_user(client, role_code="admin", email="ticket-agent@example.com")
    ticket = client.post(
        "/api/v1/hub/support/tickets",
        headers=_headers(owner),
        json={
            "subject": "Help with my profile",
            "category": "account",
            "message": "Please help update my profile details.",
        },
    )
    assert ticket.status_code == 201, ticket.text
    ticket_id = ticket.json()["id"]

    queue = client.get("/api/v1/admin/operations/support/tickets", headers=_headers(admin))
    assert queue.status_code == 200, queue.text
    row = next(item for item in queue.json() if item["id"] == ticket_id)
    assert row["messages"] == []

    detail = client.get(
        f"/api/v1/admin/operations/support/tickets/{ticket_id}", headers=_headers(admin)
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["messages"][0]["body"] == "Please help update my profile details."
    assert (
        client.post(
            f"/api/v1/admin/operations/support/tickets/{ticket_id}/reply",
            headers=_headers(admin),
            json={"body": "We have received your request and will help shortly."},
        ).json()["status"]
        == "waiting"
    )
    owner_view = client.get("/api/v1/hub/support/tickets", headers=_headers(owner))
    assert any(
        message["body"] == "We have received your request and will help shortly."
        for message in owner_view.json()[0]["messages"]
    )

    with client.app.state.session_factory() as session:
        audit = session.scalar(
            select(AuditEvent).where(
                AuditEvent.event_type == "admin.support_ticket_viewed",
                AuditEvent.subject_id == ticket_id,
            )
        )
        assert audit is not None


def test_account_restrictions_reauthenticate_block_self_and_revoke_sessions(client) -> None:
    admin = create_authenticated_user(client, role_code="admin", email="restrict-admin@example.com")
    target = create_authenticated_user(
        client, role_code="tenant", email="restrict-target@example.com"
    )
    target_user_id = client.get("/api/v1/auth/me", headers=_headers(target)).json()["id"]
    request = {
        "status": "suspended",
        "current_password": "HomeScout-Test-Password-734!",
        "reason": "Repeated policy violations were reviewed by operations.",
    }
    suspended = client.patch(
        f"/api/v1/admin/operations/users/{target_user_id}/status",
        headers=_headers(admin),
        json=request,
    )
    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["status"] == "suspended"
    assert client.get("/api/v1/auth/me", headers=_headers(target)).status_code == 401

    own_id = client.get("/api/v1/auth/me", headers=_headers(admin)).json()["id"]
    self_action = client.patch(
        f"/api/v1/admin/operations/users/{own_id}/status",
        headers=_headers(admin),
        json=request,
    )
    assert self_action.status_code == 403
    with client.app.state.session_factory() as session:
        sessions = session.scalars(
            select(AuthSession).where(AuthSession.user_id == UUID(target_user_id))
        ).all()
        assert sessions and all(row.revoked_at is not None for row in sessions)


def test_listing_moderation_uses_audited_state_and_excludes_demo_rows(client) -> None:
    landlord = create_authenticated_user(
        client, role_code="landlord", email="listing-ops-owner@example.com"
    )
    admin = create_authenticated_user(
        client, role_code="admin", email="listing-ops-admin@example.com"
    )
    listing = _publish_listing(client, landlord, title="Ops review apartment", rent=62_000)
    listings = client.get("/api/v1/admin/operations/listings", headers=_headers(admin))
    assert listings.status_code == 200, listings.text
    assert any(row["id"] == listing["id"] for row in listings.json())

    response = client.patch(
        f"/api/v1/admin/operations/listings/{listing['id']}/moderation",
        headers=_headers(admin),
        json={"status": "under_review", "reason": "The reported details need a staff review."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["moderation_status"] == "under_review"
    with client.app.state.session_factory() as session:
        row = session.get(Property, UUID(listing["id"]))
        assert row is not None and row.moderation_status == "under_review"


def test_service_review_moderation_is_authorized_audited_and_removes_public_visibility(
    client,
) -> None:
    landlord = create_authenticated_user(
        client, role_code="landlord", email="review-ops-landlord@example.com"
    )
    customer = create_authenticated_user(
        client, role_code="tenant", email="review-ops-customer@example.com"
    )
    provider = create_authenticated_user(
        client, role_code="service_provider", email="review-ops-provider@example.com"
    )
    admin = create_authenticated_user(
        client, role_code="admin", email="review-ops-admin@example.com"
    )
    listing = _publish_listing(client, landlord, title="Review moderation home", rent=54_000)
    offering = _published_provider(client, provider, county_id=listing["location"]["county_id"])
    booking = client.post(
        "/api/v1/services/bookings",
        headers=_headers(customer),
        json={
            "offering_id": offering["id"],
            "requested_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "timezone": "Africa/Nairobi",
            "request_details": "Please help move a few boxes and a desk.",
        },
    )
    booking_id = booking.json()["id"]
    for action in ("accept", "complete"):
        response = client.patch(
            f"/api/v1/services/bookings/{booking_id}",
            headers=_headers(provider),
            json={"action": action, "note": "Service update recorded."},
        )
        assert response.status_code == 200, response.text
    review = client.post(
        f"/api/v1/services/bookings/{booking_id}/review",
        headers=_headers(customer),
        json={"rating": 1, "review_text": "A test review for staff moderation."},
    )
    assert review.status_code == 201, review.text
    review_id = review.json()["id"]
    public_url = f"/api/v1/services/offerings/{offering['id']}/reviews"
    assert len(client.get(public_url).json()) == 1

    denied = client.get("/api/v1/admin/operations/reviews/services", headers=_headers(customer))
    assert denied.status_code == 403
    held = client.patch(
        f"/api/v1/admin/operations/reviews/services/{review_id}/moderation",
        headers=_headers(admin),
        json={"status": "removed", "reason": "The review requires a staff policy review."},
    )
    assert held.status_code == 200, held.text
    assert held.json()["moderation_status"] == "removed"
    assert client.get(public_url).json() == []
    with client.app.state.session_factory() as session:
        audit = session.scalar(
            select(AuditEvent).where(
                AuditEvent.event_type == "admin.service_review_moderation_changed",
                AuditEvent.subject_id == review_id,
            )
        )
        assert audit is not None


def test_super_admin_platform_settings_apply_to_support_intake(client) -> None:
    admin = create_authenticated_user(client, role_code="admin", email="settings-admin@example.com")
    super_admin = create_authenticated_user(
        client, role_code="super_admin", email="settings-root@example.com"
    )
    denied = client.get("/api/v1/admin/operations/settings", headers=_headers(admin))
    assert denied.status_code == 403

    changed = client.put(
        "/api/v1/admin/operations/settings/support.allow_new_tickets",
        headers=_headers(super_admin),
        json={"value": False},
    )
    assert changed.status_code == 200, changed.text
    owner = create_authenticated_user(
        client, role_code="tenant", email="settings-owner@example.com"
    )
    ticket = client.post(
        "/api/v1/hub/support/tickets",
        headers=_headers(owner),
        json={
            "subject": "Need help",
            "category": "account",
            "message": "Please review this account issue.",
        },
    )
    assert ticket.status_code == 503


def test_verification_queue_and_audit_history_remain_permission_scoped(client) -> None:
    tenant = create_authenticated_user(
        client, role_code="tenant", email="verify-tenant-ops@example.com"
    )
    admin = create_authenticated_user(
        client, role_code="admin", email="verify-admin-ops@example.com"
    )
    assert (
        client.get("/api/v1/trust/verifications/queue", headers=_headers(tenant)).status_code == 403
    )
    queue = client.get("/api/v1/trust/verifications/queue", headers=_headers(admin))
    assert queue.status_code == 200, queue.text
    audit = client.get("/api/v1/admin/operations/audit", headers=_headers(admin))
    assert audit.status_code == 200, audit.text
