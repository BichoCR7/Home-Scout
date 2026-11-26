# HomeScout Kenya — Phase 16 deployment preparation and competition demo report

**Date:** 2026-11-24  
**Scope:** Phase 16 only. Deployment, release, and competition presentation preparation; no actual deployment or distribution.

> **Historical snapshot:** Google Maps configuration references below predate the owner's free-map request. The current road map uses MapLibre/OpenFreeMap without a key; satellite and Places are not included. See [`MAPS_SETUP.md`](MAPS_SETUP.md) and [`EXPERIENCE_REPAIR_REPORT.md`](EXPERIENCE_REPAIR_REPORT.md).

## Executive result

Phase 16 preparation artifacts are complete. HomeScout now has a provider-neutral deployment guide, a non-root backend container definition, a production environment template, a fail-closed Android release-signing/API preflight, a release checklist, a 25-step competition demo runbook, and a presentation outline. The Home safety shortcut now opens the existing Trust & Safety screen.

**HomeScout is not deployed or launch-ready.** The production host, PostgreSQL 17 validation for Phases 6–14, durable private storage, protected signing key, production API, restricted Google keys/billing, SMTP, Daraja, Assistant provider, and isolated demo account/data were not supplied or configured. No signed APK/AAB, live provider call, payment, deployment, or distribution was produced. The requested full interactive demo is therefore not ready.

## Phase 16 deliverables

- `DEPLOYMENT_GUIDE.md`: provider-neutral FastAPI/PostgreSQL 17 deployment architecture, one-off Alembic migration procedure, environment/secrets, logging/monitoring, backups/restore, Maps, Daraja, AI, Android configuration, rollback, and deployment gates.
- `backend/Dockerfile`, `backend/.dockerignore`, `backend/requirements.runtime.lock.txt`: non-root Python 3.12 runtime image definition, local data/test exclusions, and a 34-entry pinned runtime dependency list. `backend/.env.production.example` contains placeholders only.
- Android release configuration in `app/build.gradle.kts`: configurable versionCode/versionName and signing values sourced from environment; release packaging is blocked without an external absolute keystore path, passwords/alias, HTTPS API base, and Maps/Places keys.
- `RELEASE_CHECKLIST.md`: identity, signing, API, maps, integrations, backup, functional, privacy, and owner approval gates.
- `COMPETITION_DEMO_GUIDE.md`: the requested 25 steps, current readiness per step, a safe reduced presentation path, and isolation/privacy requirements for a future synthetic demo environment.
- `COMPETITION_PRESENTATION_OUTLINE.md`: ten-slide competition structure covering product, problem, target users, SmartRent, safety, AI, maps, architecture, demo status, and limitations.
- Updated the Phase 16 roadmap/context/task/report documentation and recorded release-packaging decision D-029.

The user’s persistent naming instruction is respected: this project and its materials call the app **HomeScout**.

## Verification results

