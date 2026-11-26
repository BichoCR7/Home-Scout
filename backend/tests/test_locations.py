"""Kenyan location reference data, hierarchy, search, and validation tests."""

import pytest
from sqlalchemy import select

from app.api.v1.endpoints import locations as location_endpoints
from app.core.errors import ApiError
from app.models.location import County, Neighbourhood, Town
from app.services.locations import LocationService
from tests.helpers import create_authenticated_user


def test_all_counties_and_priority_locations_are_seeded(client) -> None:
    counties_response = client.get("/api/v1/locations/counties")

    assert counties_response.status_code == 200
    counties = counties_response.json()
    assert len(counties) == 47
    assert {item["code"] for item in counties} == {f"{number:02d}" for number in range(1, 48)}
    assert all(item["country_name"] == "Kenya" for item in counties)

    for query, expected_kind in (
        ("Westlands", "neighbourhood"),
        ("Ruaka", "town"),
        ("Naivasha", "town"),
        ("Mamboleo", "neighbourhood"),
        ("Kapseret", "town"),
    ):
        response = client.get("/api/v1/locations/search", params={"q": query})
        assert response.status_code == 200
        assert response.json()
        assert expected_kind in {item["kind"] for item in response.json()}


def test_map_search_uses_cached_kenya_only_provider_results(client, monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return [
                {
                    "place_id": 84721,
                    "display_name": "Westlands, Nairobi, Kenya",
                    "lat": "-1.2676",
                    "lon": "36.8108",
                },
                {"display_name": "Bad coordinates, Kenya", "lat": "unknown", "lon": "36"},
                {"display_name": "Outside bounds, Kenya", "lat": "100", "lon": "36"},
            ]

    class FakeAsyncClient:
        def __init__(self, *, timeout: int, headers: dict[str, str]) -> None:
            assert timeout == 9
            assert "HomeScout" in headers["User-Agent"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def get(self, endpoint: str, *, params: dict[str, object]) -> FakeResponse:
            calls.append((endpoint, params))
            return FakeResponse()

    query = "Westlands provider test"
    monkeypatch.setattr(location_endpoints.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(location_endpoints, "_map_last_request_at", 0.0)
    monkeypatch.delitem(location_endpoints._map_search_cache, query.casefold(), raising=False)

    first = client.get("/api/v1/locations/map-search", params={"q": query})
    second = client.get("/api/v1/locations/map-search", params={"q": query})

    assert first.status_code == 200
    assert first.json() == second.json()
    assert len(first.json()) == 1
    assert first.json()[0]["name"] == "Westlands"
    assert first.json()[0]["latitude"] == -1.2676
    assert first.json()[0]["longitude"] == 36.8108
    assert len(calls) == 1
    assert calls[0][1]["countrycodes"] == "ke"
    assert calls[0][1]["q"] == f"{query}, Kenya"


def test_location_relationships_and_seeded_coordinates_are_grounded(client) -> None:
    factory = client.app.state.session_factory
    with factory() as session:
        nairobi = session.scalar(select(County).where(County.code == "47"))
        assert nairobi is not None
        town = session.scalar(
            select(Town).where(Town.county_id == nairobi.id, Town.slug == "nairobi")
        )
        assert town is not None
        westlands = session.scalar(
            select(Neighbourhood).where(
                Neighbourhood.town_id == town.id, Neighbourhood.name == "Westlands"
            )
        )
        assert westlands is not None
        assert town.latitude is None and town.longitude is None
        assert westlands.latitude is None and westlands.longitude is None

    response = client.get(f"/api/v1/locations/counties/{nairobi.id}/towns")
    assert response.status_code == 200
    assert any(item["name"] == "Nairobi" for item in response.json())

    response = client.get(f"/api/v1/locations/towns/{town.id}/neighbourhoods")
    assert response.status_code == 200
    assert "Westlands" in {item["name"] for item in response.json()}


def test_property_hierarchy_rejects_town_from_another_county(client) -> None:
    factory = client.app.state.session_factory
    service = LocationService()
    with factory() as session:
        nairobi = session.scalar(select(County).where(County.code == "47"))
        ruaka = session.scalar(select(Town).where(Town.slug == "ruaka"))
        assert nairobi and ruaka
        with pytest.raises(ApiError) as caught:
            service.validate_hierarchy(
                session,
                county_id=nairobi.id,
                town_id=ruaka.id,
                neighbourhood_id=None,
            )
        assert caught.value.code == "invalid_location_hierarchy"


def test_location_creation_is_permission_gated_and_coordinates_need_sources(client) -> None:
    tenant_token = create_authenticated_user(
        client, role_code="tenant", email="tenant-locations@example.com"
    )
    response = client.post(
        "/api/v1/locations/towns",
        headers={"Authorization": f"Bearer {tenant_token}"},
        json={
            "county_id": "00000000-0000-0000-0000-000000000001",
            "name": "Sample Town",
            "source_name": "Owner note",
        },
    )
    assert response.status_code == 403

    admin_token = create_authenticated_user(
        client, role_code="admin", email="admin-locations@example.com"
    )
    county_id = client.get("/api/v1/locations/counties").json()[0]["id"]
    body = {
        "county_id": county_id,
        "name": "Sample New Town",
        "kind": "town",
        "source_name": "County planning reference",
        "latitude": -1.234,
    }
    response = client.post(
        "/api/v1/locations/towns",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=body,
    )
    assert response.status_code == 422

    body["longitude"] = 36.789
    body["coordinate_source"] = "Survey document, page 4"
    response = client.post(
        "/api/v1/locations/towns",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=body,
    )
    assert response.status_code == 201
    assert response.json()["coordinate_source"] == "Survey document, page 4"
