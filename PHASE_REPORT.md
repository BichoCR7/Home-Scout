# HomeScout Kenya — Current Phase Report

**Latest work:** Owner-supplied SmartRent Phase 5 rent reminders and user-reported payment management. See `SMARTRENT_PHASE_5_REPORT.md`.  
**Latest phase:** Phase 16 — Deployment preparation and competition demonstration  
**Status:** Phase 16 remains the latest phase. Targeted repairs are complete; no deployment, store submission, or distribution occurred.

**Separate owner-supplied SmartRent workstream:** Phases 0–5 are complete. This workstream reuses existing HomeScout Finance and adjacent features. See [`SMARTRENT_PHASE_5_REPORT.md`](SMARTRENT_PHASE_5_REPORT.md) and the earlier SmartRent reports. The HomeScout product roadmap remains at Phase 16; the SmartRent workstream does not start HomeScout product Phase 17. Stop before SmartRent Phase 6 until the owner authorizes it.

## SmartRent Phase 5 verification snapshot — 2026-11-25

- Backend full Pytest suite: **105 passed**, one upstream Starlette/httpx deprecation warning; SQLite Alembic chain reached `2f4b5d7a1c90`.
- Ruff check and format check passed on changed backend files.
- Android unit tests: **10 passed**; debug APK assembly passed; lint: **0 errors / 29 warnings**.
- Attempted normal in-place update on Samsung SM-S938B. Android rejected the APK because the installed package uses a different signing certificate. The installed app/data were preserved; Phase 5 screens were not visually tested on the phone.
- PostgreSQL 17 was not run against this new migration. No real rent checkout/provider confirmation was configured or attempted.

See [`SMARTRENT_PHASE_5_REPORT.md`](SMARTRENT_PHASE_5_REPORT.md) for implemented behavior and limits.

## SmartRent Phase 4 verification snapshot — 2026-11-25

- Backend full Pytest suite: **103 passed**, one upstream Starlette/httpx deprecation warning; focused SmartRent suite: **17 passed**. Ruff check/format passed for the four changed Python files.
- Android `:app:testDebugUnitTest`, `:app:assembleDebug`, and `:app:lintDebug`: **BUILD SUCCESSFUL**; **10 unit tests passed**; lint **0 errors / 27 warnings**.
- No migration was needed; Phase 4 extends existing encrypted JSON storage. SQLite-backed tests passed; no Phase 4 PostgreSQL migration run applies.
- The generated debug APK update was attempted on Samsung SM-S938B and rejected because the installed debug package is signed with a different certificate. The installed app and data were preserved; this Phase 4 APK was not visually checked on-device.
- No Compose instrumentation tests, payment processing, bank sync, or external reminder delivery were part of this phase.

See [`EXPERIENCE_REPAIR_REPORT.md`](EXPERIENCE_REPAIR_REPORT.md) for the latest verification and limits. Phase 16 preparation guides: [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md), [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md), [`COMPETITION_DEMO_GUIDE.md`](COMPETITION_DEMO_GUIDE.md), and [`COMPETITION_PRESENTATION_OUTLINE.md`](COMPETITION_PRESENTATION_OUTLINE.md). Previous phase snapshots are retained below.

## Post-phase repair snapshot — 2026-11-24

- Backend: **93 tests passed** in the latest full run; Ruff lint and format pass, with **131 files already formatted**.
- Android: all **6 unit tests passed**. Debug APK assembly completed and the updated APK installed/launched on the Samsung SM-S938B. Gradle then failed while replacing its generated problems report; a retry could not download the uncached Gradle 8.13 distribution.
- Map: MapLibre rendered actual OpenFreeMap/OpenStreetMap vector tiles in the emulator. No Google key or billing is required. Satellite/terrain imagery and Google Places are not part of this provider setup.
- Sign-in screen: improved hero-brand contrast and provider buttons. A clearly labeled guest path opens public Home/Discover; account-only actions and private chats still require sign-in.
- Profile: personal fields save against the existing signed-in user's profile. API tests verify save/reload and reject cross-account reads. Authorized user-to-user messaging remains in the existing collaboration feature.
- Finance: added an illustrative KES budget preview that uses the backend calculation without saving, optional monthly utility input, and an explicit save action for account-owned values. No finance data is auto-seeded or saved.
- Install: updated in place on the Samsung SM-S938B; app data was preserved. The app launched to its authentication entry and remained active. Authenticated Finance was not manually traversed on the phone.
- Demo inventory: 20 synthetic property examples remain development-only draft records, with availability unknown and no coordinates; they are intentionally excluded from public search/map results.

## Phase 16 verification snapshot

