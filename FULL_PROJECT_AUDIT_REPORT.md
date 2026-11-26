# HomeScout — Full Project Audit and Local Launch Report

**Date:** 2026-11-24  
**Scope:** Audit of the existing Phase 0–16 HomeScout implementation, targeted repair, verification, and local launch. No new development phase was started. Follow-up repair findings are appended at the end.
**Project:** C:/Users/edris/Documents/Codex/HomeScout

## Role-specific dashboard follow-up — 2026-11-26

- Connected the Home route and bottom navigation to the server-selected active role. Tenants retain the housing-discovery homepage; landlords, real-estate agents, property managers, service providers, roommates, moderators, admins, and Super Admins receive distinct dashboards and role-focused tabs/actions.
- Added active-role switching to the profile drawer through the existing authenticated `/hub/profile/active-role` API. The client displays only roles already assigned by authorized administration; the backend remains the permission authority. No demo role or account was created.
- Added focused initial-tab/section routing to the existing Services, Trust, and Operations destinations for service bookings, maintenance, moderation, reports, support, settings, and audit workflows.
- `:app:assembleDebug` passed. `adb install -r` updated `ke.co.homescout.latest` without uninstalling or clearing either HomeScout package. `am start -W` returned `Status: ok`; the process was running, but Android still reported TikTok as the top-resumed activity, so the HomeScout screen was not visually inspected on-device. No automated tests were run.
- This is a targeted post-Phase 16 repair. No backend schema, role grants, deployment, or GitHub push was performed.

### Startup crash repair — 2026-11-26

- Reproduced a startup crash on the Samsung SM-S938B. Logcat identified a `NullPointerException` in `workspaceTabs` when the fallback read a null entry from the shared `Destination.primaryItems` list.
- Replaced the fallback list with explicit Home, Discover, Areas, Finance, and Profile entries. `:app:assembleDebug` passed. Updated `ke.co.homescout.latest` in place; Android reported successful launch and HomeScout MainActivity resumed. A device screenshot showed the signed-in Profile UI rendered, and no post-fix fatal exception appeared in logcat. Existing app data and the other HomeScout package were preserved.

## Executive result

The audit snapshot originally recorded 89 backend tests. A subsequent full run passed 92 tests, Ruff lint/format passed, and Android unit tests plus debug assembly passed. A later follow-up replaced the map provider: OpenFreeMap vector tiles have now rendered in the Android emulator. The older Google Maps statements below describe the pre-follow-up audit and are superseded by the repair section at the end.

HomeScout is **running locally for backend development but is not production or competition-demo ready**. No production deployment or signed release was made. The current phone-configured debug APK was installed and launched on the Samsung SM-S938B with `127.0.0.1:8765` and `adb reverse tcp:8765 tcp:8765`; Android showed the HomeScout authentication entry with a live resumed activity and no recent fatal crash. The emulator package has a different signing certificate from that APK, so it was not overwritten and its data was preserved. Daraja, AI, PostgreSQL migrations after Phase 4, and production release signing remain gated or unverified.

## Phase-by-phase audit

