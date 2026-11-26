# HomeScout Kenya — Phase 6 Report

**Phase:** 6 — Property marketplace, search, discovery, and listing management  
**Date:** 2026-11-23  
**Status:** Implementation complete for the authorized Phase 6 scope.  
**Product name:** HomeScout.

> **Historical snapshot:** The Phase 5 Google map references below describe the implementation at Phase 6 completion. The current map uses MapLibre/OpenFreeMap; see [`MAPS_SETUP.md`](MAPS_SETUP.md) and [`EXPERIENCE_REPAIR_REPORT.md`](EXPERIENCE_REPAIR_REPORT.md).

## Scope delivered

### Marketplace API and data

- Added Alembic migration `20261123_06_marketplace` and normalized marketplace tables for amenities, saved listings, search history, search alerts, listing mandates, enquiries, and listing reports. Property media now stores validated MIME type, byte size, and a private storage key.
- Extended public property search with Kenyan county, town, and neighbourhood IDs; location-name/title/description query; KES rent range; exact or minimum bedroom count; building and unit type; furnishing; amenities; verified-only; map bounds; pagination; and deterministic rent/newest/bedroom sorts.
- Public search and detail expose only non-demo homes that are published and marked available. Synthetic records stay explicitly identified and cannot be published.
- Added detail, similar-listing, private owner/authorized-party preview, saved-listing, comparison (2–4 homes), capped search-history, and saved-search-alert APIs. Search alerts are stored; no match detection, push/email delivery, or retry worker is implemented.
- Added authenticated enquiries with sender/recipient-only access and owner/agent/manager status updates. Added listing-report submission with duplicate protection. Reports are recorded as `received`; there is no moderation queue or review outcome workflow in this phase.

### Listing workflows and access control

- Landlords can create/edit their own drafts, upload photos, set availability, preview, publish, archive, and delete drafts.
- Owners can grant or revoke an active listing mandate to an account with an approved agent role. Authorized agents can create and manage listings for that owner within their assigned scope. Existing property-level agent/manager assignments remain permission-checked.
- Publishing requires an available listing and at least one uploaded non-illustrative photo. Publishing does not imply property verification; verification status stays explicit.
- All protected operations enforce server-side authorization and write audit events for sensitive listing, media, availability, assignment, enquiry, and report actions.

### Android app

- Connected Discover and property detail to the configured HomeScout API, while retaining clearly labeled sample homes when no API URL is configured.
- Added rent, bedroom, type, furnishing, amenity, verification, and sorting controls; responsive adaptive property-card columns; KES pricing; location/fact badges; save and compare actions; detail gallery; enquiry/report dialogs; similar homes; search history; and a saved-search action with an explicit note that delivery is not active.
- Added an authenticated listing workspace for draft creation, location selection, editing, JPEG/PNG/WebP upload, availability, publish/archive/delete, and private preview. The app keeps its five primary tabs; marketplace workflows are secondary routes.
- Existing Phase 5 map and map/list screen remain connected as a secondary discovery route. Live Google Maps/Places still require the owner’s restricted keys and billing.

## Validation

- Backend Pytest: **44 passed** (one upstream Starlette/httpx deprecation warning).
- Ruff lint: passed. Ruff format check: passed (78 Python files).
- Marketplace behavior covered by API tests: filters and ordering, detail and uploaded-image reads, valid and rejected uploads, saves, compare, history, alert creation, enquiry creation/access/status, report submission, private preview, draft edits/deletion, ownership rejection, agent mandate creation/revocation, archive, and demo publication protection.
- Android `:app:testDebugUnitTest` (4 existing map/query unit tests) and `:app:assembleDebug`: passed after the final marketplace changes. Adaptive card columns are implemented. There are no dedicated Phase 6 Compose UI/instrumentation tests. The emulator already contained `ke.co.homescout.debug` signed by a different key, so Android rejected the replacement APK. I left the installed app and its data untouched; runtime installation/rendering and visual responsiveness of this Phase 6 build were not verified.
- A separate package smoke build was attempted to avoid replacing the installed app, but Gradle could not read the Android SDK's cached `core-lambda-stubs.jar` (`AccessDeniedException`) during Java compilation. The normal `.debug` package suffix was restored afterward.
- Phase 6 Alembic migration and the complete database test suite were verified with SQLite. PostgreSQL 17.12 checks recorded in earlier phase reports cover their migration set, not this new Phase 6 migration; a Phase 6 PostgreSQL 17 run remains a release validation item.

## Limits and follow-up

- No real property inventory or approved listing photos were supplied. A newly configured database therefore has no live homes; the Android sample cards are expressly labeled as sample content. Search is functional against API records once owners publish eligible listings.
- Uploaded media currently uses configurable local disk storage under `HOMESCOUT_MEDIA_STORAGE_DIR`, with a default development directory under `backend/var/property-media`. A managed object-storage provider, malware scanning, image re-encoding, backup, retention, and production CDN are not configured.
- Upload validation enforces size and JPEG/PNG/WebP signatures and serves files with `nosniff`; server-side full image decoding/re-encoding is not included.
- Saved-search alert persistence is implemented without notification delivery. Listing reports are collected without staff moderation tooling. Property verification and live external inventory feeds remain unimplemented.
- The app’s public results are available-only by API policy; owners and authorized agents control availability from listing management. Location queries match county, town, or neighbourhood names, and the API also accepts the corresponding IDs.
- PostgreSQL 17 verification for this migration, live API/device interaction, UI instrumentation, live Maps/Places calls, and production object-storage operations remain unverified.

## Stop point

Phase 6 is complete. Do not begin Phase 7 or another phase until the owner authorizes it.
