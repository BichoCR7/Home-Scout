# HomeScout Kenya — Phase 15 QA, security, performance, and accessibility report

**Date:** 2026-11-24  
**Scope:** Phase 15 only. Review and targeted fixes to the existing HomeScout application; no feature redesign or later phase work.

> **Historical snapshot:** The Google Maps findings below were recorded before the post-phase provider change. Current status: MapLibre/OpenFreeMap road-map tiles rendered in the QA emulator; satellite imagery and Places are not included. See [`MAPS_SETUP.md`](MAPS_SETUP.md) and [`EXPERIENCE_REPAIR_REPORT.md`](EXPERIENCE_REPAIR_REPORT.md).

## Executive result

The current backend test suite, SQLite migration upgrade, Python lint/format checks, Android debug and release compilation, Android unit tests, Android lint, and both APK assemblies passed. A running Android emulator was used to inspect the five primary tab destinations and Home/Discover/Areas/Finance/Profile states. The review made narrowly scoped fixes to Android target compatibility, theme resource compatibility, local SDK path parsing, and text contrast.

The project is **not launch-ready**. PostgreSQL 17 migrations after Phase 4, live Google Maps/Places, Daraja, AI provider calls, production storage, production email, and an authenticated end-to-end journey were not verified. This report is a technical QA review, not a penetration test or legal compliance opinion.

## Test results

| Check | Result | Scope and limits |
|---|---|---|
| Backend Pytest | **88 passed** | Full suite; 1 upstream Starlette/httpx test-client deprecation warning. |
| Python Ruff lint | **Passed** | `ruff check app migrations tests`. |
| Python Ruff format | **Passed** | 144 files already formatted. |
| Alembic migration | **Passed on SQLite** | Upgraded the complete schema from base through `d14a9c2e5f81` (head). Phase 6–14 PostgreSQL 17 migration execution remains outstanding. |
| Android Kotlin debug compilation | **Passed** | Current debug variant. |
| Android unit tests | **Passed** | Map models/configuration and price parser plus new WCAG color contrast regression test. No Compose instrumentation test suite exists. |
| Android lint | **Passed** | 0 errors, 30 warnings. Warnings include dependency/version advice, deprecated Compose APIs/icons, naming/style notices, and target API advisory. |
| Android debug APK | **Passed** | `:app:assembleDebug` produced `app-debug.apk`. |
| Android release APK | **Assembled, unsigned** | After pinning installed Build Tools 36.0.0, `:app:compileReleaseJavaWithJavac :app:assembleRelease` completed successfully (`BUILD SUCCESSFUL`) and produced `app-release-unsigned.apk`. The initial sandbox access-denied attempt was resolved by retrying with permitted SDK access. No release signing configuration is present, so this artifact is not ready for distribution. |
| Android emulator smoke check | **Passed, limited** | API 37 emulator, 1080×2400 display. App opened and Home, Discover, Areas, Finance, and Profile were reached. Only one emulator/device density was examined. |
| Android UI automation | **Not available** | There is no `androidTest` source suite; Compose interactions were manually smoke-checked. |
| Backend vulnerability scan | **No known third-party findings** | `pip-audit --local`; the locally named `homescout-api` project package is not resolvable from PyPI and is reported as skipped. |
| Backend Bandit scan | **No medium/high findings** | `bandit -ll -ii -r app` reported no issues at those thresholds. Broad scan reports 8 low findings: token claim string `access` is a heuristic false positive; remaining findings are assertions in application code. No high/medium findings were reported. |

Backend automated coverage includes health/configuration, database setup/migrations, authentication/session lifecycle, RBAC and role administration, property/location/marketplace, SmartRent calculations and privacy, trust/safety, messaging/viewings/comparison/shared searches/roommates, moving/services/maintenance, M-Pesa callback/idempotency, AI privacy/context, and admin/moderation/audit workflows. Relevant tests are in `backend/tests/`, including `test_authentication.py`, `test_authorization.py`, `test_marketplace.py`, `test_smartrent.py`, `test_trust_safety.py`, `test_phase10.py`, `test_services.py`, `test_payments.py`, `test_assistant.py`, and `test_admin_operations.py`.