| Phase | Audit finding | Verification boundary |
|---|---|---|
| 0 — Project intelligence | Project rules, architecture, roadmap, decisions, and phase boundaries are documented. | Documentation baseline; not a runtime feature. |
| 1 — Design system and Android shell | Compose/Material 3 shell, HomeScout logo, animated splash, Kenya-oriented home, online illustrative photos, and eight routes are present. The primary bottom bar contains five destinations. | Android build passed earlier in the audit; emulator smoke inspection reached Home, Discover, and Areas. The installed app was an older signed build. |
| 2 — Backend foundation | Modular FastAPI, SQLAlchemy, Alembic, SQLite configuration, versioned API, health/readiness, and Android base-URL configuration are present. | Current tests, live health/readiness, SQLite schema, and historical PostgreSQL 17.12 checks through Phase 4 passed. |
| 3 — Authentication and roles | Account lifecycle, token/session handling, profile, role and permission controls, and protected administration are implemented. | Covered by automated tests and earlier PostgreSQL checks; production email delivery and authenticated device journeys were not available. |
| 4 — Kenya locations and property foundation | County/town/neighbourhood hierarchy and property data foundation are implemented. | Live API returned 47 counties. Seeded county/town coordinates remain absent unless sourced. PostgreSQL 17.12 checks through Phase 4 passed. |
| 5 — Maps | Real Google Maps/Places SDK integration and map modes are implemented with configuration/error fallbacks. | No Maps key or billing configuration was supplied; live map tiles, Places requests, and satellite imagery were not verified. |
| 6 — Marketplace | Search, details, listing management, saves, comparisons, enquiries, and reports are implemented. | Automated SQLite tests passed. Live public inventory count is currently zero; Phase 6–14 PostgreSQL migrations are unverified. |
| 7 — Personal hub | Profile, saved items, activity, schedule, notifications, records, documents, support, and privacy workflows are implemented with account ownership checks. | Automated tests passed; no signed-in manual emulator journey was performed during this audit. |
| 8 — SmartRent | User-entered budget, move-in, savings, cost comparison, learning, and RentScore planning are implemented. | Automated tests passed. Calculations are planning aids, not credit scores, lending decisions, or financial outcomes. |
| 9 — Trust and safety | Manual verification, reports, moderation, and private viewing-safety workflows are implemented. | Automated tests passed. Audit repair aligned SQLAlchemy evidence uniqueness with the existing migration and added duplicate-document validation; no external identity/property checks exist. |
| 10 — Messaging and collaboration | Permission-scoped conversations, host-confirmed viewings, comparisons, opt-in roommate discovery, shared searches, and private journals are implemented. | Automated SQLite tests passed. No live notification delivery or authenticated end-to-end device test was performed; PostgreSQL validation is pending. |
| 11 — Services and moving | Provider discovery, booking workflow, moving plans, room setup, maintenance requests, and scoped provider access are implemented. | Automated SQLite tests passed. No real provider inventory or booking is present; PostgreSQL validation is pending. |
| 12 — M-Pesa | Backend-first Daraja configuration, transaction records, callbacks, and Android payment surfaces are implemented. | Disabled without credentials and a reachable HTTPS callback. No sandbox or live payment was sent; no transaction was fabricated. |
| 13 — Assistant | Consent, owner-scoped context/history, encryption, rate limits, and configurable server-side AI integration are implemented. | Disabled without provider/model/encryption configuration. No live AI response was requested or fabricated. |
| 14 — Operations | Permission-gated staff operations, moderation, support management, settings, and audit history are implemented. | Automated SQLite tests passed. No real staff account was used; PostgreSQL migration validation is pending. |
| 15 — Quality assurance | A focused QA/security review and targeted fixes are documented in the Phase 15 report. | This audit reran the full backend suite: 89 passed. Prior Android lint recorded 0 errors and 30 warnings; the current rerun could not start because the Gradle wrapper could not download its distribution. |
| 16 — Deployment preparation | Deployment, release, and competition materials and fail-closed release checks are present. | No deployment, signing, public release, or full competition demo occurred. |

“Implemented” describes the code and phase-specific checks, not production availability. Integrations and workflows in the final column still need their stated environment, credentials, data, or operational process.

## Repairs and data protection

- Created a pre-migration SQLite backup at work/audit-backups/homescout-pre-audit-20261124.db.
- Applied pending additive Phase 13 and Phase 14 migrations to the development database. The database moved from revision f12a0a1c9e60 to d14a9c2e5f81 (head); the SQLite integrity check reported ok, and no existing table row counts decreased.
- Fixed a model/schema drift: VerificationEvidence now declares the unique constraint already present in the migration, and duplicate evidence document IDs are rejected by request validation. Added a regression test.
- Alembic check now reports no new upgrade operations.
- No user database, emulator package, or emulator app data was deleted or cleared.

## Verification results

