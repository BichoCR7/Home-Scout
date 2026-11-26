"""Phase 11 provider marketplace, booking, maintenance and moving access coverage."""

from datetime import UTC, datetime, timedelta

from tests.helpers import create_authenticated_user
from tests.test_marketplace import _publish_listing


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _published_provider(client, token: str, *, county_id: str) -> dict[str, object]:
    profile = client.put(
        "/api/v1/services/providers/me",
        headers=_headers(token),
        json={
            "public_name": "Nairobi Home Helpers",
            "description": "Moving and home maintenance support across Nairobi County.",
            "is_published": False,
        },
    )
    assert profile.status_code == 200, profile.text
    offering = client.post(
        "/api/v1/services/providers/me/offerings",
        headers=_headers(token),
        json={
            "title": "Careful home moving",
            "category": "movers",
            "description": "Apartment moves with packing and careful furniture handling.",
            "pricing_model": "from",
            "price_amount": 15000,
            "service_areas": [{"county_id": county_id}],
        },
    )
    assert offering.status_code == 201, offering.text
    published = client.put(
        "/api/v1/services/providers/me",
        headers=_headers(token),
        json={
            "public_name": "Nairobi Home Helpers",
            "description": "Moving and home maintenance support across Nairobi County.",
            "is_published": True,
        },
    )
    assert published.status_code == 200, published.text
    return offering.json()


