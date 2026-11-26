"""Explicitly synthetic property fixtures; never run as a production seed."""

from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.location import County, Neighbourhood, Town
from app.models.property import Property, PropertyMedia

DEMO_NOTICE = "Synthetic HomeScout test data. Not a real, verified, or available property."
PHOTO_URLS = (
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=82",
    "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=1200&q=82",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=82",
)


def seed_demo_properties(session: Session, owner_user_id: UUID) -> list[Property]:
    """Create consistent demo properties with unknown availability and illustrative photos."""

    examples = (
        {
            "slug": "kilimani-apartment",
            "title": "Sunlit two-bedroom apartment",
            "description": (
                "Synthetic example of a bright apartment layout in Kilimani for API testing."
            ),
            "property_type": "apartment",
            "unit_type": "two_bedroom",
            "bedrooms": 2,
            "rent": Decimal("68000"),
            "county_code": "47",
            "town_slug": "nairobi",
            "neighbourhood": "Kilimani",
            "photo": PHOTO_URLS[0],
        },
        {
            "slug": "lavington-bedsitter",
            "title": "Quiet garden bedsitter",
            "description": "Synthetic bedsitter example with a compact, single-room floor plan.",
            "property_type": "apartment",
            "unit_type": "bedsitter",
            "bedrooms": 0,
            "rent": Decimal("32000"),
            "county_code": "47",
            "town_slug": "nairobi",
            "neighbourhood": "Lavington",
            "photo": PHOTO_URLS[1],
        },
        {
            "slug": "ruaka-townhouse",
            "title": "Modern family townhouse",
            "description": (
                "Synthetic townhouse example for validating the Kiambu location hierarchy."
            ),
            "property_type": "townhouse",
            "unit_type": "three_bedroom",
            "bedrooms": 3,
            "rent": Decimal("95000"),
            "county_code": "22",
            "town_slug": "ruaka",
            "neighbourhood": None,
            "photo": PHOTO_URLS[2],
        },
    )
    county_rows = {row.code: row for row in session.scalars(select(County))}
    town_rows = {(row.county_id, row.slug): row for row in session.scalars(select(Town))}
    neighbourhood_rows = {
        (row.town_id, row.name): row for row in session.scalars(select(Neighbourhood))
    }
    created: list[Property] = []
    for example in examples:
        county = county_rows[example["county_code"]]
        town = town_rows[(county.id, example["town_slug"])]
        neighbourhood = (
            neighbourhood_rows[(town.id, example["neighbourhood"])]
            if example["neighbourhood"]
            else None
        )
        property_id = uuid5(NAMESPACE_URL, f"homescout:test-demo:{example['slug']}")
        created.append(
            Property(
                id=property_id,
                title=example["title"],
                description=example["description"],
                property_type=example["property_type"],
                accommodation_type="whole_property",
                unit_type=example["unit_type"],
                rent_amount=example["rent"],
                currency="KES",
                rent_frequency="monthly",
                deposit_amount=None,
                bedrooms=example["bedrooms"],
                bathrooms=Decimal("1.0"),
                size_sqm=None,
                parking_available=False,
                parking_spaces=0,
                furnishing="unfurnished",
                pet_policy="unknown",
                water_availability="unknown",
                electricity_available=None,
                internet_available=None,
                security_features=[],
                amenities=[],
                county_id=county.id,
                town_id=town.id,
                neighbourhood_id=neighbourhood.id if neighbourhood else None,
                address=None,
                latitude=None,
                longitude=None,
                coordinate_source=None,
                owner_user_id=owner_user_id,
                verification_status="not_submitted",
                availability_status="unknown",
                listing_status="draft",
                is_demo=True,
                demo_disclaimer=DEMO_NOTICE,
                media=[
                    PropertyMedia(
                        media_type="image",
                        url=example["photo"],
                        alt_text="Illustrative stock photo; not a photo of a real property.",
                        position=0,
                        is_illustrative=True,
                        source_credit="Unsplash stock imagery",
                    )
                ],
            )
        )
    session.add_all(created)
    session.commit()
    return created
