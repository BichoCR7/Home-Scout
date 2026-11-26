# SmartRent Phase 3 — Data Model, Calculations, and Finance Layout

**Status:** Complete. The SmartRent workstream stops here; Phase 4 has not started.

## Implemented

- Added annual pay and multiple recurring income sources to the existing encrypted finance profile. Daily income uses the user's selected workdays per week. Recent monthly totals are treated as the combined total across sources and take precedence over source normalization, avoiding double-counting.
- Expanded the KES assessment with separate housing and non-housing costs, rent and total-housing income ratios, and monthly surplus or deficit. Existing Decimal-based calculations and financial-planning disclaimers remain in place.
- Added savings-goal contribution pace and estimated completion when a user enters a monthly plan. Contribution requests now accept a stable UUID so retrying the same request cannot add the same contribution twice.
- Added a rent-choice projection for comparing current and alternative housing costs, including a one-time move cost and break-even month.
- Property comparisons now separate known subtotals from unentered monthly and move-in costs; missing values are never silently treated as zero.
- Corrected monthly recorded-cost aggregation to exclude receipt copies, preventing a receipt from being counted as a second expense.
- Redesigned the Finance overview in HomeScout's navy and blue theme with a monthly housing snapshot, monthly cost breakdown, income allocation, six-month chart based on user-entered housing records, recent records, savings progress, and quick actions. Empty states appear until data exists. The chart excludes receipt copies and only displays saved user-entered records.
- Reworked the Payments section into scannable payment-method information and a direct route to payment history. M-Pesa activity remains limited to eligible service bookings; bank, cash, and card entries are manual notes and do not create payments or receipts.
- Improved section errors to distinguish expired/unauthorized sessions, outdated Finance API routes, server errors, missing encryption configuration, and an unreachable API. Removed the duplicate Overview error text from the page content.

## Data and migration

- Added additive Alembic migration `e43a91c7b205_smartrent_phase3_retry_safe_savings.py` for optional contribution request UUIDs and uniqueness per goal/contributor/request.
- Applied the migration to the local SQLite database after creating and checking this backup: `backend/audit-backups/homescout-before-phase3-20261125-005720.db`.
- The migrated database reports SQLite integrity `ok`; the new column is present and existing finance profile/contribution records were preserved.
- Stateless calculations work without the finance encryption key. Reading or saving private finance data still requires the server-side key and fails closed; no secret was added to Android.

## API and phone setup

The phone's earlier Finance errors came from the HomeScout API listener on port 8765, which returned 404 for the Phase 3 rent-choice endpoint. The current backend is running on port 8766, where readiness reports `database: ok` and the new route is present. Android Studio's ignored `local.properties` and the installed debug APK now use `http://127.0.0.1:8766`; ADB reverse is configured for that port. Setup commands are in `ANDROID_DEVICE_SETUP.md`.

The debug APK installed successfully on the Samsung phone and the HomeScout activity launched. The device was locked during the final visual check, so an authenticated Finance screen render and phone-originated Finance requests could not be observed in this run. No lock-screen bypass was attempted.

## Verification

- Backend: the full pytest suite passed **100 tests**; SmartRent-specific tests passed **14 tests**. Ruff check and formatting passed for the changed backend files. Pytest reported an upstream Starlette/httpx deprecation warning and could not write its cache because of a local permission restriction; neither affected test results.
- Android: `:app:testDebugUnitTest`, `:app:assembleDebug`, and `:app:lintDebug` completed successfully. Android JVM tests: **10 passed**. Lint: **0 errors, 29 warnings**.
- The debug APK is installed and the app process is present on the connected Samsung device. No Compose instrumentation suite exists, and the phone remained locked during the final visual check.
- PostgreSQL 17 was not available for this Phase 3 migration run. SQLite migration and behavior tests passed; PostgreSQL Phase 3 migration validation remains outstanding.
- Gradle reports compatibility warnings: Gradle 8.13 is deprecated for future Kotlin plugin releases, and Android Gradle Plugin 8.13.2 was tested through compile SDK 36.1 while this project uses SDK 37. These did not prevent the build.

## Local development

Start the API from the `backend` directory, then reapply ADB reverse after reconnecting the phone:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8766
adb reverse tcp:8766 tcp:8766
```

## Phase boundary

Phase 3 is complete. Stop here until the owner asks to start Phase 4.