Automated backend tests validate configured behavior with SQLite and test fixtures. They do not substitute for live provider testing, production PostgreSQL execution, authenticated full-device user journeys, or external security testing.

## Fixes made

- Set Android `targetSdk` to API 36. Google Play's current requirement for new app submissions and updates is API 36 or higher from August 31, 2026; see [Android Developers: target API requirements](https://developer.android.com/google/play/requirements/target-sdk). The installed API 37 emulator was used for a basic smoke check, not a full Android 16 compatibility matrix.
- Moved `windowLightNavigationBar`, an API 27 theme attribute, into `values-v27` so minSdk 26 resources do not apply it on older Android versions.
- Escaped the Windows drive colon in the local, ignored `local.properties` SDK path so Java properties parsers interpret it consistently.
- Retained the brand green `#16A34A` for the visual identity, but introduced a darker green text/status token `#15803D` for small status text on light surfaces. Its measured contrast is about 5.0:1 on white and 4.7:1 on the app background; a Compose contrast regression test protects the chosen light/dark text combinations. Navigation selected colors now use the primary blue instead of small green text.

## Functional coverage and limitations

- Backend feature groups listed above pass automated tests. API route/authorization behavior is covered by the test suite; no external user data was used.
- Android tested: debug Kotlin compilation, Compose-containing app package, map model unit tests, contrast unit test, lint, APK assembly, app launch, and primary bottom-tab switching. Five bottom tabs remain the primary navigation.
- Search/listings, saved data, profile editing, finance, trust, messaging, viewings, services, payments, AI, and admin were not each completed as authenticated, end-to-end device journeys in this QA run. Their backend API behavior is covered to the extent listed in automated tests.
- API-unconfigured/sample states were visible in the emulator; no live HomeScout inventory is seeded. The sample home content remains clearly identified as illustrative.
- Google Maps/Places SDK code and fallback states are present, but no Google Cloud key/billing setup was supplied. Live roadmap/satellite/hybrid/terrain tiles, Kenya Places, and billing restrictions were not exercised.
- M-Pesa remains disabled without Daraja credentials and public callback hosting; no sandbox or live transaction was sent. The Android client does not establish payment success.
- The AI provider remains disabled without provider credentials and an encryption key; no provider request was made and no synthetic AI answer was treated as real.
- No push/email delivery, production object storage, malware scanner, backup/restore, or CDN was tested or configured.
- SQLite Alembic upgrade reached the current head. PostgreSQL 17 execution for Phases 6–14 remains unverified; previous PostgreSQL checks through Phase 4 do not cover these later migrations.

## Security review

### Critical / high

No critical or high issue was reported by the scoped Bandit scan or installed-environment dependency scan. This is not a penetration test and does not prove the absence of vulnerabilities.

### Medium

- **Production storage and document operations:** local disk storage is development-only. Production object storage, managed encryption keys, malware scanning, backups, retention, and restore procedures must be established before real user documents are accepted.
- **Production database coverage:** Phase 6–14 migrations and representative workflows still need a PostgreSQL 17 run.
- **Live integrations:** Maps key restrictions/billing, Daraja callback deployment, provider AI terms/configuration, and SMTP must be tested in owner-controlled environments before they are enabled.

### Low / technical debt