| Check | Result |
|---|---|
| Backend Pytest | **89 passed**, one upstream Starlette/httpx test-client deprecation warning; 321.77 seconds. |
| Ruff | ruff check app tests passed; format check reported 131 files already formatted. |
| Alembic | Current revision d14a9c2e5f81 (head); no schema drift. |
| Python dependencies | pip check: no broken requirements. |
| SQLite | Ready endpoint reports database ok; the pre-audit integrity check reported ok. |
| Live API | /api/v1/health returned ok; /api/v1/health/ready returned ready; locations endpoint returned 47 counties; public property total is 0. |
| Bandit | No medium/high findings. Broad scan reports 8 low findings: one heuristic on the JWT token_use="access" purpose claim and seven assertions in application code. These were reviewed as low severity and are listed as remaining cleanup. |
| pip-audit | A fresh advisory lookup was blocked because the environment could not connect to PyPI. The earlier Phase 15 scan is historical and is not represented as a fresh result. |
| Android build | :app:assembleDebug, :app:testDebugUnitTest, and release source compilation had succeeded earlier in this audit using Android Studio's JBR/SDK. A later rerun could not start: Gradle 8.13 was not cached in the current wrapper home and outbound socket access was denied. |
| Android APK | Debug APK exists at app/build/outputs/apk/debug/app-debug.apk (28,960,346 bytes). It was built with HOMESCOUT_API_BASE_URL=http://10.0.2.2:8765. |
| Emulator | Existing ke.co.homescout.debug app launched and its Home activity remained resumed. Home, Discover, and Areas were visually inspected. Installing the new APK failed with INSTALL_FAILED_UPDATE_INCOMPATIBLE because its signing certificate differs from the installed package. No uninstall or data clear was attempted. The newly built artifact's runtime/API connection therefore remains unverified. |

The project directory is not a Git checkout and has no .git metadata. A Git diff, commit, or GitHub push could not be produced.

## Local backend

The Uvicorn development server is running at:

- Host machine: http://127.0.0.1:8765
- Android emulator bridge: http://10.0.2.2:8765

The port 8000 bind was unavailable in the sandbox, so the server was started on port 8765. Keep this process running while using the configured debug build. The current database contains location reference data but no public property listings.

## Security and release readiness

- No critical, high, or medium findings were reported by the Bandit scans. This is not a penetration test.
- Eight low Bandit findings remain. The token_use result is a purpose discriminator, not a credential. The seven assert uses are expected-invariant checks that can be removed by optimized Python execution; convert these to explicit runtime checks before production hardening.
- The fresh dependency advisory check could not reach PyPI.
- Phase 6–14 database migrations have only been validated on SQLite. PostgreSQL 17.12 validation covers Phases 2–4 only.
- Live Google Maps/Places need owner-restricted keys and billing. Daraja needs sandbox/production credentials and an HTTPS callback host. AI needs provider/model configuration and an encryption key. Production email, object storage, signing material, hosting, backups, and monitoring are not configured.
- No legal or regulatory compliance conclusion was made. Production use needs appropriate Kenyan privacy, payment, and operational review.

## Manual steps still needed

1. Open the HomeScout folder, not ShuleWise, in Android Studio. Start the backend at port 8765 before running the configured emulator build.
2. To install the new APK without removing the existing app/data, sign it with the same development key as the installed package or use a separate application ID for a side-by-side audit build.
3. Run migrations and representative API tests for Phases 6–14 against PostgreSQL 17.
4. The current OpenFreeMap road-map setup needs no map key or billing. Configure credentials only if a different map/Places provider is selected. Add Daraja sandbox credentials and callback infrastructure, and AI provider settings only when ready to test those integrations.
5. Configure production secrets, HTTPS API, storage, backups/restore, monitoring, and a protected Android signing key before release. No deployment or GitHub push was performed.

## Files created or updated for this audit

- FULL_PROJECT_AUDIT_REPORT.md
- EXPERIENCE_REPAIR_REPORT.md
- backend/app/models/trust.py
- backend/app/schemas/trust.py
- backend/tests/test_trust_safety.py
- PROJECT_CONTEXT.md
- ROADMAP.md
- TASKS.md
- ARCHITECTURE.md
- CODEX_RULES.md
- CHANGELOG.md
- DECISIONS.md
- PHASE_REPORT.md
- Local runtime database: backend/homescout.db, backed up before migration to work/audit-backups/homescout-pre-audit-20261124.db
- Debug APK: app/build/outputs/apk/debug/app-debug.apk

## Physical Android install — 2026-11-24

