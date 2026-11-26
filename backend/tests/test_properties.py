"""Property schemas, demo safeguards, owner-scoped draft APIs, and public reads."""

from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.models.location import County, Neighbourhood, Town
from app.models.property import Property
from app.schemas.properties import PropertyCreateRequest
from scripts.seed_demo_properties import DEMO_NOTICE as SEED_DEMO_NOTICE
from scripts.seed_demo_properties import seed_demo_rows
from tests.demo_properties import DEMO_NOTICE as TEST_DEMO_NOTICE
from tests.demo_properties import seed_demo_properties
from tests.helpers import create_authenticated_user


def _create_payload(client, *, title: str = "Bright two-bedroom home") -> dict[str, object]:
    factory = client.app.state.session_factory
    with factory() as session:
        county = session.scalar(select(County).where(County.code == "47"))
        assert county is not None
        town = session.scalar(
            select(Town).where(Town.county_id == county.id, Town.slug == "nairobi")
        )
        assert town is not None
        neighbourhood = session.scalar(
            select(Neighbourhood).where(
                Neighbourhood.town_id == town.id, Neighbourhood.name == "Kilimani"
            )
        )
        assert neighbourhood is not None
        county_id, town_id, neighbourhood_id = county.id, town.id, neighbourhood.id
    return {
        "title": title,
        "description": "A well-lit sample two-bedroom layout prepared for API and schema testing.",
        "property_type": "apartment",
        "accommodation_type": "whole_property",
        "unit_type": "two_bedroom",
        "rent_amount": "68000.00",
        "rent_frequency": "monthly",
        "deposit_amount": "68000.00",
        "bedrooms": 2,
        "bathrooms": "1.5",
        "size_sqm": "78.50",
        "parking_available": True,
        "parking_spaces": 1,
        "furnishing": "unfurnished",
        "pet_policy": "case_by_case",
        "water_availability": "unknown",
        "electricity_available": True,
        "internet_available": None,
        "security_features": ["guarded entrance"],
        "amenities": ["balcony", "laundry area"],
        "county_id": str(county_id),
        "town_id": str(town_id),
        "neighbourhood_id": str(neighbourhood_id),
        "address": None,
        "latitude": None,
        "longitude": None,
        "coordinate_source": None,
        "media": [
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=82",
                "alt_text": "Illustrative stock photo",
                "position": 0,
                "is_illustrative": True,
                "source_credit": "Unsplash stock imagery",
            }
        ],
    }


def test_property_schema_validates_room_counts_coordinates_and_media() -> None:
    payload = _create_payload_for_schema()
    payload["bedrooms"] = 1
    with pytest.raises(ValidationError):
        PropertyCreateRequest.model_validate(payload)

    payload = _create_payload_for_schema()
    payload["latitude"] = Decimal("-1.2345")
    with pytest.raises(ValidationError):
        PropertyCreateRequest.model_validate(payload)

    payload = _create_payload_for_schema()
    payload["media"] = [{"media_type": "image", "url": "http://example.com/photo.jpg"}]
    with pytest.raises(ValidationError):
        PropertyCreateRequest.model_validate(payload)


def _create_payload_for_schema() -> dict[str, object]:
    return {
        "title": "Bright two-bedroom home",
        "description": "A well-lit sample two-bedroom layout prepared for API and schema testing.",
        "property_type": "apartment",
        "unit_type": "two_bedroom",
        "rent_amount": "68000.00",
        "bedrooms": 2,
        "bathrooms": "1.5",
        "furnishing": "unfurnished",
        "county_id": "00000000-0000-0000-0000-000000000001",
        "town_id": "00000000-0000-0000-0000-000000000002",
    }


