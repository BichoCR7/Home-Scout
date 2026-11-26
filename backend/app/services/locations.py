"""Location hierarchy validation, search, and controlled reference-data maintenance."""

import re
import unicodedata
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.data_access.locations import LocationDataAccess
from app.models.audit import AuditEvent
from app.models.location import County, Neighbourhood, Town
from app.schemas.locations import (
    LocationSearchResult,
    NeighbourhoodCreateRequest,
    TownCreateRequest,
)
from app.services.authorization import AuthorizationService


def location_slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.casefold())
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")


class LocationService:
    def __init__(self) -> None:
        self.data = LocationDataAccess()
        self.authorization = AuthorizationService()

    def list_counties(self, session: Session) -> list[County]:
        return self.data.list_counties(session)

    def list_towns(self, session: Session, county_id: UUID) -> list[Town]:
        county = self.data.get_county(session, county_id)
        if county is None:
            raise ApiError(404, "county_not_found", "The requested county was not found.")
        return self.data.list_towns(session, county_id)

    def list_neighbourhoods(self, session: Session, town_id: UUID) -> list[Neighbourhood]:
        town = self.data.get_town(session, town_id)
        if town is None:
            raise ApiError(404, "town_not_found", "The requested town was not found.")
        return self.data.list_neighbourhoods(session, town_id)

    def search(self, session: Session, query: str, limit: int) -> list[LocationSearchResult]:
        folded_query = query.strip().casefold()
        counties, towns, neighbourhoods = self.data.searchable_locations(session)
        matches: list[tuple[int, str, LocationSearchResult]] = []
        for county in counties:
            if self._matches(folded_query, county.name, county.slug, county.aliases):
                matches.append(
                    (
                        0,
                        county.name.casefold(),
                        LocationSearchResult(
                            id=county.id,
                            kind="county",
                            name=county.name,
                            county_id=county.id,
                            county_name=county.name,
                        ),
                    )
                )
        for town, county in towns:
            if self._matches(folded_query, town.name, town.slug, town.aliases):
                matches.append(
                    (
                        1,
                        town.name.casefold(),
                        LocationSearchResult(
                            id=town.id,
                            kind="town",
                            name=town.name,
                            county_id=county.id,
                            county_name=county.name,
                            town_id=town.id,
                            town_name=town.name,
                        ),
                    )
                )
        for neighbourhood, town, county in neighbourhoods:
            if self._matches(
                folded_query, neighbourhood.name, neighbourhood.slug, neighbourhood.aliases
            ):
                matches.append(
                    (
                        2,
                        neighbourhood.name.casefold(),
                        LocationSearchResult(
                            id=neighbourhood.id,
                            kind="neighbourhood",
                            name=neighbourhood.name,
                            county_id=county.id,
                            county_name=county.name,
                            town_id=town.id,
                            town_name=town.name,
                        ),
                    )
                )
        matches.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in matches[:limit]]

    def validate_hierarchy(
        self,
        session: Session,
        *,
        county_id: UUID,
        town_id: UUID,
        neighbourhood_id: UUID | None,
    ) -> None:
        county = self.data.get_county(session, county_id)
        town = self.data.get_town(session, town_id)
        neighbourhood = session.get(Neighbourhood, neighbourhood_id) if neighbourhood_id else None
        if (
            county is None
            or town is None
            or town.county_id != county.id
            or (neighbourhood_id is not None and neighbourhood is None)
            or (neighbourhood is not None and neighbourhood.town_id != town.id)
        ):
            raise ApiError(
                status_code=422,
                code="invalid_location_hierarchy",
                message=(
                    "The selected county, town, and neighbourhood do not form a valid hierarchy."
                ),
            )

    def create_town(
        self,
        session: Session,
        *,
        user_id: UUID,
        request: TownCreateRequest,
        request_id: str | None = None,
    ) -> Town:
        self.authorization.require_permission(
            session, user_id=user_id, permission_code="location:manage:global"
        )
        county = self.data.get_county(session, request.county_id)
        if county is None:
            raise ApiError(404, "county_not_found", "The requested county was not found.")
        town = Town(
            county_id=county.id,
            name=request.name,
            slug=location_slug(request.name),
            kind=request.kind,
            aliases=request.aliases,
            latitude=request.latitude,
            longitude=request.longitude,
            coordinate_source=request.coordinate_source,
            metadata_json=request.metadata,
            source_name=request.source_name,
            source_url=request.source_url,
        )
        session.add(town)
        try:
            session.flush()
            self._audit(
                session,
                user_id=user_id,
                request_id=request_id,
                event="location.town_created",
                subject_id=str(town.id),
                county_code=county.code,
            )
            session.commit()
        except IntegrityError:
            session.rollback()
            raise ApiError(409, "location_already_exists", "That town already exists.") from None
        return town

    def create_neighbourhood(
        self,
        session: Session,
        *,
        user_id: UUID,
        request: NeighbourhoodCreateRequest,
        request_id: str | None = None,
    ) -> Neighbourhood:
        self.authorization.require_permission(
            session, user_id=user_id, permission_code="location:manage:global"
        )
        town = self.data.get_town(session, request.town_id)
        if town is None:
            raise ApiError(404, "town_not_found", "The requested town was not found.")
        neighbourhood = Neighbourhood(
            town_id=town.id,
            name=request.name,
            slug=location_slug(request.name),
            aliases=request.aliases,
            latitude=request.latitude,
            longitude=request.longitude,
            coordinate_source=request.coordinate_source,
            metadata_json=request.metadata,
            source_name=request.source_name,
            source_url=request.source_url,
        )
        session.add(neighbourhood)
        try:
            session.flush()
            self._audit(
                session,
                user_id=user_id,
                request_id=request_id,
                event="location.neighbourhood_created",
                subject_id=str(neighbourhood.id),
                county_code=town.county.code,
            )
            session.commit()
        except IntegrityError:
            session.rollback()
            raise ApiError(
                409, "location_already_exists", "That neighbourhood already exists."
            ) from None
        return neighbourhood

    @staticmethod
    def _matches(query: str, name: str, slug: str, aliases: list[str]) -> bool:
        return any(query in value.casefold() for value in (name, slug, *aliases))

    @staticmethod
    def _audit(
        session: Session,
        *,
        user_id: UUID,
        request_id: str | None,
        event: str,
        subject_id: str,
        county_code: str,
    ) -> None:
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type=event,
                subject_type="location",
                subject_id=subject_id,
                request_id=request_id,
                metadata_json={"county_code": county_code},
            )
        )