- Broad Bandit mode reports 8 low findings, mostly assertion use plus the `token_use="access"` string heuristic. The high/medium threshold run reported none.
- Android lint reports 30 warnings, including dependency-age suggestions, deprecated APIs/icons, naming/style recommendations, backup-rule guidance, and a target-SDK advisory because API 37 is installed. No Android lint errors remain.
- The Gradle wrapper remains at 8.13 and AGP is 8.13.2 while compile SDK 37 emits an AGP compatibility warning. Gradle warns that future Kotlin Gradle Plugin 2.5 requires Gradle 8.14.4 or newer. These are maintenance warnings; a toolchain upgrade was not bundled into this targeted QA pass.
- Debug explicitly allows cleartext to support the local emulator API; the main manifest does not declare cleartext traffic. Keep this debug-only and require HTTPS for deployed API endpoints.

Security controls inspected include server-side authentication and RBAC, token hashing/rotation/revocation, environment-backed secret validation, limited CORS origins, parameterized SQLAlchemy queries, private media path containment, file size/type/signature validation, ownership checks, authenticated document reads, audited admin actions, and backend-controlled payment status. These controls still require deployment configuration and independent review.

## Performance review

- No frame-time, startup, memory, database-load, network-load, or map performance benchmark was run. Only visual launch and route smoke checks were performed.
- Remote property photography is loaded with network work on `Dispatchers.IO` and connection timeouts; the current custom loader has no explicit decoded-bitmap memory cache or image downsampling layer. Profile memory use and consider a lifecycle-aware image loader before scaling inventory.
- Map/API performance was not measured because Maps keys and live inventory are unavailable. Database behavior was tested functionally, not against production-like data volume or query plans.

## Accessibility and UX review

- Fixed small green status text contrast and added a calculation-based unit test. Core brand blue/navy and muted text tokens meet the checked contrast values on light backgrounds.
- Primary navigation has five labeled destinations; common buttons have minimum heights around 46–48 dp; remote images and many icon-only actions provide semantics/content descriptions.
- The emulator smoke check covered the five primary destinations, visible loading/sample/configuration states, and navigation shell. It did not test TalkBack, keyboard-only operation, Android Accessibility Scanner, all dialogs/forms, enlarged text on every screen, color-blindness scenarios, or a broad screen-size matrix.
- Dark theme was reviewed in source and its status text contrast is in the automated calculation test; a full dark-theme device walkthrough was not recorded.

## Kenya data protection review

This technical review does **not** determine legal compliance. Before operating with real people or housing records, have Kenyan privacy counsel or a qualified data-protection professional review controller/processor roles, ODPC registration obligations, lawful bases and notices, user rights, retention/deletion, third-party processing, security operations, and any required DPIA. Primary references: [Kenya Data Protection Act, 2019](https://new.kenyalaw.org/akn/ke/act/2019/24/eng%402022-12-31/source.pdf), [ODPC registration FAQs](https://odpc.go.ke/faqs/), and [ODPC DPIA guidance](https://www.odpc.go.ke/wp-content/uploads/2024/02/ODPC-Guidance-Note-on-Data-Protection-Impact-Assessment-1.pdf). No compliance certificate or legal conclusion is asserted.

## Remaining launch risks

1. Release signing is not configured; provision protected signing credentials and validate the signed artifact before distribution.
2. PostgreSQL 17 migration/API verification for Phases 6–14 is outstanding.
3. No Compose instrumentation or authenticated end-to-end suite exists; add/run it on representative Android 15/16 devices and smaller/larger layouts.
4. Resolve the remaining lint/deprecation backlog and align AGP/Gradle with compile SDK 37 and the Kotlin plugin support window.
5. Profile remote image memory/cache behavior, representative backend query plans, map rendering, and startup on a production-like dataset/device.
6. Configure production hosting, secrets/key management, secure media storage, malware scanning, backups/restore, monitoring, alerting, incident response, and privacy retention procedures.
7. Run live Google Maps/Places, Daraja sandbox, SMTP, and AI provider tests only after owner-controlled credentials, billing, policies, and callback infrastructure are available.
8. Complete independent security testing and Kenyan data protection/legal review before pilot or public launch.

## Phase status

Phase 15 QA activities are complete within the available local environment. Stop here; do not begin Phase 16 or later without separate owner authorization.
