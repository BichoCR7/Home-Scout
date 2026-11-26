# HomeScout Kenya

HomeScout is a Kenya-first housing app. This project lives in its own `HomeScout` directory, separate from RentWise. The app keeps five bottom tabs: Home, Discover, Areas, Finance, and Profile. Other destinations remain secondary navigation or clearly marked placeholders until their phases are authorized.

## Android

Requirements: JDK 17 or newer supported Gradle JDK, Android SDK platform 37 / Build Tools 36.0.0 (target SDK 36), and Kotlin 2.4.21.

Select a supported JDK 17+ Gradle runtime in Android Studio (`Settings > Build, Execution, Deployment > Build Tools > Gradle > Gradle JDK`) or set `JAVA_HOME` before running the wrapper. Phase 15/16 Android checks used the bundled JBR 21 runtime.

```powershell
$env:JAVA_HOME = 'C:\path\to\jdk-17'
$env:ANDROID_HOME = 'C:\path\to\android-sdk'
$env:HOMESCOUT_API_BASE_URL = 'http://10.0.2.2:8766' # Android emulator
.\gradlew.bat --no-problems-report :app:assembleDebug
.\gradlew.bat --no-problems-report :app:testDebugUnitTest
```

The base address comes from Gradle property `homescout.apiBaseUrl`, environment variable `HOMESCOUT_API_BASE_URL`, or the developer-only `homescout.apiBaseUrl` entry in ignored `local.properties`; no API URL is repeated in feature source. The Profile screen connects to identity and authorized role-management flows. Its personal hub includes profile/preferences, saved items and collections, activity, schedule, in-app notifications, user-entered records, private documents, support tickets, data export, account deletion requests, and Trust & safety. Discover and property details connect to the marketplace API; landlords and authorized agents use the secondary listing workspace. Services is a secondary route for provider discovery, bookings, moving plans, room setup, and maintenance. The Finance tab includes SmartRent, HomeScout's private housing-planning and financial-learning tools. Access and refresh tokens are encrypted with AES-GCM using an Android Keystore key. The API address is configuration, not a secret.

For a physical Android phone using the current workstation-hosted backend, configure `http://127.0.0.1:8766` and run `adb reverse tcp:8766 tcp:8766`; see `ANDROID_DEVICE_SETUP.md`. The emulator uses `10.0.2.2:8766` to reach the workstation.

## Backend

See [`backend/README.md`](backend/README.md) for setup, environment configuration, migration, run commands, account, marketplace, and SmartRent flows, first-admin bootstrap, media-storage settings, tests, and PostgreSQL preparation.

## Free map setup

The current map uses MapLibre Native and OpenFreeMap's public vector tiles; no Google key, account, or billing setup is required. MapLibre is wired to render the provider's live styles, with OpenFreeMap/OpenMapTiles/OpenStreetMap attribution. Kenyan place search is sent to the HomeScout API and proxied to Nominatim on explicit search. The public services have no uptime guarantee and Nominatim has strict low-volume limits. Satellite, hybrid, terrain, Google Places, and nearby-business lookup are not part of this configuration. See [`MAPS_SETUP.md`](MAPS_SETUP.md).

## Project status

- Phase 1: Android design system and application shell complete.
- Phase 2: FastAPI, SQLAlchemy, Alembic, SQLite foundation, and centralized Android API configuration complete.
- Phase 3: account lifecycle, server-side role management, protected API operations, and Android Profile integration complete.
- Phase 4: Kenyan location hierarchy, property/media data foundation, location search, and owner-scoped draft APIs complete.
- Phase 5: the original Google Maps integration was replaced after the phase with a no-key MapLibre/OpenFreeMap map. Real vector tiles rendered in the Android emulator on 2026-11-24. Satellite imagery and Places search are not available in this provider setup.
- Phase 6: backend-backed property search/discovery, details, saves/compare/enquiries/reports, saved-search records, and authorized listing management complete.
- Phase 7: account profile, role-safe switching, saved items/collections, activity, East Africa Time schedule, in-app notifications, manual KES records, private documents, support, settings, export, and deletion requests complete.
- Phase 8: SmartRent housing-planning tools and financial learning complete. Finance data is owner-scoped and encrypted at rest; real credit, lending, payments, and money custody are not included. The Assistant was implemented separately in Phase 13.
- Phase 9: manual verification, safe-viewing, private reports, and permission-gated moderation complete. See `PHASE_9_REPORT.md`.
- Phase 10: authorized messaging, host-confirmed viewings, private comparisons and journals, opt-in roommate discovery, and shared housing searches complete. See `PHASE_10_REPORT.md`.
- Phase 11: service-provider discovery, booking/order records, private moving plans, room setup, and authorized maintenance workflows complete. See `PHASE_11_REPORT.md`.
- Phase 12: backend-first Daraja service-booking STK Push/query architecture, transaction history, idempotent callbacks, reconciliation, and Android payment history/request screens complete. The integration is disabled until credentials and public HTTPS callback hosting are configured; no sandbox transaction was sent. See `PHASE_12_REPORT.md`.
- Phase 13: privacy-first HomeScout Assistant architecture, encrypted owner-scoped history, consent/context controls, server-side provider adapter, and Android assistant entry points complete. AI remains disabled until server-side provider and encryption settings are supplied. See `PHASE_13_REPORT.md`.
- Phase 14: permission-gated staff operations, actual operational counts, audited account/listing/service controls, support queue, message and service-review moderation, controlled settings, and Android Operations console complete. See `PHASE_14_REPORT.md`.
- Phase 15: backend/API and SQLite migration QA, Android debug/release builds, lint/unit/emulator checks, security scans, and targeted compatibility/accessibility fixes complete. Later PostgreSQL migrations, live integrations, and production readiness remain outstanding. See `PHASE_15_REPORT.md`.
- Phase 16: deployment and competition-demo preparation complete. Includes production deployment guidance, a non-root backend container definition, release signing/API preflight, release checklist, demo runbook, presentation outline, and Phase 16 report. No service was deployed or distributed; PostgreSQL Phase 6–14 validation, provider credentials, signing keys, live inventory, durable storage, and the full 25-step demo remain outstanding.

