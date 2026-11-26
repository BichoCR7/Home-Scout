"""Database access for the country, county, town, and neighbourhood hierarchy."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.location import County, Neighbourhood, Town


class LocationDataAccess:
    def list_counties(self, session: Session) -> list[County]:
        statement = (
            select(County)
            .options(joinedload(County.country))
            .where(County.is_active.is_(True))
            .order_by(County.code)
        )
        return list(session.scalars(statement).unique())

    def get_county(self, session: Session, county_id: UUID) -> County | None:
        return session.scalar(
            select(County)
            .options(joinedload(County.country))
            .where(County.id == county_id, County.is_active.is_(True))
        )

    def get_county_by_code(self, session: Session, county_code: str) -> County | None:
        return session.scalar(
            select(County)
            .options(joinedload(County.country))
            .where(County.code == county_code, County.is_active.is_(True))
        )

    def list_towns(self, session: Session, county_id: UUID) -> list[Town]:
        return list(
            session.scalars(
                select(Town)
                .where(Town.county_id == county_id, Town.is_active.is_(True))
                .order_by(Town.name)
            )
        )

    def get_town(self, session: Session, town_id: UUID) -> Town | None:
        return session.scalar(select(Town).where(Town.id == town_id, Town.is_active.is_(True)))

    def list_neighbourhoods(self, session: Session, town_id: UUID) -> list[Neighbourhood]:
        return list(
            session.scalars(
                select(Neighbourhood)
                .where(
                    Neighbourhood.town_id == town_id,
                    Neighbourhood.is_active.is_(True),
                )
                .order_by(Neighbourhood.name)
            )
        )

    def searchable_locations(
        self, session: Session
    ) -> tuple[list[County], list[tuple[Town, County]], list[tuple[Neighbourhood, Town, County]]]:
        counties = self.list_counties(session)
        town_rows = session.execute(
            select(Town, County)
            .join(County, County.id == Town.county_id)
            .where(Town.is_active.is_(True), County.is_active.is_(True))
        ).all()
        neighbourhood_rows = session.execute(
            select(Neighbourhood, Town, County)
            .join(Town, Town.id == Neighbourhood.town_id)
            .join(County, County.id == Town.county_id)
            .where(
                Neighbourhood.is_active.is_(True),
                Town.is_active.is_(True),
                County.is_active.is_(True),
            )
        ).all()
        return counties, list(town_rows), list(neighbourhood_rows)
