"""Database access for property records and media."""

from uuid import UUID

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.location import County, Neighbourhood, Town
from app.models.property import Property, PropertyAmenity


class PropertyDataAccess:
    def get(self, session: Session, property_id: UUID) -> Property | None:
        statement = (
            select(Property)
            .options(
                joinedload(Property.county),
                joinedload(Property.town),
                joinedload(Property.neighbourhood),
                selectinload(Property.media),
            )
            .where(Property.id == property_id)
        )
        return session.scalar(statement)

    def list_public(
        self,
        session: Session,
        *,
        county_id: UUID | None,
        town_id: UUID | None,
        neighbourhood_id: UUID | None,
        property_type: str | None,
        unit_type: str | None,
        bedrooms: int | None,
        bedrooms_min: int | None,
        furnishing: str | None,
        verified_only: bool,
        rent_min: int | None,
        rent_max: int | None,
        query: str | None,
        amenities: list[str],
        sort_by: str,
        south: float | None,
        west: float | None,
        north: float | None,
        east: float | None,
        include_demo: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[Property], int]:
        conditions = [
            Property.moderation_status == "clear",
            or_(
                (Property.is_demo.is_(False))
                & (Property.listing_status == "published")
                & (Property.availability_status == "available"),
                Property.is_demo.is_(True) if include_demo else False,
            ),
        ]
        if county_id:
            conditions.append(Property.county_id == county_id)
        if town_id:
            conditions.append(Property.town_id == town_id)
        if neighbourhood_id:
            conditions.append(Property.neighbourhood_id == neighbourhood_id)
        if property_type:
            conditions.append(Property.property_type == property_type)
        if unit_type:
            conditions.append(Property.unit_type == unit_type)
        if bedrooms is not None:
            conditions.append(Property.bedrooms == bedrooms)
        if bedrooms_min is not None:
            conditions.append(Property.bedrooms >= bedrooms_min)
        if furnishing:
            conditions.append(Property.furnishing == furnishing)
        if verified_only:
            conditions.append(Property.verification_status == "verified")
        if rent_min is not None:
            conditions.append(Property.rent_amount >= rent_min)
        if rent_max is not None:
            conditions.append(Property.rent_amount <= rent_max)
        if query:
            pattern = f"%{query.strip()}%"
            conditions.append(
                or_(
                    Property.title.ilike(pattern),
                    Property.description.ilike(pattern),
                    Property.county.has(County.name.ilike(pattern)),
                    Property.town.has(Town.name.ilike(pattern)),
                    Property.neighbourhood.has(Neighbourhood.name.ilike(pattern)),
                )
            )
        for amenity in amenities:
            conditions.append(
                exists(
                    select(PropertyAmenity.property_id).where(
                        PropertyAmenity.property_id == Property.id,
                        func.lower(PropertyAmenity.amenity) == amenity.lower(),
                    )
                )
            )
        if south is not None and north is not None:
            conditions.extend(
                (
                    Property.latitude.is_not(None),
                    Property.latitude >= south,
                    Property.latitude <= north,
                )
            )
        if west is not None and east is not None:
            longitude_in_bounds = (
                (Property.longitude >= west) & (Property.longitude <= east)
                if west <= east
                else or_(Property.longitude >= west, Property.longitude <= east)
            )
            conditions.extend((Property.longitude.is_not(None), longitude_in_bounds))

        count_statement = select(func.count()).select_from(Property).where(*conditions)
        total = int(session.scalar(count_statement) or 0)
        ordering = {
            "newest": (Property.created_at.desc(), Property.id),
            "rent_low": (Property.rent_amount.asc(), Property.id),
            "rent_high": (Property.rent_amount.desc(), Property.id),
            "bedrooms": (Property.bedrooms.asc(), Property.rent_amount.asc(), Property.id),
        }[sort_by]
        statement = (
            select(Property)
            .options(
                joinedload(Property.county),
                joinedload(Property.town),
                joinedload(Property.neighbourhood),
                selectinload(Property.media),
            )
            .where(*conditions)
            .order_by(*ordering)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(statement).unique()), total

    def list_accessible(self, session: Session, user_id: UUID) -> list[Property]:
        statement = (
            select(Property)
            .options(
                joinedload(Property.county),
                joinedload(Property.town),
                joinedload(Property.neighbourhood),
                selectinload(Property.media),
            )
            .where(
                or_(
                    Property.owner_user_id == user_id,
                    Property.authorized_agent_user_id == user_id,
                    Property.property_manager_user_id == user_id,
                ),
                Property.is_demo.is_(False),
            )
            .order_by(Property.created_at.desc(), Property.id)
        )
        return list(session.scalars(statement).unique())

    def list_public_by_id(
        self, session: Session, property_id: UUID, *, include_demo: bool
    ) -> Property | None:
        public = (
            (Property.is_demo.is_(False))
            & (Property.listing_status == "published")
            & (Property.availability_status == "available")
        )
        condition = or_(public, Property.is_demo.is_(True)) if include_demo else public
        return session.scalar(
            select(Property)
            .options(
                joinedload(Property.county),
                joinedload(Property.town),
                joinedload(Property.neighbourhood),
                selectinload(Property.media),
            )
            .where(Property.id == property_id, Property.moderation_status == "clear", condition)
        )


__all__ = ["PropertyDataAccess"]
