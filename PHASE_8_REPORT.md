# HomeScout Phase 8 Report

**Phase:** SmartRent financial inclusion and housing planning  
**Status:** Implemented. Stop after Phase 8; Phase 9 requires separate owner authorization.  
**Product name:** HomeScout

## Delivered

- Added an authenticated, owner-scoped `/api/v1/finance` API and the Android Finance-tab SmartRent experience without changing the five primary tabs: Home, Discover, Areas, Finance, and Profile.
- Added encrypted finance profiles, move-in plans, virtual savings goals, contributions, records, property comparisons, lease/deposit notes, and in-app alerts. Explicit savings sharing reveals only the selected goal and the permissions granted by its owner.
- Added deterministic KES housing-budget and RentScore calculations. The UI and API disclose their assumptions; variable income may use recent monthly amounts, and a payslip is not required. These estimates are not credit scores, lending decisions, or property-eligibility decisions.
- Added move-in cost planning, savings simulation, manually recorded virtual savings contributions, and budget-based discovery using available published listings only.
- The Finance screen exposes the saved financial dashboard and household-size input; owners can edit move-in plans with evidence labels and manage savings goals with optional deadlines, contributions, completion, and archiving.
- Added true-cost comparisons for current published listings with additional user-entered recurring and one-time costs. Comparison excludes demo, draft, and unavailable inventory.
- Added private housing expense/payment notes, account-owned document references, financial-literacy lessons and quiz progress, utility summaries based only on user entries, a lease/deposit organizer, and in-app budget/goal/comparison alerts.
- Lease notes include editable start/end dates, rent/deposit values, a user-written obligation summary, and a question to raise. These fields organize user-provided information and do not interpret legal terms.
- Added an AI interface preview only. No AI provider receives finance data. No payment processor, M-PESA, lending, credit bureau, transfer, or funds-custody workflow was added.
- Added the Phase 8 Alembic migration `c46199e48c9f` and documented the required finance encryption key and its operational handling.

## Privacy and key management

Sensitive financial payloads are encrypted with AES-GCM using a fresh 96-bit nonce. The authenticated account UUID is supplied as associated data. The encryption key is supplied through `HOMESCOUT_FINANCE_ENCRYPTION_KEY`, must decode from URL-safe base64 to 32 bytes, and is required in staging and production. It is not returned by the API or included in the Android app.

Some relational metadata remains queryable in ordinary database columns, including identifiers, ownership, timestamps, status, and alert indexes. Phase 7 private-document file contents continue to use development local disk storage and are not encrypted by the SmartRent payload cipher. Production private object storage, managed key custody, backup, retention, malware scanning, and key rotation/re-encryption procedures are still required. Losing the finance key makes existing encrypted payloads unreadable.

## Verification

- Backend: **55 tests passed** with one upstream Starlette/httpx deprecation warning.
- Ruff: full backend lint and formatting checks passed (95 Python files checked for formatting).
- Android: `:app:testDebugUnitTest` and `:app:assembleDebug` passed. APK: `app/build/outputs/apk/debug/app-debug.apk`.
- Android compilation emitted non-blocking Gradle/Android SDK compatibility and Kotlin deprecation warnings. `adb` is unavailable in the environment, so no Phase 8 device/emulator rendering check was performed.
- SQLite: Alembic upgrade and finance API/database behavior passed in the test suite.
- PostgreSQL: Phase 8 was **not** verified on PostgreSQL 17. The available Windows PostgreSQL services are versions 16 and 18; they were not used as a substitute. Prior PostgreSQL 17.12 verification covers Phases 2–4 only.

## Not included

- Real banking, payments, M-PESA integration, credit products, lending, credit scoring, or money held/transferred by HomeScout.
- Connected AI or automated financial advice, utility-provider quotes, legal interpretation, payment confirmation, push/email alerts, or external reminder delivery.
- Production PostgreSQL 17 migration validation, hosting, managed secret storage, production document storage, and production security operations.
- Phase 9 rental-safety work or any later phase.

## GitHub delivery

The user authorized GitHub access and supplied `https://github.com/BichoCR7/Home-Scout`. No commit or push was made: the HomeScout folder has no `.git` metadata, this chat has no active GitHub publishing connection, and GitHub HTTPS requests report that no credentials are available. The repository URL is known; an authenticated GitHub connection is still required to inspect the remote safely and publish.
