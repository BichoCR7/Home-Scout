# HomeScout SmartRent Phase 5 — Rent and Payment Management

**Status:** Complete. Stop here; do not begin SmartRent Phase 6 without the owner's instruction.

## Implemented

- Added private rent obligations with title, KES amount, due date, optional property reference/notes, and open/cancelled lifecycle.
- Added user-reported external payment records with partial amounts, payment method/date, optional reference/notes, and request UUID idempotency.
- Stored the obligation and payment payloads with the existing AES-GCM Finance cipher. Added owner-scoped reads and writes, a composite ownership constraint for a payment's obligation, amount bounds, duplicate-report protection, and a guard against editing the obligation below already reported amounts.
- Exposed authenticated Finance API operations to list, create, update and delete rent obligations, submit reports, and remove reports. The API describes totals as reported by the user and never marks them provider-confirmed or HomeScout-paid.
- Added the Phase 5 Alembic migration `2f4b5d7a1c90` for `rent_obligations` and `rent_payment_records`.
- Connected the existing Android Payments route to a rent tracker: add a reminder; review due date, amount and balance from reports; record a partial/full external payment; remove a report; cancel/reopen a reminder; and refresh account data. The UI explains that a report is not a verified payment.
- Separated rent tracking from the existing Daraja service-booking history and displayed configured provider availability. M-Pesa remains service-booking-only, while Visa, Mastercard and PayPal are not configured for rent checkout. Bank transfer, cash and other methods are only labels for an external report.
- Kept the existing five HomeScout primary tabs, navigation and authentication. No chat or other user communication behavior was changed.

## Verification

- Backend full Pytest suite: **105 passed**, with one upstream Starlette/httpx test-client deprecation warning. The suite applied all Alembic revisions to a disposable SQLite database through `2f4b5d7a1c90`.
- Ruff check and format check passed for the changed backend models, schema, data-access, service, endpoint, migration, and tests.
- Alembic reports a single head: `2f4b5d7a1c90`.
- Android `:app:testDebugUnitTest`, `:app:assembleDebug`, and `:app:lintDebug`: **BUILD SUCCESSFUL**. All **10 Android unit tests passed**; lint reported **0 errors and 29 warnings**.
- Debug APK produced at `app/build/outputs/apk/debug/app-debug.apk`.
- In-place installation was attempted on the connected Samsung SM-S938B. Android rejected it with `INSTALL_FAILED_UPDATE_INCOMPATIBLE` because the installed `ke.co.homescout.debug` package has a different signing certificate. The installed app was not uninstalled and its app data was not erased. The new Phase 5 UI was therefore not visually exercised on that phone.
- Tests validate the migration on SQLite. PostgreSQL 17 was not run against this new revision; earlier PostgreSQL checks do not cover `2f4b5d7a1c90`.

## Payment and product boundaries

- No rent payment was initiated, transferred, settled, or confirmed by HomeScout. No HomeScout rent receipt is generated.
- The backend's local configuration has M-Pesa disabled. Even when the existing Daraja integration is configured for service bookings, its status explicitly excludes rent checkout. Visa, Mastercard and PayPal remain unconfigured. No card information is collected.
- A payment report means only that the signed-in user entered a note. The displayed remaining figure is the obligation amount minus reported entries; it is not a landlord balance or account statement.
- Live rent checkout needs a suitable provider integration, production credentials, callback/reconciliation operations, and explicit legal/merchant authorization. That work is outside this phase.
- External reminders, automatic rent receipts, landlord confirmation, recurring payment initiation, and financial institution sync are not included.
- No Compose instrumentation/UI automation suite is configured. Compilation/lint/unit tests passed, but visual rendering and tap-through behavior could not be checked because the signed APK could not update the phone.

**Phase boundary:** SmartRent Phases 0–5 are complete. Stop before Phase 6.
