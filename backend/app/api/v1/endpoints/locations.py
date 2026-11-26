"""Kenyan county, town, neighbourhood search and guarded reference maintenance."""

import asyncio
import time
from collections import OrderedDict
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db
from app.core.errors import ApiError
from app.data_access.locations import LocationDataAccess
from app.schemas.locations import (
    CountyResponse,
    LocationSearchResult,
    MapGeocodeResult,
    NeighbourhoodCreateRequest,
    NeighbourhoodResponse,
    TownCreateRequest,
    TownResponse,
)
from app.services.authentication import AuthenticatedPrincipal
from app.services.locations import LocationService

router = APIRouter(prefix="/locations", tags=["locations"])
service = LocationService()
data_access = LocationDataAccess()
_map_search_cache: OrderedDict[str, list[MapGeocodeResult]] = OrderedDict()
_map_search_lock = asyncio.Lock()
_map_last_request_at = 0.0


@router.get("/counties", response_model=list[CountyResponse], summary="List Kenyan counties")
def list_counties(session: Annotated[Session, Depends(get_db)]) -> list[CountyResponse]:
    return [
        CountyResponse(
            id=county.id,
            code=county.code,
            name=county.name,
            slug=county.slug,
            aliases=county.aliases,
            country_name=county.country.name,
        )
        for county in service.list_counties(session)
    ]


@router.get(
    "/counties/{county_id}/towns",
    response_model=list[TownResponse],
    summary="List towns in a county",
)
def list_towns(county_id: UUID, session: Annotated[Session, Depends(get_db)]) -> list[TownResponse]:
    return [TownResponse.model_validate(town) for town in service.list_towns(session, county_id)]


@router.get(
    "/towns/{town_id}/neighbourhoods",
    response_model=list[NeighbourhoodResponse],
    summary="List neighbourhoods in a town",
)
def list_neighbourhoods(
    town_id: UUID, session: Annotated[Session, Depends(get_db)]
) -> list[NeighbourhoodResponse]:
    return [
        NeighbourhoodResponse.model_validate(neighbourhood)
        for neighbourhood in service.list_neighbourhoods(session, town_id)
    ]


@router.get("/search", response_model=list[LocationSearchResult], summary="Search Kenya locations")
def search_locations(
    q: Annotated[str, Query(min_length=2, max_length=120)],
    session: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[LocationSearchResult]:
    return service.search(session, q, limit)


@router.get(
    "/map-search",
    response_model=list[MapGeocodeResult],
    summary="Find a Kenyan place for the map",
)
async def search_map_locations(
    q: Annotated[str, Query(min_length=2, max_length=120)],
    request: Request,
) -> list[MapGeocodeResult]:
    """Proxy user-submitted place lookups through a switchable, low-volume provider."""

    global _map_last_request_at
    query = q.strip()
    cache_key = query.casefold()
    async with _map_search_lock:
        cached = _map_search_cache.get(cache_key)
        if cached is not None:
            _map_search_cache.move_to_end(cache_key)
            return cached

        wait_seconds = 1.1 - (time.monotonic() - _map_last_request_at)
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        _map_last_request_at = time.monotonic()
        endpoint = request.app.state.settings.map_geocoder_url
        try:
            async with httpx.AsyncClient(
                timeout=9,
                headers={"User-Agent": "HomeScout API/1.0"},
            ) as client:
                response = await client.get(
                    endpoint,
                    params={
                        "format": "jsonv2",
                        "limit": 5,
                        "addressdetails": 1,
                        "countrycodes": "ke",
                        "q": query if "kenya" in query.casefold() else f"{query}, Kenya",
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as error:
            raise ApiError(
                503,
                "map_search_unavailable",
                "Area search is temporarily unavailable. Try again shortly.",
            ) from error

        results: list[MapGeocodeResult] = []
        payload = response.json()
        if isinstance(payload, list):
            for row in payload[:5]:
                if not isinstance(row, dict):
                    continue
                try:
                    latitude = float(row["lat"])
                    longitude = float(row["lon"])
                except (KeyError, TypeError, ValueError):
                    continue
                display_name = str(row.get("display_name", "")).strip()
                if (
                    not display_name
                    or latitude < -90
                    or latitude > 90
                    or longitude < -180
                    or longitude > 180
                ):
                    continue
                results.append(
                    MapGeocodeResult(
                        id=str(row.get("place_id") or f"{latitude}:{longitude}"),
                        name=display_name.split(",", maxsplit=1)[0].strip() or "Kenyan location",
                        label=display_name,
                        latitude=latitude,
                        longitude=longitude,
                    )
                )

        _map_search_cache[cache_key] = results
        _map_search_cache.move_to_end(cache_key)
        while len(_map_search_cache) > 128:
            _map_search_cache.popitem(last=False)
        return results


@router.post(
    "/towns",
    response_model=TownResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a town to the location reference data",
)
def create_town(
    body: TownCreateRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> TownResponse:
    town = service.create_town(
        session,
        user_id=principal.user_id,
        request=body,
        request_id=getattr(request.state, "request_id", None),
    )
    return TownResponse.model_validate(town)


@router.post(
    "/neighbourhoods",
    response_model=NeighbourhoodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a neighbourhood to the location reference data",
)
def create_neighbourhood(
    body: NeighbourhoodCreateRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> NeighbourhoodResponse:
    neighbourhood = service.create_neighbourhood(
        session,
        user_id=principal.user_id,
        request=body,
        request_id=getattr(request.state, "request_id", None),
    )
    return NeighbourhoodResponse.model_validate(neighbourhood)


def require_county(session: Session, county_id: UUID):
    county = data_access.get_county(session, county_id)
    if county is None:
        raise ApiError(404, "county_not_found", "The requested county was not found.")
    return county
