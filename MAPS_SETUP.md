# HomeScout map setup

HomeScout now uses MapLibre Native for Android with OpenFreeMap's public map styles. These map tiles do not require a Google account, API key, or billing account. The public instance permits commercial use and requires attribution. It has no service-level or uptime guarantee, so production availability is not assured. See [OpenFreeMap](https://openfreemap.org/) and its [mobile quick start](https://openfreemap.org/quick_start/).

## Android implementation

- MapLibre Native renders the interactive map in the Android app.
- The default style is https://tiles.openfreemap.org/styles/liberty; Bright, Positron, and Dark styles are also selectable.
- MapLibre displays the style attribution. HomeScout also visibly credits OpenFreeMap, OpenMapTiles, and OpenStreetMap contributors.
- No Google Maps/Places key, account, or billing setup is used.
- The project uses org.maplibre.gl:android-sdk:13.5.4.
- Internet permission is required. Location permission is requested only after the user chooses **My location**.
- Satellite and terrain imagery are not provided by these vector map styles. The app does not label the standard vector map as satellite imagery.

OpenFreeMap states that no map-view/request limits are imposed on its public instance, permits commercial use, and does not provide an SLA or warranty. Its maintainers depend on donations, so a future service change or outage remains possible. Review the provider's current terms before production scale. A self-hosted OpenFreeMap server or another provider can be selected by changing the Android map style configuration; higher-volume production should plan for a supported service.

## Kenyan area search

Area search is a user-submitted request proxied through the HomeScout API. By default, the backend uses the public Nominatim search endpoint with Kenya country filtering. The configured endpoint can be switched on the backend without releasing a new Android build:

HOMESCOUT_MAP_GEOCODER_URL=https://nominatim.openstreetmap.org/search

The proxy sends a HomeScout-identifying User-Agent, caches recent normalized searches in process memory, limits itself to one upstream request at a time and at least 1.1 seconds between uncached queries, and does not implement autocomplete or bulk geocoding. Search labels and coordinates are not saved to the location database. The mobile client retains only a small in-memory result cache for its running process.

The public Nominatim service is for moderate, directly user-triggered use. Its policy sets an absolute maximum of one request per second per application, requires an identifying User-Agent, disallows client autocomplete and systematic queries, and asks apps to remain switchable if the service asks them to stop. It may block traffic or change policy. At substantial production volume, configure a suitable alternative endpoint or self-host Nominatim before launch. See the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/).

## Property data integrity

- The map queries the existing public property endpoint with visible viewport bounds and selected filters.
- Markers are limited to published, available, non-demo property records with both coordinates and a recorded coordinate source.
- Synthetic development homes have no coordinates and are excluded from map markers.
- Nominatim's place coordinates only position the user's selected map search. They do not become property coordinates or get persisted.
- Marker previews open the selected listing detail screen. Map/list results stay linked to the same property IDs.
- Nearby business search is not included because the selected no-key map provider does not supply a Places search API. No nearby results are fabricated.

## Development

1. Run the HomeScout FastAPI backend and configure the Android API base URL as documented in ANDROID_DEVICE_SETUP.md.
2. Use a device or emulator with internet access. Google Play services are needed only for the optional device-location button.
3. Open the Map destination. Search a Kenyan town or neighbourhood, choose a returned result, then pan/zoom and use **Search this area**.
4. If the map tiles do not load, the screen reports a loading error and offers a retry; property search and other app destinations remain available.

No map API key or billing configuration is required for this development setup.

## Emulator verification — 2026-11-24

- Opened the Map destination in the Android emulator and visually confirmed actual OpenFreeMap/OpenMapTiles vector tiles and map labels rendered in MapLibre. This was the existing installed MapLibre build; the map provider/style implementation is unchanged in the latest source.
- The phone-configured APK compiles with `http://127.0.0.1:8765`; use `adb reverse tcp:8765 tcp:8765` for the workstation API. A separate emulator build needs `http://10.0.2.2:8765`.
- No public real property inventory was present, and synthetic demo records are drafts without coordinates, so no property markers were expected or shown.
- This verifies tile rendering, not satellite imagery, Nominatim production-scale capacity, property marker selection against live listings, or public-service uptime.