- Installed the debug APK on the connected Samsung SM-S938B running Android 17 as package ke.co.homescout.debug. Android confirmed installation succeeded.
- Launched the app and confirmed the HomeScout MainActivity remained resumed with a live process.
- This APK was built with the emulator-only API address http://10.0.2.2:8765. The physical phone can open the app, but its backend requests will not reach this workstation through that emulator address. A device-specific debug configuration is needed to verify phone-to-backend communication.
- The physical phone did not have this package installed beforehand; no existing app or data was removed.

## Follow-up repair — 2026-11-24

- Replaced the Google Maps client with MapLibre Native using OpenFreeMap's public vector styles. No API key/account/billing is required. Satellite/terrain imagery and Places search are not included. The emulator displayed real map tiles and labels; attribution was visible.
- Added a backend-proxied, explicit-search Nominatim area lookup. Requests remain rate-limited, Kenya-filtered, and subject to the public service's low-volume policy.
- Corrected the authentication hero wordmark contrast and provider button layout. Added accessible Google/Facebook/Apple provider marks; each provider still accurately states that OAuth is not configured. Added an optional “Browse homes first” entry for public browsing.
- The profile editor exposes first/last/preferred names, phone, location, and about-you fields and saves through the existing authenticated `/api/v1/hub/profile` route. Tests cover save→reload and account isolation; sign-in email and verification state remain read-only. No duplicate profile model or endpoint was added.
- Existing participant-authorized user-to-user conversations remain in the collaboration flow. The Home screen and top bar keep message entry points; private messaging still requires sign-in.
- Android `:app:testDebugUnitTest` and `:app:assembleDebug` passed. The phone-configured APK uses `http://127.0.0.1:8765`; it was installed and launched on the Samsung SM-S938B with `adb reverse tcp:8765 tcp:8765` active. The backend readiness endpoint returned ready/database ok. Android reported the HomeScout activity resumed and no fatal crash appeared in recent logcat. The latest APK's authenticated Discover/API flows were not end-to-end exercised. The emulator requires `http://10.0.2.2:8765`, but its existing package has a different signing certificate; it was not overwritten and its app data was preserved.
- Latest full backend suite: **92 passed**. Ruff check and format passed; **131 Python files** are formatted.
- The 20 development property records remain synthetic draft data with unknown availability and no coordinates. Public search/map intentionally excludes them; public live inventory is still empty until real listings are added and published.
- Non-blocking toolchain warnings remain: Gradle 8.13 is deprecated ahead of Kotlin 2.5, the installed Android Gradle Plugin reports compile SDK 37 is newer than its tested range, and Android SDK XML tooling is version-skewed. Compilation/tests still passed.
- Only the MapLibre/OpenFreeMap road-map tiles are verified; Google Maps, satellite imagery, live Nominatim lookup, and public inventory markers are not. Existing user-to-user messaging remains authorization-controlled, but no authenticated device chat journey was performed in this follow-up. The profile save is covered by API tests. No production build, deployment, or GitHub push is claimed.

## Finance usability follow-up — 2026-11-24

- Updated the existing SmartRent Finance overview with an illustrative KES household budget: variable monthly income examples, expenses, obligations, savings, target rent, move-in estimate, utilities, and household size.
- Added authenticated POST /api/v1/finance/assessment/preview, which runs the same assessment calculation as the saved-profile workflow without persisting a profile. The interface labels the sample and preview and requires an explicit save action for the signed-in user's own finance profile.
- Added optional monthly utilities input and client validation. No new table, migration, duplicate finance model, automatic financial seeding, or real-money transfer was added.
- Backend Pytest: 93 passed; Ruff check/format passed. Android unit-test result files show 6 passed and 0 failures.
- Rebuilt APK installed in place on the connected Samsung SM-S938B, preserving app data. ADB confirmed the HomeScout MainActivity resumed with a live process; API readiness returned ready/database ok through the reverse tunnel; no HomeScout fatal exception appeared in the inspected logcat.
- Gradle's prior run completed the debug test and assemble tasks but exited nonzero while replacing its generated problems-report HTML. A clean retry could not start because the wrapper could not fetch the uncached Gradle 8.13 distribution. The signed-in Finance UI itself was not manually navigated on the device.
- These are post-Phase 16 repairs, not a new phase. No GitHub push, deployment, or production readiness claim.

## Finance section reliability follow-up — 2026-11-24