See [`ROADMAP.md`](ROADMAP.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), and the latest [`PHASE_REPORT.md`](PHASE_REPORT.md). Phase 16 guidance: [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md), [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md), [`COMPETITION_DEMO_GUIDE.md`](COMPETITION_DEMO_GUIDE.md), and [`COMPETITION_PRESENTATION_OUTLINE.md`](COMPETITION_PRESENTATION_OUTLINE.md). Phase reports: [`PHASE_1_REPORT.md`](PHASE_1_REPORT.md), [`PHASE_2_REPORT.md`](PHASE_2_REPORT.md), [`PHASE_3_REPORT.md`](PHASE_3_REPORT.md), [`PHASE_4_REPORT.md`](PHASE_4_REPORT.md), [`PHASE_5_REPORT.md`](PHASE_5_REPORT.md), [`PHASE_6_REPORT.md`](PHASE_6_REPORT.md), [`PHASE_7_REPORT.md`](PHASE_7_REPORT.md), [`PHASE_8_REPORT.md`](PHASE_8_REPORT.md), [`PHASE_9_REPORT.md`](PHASE_9_REPORT.md), [`PHASE_10_REPORT.md`](PHASE_10_REPORT.md), [`PHASE_11_REPORT.md`](PHASE_11_REPORT.md), [`PHASE_12_REPORT.md`](PHASE_12_REPORT.md), [`PHASE_13_REPORT.md`](PHASE_13_REPORT.md), [`PHASE_14_REPORT.md`](PHASE_14_REPORT.md), [`PHASE_15_REPORT.md`](PHASE_15_REPORT.md), and [`PHASE_16_REPORT.md`](PHASE_16_REPORT.md).

Twenty synthetic listings with distinct illustrative stock images are seeded only in the development database for discovery testing. They are explicitly marked, draft, unverified, availability-unknown, and have no coordinates; they are not real inventory and will not appear as map markers or public search results. No real listings or service providers are seeded. Listing media, provider images, maintenance attachments, profile photos, and private documents use development local disk storage. Verification documents and trust evidence are encrypted at rest with `HOMESCOUT_TRUST_ENCRYPTION_KEY`; Phase 10 message bodies and private comparison/journal payloads use a distinct `HOMESCOUT_MESSAGE_ENCRYPTION_KEY`. Phase 13 Assistant history is encrypted using its own `HOMESCOUT_AI_ENCRYPTION_KEY`; provider processing remains disabled until configured. Phase 14 admin operations are permission-gated and audited, with privacy-limited operational counts and an allow-listed settings panel. Production storage, key custody, malware scanning, backup, and retention controls remain unconfigured. Trust/provider approval indicators use recorded system cases only; allegations do not automatically change user or listing standing. A Phase 11 service order remains a booking record until a Phase 12 backend payment is confirmed by Daraja; M-Pesa is disabled by default, real credentials/callback hosting are not configured, and sandbox transactions were not run. No rent custody, escrow, refunds, or provider payout is implemented. Notifications and viewing reminders are in-app records; push/email delivery is not implemented. OpenFreeMap vector tiles were visually confirmed in the emulator. The latest phone-configured APK was installed and launched on the Samsung SM-S938B with ADB reverse active; the emulator's separately installed package still has a different signing certificate and was left untouched. See [`MAPS_SETUP.md`](MAPS_SETUP.md) and [`EXPERIENCE_REPAIR_REPORT.md`](EXPERIENCE_REPAIR_REPORT.md). Phase 6–14 migrations still need PostgreSQL 17 verification.