- Release packaging preflight was exercised. `:app:bundleRelease` was safely blocked because no external signing keystore/passwords, HTTPS production API base, or restricted Maps/Places keys are configured; it printed names only.
- Android debug Kotlin compilation, release Kotlin/Java compilation, debug unit tests, and debug APK assembly passed. Android lint did not complete because Gradle could not download missing lint/test AndroidX metadata dependencies; the shell remained unable to open those outbound sockets even after network permission was granted.
- The 34-entry runtime dependency list matches versions in the project dependency lock. Docker/Podman and a PostgreSQL 17 service/client are unavailable, so the container image and PG17 deployment/migration path were not tested.
- No host, cloud account, provider credentials, demo account, production signing key, or real property inventory was supplied. No deployment, M-Pesa transaction, live map, AI request, or full 25-step competition demo occurred.

## Phase 15 verification snapshot

- Backend Pytest: **88 passed**, with one upstream Starlette/httpx deprecation warning.
- Ruff lint/format passed; 144 Python files were already formatted.
- Alembic upgraded the complete schema through `d14a9c2e5f81` on SQLite.
- Installed dependency audit: no known findings; Bandit high/medium scan: no findings.
- Android debug and release compilation/APK assembly passed; debug lint reported **0 errors, 30 warnings**, and Android unit tests passed.
- The release variant artifact is `app-release-unsigned.apk`; protected release signing is not configured.
- API 37 emulator smoke check reached Home, Discover, Areas, Finance, and Profile; it was not a full authenticated end-to-end test.
- PostgreSQL 17 Phase 6–14 migrations, live Google/Daraja/AI/SMTP integrations, TalkBack, and production operations remain unverified.

## Phase 14 verification snapshot

- Backend Pytest: **88 passed**, with one upstream Starlette/httpx deprecation warning.
- Ruff lint and format checks passed; 144 Python files were already formatted.
- Android `:app:compileDebugKotlin`, `:app:testDebugUnitTest`, and `:app:assembleDebug`: **BUILD SUCCESSFUL**.
- Backend Phase 14 migration and operations tests ran on SQLite. PostgreSQL 17 validation for migration `d14a9c2e5f81` was not performed; earlier PostgreSQL checks through Phase 4 do not cover it.
- No emulator/device rendering walkthrough was performed.

## Phase 13 verification snapshot

- Backend Pytest: **81 passed**, with one upstream Starlette/httpx test-client deprecation warning.
- Ruff lint and format checks passed.
- Android `:app:compileDebugKotlin`, `:app:testDebugUnitTest`, and `:app:assembleDebug` completed with **BUILD SUCCESSFUL**.
- Phase 13 migration and behavior tests ran on SQLite. PostgreSQL 17 validation for this migration was not performed.
- No live AI request was made because no provider credential/model or assistant encryption key was configured. No emulator rendering walkthrough was performed.

## Phase 12 verification snapshot

- Backend Pytest: **72 passed**, with one upstream Starlette/httpx test-client deprecation warning.
- Ruff check and format checks passed for backend application code, tests, and migrations.
- Android `:app:compileDebugKotlin`, `:app:testDebugUnitTest`, and `:app:assembleDebug` completed with **BUILD SUCCESSFUL**. Existing Gradle/Android plugin compatibility and Kotlin warnings were emitted.
- Phase 12 migration and behavior tests use SQLite. PostgreSQL 17.12 validation covers Phases 2–4 only; Phases 6–13 remain outstanding.
- No Daraja sandbox request or authenticated emulator walkthrough was performed because no Daraja credentials or public callback host were supplied.

## Phase 11 verification snapshot

- Backend Pytest: **64 passed**; one upstream Starlette/httpx test-client deprecation warning was emitted.
- Ruff check and format checks passed for backend application code, tests, and migrations.
- Android `:app:compileDebugKotlin`, `:app:testDebugUnitTest`, and `:app:assembleDebug` completed with **BUILD SUCCESSFUL**. The JDK emitted a caught Android SDK archive access diagnostic; Gradle completed successfully.
- Phase 11 migration and behavior tests passed on SQLite. PostgreSQL 17.12 has not been run against this migration.
- No authenticated emulator walkthrough, external notification delivery, or real provider integration was performed.

## Authentication entry flow follow-up — 2026-11-24

After Phase 16, the owner authorized an auth-flow repair without starting a new phase. The existing splash is preserved; app routes now wait for secure session restoration and unauthenticated users land on Log in/Create account. Existing backend auth flows are reused. Android tests/build, targeted backend auth tests, and physical phone install/launch passed. See AUTH_FLOW_FIX_REPORT.md; physical phone API networking remains unconfigured.
