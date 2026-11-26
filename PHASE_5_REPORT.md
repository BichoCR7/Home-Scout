# HomeScout Kenya — Phase 5 Report

**Phase:** 5 — Google Maps and property location exploration  
**Date:** 2026-11-23  
**Status:** Implementation complete. Live Google Cloud service verification needs restricted owner keys.

> **Historical snapshot:** This report records the original Phase 5 implementation. The owner later chose a no-key map; current MapLibre/OpenFreeMap implementation and device-render verification are documented in [`MAPS_SETUP.md`](MAPS_SETUP.md) and [`EXPERIENCE_REPAIR_REPORT.md`](EXPERIENCE_REPAIR_REPORT.md).

## Scope completed

- Integrated the actual Google Maps SDK for Android through Jetpack Compose Maps Compose. Supported map types are roadmap, satellite, hybrid, and terrain.
- Added a location-first map screen. The camera target comes from a selected Kenya-restricted Google Places result or an explicitly permissioned device location. The app does not seed guessed Kenyan coordinates or open a pretend map if the Maps key is absent.
- Added Places SDK (New) autocomplete and Place Details to resolve selected search results. Requests are debounced, begin after three typed characters, restricted to Kenya, and use an autocomplete session token.
- Added on-demand Places Nearby Search for schools, healthcare, transit, and shopping, using a limited field mask and five-kilometre radius. Nearby results carry a Google Places attribution in the UI.
- Added runtime coarse/fine location permission only after a user taps a location control. No background location permission is requested.
- Added road/satellite/hybrid/terrain chips, map/list switching, fullscreen, search-this-area, filters, loading/error/empty states, a filter sheet, selected-listing preview, KES price markers, and marker clustering.
- Added filters for rent, property type, bedrooms including four-plus, furnishing and verified status. Availability remains implicitly available-only because the public endpoint only returns published, available, non-demo properties.
- Extended the public property list endpoint with map viewport, minimum-bedroom, furnishing, and verified-only filters. Map responses still omit synthetic/draft/unavailable rows. Android marker parsing requires paired coordinates and recorded coordinate source.
- Added external API key configuration through `HOMESCOUT_MAPS_API_KEY` and `HOMESCOUT_PLACES_API_KEY` or Gradle properties. No key was placed in source. Added setup documentation for APIs, Android/package/SHA-1 and API restrictions, billing, development, release, and fallback.
- Preserved HomeScout branding, the five persistent tabs, and the secondary Map route.

## Verification

| Check | Result |
|---|---|
| Backend Pytest | Passed: 39 tests (including map filter and viewport validation). |
| Ruff lint/format | Passed after Phase 5 changes. |
| Android Kotlin/Java compilation and unit tests | Passed: 4 map unit tests. |
| Debug APK assembly | Passed: `:app:assembleDebug`; installed as `ke.co.homescout.debug`. |
| Google Maps/Places live requests | Not run: no Google Cloud keys were provided. |
| Emulator/device interaction and visual rendering | Passed for launch, animated splash-to-home, five-tab shell, Discover-to-Map navigation, and missing-key fallback. |
| PostgreSQL migration | Not applicable: Phase 5 changed no database schema or migration. |

The Android verification environment initially had no PATH Java. The installed Android Studio JDK 25 still fails Gradle configuration with the version string `25.0.4`; the successful build used a temporary project-local JDK 17 in the ignored `work/` directory. No machine-wide Java installation was changed. Select JDK 17 as Android Studio's Gradle runtime, as noted in `README.md`. Gradle's generated problems report was disabled for the verified run because its temporary-file move collides with the protected Windows workspace report path. AGP also warns that 8.13.2 was tested through SDK 36.1 while this resolved Google SDK graph requires compile SDK 37; compilation and packaging passed despite that compatibility warning.

## Setup dependency / limitations

- A Google Cloud project, billing account, Maps SDK for Android and Places API (New) must be enabled. Two separate Android-application-restricted and API-restricted keys are required. See [`MAPS_SETUP.md`](MAPS_SETUP.md).
- The app currently has no real published listings. The live backend therefore correctly yields no property markers until published, available, non-demo listings with sourced coordinates exist.
- Google may return provider errors for an invalid key, unavailable service, network failure, or billing/restriction issue. Missing keys are handled explicitly; live failure diagnosis and tile rendering need an actual configured device. Map SDK does not expose a reliable Compose callback for every individual tile authorization failure.
- The debug package uses `ke.co.homescout.debug` so it can be installed beside a differently signed `ke.co.homescout` package. Configure the matching debug package and certificate SHA-1 in Maps/Places key restrictions; release remains `ke.co.homescout`.
- No geocoding service was added for database reference locations. Places results are used for the selected viewport, not persisted as authoritative neighbourhood coordinates.

## Key implementation files

- `app/src/main/java/ke/co/homescout/features/map/MapScreen.kt`
- `app/src/main/java/ke/co/homescout/features/map/MapModels.kt`
- `app/src/main/java/ke/co/homescout/features/map/MapPropertyApi.kt`
- `app/src/main/java/ke/co/homescout/navigation/HomeScoutApp.kt`
- `backend/app/api/v1/endpoints/properties.py`
- `backend/app/services/properties.py`
- `backend/app/data_access/properties.py`
- `app/src/test/java/ke/co/homescout/features/map/MapModelsTest.kt`
- `backend/tests/test_properties.py`

The debug APK is at `app/build/outputs/apk/debug/app-debug.apk`.

---

See [`PHASE_4_REPORT.md`](PHASE_4_REPORT.md) for the Kenya location/property model and PostgreSQL checks.
