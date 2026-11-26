"""Phase 6 search, listing lifecycle, user state, uploads, and enquiry access."""

from decimal import Decimal
from uuid import UUID

from tests.helpers import create_authenticated_user
from tests.test_properties import _create_payload

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a"
    "0000000d49484452000000010000000108060000001f15c489"
    "0000000b49444154789c636000020000050001a5f64540"
    "0000000049454e44ae426082"
)


def _publish_listing(client, owner_token: str, *, title: str, rent: int) -> dict[str, object]:
    payload = _create_payload(client, title=title)
    payload["rent_amount"] = rent
    response = client.post(
        "/api/v1/properties",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=payload,
    )
    assert response.status_code == 201, response.text
    listing = response.json()
    image = client.post(
        f"/api/v1/properties/{listing['id']}/media?alt_text=Living%20room",
        headers={
            "Authorization": f"Bearer {owner_token}",
            "Content-Type": "image/png",
        },
        content=PNG_1X1,
    )
    assert image.status_code == 201, image.text
    assert image.json()["is_illustrative"] is False
    assert image.json()["byte_size"] == len(PNG_1X1)
    available = client.patch(
        f"/api/v1/properties/{listing['id']}/availability",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"availability_status": "available"},
    )
    assert available.status_code == 200, available.text
    published = client.post(
        f"/api/v1/properties/{listing['id']}/publish",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert published.status_code == 200, published.text
    assert published.json()["verification_status"] == "not_submitted"
    return published.json()


def test_search_sort_filters_detail_save_compare_and_enquiry(client) -> None:
    owner_token = create_authenticated_user(
        client, role_code="landlord", email="market-owner@example.com"
    )
    renter_token = create_authenticated_user(
        client, role_code="tenant", email="market-renter@example.com"
    )
    first = _publish_listing(client, owner_token, title="Kilimani bright two-bedroom", rent=68_000)
    second = _publish_listing(client, owner_token, title="Kilimani garden two-bedroom", rent=52_000)

    response = client.get(
        "/api/v1/properties",
        params={
            "query": "Kilimani",
            "rent_min": 50_000,
            "rent_max": 70_000,
            "bedrooms": 2,
            "property_type": "apartment",
            "furnishing": "unfurnished",
            "amenities": ["balcony"],
            "sort_by": "rent_low",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 2
    assert response.json()["items"][0]["id"] == second["id"]

    detail = client.get(f"/api/v1/properties/{first['id']}")
    assert detail.status_code == 200
    uploaded = next(item for item in detail.json()["media"] if not item["is_illustrative"])
    assert uploaded["mime_type"] == "image/png"
    assert detail.json()["location"]["neighbourhood_name"] == "Kilimani"
    media_response = client.get(uploaded["url"])
    assert media_response.status_code == 200
    assert media_response.headers["content-type"] == "image/png"
    assert media_response.headers["x-content-type-options"] == "nosniff"

    headers = {"Authorization": f"Bearer {renter_token}"}
    saved = client.put(f"/api/v1/marketplace/saved/{first['id']}", headers=headers)
    assert saved.status_code == 204
    client.put(f"/api/v1/marketplace/saved/{first['id']}", headers=headers)
    assert client.get("/api/v1/marketplace/saved", headers=headers).json()["total"] == 1
    comparison = client.post(
        "/api/v1/marketplace/compare",
        headers=headers,
        json=[first["id"], second["id"]],
    )
    assert comparison.status_code == 200
    assert len(comparison.json()) == 2
    assert comparison.json()[0]["currency"] == "KES"

    history = client.post(
        "/api/v1/marketplace/search-history",
        headers=headers,
        json={"filters": {"query": "Kilimani", "sort_by": "rent_low"}, "result_count": 2},
    )
    assert history.status_code == 201
    assert (
        client.get("/api/v1/marketplace/search-history", headers=headers).json()[0]["result_count"]
        == 2
    )
    alert = client.post(
        "/api/v1/marketplace/alerts",
        headers=headers,
        json={"filters": {"query": "Kilimani", "rent_max": 70_000}},
    )
    assert alert.status_code == 201
    assert client.get("/api/v1/marketplace/alerts", headers=headers).json()[0]["is_active"]

    enquiry = client.post(
        f"/api/v1/marketplace/properties/{first['id']}/enquiries",
        headers=headers,
        json={"message": "Could I arrange a viewing this Saturday afternoon?"},
    )
    assert enquiry.status_code == 201, enquiry.text
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    received = client.get("/api/v1/marketplace/enquiries/received", headers=owner_headers)
    assert received.status_code == 200
    assert received.json()[0]["id"] == enquiry.json()["id"]
    updated = client.patch(
        f"/api/v1/marketplace/enquiries/{enquiry.json()['id']}",
        headers=owner_headers,
        json={"status": "read"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "read"
    assert (
        client.get("/api/v1/marketplace/enquiries/sent", headers=headers).json()[0]["property_id"]
        == first["id"]
    )

    report = client.post(
        f"/api/v1/marketplace/properties/{first['id']}/reports",
        headers=headers,
        json={
            "reason": "inaccurate_details",
            "details": "The stated room count looks inconsistent.",
        },
    )
    assert report.status_code == 201, report.text
    assert report.json()["status"] == "received"
    duplicate = client.post(
        f"/api/v1/marketplace/properties/{first['id']}/reports",
        headers=headers,
        json={"reason": "other"},
    )
    assert duplicate.status_code == 409
    assert (
        client.get("/api/v1/marketplace/reports/mine", headers=headers).json()[0]["id"]
        == report.json()["id"]
    )
    timeline = client.get("/api/v1/hub/activity", headers=headers)
    assert timeline.status_code == 200
    assert {item["event_type"] for item in timeline.json()} >= {
        "saved_item",
        "comparison",
        "search",
        "message",
        "report",
    }


def test_listing_authorization_archive_and_demo_protection(client) -> None:
    owner = create_authenticated_user(
        client, role_code="landlord", email="workflow-owner@example.com"
    )
    other = create_authenticated_user(
        client, role_code="landlord", email="workflow-other@example.com"
    )
    owner_headers = {"Authorization": f"Bearer {owner}"}
    listing = _publish_listing(client, owner, title="Secure published listing", rent=44_000)
    unauthorized = client.patch(
        f"/api/v1/properties/{listing['id']}",
        headers={"Authorization": f"Bearer {other}"},
        json={"title": "Unauthorized listing edit"},
    )
    assert unauthorized.status_code == 404
    archived = client.post(f"/api/v1/properties/{listing['id']}/archive", headers=owner_headers)
    assert archived.status_code == 200
    assert archived.json()["listing_status"] == "archived"
    assert client.get(f"/api/v1/properties/{listing['id']}").status_code == 404

    demo_owner = create_authenticated_user(
        client, role_code="landlord", email="workflow-demo@example.com"
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {demo_owner}"})
    demo_owner_id = UUID(response.json()["id"])
    from tests.demo_properties import seed_demo_properties

    with client.app.state.session_factory() as session:
        demo = seed_demo_properties(session, demo_owner_id)[0]
        demo_id = str(demo.id)
    blocked = client.post(
        f"/api/v1/properties/{demo_id}/publish",
        headers={"Authorization": f"Bearer {demo_owner}"},
    )
    assert blocked.status_code == 404


def test_demo_home_favourites_are_scoped_and_never_visible_outside_development(client) -> None:
    from tests.demo_properties import seed_demo_properties

    owner_token = create_authenticated_user(
        client, role_code="landlord", email="demo-favourite-owner@example.com"
    )
    renter_token = create_authenticated_user(
        client, role_code="tenant", email="demo-favourite-renter@example.com"
    )
    other_token = create_authenticated_user(
        client, role_code="tenant", email="demo-favourite-other@example.com"
    )
    owner = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {owner_token}"}).json()
    with client.app.state.session_factory() as session:
        demo = seed_demo_properties(session, UUID(owner["id"]))[0]
        demo_id = str(demo.id)

    renter_headers = {"Authorization": f"Bearer {renter_token}"}
    saved = client.put(f"/api/v1/marketplace/saved/{demo_id}", headers=renter_headers)
    assert saved.status_code == 204
    saved_items = client.get("/api/v1/marketplace/saved", headers=renter_headers).json()["items"]
    assert len(saved_items) == 1
    assert saved_items[0]["is_demo"] is True
    assert saved_items[0]["demo_disclaimer"]
    assert (
        client.get(
            "/api/v1/marketplace/saved",
            headers={"Authorization": f"Bearer {other_token}"},
        ).json()["total"]
        == 0
    )

    client.app.state.settings.environment = "production"
    assert client.get("/api/v1/properties", params={"include_demo": True}).json()["total"] == 0
    assert (
        client.get(f"/api/v1/properties/{demo_id}", params={"include_demo": True}).status_code
        == 404
    )
    assert client.get("/api/v1/marketplace/saved", headers=renter_headers).json()["total"] == 0
    assert (
        client.put(f"/api/v1/marketplace/saved/{demo_id}", headers=renter_headers).status_code
        == 404
    )


def test_private_preview_edit_and_draft_delete(client) -> None:
    owner_token = create_authenticated_user(
        client, role_code="landlord", email="preview-owner@example.com"
    )
    other_token = create_authenticated_user(
        client, role_code="landlord", email="preview-other@example.com"
    )
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}
    payload = _create_payload(client, title="Private draft for preview")
    created = client.post("/api/v1/properties", headers=owner_headers, json=payload)
    assert created.status_code == 201, created.text
    property_id = created.json()["id"]

    preview = client.get(f"/api/v1/properties/{property_id}/preview", headers=owner_headers)
    assert preview.status_code == 200
    assert preview.json()["listing_status"] == "draft"
    assert (
        client.get(f"/api/v1/properties/{property_id}/preview", headers=other_headers).status_code
        == 404
    )
    assert client.get(f"/api/v1/properties/{property_id}").status_code == 404

    edited = client.patch(
        f"/api/v1/properties/{property_id}",
        headers=owner_headers,
        json={"title": "Updated private two-bedroom home", "rent_amount": 57_000},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["title"] == "Updated private two-bedroom home"
    assert Decimal(edited.json()["rent_amount"]) == Decimal("57000")

    deleted = client.delete(f"/api/v1/properties/{property_id}", headers=owner_headers)
    assert deleted.status_code == 204
    assert (
        client.get(f"/api/v1/properties/{property_id}/preview", headers=owner_headers).status_code
        == 404
    )


def test_image_upload_rejects_unauthorized_wrong_type_and_oversize(client) -> None:
    owner_token = create_authenticated_user(
        client, role_code="landlord", email="upload-owner@example.com"
    )
    other_token = create_authenticated_user(
        client, role_code="landlord", email="upload-other@example.com"
    )
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    payload = _create_payload(client, title="Upload validation draft")
    created = client.post("/api/v1/properties", headers=owner_headers, json=payload)
    assert created.status_code == 201, created.text
    property_id = created.json()["id"]

    unauthorized = client.post(
        f"/api/v1/properties/{property_id}/media",
        headers={
            "Authorization": f"Bearer {other_token}",
            "Content-Type": "image/png",
        },
        content=PNG_1X1,
    )
    assert unauthorized.status_code == 404

    wrong_type = client.post(
        f"/api/v1/properties/{property_id}/media",
        headers={**owner_headers, "Content-Type": "image/gif"},
        content=PNG_1X1,
    )
    assert wrong_type.status_code == 415

    client.app.state.settings.media_max_image_bytes = 32
    too_large = client.post(
        f"/api/v1/properties/{property_id}/media",
        headers={**owner_headers, "Content-Type": "image/png"},
        content=PNG_1X1,
    )
    assert too_large.status_code == 413


def test_assigned_agent_can_create_and_manage_only_by_owner_mandate(client) -> None:
    owner_token = create_authenticated_user(
        client, role_code="landlord", email="mandate-owner@example.com"
    )
    agent_token = create_authenticated_user(
        client, role_code="real_estate_agent", email="mandated-agent@example.com"
    )
    owner_id = UUID(
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {owner_token}"}).json()[
            "id"
        ]
    )
    agent_id = UUID(
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {agent_token}"}).json()[
            "id"
        ]
    )
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    grant = client.post(
        "/api/v1/marketplace/listing-mandates",
        headers=owner_headers,
        json={"agent_user_id": str(agent_id)},
    )
    assert grant.status_code == 201, grant.text

    payload = _create_payload(client, title="Agent managed two-bedroom")
    payload["owner_user_id"] = str(owner_id)
    created = client.post("/api/v1/properties", headers=agent_headers, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["owner_user_id"] == str(owner_id)
    assert created.json()["authorized_agent_user_id"] == str(agent_id)
    assert (
        client.get("/api/v1/properties/mine", headers=agent_headers).json()[0]["id"]
        == created.json()["id"]
    )

    revoke = client.delete(
        f"/api/v1/marketplace/listing-mandates/{agent_id}", headers=owner_headers
    )
    assert revoke.status_code == 204
    assert client.get("/api/v1/properties/mine", headers=agent_headers).json() == []
