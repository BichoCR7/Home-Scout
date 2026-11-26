# HomeScout Phase 9 Report

**Phase:** Trust, verification, fraud protection, and rental safety  
**Status:** Complete. Stop here; do not begin Phase 10 without owner authorization.  
**Product name:** HomeScout

## Delivered

- Added `/api/v1/trust` endpoints for landlord, agent, service-provider, and property verification submissions, owner history, authorized review queues, reviewer decisions, expiry, and resubmission. Each case is a HomeScout manual review record; the app does not connect to government identity, title, tenancy, license, or police databases.
- Verification submissions require files from the account's private document store. Verification uploads and trust evidence are encrypted at rest with AES-GCM using the separate `HOMESCOUT_TRUST_ENCRYPTION_KEY`. Owner and authorized reviewer downloads decrypt only after access checks; reviewer evidence reads are audited. Report narratives and private viewing details use the same key. Internal moderation notes are stored as plaintext in the development database, are omitted from API responses, and have no moderation-history read endpoint in this phase.
- Added owner-private listing reports and safe-viewing incident reports with evidence references, status history, moderation queues, escalation, reviewer messages, and audit records. A report is an allegation. It does not automatically mark a person as fraudulent or change property visibility.
- Added human-only property moderation actions. An authorized reviewer may explicitly hide, restore, or remove a listing while resolving a listing report. Public property queries exclude moderation-held/removed listings. Listing visibility is not changed by duplicate or price heuristics.
- Added exact normalized-address duplicate and comparable-rent outlier signals for reviewer attention only. There is no automated fraud verdict, user trust score, or suspicious-contact-pattern model; the latter would require data the service does not collect.
- Added encrypted safe-viewing plans with meeting point, trusted-contact details, private notes, scheduled time, check-in/check-out/cancel status, and optional sharing to one selected active HomeScout account after explicit consent. Sharing does not send messages or reminders.
- Added safety guidance/checklist with clear limits, public property trust indicators based on actual records, a Profile secondary route with guest access to the guidance, and a “Plan a safer viewing” path from property details. The app retains its five primary tabs.
- Added Phase 9 Alembic migration `20261123_09` and trust/safety API tests. Updated architecture, decisions, roadmap, setup guidance, changelog, task status, and phase reports.

## Verification

- Backend full suite: **58 passed**, with one upstream Starlette/httpx deprecation warning.
- Focused trust/configuration/database/health/marketplace tests: **23 passed**, with one upstream deprecation warning.
- Ruff: lint passed; **102 Python files** passed formatting checks.
- Android: `:app:testDebugUnitTest` and `:app:assembleDebug` passed. The current Android unit-test report contains **4 passing map-model tests**. Kotlin Compose compilation passed.
- Emulator: installed the debug APK in place without uninstalling or clearing existing app data. Inspected HomeScout Home, Profile, and the guest Trust & safety guidance on one emulator. The five bottom tabs remain visible. Other screen widths and complete authenticated backend interaction were not manually exercised.
- SQLite: existing development database reached revision `20261123_09`. Its seeded **47 counties, 66 towns, and 33 neighbourhoods** remain. No application property, verification, viewing, incident, or report records were present in the database during the final count check.
- Migration tests in the backend suite exercised the migration lifecycle on test databases. No PostgreSQL 17 server was used for this phase.

## Configuration and operating limits

- Set a stable, separate URL-safe base64 32-byte `HOMESCOUT_TRUST_ENCRYPTION_KEY` in a private development environment to enable encrypted trust writes/reads. Staging and production require it. Never put it in Android or source control. Back it up and define key rotation/re-encryption before production; losing it makes encrypted trust data unreadable.
- The debug app's API base address remains unconfigured by default. Configure `HOMESCOUT_API_BASE_URL` or Gradle property `homescout.apiBaseUrl` to use protected API actions from Android.
- HomeScout manual verification is not independent identity, ownership, tenancy, or professional-license validation. Review criteria, staff coverage, turnaround, appeals, evidence retention/deletion, and escalation procedures still need an approved operating policy.
- Private files still use development local-disk storage. Production needs managed private object storage, key custody, backups, malware scanning, retention/deletion controls, and least-privilege reviewer operations. Other Phase 7 personal documents are not encrypted by the Phase 9 document cipher.
- No Google/registry identity lookup, phone/SMS verification, external contact sharing, emergency response service, push/email reminder delivery, or suspicious-contact-history analysis is implemented. Safe-viewing guidance is informational and cannot guarantee safety.
- PostgreSQL 17 verification remains outstanding for Phases 6–9. The existing PostgreSQL 17.12 checks cover Phases 2–4 only.
- No GitHub push was made. The HomeScout folder has no Git metadata or remote configured in the workspace, and no authenticated GitHub publishing connection is active here.

## Changed areas

- Backend: trust/safety ORM models, schemas, service, API routes, encryption/configuration, access permissions, public property filtering, Phase 9 migration, and integration tests.
- Android: Trust & safety secondary screen, guest safety-guide entry from Profile, property-detail safe-viewing entry and record-based trust indicators, central API support for public indicators, and primary button loading/disabled state support.
- Documentation: `README.md`, `backend/README.md`, `ARCHITECTURE.md`, `PROJECT_CONTEXT.md`, `ROADMAP.md`, `TASKS.md`, `DECISIONS.md`, `CHANGELOG.md`, and `PHASE_REPORT.md`.
