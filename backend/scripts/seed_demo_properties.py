"""Seed 20 synthetic listing examples into the local HomeScout development database.

Run from backend/: `python scripts/seed_demo_properties.py`.
This utility refuses staging and production databases. It never assigns coordinates,
availability, or verification to the synthetic examples.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import create_database_engine, create_session_factory
from app.models.location import County, Neighbourhood, Town
from app.models.property import Property, PropertyAmenity, PropertyMedia
from app.models.user import UserAccount, UserProfile

DEMO_NOTICE = "Synthetic HomeScout development example. Not a real, verified, or available property."
DEMO_OWNER_EMAIL = "demo-listings@homescout.invalid"

# Unsplash stock references; these are illustrative images, never photos of these example homes.
PHOTO_IDS = (
    "1600607687939-ce8a6c25118c", "1600566753086-00f18fb6b3ea",
    "1600585154340-be6161a56a0c", "1639663742190-1b3dba2eebcf",
    "1701092868263-2ed67ac8dfa0", "1609766857326-18a204c2cf31",
    "1630699144865-d3230bf37016", "1704428381339-3b3087053b3a",
    "1484154218962-a197022b5858", "1646615811071-f4f0735e2355",
    "1630699144886-d6d025f5d0f1", "1646592491770-c113dd6f8827",
    "1721824318446-8ad0857decdd", "1577579242425-b323e6d61bd4",
    "1630699294512-64ecddd912c5", "1630699034288-21159cfd7d74",
    "1737737149038-e6532662659e", "1615749250437-8f3fd29f9118",
    "1721396185451-ff45e7440c30", "1612419299101-6c294dc2901d",
)

EXAMPLES = (
    ("kilimani", "Kilimani", "47", "nairobi", "Kilimani", "apartment", "two_bedroom", 2, 68_000, "unfurnished", 2, 78, ("balcony", "parking", "security"), "reliable", "allowed"),
    ("westlands", "Westlands", "47", "nairobi", "Westlands", "apartment", "one_bedroom", 1, 72_000, "furnished", 1, 54, ("gym", "elevator", "security"), "reliable", "case_by_case"),
    ("kileleshwa", "Kileleshwa", "47", "nairobi", "Kileleshwa", "apartment", "three_bedroom", 3, 105_000, "semi_furnished", 2, 132, ("balcony", "parking", "gym"), "reliable", "unknown"),
    ("lavington", "Lavington", "47", "nairobi", "Lavington", "maisonette", "four_bedroom", 4, 180_000, "unfurnished", 2, 205, ("garden", "parking", "security"), "reliable", "allowed"),
    ("parklands", "Parklands", "47", "nairobi", "Parklands", "apartment", "studio", 0, 38_000, "furnished", 0, 35, ("elevator", "security"), "intermittent", "not_allowed"),
    ("karen", "Karen", "47", "nairobi", "Karen", "villa", "five_plus_bedrooms", 5, 320_000, "unfurnished", 3, 390, ("garden", "swimming pool", "parking"), "reliable", "allowed"),
    ("ruaka", "Ruaka", "22", "ruaka", None, "townhouse", "three_bedroom", 3, 88_000, "semi_furnished", 2, 118, ("balcony", "parking", "security"), "reliable", "case_by_case"),
    ("ruiru", "Ruiru", "22", "ruiru", None, "apartment", "two_bedroom", 2, 46_000, "unfurnished", 1, 72, ("parking", "security"), "intermittent", "unknown"),
    ("syokimau", "Syokimau", "16", "syokimau", None, "apartment", "one_bedroom", 1, 42_000, "furnished", 1, 56, ("balcony", "gym", "security"), "reliable", "allowed"),
    ("athi-river", "Athi River", "16", "athi-river", None, "house", "three_bedroom", 3, 65_000, "unfurnished", 2, 148, ("garden", "parking"), "intermittent", "allowed"),
    ("south-b", "South B", "47", "nairobi", "South B", "apartment", "bedsitter", 0, 24_000, "unfurnished", 0, 28, ("security", "laundry"), "reliable", "not_allowed"),
    ("south-c", "South C", "47", "nairobi", "South C", "apartment", "two_bedroom", 2, 58_000, "semi_furnished", 1, 84, ("balcony", "parking", "security"), "reliable", "case_by_case"),
    ("kasarani", "Kasarani", "47", "nairobi", "Kasarani", "apartment", "one_bedroom", 1, 31_000, "unfurnished", 0, 48, ("parking", "security"), "intermittent", "unknown"),
    ("roysambu", "Roysambu", "47", "nairobi", "Roysambu", "apartment", "student_accommodation", 1, 19_000, "furnished", 0, 30, ("internet", "security", "laundry"), "reliable", "not_allowed"),
    ("nyali", "Nyali", "01", "mombasa-city", "Nyali", "apartment", "three_bedroom", 3, 115_000, "furnished", 2, 142, ("balcony", "swimming pool", "parking"), "reliable", "allowed"),
    ("bamburi", "Bamburi", "01", "mombasa-city", "Bamburi", "apartment", "bedsitter", 0, 20_000, "unfurnished", 0, 26, ("security",), "intermittent", "case_by_case"),
    ("nakuru", "Nakuru Town", "32", "nakuru", None, "maisonette", "three_bedroom", 3, 52_000, "unfurnished", 2, 150, ("garden", "parking", "water storage"), "reliable", "allowed"),
    ("kisumu", "Kisumu City", "42", "kisumu-city", "Milimani", "apartment", "two_bedroom", 2, 55_000, "semi_furnished", 1, 96, ("balcony", "security", "internet"), "reliable", "unknown"),
    ("eldoret", "Eldoret", "27", "eldoret", None, "house", "four_bedroom", 4, 75_000, "unfurnished", 2, 188, ("garden", "parking", "security"), "intermittent", "allowed"),
    ("ngong", "Ngong", "34", "ngong", None, "shared_accommodation", "one_bedroom", 1, 16_000, "furnished", 0, 38, ("internet", "shared kitchen", "security"), "reliable", "unknown"),
)


def seed_demo_rows(session: Session) -> int:
    owner = session.scalar(select(UserAccount).where(UserAccount.email == DEMO_OWNER_EMAIL))
    if owner is None:
        owner = UserAccount(email=DEMO_OWNER_EMAIL, status="pending")
        owner.profile = UserProfile(given_name="HomeScout", family_name="Demo Listings")
        session.add(owner)
        session.flush()

    counties = {row.code: row for row in session.scalars(select(County))}
    towns = {(row.county_id, row.slug): row for row in session.scalars(select(Town))}
    neighbourhoods = {
        (row.town_id, row.slug): row for row in session.scalars(select(Neighbourhood))
    }
    inserted = 0
    for index, example in enumerate(EXAMPLES):
        (
            slug, area, county_code, town_slug, neighbourhood_slug, property_type,
            unit_type, bedrooms, rent, furnishing, parking_spaces, size_sqm, amenities,
            water, pet_policy,
        ) = example
        property_id = uuid5(NAMESPACE_URL, f"homescout:development-demo:{slug}")
        if session.get(Property, property_id) is not None:
            continue
        county = counties[county_code]
        town = towns[(county.id, town_slug)]
        neighbourhood = neighbourhoods.get((town.id, neighbourhood_slug)) if neighbourhood_slug else None
        photo = f"https://images.unsplash.com/photo-{PHOTO_IDS[index]}?auto=format&fit=crop&w=1200&q=82"
        is_shared = slug == "ngong"
        property_ = Property(
            id=property_id,
            title=f"{area} synthetic {unit_type.replace('_', ' ')} example",
            description=(
                f"Synthetic HomeScout development example for {area}. The KSh amount, layout, "
                "amenities and illustrative stock image are for interface and search testing only. "
                "This is not a real listing; availability and verification have not been established."
            ),
            property_type=property_type if property_type != "shared_accommodation" else "apartment",
            accommodation_type="shared_accommodation" if is_shared else "whole_property",
            unit_type=unit_type if unit_type != "student_accommodation" else "one_bedroom",
            rent_amount=Decimal(rent), currency="KES", rent_frequency="monthly",
            deposit_amount=Decimal(rent), bedrooms=bedrooms,
            bathrooms=Decimal("1.0" if bedrooms < 2 else "2.0"),
            size_sqm=Decimal(size_sqm), parking_available=parking_spaces > 0,
            parking_spaces=parking_spaces, furnishing=furnishing, pet_policy=pet_policy,
            water_availability=water, electricity_available=True,
            internet_available="internet" in amenities,
            security_features=[item for item in amenities if item == "security"],
            amenities=list(amenities), county_id=county.id, town_id=town.id,
            neighbourhood_id=neighbourhood.id if neighbourhood else None,
            owner_user_id=owner.id, verification_status="not_submitted",
            availability_status="unknown", listing_status="draft", is_demo=True,
            demo_disclaimer=DEMO_NOTICE,
            media=[PropertyMedia(
                media_type="image", url=photo,
                alt_text=f"Illustrative Unsplash stock image for the synthetic {area} example.",
                caption="Stock photograph for demonstration; not the described property.",
                position=0, is_illustrative=True, source_credit="Unsplash stock image",
            )],
            amenity_records=[PropertyAmenity(amenity=item) for item in amenities],
        )
        session.add(property_)
        inserted += 1
    session.commit()
    return inserted


def main() -> None:
    settings = get_settings()
    if settings.environment != "development":
        raise SystemExit("Refusing to seed demo homes outside the development environment.")
    engine = create_database_engine(settings.database_url)
    factory = create_session_factory(engine)
    try:
        with factory() as session:
            inserted = seed_demo_rows(session)
        print(f"Inserted {inserted} synthetic development listings. No coordinates were assigned.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
