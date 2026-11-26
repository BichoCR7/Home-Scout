"""add Kenyan locations and property data foundation

Revision ID: add5ba78b682
Revises: bdb6297372fc
Create Date: 2026-11-23 13:10:05.335508
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "add5ba78b682"
down_revision: str | None = "bdb6297372fc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "homescout:phase-4:kenya-locations-v1")
_COUNTIES = (
    ("01", "Mombasa", "mombasa", []),
    ("02", "Kwale", "kwale", []),
    ("03", "Kilifi", "kilifi", []),
    ("04", "Tana River", "tana-river", []),
    ("05", "Lamu", "lamu", []),
    ("06", "Taita-Taveta", "taita-taveta", ["Taita Taveta"]),
    ("07", "Garissa", "garissa", []),
    ("08", "Wajir", "wajir", []),
    ("09", "Mandera", "mandera", []),
    ("10", "Marsabit", "marsabit", []),
    ("11", "Isiolo", "isiolo", []),
    ("12", "Meru", "meru", []),
    ("13", "Tharaka-Nithi", "tharaka-nithi", ["Tharaka Nithi"]),
    ("14", "Embu", "embu", []),
    ("15", "Kitui", "kitui", []),
    ("16", "Machakos", "machakos", []),
    ("17", "Makueni", "makueni", []),
    ("18", "Nyandarua", "nyandarua", []),
    ("19", "Nyeri", "nyeri", []),
    ("20", "Kirinyaga", "kirinyaga", []),
    ("21", "Murang'a", "muranga", ["Murang'a", "Muranga"]),
    ("22", "Kiambu", "kiambu", []),
    ("23", "Turkana", "turkana", []),
    ("24", "West Pokot", "west-pokot", []),
    ("25", "Samburu", "samburu", []),
    ("26", "Trans Nzoia", "trans-nzoia", ["Trans-Nzoia"]),
    ("27", "Uasin Gishu", "uasin-gishu", []),
    ("28", "Elgeyo-Marakwet", "elgeyo-marakwet", ["Elgeyo Marakwet"]),
    ("29", "Nandi", "nandi", []),
    ("30", "Baringo", "baringo", []),
    ("31", "Laikipia", "laikipia", []),
    ("32", "Nakuru", "nakuru", []),
    ("33", "Narok", "narok", []),
    ("34", "Kajiado", "kajiado", []),
    ("35", "Kericho", "kericho", []),
    ("36", "Bomet", "bomet", []),
    ("37", "Kakamega", "kakamega", []),
    ("38", "Vihiga", "vihiga", []),
    ("39", "Bungoma", "bungoma", []),
    ("40", "Busia", "busia", []),
    ("41", "Siaya", "siaya", []),
    ("42", "Kisumu", "kisumu", []),
    ("43", "Homa Bay", "homa-bay", []),
    ("44", "Migori", "migori", []),
    ("45", "Kisii", "kisii", []),
    ("46", "Nyamira", "nyamira", []),
    ("47", "Nairobi City", "nairobi-city", ["Nairobi"]),
)

# Administrative headquarters sourced from the State Department for Devolution.
_CAPITAL_TOWNS = (
    ("01", "Mombasa City", "city", ["Mombasa"]),
    ("02", "Kwale", "town", []),
    ("03", "Kilifi", "town", []),
    ("04", "Hola", "town", []),
    ("05", "Lamu", "town", []),
    ("06", "Mwatate", "town", []),
    ("07", "Garissa", "town", []),
    ("08", "Wajir", "town", []),
    ("09", "Mandera", "town", []),
    ("10", "Marsabit", "town", []),
    ("11", "Isiolo", "town", []),
    ("12", "Meru", "town", []),
    ("13", "Kathwana", "town", []),
    ("14", "Embu", "town", []),
    ("15", "Kitui", "town", []),
    ("16", "Machakos Town", "town", ["Machakos"]),
    ("17", "Wote", "town", []),
    ("18", "Ol Kalou", "town", []),
    ("19", "Nyeri", "town", []),
    ("20", "Kerugoya", "town", []),
    ("21", "Murang'a", "town", ["Murang'a"]),
    ("22", "Kiambu Town", "town", ["Kiambu"]),
    ("23", "Lodwar", "town", []),
    ("24", "Kapenguria", "town", []),
    ("25", "Maralal", "town", []),
    ("26", "Kitale", "town", []),
    ("27", "Eldoret", "city", []),
    ("28", "Iten", "town", []),
    ("29", "Kapsabet", "town", []),
    ("30", "Kabarnet", "town", []),
    ("31", "Nanyuki", "town", []),
    ("32", "Nakuru", "city", ["Nakuru Town"]),
    ("33", "Narok", "town", []),
    ("34", "Kajiado", "town", []),
    ("35", "Kericho", "town", []),
    ("36", "Bomet", "town", []),
    ("37", "Kakamega", "town", []),
    ("38", "Vihiga", "town", []),
    ("39", "Bungoma", "town", []),
    ("40", "Busia", "town", []),
    ("41", "Siaya", "town", []),
    ("42", "Kisumu City", "city", ["Kisumu"]),
    ("43", "Homa Bay", "town", []),
    ("44", "Migori", "town", []),
    ("45", "Kisii", "town", []),
    ("46", "Nyamira", "town", []),
    ("47", "Nairobi", "city", ["Nairobi City"]),
)
_ADDITIONAL_TOWNS = (
    ("16", "Athi River", "town", []),
    ("16", "Mlolongo", "town", []),
    ("16", "Syokimau", "locality", []),
    ("20", "Kutus", "town", []),
    ("22", "Ruiru", "town", []),
    ("22", "Thika", "town", []),
    ("22", "Juja", "town", []),
    ("22", "Kikuyu", "town", []),
    ("22", "Limuru", "town", []),
    ("22", "Githunguri", "town", []),
    ("22", "Ruaka", "town", []),
    ("22", "Ndenderu", "locality", []),
    ("27", "Kapseret", "locality", []),
    ("32", "Naivasha", "town", []),
    ("32", "Gilgil", "town", []),
    ("34", "Kitengela", "town", []),
    ("34", "Ngong", "town", []),
    ("34", "Kiserian", "town", []),
    ("34", "Ongata Rongai", "town", []),
)
_NEIGHBOURHOODS = (
    ("47", "Westlands"),
    ("47", "Kilimani"),
    ("47", "Kileleshwa"),
    ("47", "Lavington"),
    ("47", "Karen"),
    ("47", "Runda"),
    ("47", "Parklands"),
    ("47", "Ngara"),
    ("47", "South C"),
    ("47", "South B"),
    ("47", "Langata"),
    ("47", "Kasarani"),
    ("47", "Roysambu"),
    ("47", "Embakasi"),
    ("47", "Umoja"),
    ("47", "Donholm"),
    ("47", "Upper Hill"),
    ("47", "Hurlingham"),
    ("47", "Gigiri"),
    ("47", "Ridgeways"),
    ("47", "Eastleigh"),
    ("47", "Kawangware"),
    ("47", "Imara Daima"),
    ("47", "Muthaiga"),
    ("47", "Spring Valley"),
    ("01", "Nyali"),
    ("01", "Bamburi"),
    ("01", "Mombasa Island"),
    ("01", "Tudor"),
    ("01", "Shanzu"),
    ("01", "Likoni"),
    ("42", "Milimani"),
    ("42", "Mamboleo"),
)
_COUNTY_SOURCE = "KNBS 2019 Kenya Population and Housing Census Atlas"
_COUNTY_SOURCE_URL = (
    "https://www.knbs.or.ke/wp-content/uploads/2025/11/2019-KPHC-Atlas-Reference-Maps.pdf"
)
_CAPITAL_SOURCE = "State Department for Devolution county information"
_CAPITAL_SOURCE_URL = "https://devolution.go.ke/county-information"
_BRIEF_SOURCE = "Owner-provided HomeScout Phase 4 location brief"


def _id(*parts: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, ":".join(parts))


def _slug(name: str) -> str:
    return name.lower().replace("'", "").replace("’", "").replace(" ", "-").replace("/", "-")


def _seed_reference_locations() -> None:
    """Seed sourced county/headquarters references and owner-supplied priority areas."""

    now = datetime.now(UTC)
    country_id = _id("country", "KE")
    country_table = sa.table(
        "countries",
        sa.column("id", sa.Uuid()),
        sa.column("iso_alpha2", sa.String()),
        sa.column("iso_alpha3", sa.String()),
        sa.column("name", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        country_table,
        [
            {
                "id": country_id,
                "iso_alpha2": "KE",
                "iso_alpha3": "KEN",
                "name": "Kenya",
                "created_at": now,
            }
        ],
    )

    county_table = sa.table(
        "counties",
        sa.column("id", sa.Uuid()),
        sa.column("country_id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("aliases", sa.JSON()),
        sa.column("source_name", sa.String()),
        sa.column("source_url", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        county_table,
        [
            {
                "id": _id("county", code),
                "country_id": country_id,
                "code": code,
                "name": name,
                "slug": slug,
                "aliases": aliases,
                "source_name": _COUNTY_SOURCE,
                "source_url": _COUNTY_SOURCE_URL,
                "is_active": True,
                "created_at": now,
            }
            for code, name, slug, aliases in _COUNTIES
        ],
    )

    town_table = sa.table(
        "towns",
        sa.column("id", sa.Uuid()),
        sa.column("county_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("kind", sa.String()),
        sa.column("aliases", sa.JSON()),
        sa.column("latitude", sa.Numeric(9, 6)),
        sa.column("longitude", sa.Numeric(9, 6)),
        sa.column("coordinate_source", sa.String()),
        sa.column("metadata", sa.JSON()),
        sa.column("source_name", sa.String()),
        sa.column("source_url", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    town_rows: list[dict[str, object]] = []
    town_ids: dict[tuple[str, str], uuid.UUID] = {}
    for code, name, kind, aliases in (*_CAPITAL_TOWNS, *_ADDITIONAL_TOWNS):
        slug = _slug(name)
        town_id = _id("town", code, slug)
        town_ids[(code, slug)] = town_id
        is_capital = (code, name, kind, aliases) in _CAPITAL_TOWNS
        town_rows.append(
            {
                "id": town_id,
                "county_id": _id("county", code),
                "name": name,
                "slug": slug,
                "kind": kind,
                "aliases": aliases,
                "latitude": None,
                "longitude": None,
                "coordinate_source": None,
                "metadata": {},
                "source_name": _CAPITAL_SOURCE if is_capital else _BRIEF_SOURCE,
                "source_url": _CAPITAL_SOURCE_URL if is_capital else None,
                "is_active": True,
                "created_at": now,
            }
        )
    op.bulk_insert(town_table, town_rows)

    neighbourhood_table = sa.table(
        "neighbourhoods",
        sa.column("id", sa.Uuid()),
        sa.column("town_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("aliases", sa.JSON()),
        sa.column("latitude", sa.Numeric(9, 6)),
        sa.column("longitude", sa.Numeric(9, 6)),
        sa.column("coordinate_source", sa.String()),
        sa.column("metadata", sa.JSON()),
        sa.column("source_name", sa.String()),
        sa.column("source_url", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    town_slugs = {"01": "mombasa-city", "42": "kisumu-city", "47": "nairobi"}
    op.bulk_insert(
        neighbourhood_table,
        [
            {
                "id": _id("neighbourhood", code, _slug(name)),
                "town_id": town_ids[(code, town_slugs[code])],
                "name": name,
                "slug": _slug(name),
                "aliases": [],
                "latitude": None,
                "longitude": None,
                "coordinate_source": None,
                "metadata": {},
                "source_name": _BRIEF_SOURCE,
                "source_url": None,
                "is_active": True,
                "created_at": now,
            }
            for code, name in _NEIGHBOURHOODS
        ],
    )


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "countries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("iso_alpha2", sa.String(length=2), nullable=False),
        sa.Column("iso_alpha3", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_countries")),
        sa.UniqueConstraint("iso_alpha2", name=op.f("uq_countries_iso_alpha2")),
        sa.UniqueConstraint("iso_alpha3", name=op.f("uq_countries_iso_alpha3")),
        sa.UniqueConstraint("name", name=op.f("uq_countries_name")),
    )
    op.create_table(
        "counties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("country_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(code) = 2", name=op.f("ck_counties_county_code_width")),
        sa.ForeignKeyConstraint(
            ["country_id"],
            ["countries.id"],
            name=op.f("fk_counties_country_id_countries"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_counties")),
        sa.UniqueConstraint("code", name=op.f("uq_counties_code")),
        sa.UniqueConstraint("country_id", "slug", name="uq_counties_country_slug"),
        sa.UniqueConstraint("id", "country_id", name="uq_counties_id_country"),
    )
    op.create_table(
        "towns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("county_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("coordinate_source", sa.String(length=300), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('city', 'town', 'municipality', 'locality')", name=op.f("ck_towns_town_kind")
        ),
        sa.CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL AND coordinate_source IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL AND coordinate_source IS NOT NULL)",
            name=op.f("ck_towns_town_coordinate_pair_source"),
        ),
        sa.CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name=op.f("ck_towns_town_latitude_range"),
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name=op.f("ck_towns_town_longitude_range"),
        ),
        sa.ForeignKeyConstraint(
            ["county_id"],
            ["counties.id"],
            name=op.f("fk_towns_county_id_counties"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_towns")),
        sa.UniqueConstraint("county_id", "slug", name="uq_towns_county_slug"),
        sa.UniqueConstraint("id", "county_id", name="uq_towns_id_county"),
    )
    op.create_table(
        "neighbourhoods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("town_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("coordinate_source", sa.String(length=300), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL AND coordinate_source IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL AND coordinate_source IS NOT NULL)",
            name=op.f("ck_neighbourhoods_neighbourhood_coordinate_pair_source"),
        ),
        sa.CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name=op.f("ck_neighbourhoods_neighbourhood_latitude_range"),
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name=op.f("ck_neighbourhoods_neighbourhood_longitude_range"),
        ),
        sa.ForeignKeyConstraint(
            ["town_id"],
            ["towns.id"],
            name=op.f("fk_neighbourhoods_town_id_towns"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_neighbourhoods")),
        sa.UniqueConstraint("id", "town_id", name="uq_neighbourhoods_id_town"),
        sa.UniqueConstraint("town_id", "slug", name="uq_neighbourhoods_town_slug"),
    )
    op.create_table(
        "properties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("property_type", sa.String(length=32), nullable=False),
        sa.Column("accommodation_type", sa.String(length=32), nullable=False),
        sa.Column("unit_type", sa.String(length=32), nullable=False),
        sa.Column("rent_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("rent_frequency", sa.String(length=16), nullable=False),
        sa.Column("deposit_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("bedrooms", sa.Integer(), nullable=False),
        sa.Column("bathrooms", sa.Numeric(precision=4, scale=1), nullable=False),
        sa.Column("size_sqm", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("parking_available", sa.Boolean(), nullable=False),
        sa.Column("parking_spaces", sa.Integer(), nullable=False),
        sa.Column("furnishing", sa.String(length=24), nullable=False),
        sa.Column("pet_policy", sa.String(length=24), nullable=False),
        sa.Column("water_availability", sa.String(length=24), nullable=False),
        sa.Column("electricity_available", sa.Boolean(), nullable=True),
        sa.Column("internet_available", sa.Boolean(), nullable=True),
        sa.Column("security_features", sa.JSON(), nullable=False),
        sa.Column("amenities", sa.JSON(), nullable=False),
        sa.Column("county_id", sa.Uuid(), nullable=False),
        sa.Column("town_id", sa.Uuid(), nullable=False),
        sa.Column("neighbourhood_id", sa.Uuid(), nullable=True),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("coordinate_source", sa.String(length=300), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("authorized_agent_user_id", sa.Uuid(), nullable=True),
        sa.Column("property_manager_user_id", sa.Uuid(), nullable=True),
        sa.Column("verification_status", sa.String(length=24), nullable=False),
        sa.Column("availability_status", sa.String(length=24), nullable=False),
        sa.Column("listing_status", sa.String(length=24), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("demo_disclaimer", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(unit_type IN ('bedsitter', 'studio') AND bedrooms = 0) OR "
            "(unit_type = 'one_bedroom' AND bedrooms = 1) OR "
            "(unit_type = 'two_bedroom' AND bedrooms = 2) OR "
            "(unit_type = 'three_bedroom' AND bedrooms = 3) OR "
            "(unit_type = 'four_bedroom' AND bedrooms = 4) OR "
            "(unit_type = 'five_plus_bedrooms' AND bedrooms >= 5)",
            name=op.f("ck_properties_bedroom_configuration"),
        ),
        sa.CheckConstraint(
            "accommodation_type IN ('whole_property', 'shared_accommodation', "
            "'student_accommodation')",
            name=op.f("ck_properties_accommodation_type"),
        ),
        sa.CheckConstraint(
            "availability_status IN ('unknown', 'available', 'unavailable')",
            name=op.f("ck_properties_availability_status"),
        ),
        sa.CheckConstraint("currency = 'KES'", name=op.f("ck_properties_currency_kes")),
        sa.CheckConstraint(
            "furnishing IN ('furnished', 'unfurnished', 'semi_furnished')",
            name=op.f("ck_properties_furnishing"),
        ),
        sa.CheckConstraint(
            "is_demo = FALSE OR (listing_status = 'draft' "
            "AND availability_status = 'unknown' "
            "AND verification_status = 'not_submitted')",
            name=op.f("ck_properties_demo_listing_disclosure_state"),
        ),
        sa.CheckConstraint(
            "listing_status IN ('draft', 'pending_review', 'published', 'archived', 'rejected')",
            name=op.f("ck_properties_listing_status"),
        ),
        sa.CheckConstraint(
            "pet_policy IN ('allowed', 'not_allowed', 'case_by_case', 'unknown')",
            name=op.f("ck_properties_pet_policy"),
        ),
        sa.CheckConstraint(
            "property_type IN ('apartment', 'house', 'maisonette', 'villa', 'townhouse')",
            name=op.f("ck_properties_property_type"),
        ),
        sa.CheckConstraint(
            "rent_frequency IN ('monthly', 'weekly', 'daily')",
            name=op.f("ck_properties_rent_frequency"),
        ),
        sa.CheckConstraint(
            "unit_type IN ('bedsitter', 'studio', 'one_bedroom', 'two_bedroom', "
            "'three_bedroom', 'four_bedroom', 'five_plus_bedrooms')",
            name=op.f("ck_properties_unit_type"),
        ),
        sa.CheckConstraint(
            "verification_status IN ('not_submitted', 'pending', 'verified', 'rejected')",
            name=op.f("ck_properties_verification_status"),
        ),
        sa.CheckConstraint(
            "water_availability IN ('reliable', 'intermittent', 'not_available', 'unknown')",
            name=op.f("ck_properties_water_availability"),
        ),
        sa.CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL AND coordinate_source IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL AND coordinate_source IS NOT NULL)",
            name=op.f("ck_properties_property_coordinate_pair_source"),
        ),
        sa.CheckConstraint(
            "bathrooms > 0 AND bathrooms <= 50", name=op.f("ck_properties_bathroom_range")
        ),
        sa.CheckConstraint(
            "deposit_amount IS NULL OR deposit_amount >= 0",
            name=op.f("ck_properties_deposit_nonnegative"),
        ),
        sa.CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name=op.f("ck_properties_property_latitude_range"),
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name=op.f("ck_properties_property_longitude_range"),
        ),
        sa.CheckConstraint(
            "parking_spaces = 0 OR parking_available = TRUE",
            name=op.f("ck_properties_parking_spaces_consistent"),
        ),
        sa.CheckConstraint("parking_spaces >= 0", name=op.f("ck_properties_parking_nonnegative")),
        sa.CheckConstraint("rent_amount > 0", name=op.f("ck_properties_positive_rent")),
        sa.CheckConstraint(
            "size_sqm IS NULL OR size_sqm > 0", name=op.f("ck_properties_size_positive")
        ),
        sa.ForeignKeyConstraint(
            ["authorized_agent_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_properties_authorized_agent_user_id_user_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["county_id"],
            ["counties.id"],
            name=op.f("fk_properties_county_id_counties"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["neighbourhood_id", "town_id"],
            ["neighbourhoods.id", "neighbourhoods.town_id"],
            name="fk_properties_neighbourhood_town",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_properties_owner_user_id_user_accounts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["property_manager_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_properties_property_manager_user_id_user_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["town_id", "county_id"],
            ["towns.id", "towns.county_id"],
            name="fk_properties_town_county",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_properties")),
    )
    with op.batch_alter_table("properties", schema=None) as batch_op:
        batch_op.create_index(
            "ix_properties_location_status",
            ["county_id", "town_id", "listing_status"],
            unique=False,
        )
        batch_op.create_index(
            "ix_properties_owner_created", ["owner_user_id", "created_at"], unique=False
        )
        batch_op.create_index(
            "ix_properties_public_status_rent", ["listing_status", "rent_amount"], unique=False
        )

    op.create_table(
        "property_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("media_type", sa.String(length=16), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("alt_text", sa.String(length=300), nullable=True),
        sa.Column("caption", sa.String(length=300), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_illustrative", sa.Boolean(), nullable=False),
        sa.Column("source_credit", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "media_type IN ('image', 'video', 'floor_plan')",
            name=op.f("ck_property_media_media_type"),
        ),
        sa.CheckConstraint(
            "position >= 0", name=op.f("ck_property_media_media_position_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("fk_property_media_property_id_properties"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_property_media")),
        sa.UniqueConstraint("property_id", "position", name="uq_property_media_position"),
    )
    _seed_reference_locations()
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("property_media")
    with op.batch_alter_table("properties", schema=None) as batch_op:
        batch_op.drop_index("ix_properties_public_status_rent")
        batch_op.drop_index("ix_properties_owner_created")
        batch_op.drop_index("ix_properties_location_status")

    op.drop_table("properties")
    op.drop_table("neighbourhoods")
    op.drop_table("towns")
    op.drop_table("counties")
    op.drop_table("countries")
    # ### end Alembic commands ###
