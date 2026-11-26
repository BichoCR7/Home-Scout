"""Private personal hub account, schedule, records, and storage behavior."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.models.notification import InAppNotification
from tests.test_authentication import login, register_and_verify


def _token(client, email: str) -> str:
    register_and_verify(client, email)
    return login(client, email)["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_profile_preferences_role_switch_and_export_are_account_scoped(client) -> None:
    token = _token(client, "hub-profile@example.com")
    headers = _headers(token)

    updated = client.patch(
        "/api/v1/hub/profile",
        headers=headers,
        json={
            "given_name": "Amani",
            "phone_number": "+254 718 623 114",
            "location_label": "Westlands, Nairobi",
            "bio": "Looking for a long-term rental.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["phone_number"] == "+254718623114"
    assert updated.json()["given_name"] == "Amani"
    assert updated.json()["location_label"] == "Westlands, Nairobi"
    assert updated.json()["bio"] == "Looking for a long-term rental."
    assert updated.json()["roles"] == ["tenant"]
    assert updated.json()["phone_verified"] is False
    stored_profile = client.get("/api/v1/hub/profile", headers=headers)
    assert stored_profile.status_code == 200
    assert stored_profile.json()["given_name"] == "Amani"
    assert stored_profile.json()["phone_number"] == "+254718623114"
    assert stored_profile.json()["location_label"] == "Westlands, Nairobi"
    assert stored_profile.json()["bio"] == "Looking for a long-term rental."
    assert updated.json()["id"] == client.get("/api/v1/auth/me", headers=headers).json()["id"]
    other_headers = _headers(_token(client, "hub-profile-other@example.com"))
    other_profile = client.get("/api/v1/hub/profile", headers=other_headers)
    assert other_profile.status_code == 200
    assert other_profile.json()["location_label"] is None
    assert other_profile.json()["bio"] is None

    switched = client.put(
        "/api/v1/hub/profile/active-role", headers=headers, json={"role_code": "tenant"}
    )
    assert switched.status_code == 200
    rejected = client.put(
        "/api/v1/hub/profile/active-role", headers=headers, json={"role_code": "admin"}
    )
    assert rejected.status_code == 403

    saved = client.patch(
        "/api/v1/hub/preferences",
        headers=headers,
        json={
            "appearance": "dark",
            "notification_preferences": {"in_app": True, "email": False},
            "accessibility_preferences": {"larger_text": True},
        },
    )
    assert saved.status_code == 200
    assert saved.json()["appearance"] == "dark"
    assert saved.json()["notification_preferences"]["email"] is False

    exported = client.get("/api/v1/hub/account/export", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["product"] == "HomeScout"
    assert exported.json()["profile"]["location_label"] == "Westlands, Nairobi"


def test_saved_collections_are_private_and_sharing_is_explicit(client) -> None:
    owner_token = _token(client, "hub-collection-owner@example.com")
    other_token = _token(client, "hub-collection-other@example.com")
    owner_headers = _headers(owner_token)
    other_headers = _headers(other_token)

    created = client.post(
        "/api/v1/hub/collections",
        headers=owner_headers,
        json={"name": "Nairobi shortlist", "description": "Areas to explore"},
    )
    assert created.status_code == 201
    assert created.json()["can_edit"] is True
    assert created.json()["shared_with_user_ids"] == []
    collection_id = created.json()["id"]
    item = client.post(
        "/api/v1/hub/saved",
        headers=owner_headers,
        json={
            "kind": "neighbourhood",
            "title": "Kilimani",
            "target_path": "/discover?query=Kilimani",
            "collection_id": collection_id,
            "personal_note": "Check commute options",
        },
    )
    assert item.status_code == 201
    assert (
        client.get(
            f"/api/v1/hub/collections/{collection_id}/items", headers=other_headers
        ).status_code
        == 404
    )

    shared = client.post(
        f"/api/v1/hub/collections/{collection_id}/share",
        headers=owner_headers,
        json={"user_id": client.get("/api/v1/auth/me", headers=other_headers).json()["id"]},
    )
    assert shared.status_code == 204
    owner_collection = client.get(f"/api/v1/hub/collections/{collection_id}", headers=owner_headers)
    viewer_collection = client.get(
        f"/api/v1/hub/collections/{collection_id}", headers=other_headers
    )
    assert owner_collection.json()["can_edit"] is True
    assert owner_collection.json()["shared_with_user_ids"] == [
        client.get("/api/v1/auth/me", headers=other_headers).json()["id"]
    ]
    assert viewer_collection.json()["can_edit"] is False
    assert viewer_collection.json()["shared_with_user_ids"] == []
    visible = client.get(f"/api/v1/hub/collections/{collection_id}/items", headers=other_headers)
    assert visible.status_code == 200
    assert visible.json()[0]["title"] == "Kilimani"
    assert (
        client.delete(f"/api/v1/hub/saved/{item.json()['id']}", headers=other_headers).status_code
        == 404
    )
    renamed = client.patch(
        f"/api/v1/hub/collections/{collection_id}",
        headers=owner_headers,
        json={"name": "Kilimani shortlist"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["can_edit"] is True
    assert renamed.json()["shared_with_user_ids"] == owner_collection.json()["shared_with_user_ids"]


def test_schedule_uses_timezone_and_enforces_ownership(client) -> None:
    owner = _token(client, "hub-schedule-owner@example.com")
    other = _token(client, "hub-schedule-other@example.com")
    starts = (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0)
    created = client.post(
        "/api/v1/hub/schedule",
        headers=_headers(owner),
        json={
            "title": "View a home in Kilimani",
            "category": "viewing",
            "starts_at": starts.isoformat(),
            "timezone": "Africa/Nairobi",
            "reminder_minutes": 60,
        },
    )
    assert created.status_code == 201
    assert created.json()["timezone"] == "Africa/Nairobi"
    entry_id = created.json()["id"]
    assert (
        client.patch(
            f"/api/v1/hub/schedule/{entry_id}",
            headers=_headers(other),
            json={"title": "Changed by another account"},
        ).status_code
        == 404
    )
    edited = client.patch(
        f"/api/v1/hub/schedule/{entry_id}",
        headers=_headers(owner),
        json={"status": "done"},
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "done"
    assert (
        client.post(
            "/api/v1/hub/schedule",
            headers=_headers(owner),
            json={"title": "Naive timestamp", "starts_at": "2026-11-25T09:00:00"},
        ).status_code
        == 422
    )


def test_private_documents_support_and_manual_records(client) -> None:
    owner = _token(client, "hub-doc-owner@example.com")
    other = _token(client, "hub-doc-other@example.com")
    headers = _headers(owner)
    uploaded = client.post(
        "/api/v1/hub/documents?category=agreement&filename=tenancy.pdf",
        headers={**headers, "Content-Type": "application/pdf"},
        content=b"%PDF-1.4\nHomeScout private test\n",
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]
    downloaded = client.get(f"/api/v1/hub/documents/{document_id}/download", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"%PDF-")
    assert (
        client.get(
            f"/api/v1/hub/documents/{document_id}/download", headers=_headers(other)
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/hub/documents?category=agreement",
            headers=headers,
            content=b"not a pdf",
        ).status_code
        == 422
    )

    record = client.post(
        "/api/v1/hub/records",
        headers=headers,
        json={
            "category": "rent",
            "title": "November rent note",
            "amount": "28000.00",
            "record_date": datetime.now(UTC).isoformat(),
            "notes": "Entered by me",
        },
    )
    assert record.status_code == 201
    assert record.json()["currency"] == "KES"
    assert record.json()["evidence_status"] == "user_entered"

    ticket = client.post(
        "/api/v1/hub/support/tickets",
        headers=headers,
        json={
            "subject": "Need help",
            "category": "technical",
            "message": "I need help with settings.",
        },
    )
    assert ticket.status_code == 201
    ticket_id = ticket.json()["id"]
    assert (
        client.post(
            f"/api/v1/hub/support/tickets/{ticket_id}/messages",
            headers=_headers(other),
            json={"body": "This is not my ticket"},
        ).status_code
        == 404
    )


def test_activity_notifications_and_deletion_require_owner_and_reauthentication(client) -> None:
    token = _token(client, "hub-private@example.com")
    other = _token(client, "hub-private-other@example.com")
    headers = _headers(token)
    created = client.post(
        "/api/v1/hub/activity",
        headers=headers,
        json={
            "event_type": "property_view",
            "title": "Viewed a sample listing",
            "target_path": "/property/abc",
        },
    )
    assert created.status_code == 201
    assert len(client.get("/api/v1/hub/activity", headers=headers).json()) == 1
    assert client.get("/api/v1/hub/activity", headers=_headers(other)).json() == []

    user_id = UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])
    db = client.app.state.session_factory()
    notification = InAppNotification(
        recipient_user_id=user_id,
        category="account",
        title="Security update",
        body="A session was ended.",
        target_path="/hub/profile",
    )
    db.add(notification)
    db.commit()
    notification_id = str(notification.id)
    db.close()
    assert (
        client.get("/api/v1/hub/notifications", headers=headers).json()[0]["title"]
        == "Security update"
    )
    read = client.post(f"/api/v1/hub/notifications/{notification_id}/read", headers=headers)
    assert read.status_code == 200 and read.json()["read_at"]
    assert (
        client.post(
            f"/api/v1/hub/notifications/{notification_id}/dismiss", headers=_headers(other)
        ).status_code
        == 404
    )

    password = "a-secure-passphrase-2026"
    denied = client.post(
        "/api/v1/hub/account/deletion-requests",
        headers=headers,
        json={"current_password": "wrong", "confirmation": "DELETE"},
    )
    assert denied.status_code == 403
    invalid_confirmation = client.post(
        "/api/v1/hub/account/deletion-requests",
        headers=headers,
        json={"current_password": password, "confirmation": "DELETE NOW"},
    )
    assert invalid_confirmation.status_code == 422
    requested = client.post(
        "/api/v1/hub/account/deletion-requests",
        headers=headers,
        json={"current_password": password, "confirmation": "DELETE"},
    )
    assert requested.status_code == 202
    deletion_id = requested.json()["id"]
    cancelled = client.delete(
        f"/api/v1/hub/account/deletion-requests/{deletion_id}", headers=headers
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
