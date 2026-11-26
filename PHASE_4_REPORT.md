# HomeScout Kenya — Phase 4 Report

**Phase:** 4 — Kenyan location system and property data foundation  
**Date:** 2026-11-23  
**Status:** Complete. Work stopped at the Phase 4 boundary.

## Scope completed

- Added SQLAlchemy country, county, town, neighbourhood, property, and property-media models with a portable Alembic migration (`add5ba78b682`).
- Seeded Kenya and all 47 county names/codes. The county list follows the [Kenya National Bureau of Statistics 2019 Census Atlas](https://www.knbs.or.ke/wp-content/uploads/2025/11/2019-KPHC-Atlas-Reference-Maps.pdf); administrative headquarters follow the [State Department for Devolution county reference](https://devolution.go.ke/county-information).
- Seeded each county headquarters and the priority towns and neighbourhoods from the Phase 4 brief. This yields 66 towns/localities and 33 neighbourhoods in the migration.
- Kept all seeded location coordinates null. API/model validation requires paired latitude/longitude plus a coordinate source before coordinates can be saved.
- Added location list, hierarchy, search, and admin-gated town/neighbourhood extension APIs. Search results include their county and town context.
- Added property fields for building type, accommodation type, room configuration, KES rent/deposit, furnishing, utilities, amenities, security, location, ownership, verification/availability/listing state, and dates. Image, video, and floor-plan metadata use a separate media table.
- Added validation for KES, positive rent, room-count/type consistency, location parent relationships, coordinate provenance, HTTPS media URLs, bounded media counts, and supported status values.
- Added public property list/detail reads that only return published, available, non-demo records. Landlords can create and edit their own draft records; these routes do not publish or verify them.
- Added test-only synthetic property fixtures for Kilimani, Lavington, and Ruaka with KES examples and illustrative Unsplash images. They are marked as demo, draft, not submitted for verification, and availability unknown. API access requires `include_demo=true`; they are not seeded into runtime databases.
- Updated project architecture, roadmap, task status, changelog, decisions, backend setup, and photo-source documentation. Preserved the former Phase 3 report as `PHASE_3_REPORT.md`.

## Verification

| Check | Result |
|---|---|
| Full backend Pytest suite | Passed: 37 tests. One upstream Starlette/httpx test-client deprecation warning. |
| Ruff lint | Passed: no findings. |
| Ruff format check | Passed: all 70 Python files formatted. |
| SQLite Alembic upgrade | Passed on a temporary database. The migration created the schema and seeded 47 counties, 66 towns/localities, and 33 neighbourhoods. |
| SQLite migration upgrade/downgrade | Passed through the backend migration tests, including downgrade to base. |
| Location/property API behavior | Passed search/hierarchy, admin permission, property validation, owner-only draft edit, public filtering, and explicit demo inclusion checks. |
| PostgreSQL 17.12 migration and behavior | Passed on a disposable local PostgreSQL 17.12 cluster. Applied all migrations to head, checked 47/66/33 seeded locations, exercised county listing and Westlands search, created a landlord draft with KES and illustrative media, confirmed owner-scoped retrieval and public draft exclusion, then downgraded to Phase 3 and upgraded to head again. The cluster was stopped and its test data removed. |
| Android build | Not run: Phase 4 changed only backend code and documentation; Android sources were not changed. |

## Scope limits

- No real or verified inventory is included. No property is auto-published or asserted available by the draft APIs.
- Publishing/moderation, agent and property-manager assignment workflows, media upload/object storage, map/geocoding integration, spatial search, and Android live discovery remain out of scope.
- Seeded towns/neighbourhoods are a reference-data starting set. Additional areas require sourced/admin-maintained data; coordinates must not be guessed.
- Production hosting, backup/restore, and automated PostgreSQL CI remain unverified; the local PostgreSQL run does not substitute for those release checks.

## Main implementation files

- `backend/app/models/location.py`, `backend/app/models/property.py`
- `backend/app/schemas/locations.py`, `backend/app/schemas/properties.py`
- `backend/app/data_access/locations.py`, `backend/app/data_access/properties.py`
- `backend/app/services/locations.py`, `backend/app/services/properties.py`
- `backend/app/api/v1/endpoints/locations.py`, `backend/app/api/v1/endpoints/properties.py`
- `backend/migrations/versions/add5ba78b682_add_kenyan_locations_and_property_data_.py`
- `backend/tests/test_locations.py`, `backend/tests/test_properties.py`, `backend/tests/demo_properties.py`

---

See [`PHASE_3_REPORT.md`](PHASE_3_REPORT.md) for Phase 3 identity implementation and PostgreSQL 17.12 checks.