def test_service_search_booking_state_and_participant_privacy(client) -> None:
    landlord = create_authenticated_user(
        client, role_code="landlord", email="p11-service-landlord@example.com"
    )
    tenant = create_authenticated_user(
        client, role_code="tenant", email="p11-service-tenant@example.com"
    )
    provider = create_authenticated_user(
        client, role_code="service_provider", email="p11-service-provider@example.com"
    )
    unrelated_provider = create_authenticated_user(
        client, role_code="service_provider", email="p11-service-other@example.com"
    )
    listing = _publish_listing(client, landlord, title="Nairobi move-in home", rent=48_000)
    county_id = listing["location"]["county_id"]
    offering = _published_provider(client, provider, county_id=county_id)

    search = client.get(
        "/api/v1/services/offerings",
        params={"query": "careful", "category": "movers", "min_price": 10_000},
    )
    assert search.status_code == 200, search.text
    assert [item["id"] for item in search.json()] == [offering["id"]]
    assert search.json()[0]["currency"] == "KES"
    assert search.json()[0]["provider_verification_status"] == "not_submitted"
    assert search.json()[0]["review_count"] == 0

    request = client.post(
        "/api/v1/services/bookings",
        headers=_headers(tenant),
        json={
            "offering_id": offering["id"],
            "requested_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
            "timezone": "Africa/Nairobi",
            "request_details": "Please help move two rooms in Kilimani.",
        },
    )
    assert request.status_code == 201, request.text
    booking_id = request.json()["id"]
    assert request.json()["status"] == "pending"

    provider_bookings = client.get("/api/v1/services/bookings", headers=_headers(provider))
    assert provider_bookings.status_code == 200, provider_bookings.text
    assert [item["id"] for item in provider_bookings.json()] == [booking_id]
    assert (
        client.get("/api/v1/services/bookings", headers=_headers(unrelated_provider)).json() == []
    )
    assert (
        client.get(
            f"/api/v1/services/bookings/{booking_id}/history",
            headers=_headers(unrelated_provider),
        ).status_code
        == 404
    )

    accepted = client.patch(
        f"/api/v1/services/bookings/{booking_id}",
        headers=_headers(provider),
        json={"action": "accept", "note": "Saturday morning is available."},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"
    assert client.get("/api/v1/services/orders", headers=_headers(unrelated_provider)).json() == []


def test_move_plan_tasks_budget_and_room_setup_are_owner_private(client) -> None:
    owner = create_authenticated_user(
        client, role_code="tenant", email="p11-move-owner@example.com"
    )
    other = create_authenticated_user(
        client, role_code="tenant", email="p11-move-other@example.com"
    )
    headers = _headers(owner)
    plan = client.post(
        "/api/v1/services/move-plans",
        headers=headers,
        json={"title": "Move to Westlands", "move_date": "2026-12-05", "target_budget_kes": 85000},
    )
    assert plan.status_code == 201, plan.text
    plan_id = plan.json()["id"]
    task = client.post(
        f"/api/v1/services/move-plans/{plan_id}/tasks",
        headers=headers,
        json={"title": "Book movers", "category": "moving_day", "due_date": "2026-12-02"},
    )
    assert task.status_code == 201, task.text
    assert task.json()["status"] == "open"
    budget = client.post(
        f"/api/v1/services/move-plans/{plan_id}/budget",
        headers=headers,
        json={"title": "Moving van", "amount_kes": 18000},
    )
    assert budget.status_code == 201, budget.text
    room_item = client.post(
        f"/api/v1/services/move-plans/{plan_id}/room-setup",
        headers=headers,
        json={"room_name": "Bedroom", "item_name": "Wardrobe", "quantity": 1},
    )
    assert room_item.status_code == 201, room_item.text
    assert (
        client.get(
            f"/api/v1/services/move-plans/{plan_id}/tasks", headers=_headers(other)
        ).status_code
        == 404
    )
    assert client.get("/api/v1/services/move-plans", headers=_headers(other)).json() == []


def test_maintenance_requires_granted_resident_access_and_provider_assignment(client) -> None:
    landlord = create_authenticated_user(
        client, role_code="landlord", email="p11-maint-landlord@example.com"
    )
    tenant = create_authenticated_user(
        client, role_code="tenant", email="p11-maint-tenant@example.com"
    )
    provider = create_authenticated_user(
        client, role_code="service_provider", email="p11-maint-provider@example.com"
    )
    stranger = create_authenticated_user(
        client, role_code="service_provider", email="p11-maint-stranger@example.com"
    )
    listing = _publish_listing(client, landlord, title="Maintenance test home", rent=42_000)
    county_id = listing["location"]["county_id"]
    profile = client.put(
        "/api/v1/services/providers/me",
        headers=_headers(provider),
        json={
            "public_name": "Reliable Plumbing",
            "description": "Home plumbing repairs and checks.",
        },
    )
    assert profile.status_code == 200, profile.text
    offering = client.post(
        "/api/v1/services/providers/me/offerings",
        headers=_headers(provider),
        json={
            "title": "Plumbing repair",
            "category": "plumbers",
            "description": "Repairs and checks for household water fittings.",
            "pricing_model": "quote",
            "service_areas": [{"county_id": county_id}],
        },
    )
    assert offering.status_code == 201, offering.text
    client.put(
        "/api/v1/services/providers/me",
        headers=_headers(provider),
        json={
            "public_name": "Reliable Plumbing",
            "description": "Home plumbing repairs and checks.",
            "is_published": True,
        },
    )
    property_id = listing["id"]
    denied = client.post(
        "/api/v1/services/maintenance",
        headers=_headers(tenant),
        json={
            "property_id": property_id,
            "category": "plumbing",
            "description": "A kitchen tap is leaking badly.",
        },
    )
    assert denied.status_code == 404

    grant = client.post(
        f"/api/v1/services/properties/{property_id}/residents",
        headers=_headers(landlord),
        json={
            "resident_user_id": client.get("/api/v1/auth/me", headers=_headers(tenant)).json()["id"]
        },
    )
    assert grant.status_code == 201, grant.text
    assert (
        client.get("/api/v1/services/resident-properties", headers=_headers(tenant)).json()[0]["id"]
        == property_id
    )
    created = client.post(
        "/api/v1/services/maintenance",
        headers=_headers(tenant),
        json={
            "property_id": property_id,
            "category": "plumbing",
            "description": "A kitchen tap is leaking badly.",
        },
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]
    assert created.json()["status"] == "submitted"
    assignment = client.patch(
        f"/api/v1/services/maintenance/{request_id}/assignment",
        headers=_headers(landlord),
        json={
            "provider_user_id": client.get("/api/v1/auth/me", headers=_headers(provider)).json()[
                "id"
            ],
            "offering_id": offering.json()["id"],
        },
    )
    assert assignment.status_code == 200, assignment.text
    assert assignment.json()["status"] == "assigned"
    assert (
        client.get(
            f"/api/v1/services/maintenance/{request_id}", headers=_headers(stranger)
        ).status_code
        == 404
    )
    provider_view = client.get(
        f"/api/v1/services/maintenance/{request_id}", headers=_headers(provider)
    )
    assert provider_view.status_code == 200, provider_view.text
    started = client.patch(
        f"/api/v1/services/maintenance/{request_id}/actions",
        headers=_headers(provider),
        json={"action": "start"},
    )
    assert started.status_code == 200, started.text
    completed = client.patch(
        f"/api/v1/services/maintenance/{request_id}/actions",
        headers=_headers(provider),
        json={"action": "complete", "note": "Replaced the tap washer and checked the joint."},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"
    revoked = client.delete(
        f"/api/v1/services/properties/{property_id}/residents/{grant.json()['resident_user_id']}",
        headers=_headers(landlord),
    )
    assert revoked.status_code == 200, revoked.text
    assert (
        client.get(
            f"/api/v1/services/maintenance/{request_id}", headers=_headers(tenant)
        ).status_code
        == 404
    )