- Reworked SmartRent refresh into parallel per-endpoint loads. A failure in one service now produces a retry/error state only in the related Finance section and does not discard successful section data or hide other tools.
- Added regression tests for partial Overview failure and isolated Records failure. Current Android results are 9 unit tests passed and debug APK assembly passed; current backend results are 94 full-suite tests passed and 8 targeted SmartRent tests passed; Ruff checks passed.
- Added stable development-only finance-encryption and auth-signing keys to ignored `backend/.env` and restarted the local API. The phone uses `adb reverse` to reach the local server. API health is ready/database ok.
- Installed and launched the final debug APK in place on the Samsung SM-S938B without removing app data. The Finance UI smoke check found no shared data-load error or missing-key message and no fatal app exception. Individual save actions and every subsection were not exhaustively driven on device.
- No production keys, OAuth provider, AI provider, M-Pesa credentials, public inventory, or live payment claims were added. This remains a post-Phase 16 reliability repair; there was no GitHub push, deployment, or production release.

## Finance session, messaging, and dashboard follow-up — 2026-11-26

- Repaired the shared expired-access-token path in Android API clients. Authenticated calls now attempt one refresh using the refresh token already stored in Android Keystore-backed encrypted storage, persist the rotated token pair, and retry the original request once. Synchronized refresh handling prevents parallel Finance and Messages requests from racing refresh-token rotation. A rejected/expired refresh token clears the local session and returns the app to sign-in; connectivity failures preserve the session.
- The same API layer is used by Finance budget preview/save and Collaboration messages. A successful message send now clears its draft and selected attachments; failed sends retain them for retry.
- Added a Discover action to the empty Messages inbox to make the authorized property-enquiry path into a new conversation easy to find.
- Refined the Finance overview: the six-month cost graph displays monthly KES values, the existing category breakdown/upcoming costs/recent records remain available, and the housing-goals card lists up to three active account goals with progress and any target/contribution timeline returned by the backend. Empty charts and goals remain honest empty states.
- Verification: `:app:compileDebugKotlin`, `:app:assembleDebug`, and `:app:lintDebug` passed; lint reported 0 errors and 29 warnings, mainly pre-existing style, dependency, and toolchain notices. The configured local API readiness endpoint returned `ready` with database `ok`. Automated tests and full authenticated UI journeys were not run for this follow-up.
- Phone install: the connected Samsung SM-S938B already has `ke.co.homescout.debug`, but Android rejected the new debug APK with `INSTALL_FAILED_UPDATE_INCOMPATIBLE` because the signatures differ. The existing installed app and its data were left intact. The new APK was built but was not installed or launched on the phone. Installing in place requires the signing key matching that existing package.
- Phone-install resolution: located the matching local Android debug key, re-signed the same APK, and successfully installed with `adb install -r`. Android confirmed `MainActivity` resumed and the process was running. The API reverse tunnel and readiness endpoint both worked (`ready`, database `ok`). The app was updated without uninstalling or clearing app data.
- This is a post-Phase 16 targeted repair, not a new phase. No production deployment or GitHub push occurred.

## Android Areas discovery update — 2026-11-26

- Connected the Android Areas destination to the existing versioned location and property APIs. The screen loads the 47 counties and supports county → town/city → neighbourhood browsing, popular-area shortcuts, location search, and handoff to Discover with the selected location filters.
- Added a clearly marked local reference directory for offline/unavailable API browsing. The local reference data contains no inferred coordinates.
- Fixed Discover to restore and clear location IDs from an Areas selection. When an exact neighbourhood filter returns no result because a synthetic listing has no neighbourhood ID, Discover retries within its county and town using the selected area text and explains the fallback.
- Enabled cleartext traffic for debug builds only so the phone can use the local `adb reverse` API tunnel; release builds remain configured to disallow cleartext traffic.
- Verification: `:app:assembleDebug` passed. The local API returned 47 counties and Kilimani search results. The Samsung SM-S938B loaded Areas from the API; tapping Kilimani opened Discover and displayed the matching synthetic example with “DEMO · NOT AVAILABLE”. Inspected logcat showed no fatal HomeScout exception.
- Installation: updated and launched `ke.co.homescout.latest` (launcher label “HomeScout Kenya Latest”) alongside the existing installed package. No uninstall, app-data clear, production deployment, or GitHub push occurred. The device tunnel maps port 8766 to this workstation's local API and will only work while that API and ADB connection remain active.
- No product phase was started. This targeted repair did not test all 47 county result sets or authenticated listing workflows; the demo record itself still has incomplete neighbourhood metadata, which is surfaced by the fallback note.