def test_landlord_can_create_and_edit_only_owned_draft_properties(client) -> None:
    owner_token = create_authenticated_user(client, role_code="landlord", email="owner@example.com")
    other_token = create_authenticated_user(
        client, role_code="landlord", email="other-owner@example.com"
    )
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = client.post("/api/v1/properties", headers=headers, json=_create_payload(client))

    assert response.status_code == 201, response.text
    created = response.json()
    assert created["currency"] == "KES"
    assert created["listing_status"] == "draft"
    assert created["availability_status"] == "unknown"
    assert created["verification_status"] == "not_submitted"
    assert created["is_demo"] is False
    assert created["location"]["county_name"] == "Nairobi City"
    assert created["location"]["neighbourhood_name"] == "Kilimani"
    assert created["media"][0]["is_illustrative"] is True

    response = client.get("/api/v1/properties")
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert client.get(f"/api/v1/properties/{created['id']}").status_code == 404

    response = client.get("/api/v1/properties/mine", headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [created["id"]]

    response = client.patch(
        f"/api/v1/properties/{created['id']}",
        headers=headers,
        json={"title": "Updated two-bedroom draft"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Updated two-bedroom draft"

    response = client.patch(
        f"/api/v1/properties/{created['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"title": "Another user's draft"},
    )
    assert response.status_code == 404


def test_demo_properties_are_opt_in_disclaimed_and_never_available(client) -> None:
    token = create_authenticated_user(client, role_code="landlord", email="demo-owner@example.com")
    principal_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert principal_response.status_code == 200
    owner_id = UUID(principal_response.json()["id"])
    with client.app.state.session_factory() as session:
        demo_rows = seed_demo_properties(session, owner_id)
        demo_ids = [str(row.id) for row in demo_rows]

    assert client.get("/api/v1/properties").json()["total"] == 0
    response = client.get("/api/v1/properties", params={"include_demo": True})
    assert response.status_code == 200
    rows = response.json()["items"]
    assert len(rows) == 3
    assert all(item["is_demo"] for item in rows)
    assert all(item["demo_disclaimer"] == TEST_DEMO_NOTICE for item in rows)
    assert all(item["availability_status"] == "unknown" for item in rows)
    assert all(item["verification_status"] == "not_submitted" for item in rows)
    assert all(item["listing_status"] == "draft" for item in rows)
    assert all(item["media"][0]["is_illustrative"] for item in rows)
    assert {item["id"] for item in rows} == set(demo_ids)

    response = client.get(f"/api/v1/properties/{demo_ids[0]}", params={"include_demo": True})
    assert response.status_code == 200
    assert response.json()["is_demo"] is True


def test_map_property_filters_keep_demo_and_coordinate_rules(client) -> None:
    token = create_authenticated_user(client, role_code="landlord", email="map-demo@example.com")
    principal_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    owner_id = UUID(principal_response.json()["id"])
    with client.app.state.session_factory() as session:
        seed_demo_properties(session, owner_id)

    params = {"include_demo": True}
    rent_response = client.get("/api/v1/properties", params={**params, "rent_min": 50_000})
    bedroom_response = client.get("/api/v1/properties", params={**params, "bedrooms_min": 2})
    furnishing_response = client.get(
        "/api/v1/properties", params={**params, "furnishing": "unfurnished"}
    )
    verified_response = client.get("/api/v1/properties", params={**params, "verified_only": True})
    assert rent_response.json()["total"] == 2
    assert bedroom_response.json()["total"] == 2
    assert furnishing_response.json()["total"] == 3
    assert verified_response.json()["total"] == 0

    world = {"south": -90, "west": -180, "north": 90, "east": 180}
    response = client.get("/api/v1/properties", params={**params, **world})
    assert response.status_code == 200
    assert response.json()["total"] == 0  # Test records have no sourced coordinates.


def test_map_property_filters_reject_partial_or_contradictory_ranges(client) -> None:
    partial_bounds = client.get("/api/v1/properties", params={"south": -90})
    assert partial_bounds.status_code == 422
    assert partial_bounds.json()["error"]["code"] == "incomplete_map_bounds"

    invalid_bounds = client.get(
        "/api/v1/properties", params={"south": 10, "west": -180, "north": 10, "east": 180}
    )
    assert invalid_bounds.status_code == 422
    assert invalid_bounds.json()["error"]["code"] == "invalid_map_bounds"

    invalid_rent = client.get("/api/v1/properties", params={"rent_min": 50_000, "rent_max": 20_000})
    assert invalid_rent.status_code == 422
    assert invalid_rent.json()["error"]["code"] == "invalid_rent_range"

    ambiguous_bedrooms = client.get("/api/v1/properties", params={"bedrooms": 2, "bedrooms_min": 2})
    assert ambiguous_bedrooms.status_code == 422
    assert ambiguous_bedrooms.json()["error"]["code"] == "ambiguous_bedroom_filter"


def test_property_create_rejects_mismatched_location_hierarchy(client) -> None:
    token = create_authenticated_user(
        client, role_code="landlord", email="location-owner@example.com"
    )
    payload = _create_payload(client)
    factory = client.app.state.session_factory
    with factory() as session:
        ruaka = session.scalar(select(Town).where(Town.slug == "ruaka"))
        assert ruaka is not None
        payload["town_id"] = str(ruaka.id)
    response = client.post(
        "/api/v1/properties",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_location_hierarchy"


def test_development_demo_seeder_creates_twenty_distinct_disclaimed_rows(client) -> None:
    with client.app.state.session_factory() as session:
        assert seed_demo_rows(session) == 20
        assert seed_demo_rows(session) == 0
        rows = list(session.scalars(select(Property).where(Property.is_demo.is_(True))))
        assert len(rows) == 20
        assert len({row.id for row in rows}) == 20
        assert len({row.media[0].url for row in rows}) == 20
        assert all(row.demo_disclaimer == SEED_DEMO_NOTICE for row in rows)
        assert all(row.latitude is None and row.longitude is None for row in rows)
        assert all(row.availability_status == "unknown" for row in rows)
        assert all(row.verification_status == "not_submitted" for row in rows)
        assert all(row.listing_status == "draft" for row in rows)
    results = client.get("/api/v1/properties", params={"include_demo": True})
    assert results.status_code == 200
    assert results.json()["total"] == 20
    kilimani = client.get(
        "/api/v1/properties",
        params={"include_demo": True, "query": "Kilimani", "amenities": ["balcony"]},
    )
    assert kilimani.status_code == 200
    assert kilimani.json()["total"] == 1
