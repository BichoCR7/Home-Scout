"""Phase 10 messaging, viewing, sharing, roommate, and journal privacy coverage."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.models.phase10 import ComparisonItem, ConversationMessage
from tests.helpers import create_authenticated_user
from tests.test_marketplace import _publish_listing


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _user_id(client, token: str) -> str:
    response = client.get("/api/v1/auth/me", headers=_headers(token))
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_enquiry_messaging_is_encrypted_private_reportable_and_blockable(client) -> None:
    landlord = create_authenticated_user(
        client, role_code="landlord", email="p10-msg-landlord@example.com"
    )
    tenant = create_authenticated_user(
        client, role_code="tenant", email="p10-msg-tenant@example.com"
    )
    stranger = create_authenticated_user(
        client, role_code="tenant", email="p10-msg-stranger@example.com"
    )
    listing = _publish_listing(client, landlord, title="Phase ten messaging home", rent=48_000)
    enquiry = client.post(
        f"/api/v1/marketplace/properties/{listing['id']}/enquiries",
        headers=_headers(tenant),
        json={"message": "Please share a viewing time."},
    )
    assert enquiry.status_code == 201, enquiry.text
    conversation = client.post(
        f"/api/v1/communications/property-enquiries/{enquiry.json()['id']}/conversation",
        headers=_headers(tenant),
    )
    assert conversation.status_code == 200, conversation.text
    conversation_id = conversation.json()["id"]

    denied = client.get(
        f"/api/v1/communications/conversations/{conversation_id}/messages",
        headers=_headers(stranger),
    )
    assert denied.status_code == 404

    sent = client.post(
        f"/api/v1/communications/conversations/{conversation_id}/messages",
        headers=_headers(tenant),
        json={"body": "I can visit on Saturday morning."},
    )
    assert sent.status_code == 201, sent.text
    message_id = UUID(sent.json()["id"])
    assert sent.json()["body"] == "I can visit on Saturday morning."
    with client.app.state.session_factory() as session:
        row = session.get(ConversationMessage, message_id)
        assert row is not None
        assert b"Saturday morning" not in row.encrypted_body

    landlord_inbox = client.get("/api/v1/communications/inbox", headers=_headers(landlord))
    assert landlord_inbox.status_code == 200
    assert landlord_inbox.json()[0]["unread_count"] == 1
    messages = client.get(
        f"/api/v1/communications/conversations/{conversation_id}/messages",
        headers=_headers(landlord),
    )
    assert messages.status_code == 200
    assert messages.json()[0]["body"] == "I can visit on Saturday morning."
    report = client.post(
        f"/api/v1/communications/messages/{message_id}/reports",
        headers=_headers(landlord),
        json={"category": "unsafe_request", "details": "Request for advance cash."},
    )
    assert report.status_code == 201, report.text

    block = client.put(
        f"/api/v1/communications/blocks/{_user_id(client, landlord)}",
        headers=_headers(tenant),
    )
    assert block.status_code == 200
    blocked_send = client.post(
        f"/api/v1/communications/conversations/{conversation_id}/messages",
        headers=_headers(landlord),
        json={"body": "This should not deliver."},
    )
    assert blocked_send.status_code == 403
    blocked_list = client.get("/api/v1/communications/blocks", headers=_headers(tenant))
    assert blocked_list.status_code == 200
    assert blocked_list.json()[0]["blocked_user_id"] == _user_id(client, landlord)
    unblocked = client.delete(
        f"/api/v1/communications/blocks/{_user_id(client, landlord)}",
        headers=_headers(tenant),
    )
    assert unblocked.status_code == 200
    unblocked_send = client.post(
        f"/api/v1/communications/conversations/{conversation_id}/messages",
        headers=_headers(landlord),
        json={"body": "I will follow up on the viewing time."},
    )
    assert unblocked_send.status_code == 201


def test_viewing_requires_host_confirmation_and_journal_share_is_revocable(client) -> None:
    landlord = create_authenticated_user(
        client, role_code="landlord", email="p10-view-host@example.com"
    )
    tenant = create_authenticated_user(
        client, role_code="tenant", email="p10-view-renter@example.com"
    )
    journal_guest = create_authenticated_user(
        client, role_code="tenant", email="p10-view-guest@example.com"
    )
    listing = _publish_listing(client, landlord, title="Viewing schedule home", rent=41_000)
    requested_at = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    request = client.post(
        "/api/v1/viewings/requests",
        headers=_headers(tenant),
        json={
            "property_id": listing["id"],
            "requested_at": requested_at,
            "timezone": "Africa/Nairobi",
        },
    )
    assert request.status_code == 201, request.text
    viewing_id = request.json()["id"]
    assert request.json()["status"] == "requested"

    host_confirmed = client.post(
        f"/api/v1/viewings/{viewing_id}/actions",
        headers=_headers(landlord),
        json={"action": "confirm", "note": "See you then."},
    )
    assert host_confirmed.status_code == 200, host_confirmed.text
    assert host_confirmed.json()["status"] == "confirmed"
    schedule = client.get("/api/v1/hub/schedule", headers=_headers(tenant))
    assert schedule.status_code == 200
    assert any(item["category"] == "viewing" for item in schedule.json())

    journal = client.post(
        "/api/v1/viewings/journals",
        headers=_headers(tenant),
        json={
            "property_id": listing["id"],
            "viewing_id": viewing_id,
            "title": "Kilimani visit notes",
            "notes": "Bright living room; ask about water pressure.",
            "pros": ["Near the bus route"],
            "cons": ["No lift information"],
            "rating": 4,
            "checklist": {"water": False, "lease": True},
        },
    )
    assert journal.status_code == 201, journal.text
    journal_id = journal.json()["id"]
    assert (
        client.get(
            f"/api/v1/viewings/journals/{journal_id}", headers=_headers(journal_guest)
        ).status_code
        == 404
    )
    with client.app.state.session_factory() as session:
        from app.models.phase10 import ViewingJournal

        stored = session.get(ViewingJournal, UUID(journal_id))
        assert stored is not None
        assert b"water pressure" not in stored.encrypted_data

    shared = client.put(
        f"/api/v1/viewings/journals/{journal_id}/shares",
        headers=_headers(tenant),
        json={"recipient_user_id": _user_id(client, journal_guest)},
    )
    assert shared.status_code == 204
    assert (
        client.get(f"/api/v1/viewings/journals/{journal_id}", headers=_headers(journal_guest))
        .json()["notes"]
        .startswith("Bright")
    )
    revoked = client.delete(
        f"/api/v1/viewings/journals/{journal_id}/shares/{_user_id(client, journal_guest)}",
        headers=_headers(tenant),
    )
    assert revoked.status_code == 204
    assert (
        client.get(
            f"/api/v1/viewings/journals/{journal_id}", headers=_headers(journal_guest)
        ).status_code
        == 404
    )


def test_comparison_roommate_opt_in_and_shared_group_revoke_and_financial_consent(client) -> None:
    landlord = create_authenticated_user(
        client, role_code="landlord", email="p10-group-landlord@example.com"
    )
    owner = create_authenticated_user(
        client, role_code="tenant", email="p10-group-owner@example.com"
    )
    member = create_authenticated_user(
        client, role_code="tenant", email="p10-group-member@example.com"
    )
    outsider = create_authenticated_user(
        client, role_code="tenant", email="p10-group-outsider@example.com"
    )
    listing_a = _publish_listing(client, landlord, title="Shared-search home A", rent=38_000)
    listing_b = _publish_listing(client, landlord, title="Shared-search home B", rent=46_000)

    profile = client.put(
        "/api/v1/collaboration/roommates/me",
        headers=_headers(member),
        json={
            "display_alias": "Mtaa Explorer",
            "about": "Quiet and tidy",
            "budget_min": 20_000,
            "budget_max": 50_000,
            "lifestyle_tags": ["quiet", "tidy"],
            "matching_enabled": True,
        },
    )
    assert profile.status_code == 200, profile.text
    suggestions = client.get("/api/v1/collaboration/roommates/suggestions", headers=_headers(owner))
    assert suggestions.status_code == 200
    candidate = next(
        item for item in suggestions.json() if item["profile_id"] == profile.json()["id"]
    )
    assert candidate["display_alias"] == "Mtaa Explorer"
    assert "email" not in candidate and "phone" not in candidate and "user_id" not in candidate
    interest = client.post(
        f"/api/v1/collaboration/roommates/{profile.json()['id']}/interests",
        headers=_headers(owner),
    )
    assert interest.status_code == 201, interest.text
    accepted = client.patch(
        f"/api/v1/collaboration/roommates/interests/{interest.json()['id']}",
        headers=_headers(member),
        json={"accept": True},
    )
    assert accepted.status_code == 200
    roommate_conversation = client.post(
        f"/api/v1/communications/roommate-interests/{interest.json()['id']}/conversation",
        headers=_headers(owner),
    )
    assert roommate_conversation.status_code == 200

    board = client.post(
        "/api/v1/collaboration/comparisons",
        headers=_headers(owner),
        json={
            "name": "My options",
            "items": [
                {
                    "property_id": listing_a["id"],
                    "monthly_cost_input": 3_500,
                    "move_in_cost_input": 5_000,
                    "note": "Ask about water.",
                },
                {"property_id": listing_b["id"], "note": "Compare commute."},
            ],
        },
    )
    assert board.status_code == 201, board.text
    board_id = board.json()["id"]
    assert len(board.json()["items"]) == 2
    assert (
        client.get(
            f"/api/v1/collaboration/comparisons/{board_id}", headers=_headers(outsider)
        ).status_code
        == 404
    )
    with client.app.state.session_factory() as session:
        encrypted = [row.encrypted_user_data for row in session.query(ComparisonItem).all()]
        assert encrypted and all(b"water" not in item for item in encrypted if item is not None)
    too_many = client.post(
        "/api/v1/collaboration/comparisons",
        headers=_headers(owner),
        json={"items": [{"property_id": listing_a["id"]}] * 6},
    )
    assert too_many.status_code == 422

    group = client.post(
        "/api/v1/collaboration/groups",
        headers=_headers(owner),
        json={"name": "Our next home", "invite_user_ids": [_user_id(client, member)]},
    )
    assert group.status_code == 201, group.text
    group_id = group.json()["id"]
    response = client.post(
        f"/api/v1/collaboration/groups/{group_id}/invitation-response?accept=true",
        headers=_headers(member),
    )
    assert response.status_code == 200
    search = client.post(
        f"/api/v1/collaboration/groups/{group_id}/searches",
        headers=_headers(owner),
        json={"name": "Under 50k", "filters": {"rent_max": 50_000}},
    )
    assert search.status_code == 201, search.text
    assert (
        len(
            client.get(
                f"/api/v1/collaboration/groups/{group_id}/searches", headers=_headers(member)
            ).json()
        )
        == 1
    )

    for listing in (listing_a, listing_b):
        added = client.post(
            f"/api/v1/collaboration/groups/{group_id}/properties",
            headers=_headers(owner),
            json={"property_id": listing["id"]},
        )
        assert added.status_code == 201
    comparison = client.post(
        f"/api/v1/collaboration/groups/{group_id}/comparisons",
        headers=_headers(owner),
        json={"name": "Shared shortlist", "property_ids": [listing_a["id"], listing_b["id"]]},
    )
    assert comparison.status_code == 201, comparison.text
    assert len(comparison.json()["items"]) == 2
    shared_goal = client.post(
        f"/api/v1/collaboration/groups/{group_id}/moving-goals",
        headers=_headers(owner),
        json={
            "title": "Deposit savings",
            "target_amount": 80_000,
            "share_amount_with_members": True,
        },
    )
    assert shared_goal.status_code == 201, shared_goal.text
    goals = client.get(
        f"/api/v1/collaboration/groups/{group_id}/moving-goals", headers=_headers(member)
    )
    assert goals.status_code == 200
    assert goals.json()[0]["target_amount_kes"] is None
    consent = client.put(
        f"/api/v1/collaboration/groups/{group_id}/moving-goals/{shared_goal.json()['id']}/financial-consent",
        headers=_headers(member),
        json={"consent_to_view_shared_amounts": True},
    )
    assert consent.status_code == 200
    assert consent.json()["target_amount_kes"] == "80000"

    revoke = client.delete(
        f"/api/v1/collaboration/groups/{group_id}/members/{_user_id(client, member)}",
        headers=_headers(owner),
    )
    assert revoke.status_code == 204
    revoked_read = client.get(
        f"/api/v1/collaboration/groups/{group_id}/searches", headers=_headers(member)
    )
    assert revoked_read.status_code == 404