## 2026-11-26 — Discover results scrolling and refresh

- Replaced the fixed Discover controls plus nested results grid with one continuous vertical results list, so listings remain reachable by scrolling through the filters and results together.
- Added pull-to-refresh at the top of Discover. It repeats the current search with the active filters and refreshes the signed-in user's saved-property state; the existing retry action uses the same reload path.
- `:app:compileDebugKotlin` and `:app:assembleDebug` passed. The debug APK was signed with the device-matching local key and installed in place on Samsung SM-S938B without clearing app data. HomeScout MainActivity remained resumed. The local API readiness endpoint returned ready/database ok through ADB reverse.
- The UI gesture itself was not manually exercised on-device; no automated tests were run for this targeted repair.
- This is a post-Phase 16 repair. No production deployment or GitHub push occurred.


## 2026-11-26 — Profile navigation grid

- Replaced the Profile tab's stacked full-width shortcut buttons with a responsive action-card grid. The separate HomeScout hub now uses the same grid, so its account and workflow shortcuts are easier to scan.
- Tiles use existing HomeScout Material theme colors, accessible icon labels via the button title, short supporting text, and responsive column counts. Saved homes, activity, schedule, messages/shared plans, notifications, trust and safety, settings, and the account hub retain their original destinations. Listing management and platform operations remain role-gated.
- Android `:app:compileDebugKotlin` and `:app:assembleDebug` passed. The matching-signed debug APK installed in place on Samsung SM-S938B; `MainActivity` resumed and the HomeScout process remained active. No app data was cleared.
- Profile tile taps and responsive layouts were not manually exercised on-device; no automated tests were run for this visual update.
- This is a post-Phase 16 targeted repair. No production deployment or GitHub push occurred.


## 2026-11-26 — Profile page reference layout and top-bar avatar

- Added a tappable initials avatar to the upper-left app bar. It opens the signed-in Profile destination while preserving navigation state.
- Redesigned the signed-in Profile overview with a HomeScout navy identity panel, cream initials avatar, verified-email indicator, account-detail rows, current role chips, and a direct Edit profile details action. Existing session management, sign-out, and profile shortcut destinations remain available.
- Kept the Profile shortcut grid and role-gated listing/admin links. The profile page uses actual account email, status, verification and assigned roles; no follower counts or other sample account metrics were introduced.
- Android `:app:compileDebugKotlin` and `:app:assembleDebug` passed. Installed the matching-signed APK in place on Samsung SM-S938B with app data preserved. A focused device check tapped the top-left avatar and found the Profile page's Edit profile details action.
- The whole profile page was not exhaustively tested on-device; no automated tests were run for this UI update.
- This is a post-Phase 16 targeted repair. No production deployment or GitHub push occurred.


## 2026-11-26 — Profile drawer layout correction

- Replaced the top-left avatar's direct Profile navigation with a modal left-side drawer styled in HomeScout navy, with a close control, account initials/name/email/role/verification, and compact menu rows.
- Drawer actions navigate to Profile, saved homes, messages/viewings, schedule, SmartRent Finance, notifications, trust and safety, and settings. Listing management and platform operations appear only for the corresponding assigned roles. Sign-out requires confirmation.
- Removed the rejected two-column shortcut grid from the Profile tab. The tab now focuses on the account identity/details, profile editing, device sessions, sign-out and authorized administration. The separate account hub also uses compact single-column menu rows.
- Android `:app:compileDebugKotlin` and `:app:assembleDebug` passed. Installed the matching-signed debug APK in place on Samsung SM-S938B without clearing data; MainActivity remained active. A device check opened the drawer and confirmed the profile and HomeScout menu entries were visible.
- No automated tests were run for this visual/navigation update; not every drawer destination was tapped on-device.
- This is a post-Phase 16 targeted repair. No production deployment or GitHub push occurred.