| Check | Result | Evidence and limits |
|---|---|---|
| Android debug Kotlin compilation | **Passed** | `:app:compileDebugKotlin` compiled the Home Trust & Safety shortcut change. |
| Android release source compilation | **Passed** | `:app:compileReleaseKotlin :app:compileReleaseJavaWithJavac`; this did not sign/package a release. |
| Android unit tests | **Passed** | `:app:testDebugUnitTest`. |
| Android debug APK | **Passed** | `:app:assembleDebug`. |
| Release preflight | **Passed as a fail-closed gate** | `:app:preflightRelease` reported missing signing/API/Maps/Places setting names only; it did not reveal values. |
| Release AAB packaging | **Blocked by design** | `:app:bundleRelease` stopped at `preflightRelease` because no owner keys, HTTPS endpoint, or Google client keys are configured. No unsigned AAB was created. |
| Android lint | **Not completed** | `:app:lintDebug` stopped before analysis because Gradle could not download missing AndroidX lint/test dependencies. Network access was granted and the check was retried with elevated shell access; this environment still returned `Permission denied: getsockopt` for Google/Maven artifact hosts. This is an environment dependency-fetch failure, not a lint diagnostic. |
| Runtime dependency lock | **Passed consistency check** | All 34 runtime lock entries and versions are present in `backend/requirements.lock.txt`. This checks list consistency only. |
| Backend test suite | **Not rerun in Phase 16** | No backend application Python source changed. Phase 15's existing suite result was 88 passed; Docker and environment-template changes were not exercised by that test suite. |
| Docker image | **Not built** | Docker/Podman is not installed in the environment. |
| PostgreSQL 17 | **Not tested in Phase 16** | No PostgreSQL 17 service/client is available; PostgreSQL 16/18 installations are not used as substitutes. Phases 6–14 remain SQLite-only. |
| Maps, Daraja, AI, SMTP | **Not live-tested** | No owner-controlled credentials, billing account, public callback, provider, or production endpoint was supplied. |
| Competition demo | **Not completed** | Only the Phase 15 emulator shell smoke-check exists. There is no isolated demo API/database/account, public demo inventory, or live Maps/AI/provider setup. See `COMPETITION_DEMO_GUIDE.md`. |

## Launch and competition blockers

1. **Database:** Execute all Phase 6–14 Alembic migrations and representative API, authorization, and rollback/restore checks on PostgreSQL 17 staging.
2. **Private files:** Replace development local storage with durable private object storage, encryption/access policy, malware scanning, retention/deletion, backup, and restore. Local private-document files exist under ignored `backend/var/`; they are excluded from the Docker build context and source ignore. This phase did not open or read their contents, or delete those files; classify and handle them under the owner’s retention policy before publishing or sharing workspace data.
3. **Android signing:** Create a protected upload key outside the checkout, set values via CI secret manager, configure Play App Signing or approved controlled APK signing, and inspect the signature/certificate before use. The current release version remains `0.1.0` / code `1`; no store release is prepared.
4. **Release integrations:** Select host/provider, inject HTTPS API URL, configure restricted Maps SDK/Places keys and billing/quota controls, and verify satellite tiles/search with the final signing identity.
5. **Backend operations:** Configure SMTP, monitoring/log alerts, incident handling, database backup and restore, TLS, production secrets and key custody.
6. **Payments and AI:** Keep both disabled until sandbox tests, approved business/provider policies, merchant onboarding, consent/privacy review, server keys, callback monitoring, and live integration evidence exist.
7. **Demo:** Create an isolated, purgeable synthetic demo database/account/data workflow. Do not place demo properties in production public discovery or call them available, verified, or real. Do not use a screenshot/mock image as a live satellite map.
8. **Quality:** Rerun Android lint after resolving outbound dependency access, test the exact signed release on several Android versions/sizes, and complete authenticated end-to-end demo journeys.

## Competition demonstration status

The Home UI has three illustrative synthetic sample cards. They are not a searchable backend inventory, are not publishable or map-visible, and must not be described as available homes. The map currently shows an honest unconfigured state without Google credentials. The full journey steps involving real markers, saved listings, comparisons, personalized finance, viewings, provider records, profile activity, or the Assistant need an isolated demo environment and configured services before they can be shown as interactive.

The provided competition guide offers a limited honest shell walkthrough and marks each unavailable step. The outline is a presentation plan, not a finished slide deck and not proof of product-market fit. No unsupported market-size statistics are asserted.

## Deployment and distribution status

Nothing has been deployed, submitted to Google Play, signed with a release key, or distributed. The Phase 15 `app-release-unsigned.apk` is not suitable for distribution. The current HomeScout folder is not a Git checkout and has no configured remote; no push to GitHub was attempted.

## Phase status

Phase 16 preparation is complete. Stop here; do not deploy, submit, distribute, enable production payments/AI, import real user data, or start a later phase without separate owner authorization and the listed gates.
