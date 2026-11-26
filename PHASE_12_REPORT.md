# HomeScout Kenya — Phase 12 Report

**Phase:** M-Pesa Daraja integration and transaction management  
**Status:** Backend-first service-payment architecture and Android payment surfaces implemented. Daraja sandbox execution is pending app credentials and a publicly reachable HTTPS callback.  
**Date:** 2026-11-24

## Delivered

- Added environment-backed Daraja configuration with sandbox/production modes, merchant transaction type, bounded timeouts, and a disabled-by-default switch. Production configuration requires explicit service-collection authorization. Secrets stay in the backend environment and never enter Android.
- Added a backend Daraja client for OAuth, STK Push, and authenticated STK Query using fixed Safaricom hosts. Network failures that could have submitted an STK prompt stay ambiguous/pending; the server does not blindly retry them.
- Added payment transaction and callback-evidence models, schemas, data access, service logic, API routes, permissions, audit events, and Alembic revision `f12a0a1c9e60`.
- Limited collection to an accepted customer-owned service booking with a fixed, positive whole-KES order amount. The caller supplies an idempotency key and Kenyan phone number. The database prevents duplicate active/successful order charges.
- Kept the payer's phone private: only an HMAC digest and last four digits are stored. Callback bodies are size-bounded, schema-validated, deduplicated, and reduced to minimal evidence. A callback is treated as untrusted and is followed by an authenticated provider query before status changes.
- Added payer-owned history/detail/reconciliation, provider-visible order status with phone/receipt details redacted, and an admin reconciliation queue. Receipts are surfaced only when the provider result and callback metadata match.
- Prevented cancelling a service booking while its payment is initiated, pending, or successful. No refund policy exists in this phase, so cancellation cannot silently follow a charge.
- Added an Android M-Pesa request action for eligible accepted fixed-price service bookings and a payment history/status screen reachable from Finance. The app does not mark a payment successful from client input, and the five primary bottom tabs remain unchanged.
- Updated setup and architecture documentation, the roadmap/task status, changelog, decisions, and current phase index.

## Verification

- Backend Pytest: **72 passed**, with one upstream Starlette/httpx test-client deprecation warning.
- Payment API behavior tests exercise disabled configuration, idempotent requests, provider-history redaction, booking-cancellation guard, callback deduplication, server-side confirmation, mismatched merchant rejection, pending reconciliation, cancelled status, owner scoping, and Kenyan phone normalization.
- Payment settings tests exercise disabled-by-default behavior, complete sandbox configuration, HTTPS callback validation, shortcode validation, and minimum HMAC-key length.
- Ruff lint and formatting checks passed for backend application code, tests, and migrations.
- Android `:app:compileDebugKotlin`, `:app:testDebugUnitTest`, and `:app:assembleDebug` completed with **BUILD SUCCESSFUL**. The toolchain emitted existing Gradle/Android plugin compatibility advisories and Kotlin deprecation/unchecked-cast warnings.
- The migration chain and payment behavior use SQLite in automated tests. PostgreSQL 17 checks for this Phase 12 migration were not run; the previously documented PostgreSQL checks cover Phases 2–4 only.

## Security and transaction boundaries

- Daraja consumer credentials, shortcode passkey, callback configuration, and the phone-HMAC key are backend-only. No secret is compiled into Android.
- The app remains in disabled mode until a complete valid configuration is supplied. A response from STK Push is only a request/pending state; provider-side query is required to establish a terminal result.
- Callback receipts are not trusted until matched to the corresponding checkout, amount, merchant, and payer digest. Duplicate callback evidence is idempotent. Internal callback failures return a retryable error; unknown or malformed callbacks receive a generic acknowledgement.
- This phase does not collect rent, custody funds, escrow money, pay out providers, or initiate refunds/reversals. A `reversed` status can only be recorded if an authenticated provider status explicitly reports it; no reversal request is issued.

## Limitations and required configuration

- No Safaricom Daraja credentials, sandbox app, or public HTTPS callback host were supplied. Therefore no sandbox or production request, callback round-trip, settlement, or receipt was exercised. Before enabling traffic, validate the app-specific STK Push/STK Query contract and credentials in the [Safaricom Daraja Developers Portal](https://developer.safaricom.co.ke/).
- Production use additionally needs approved merchant onboarding and authorization for the specific HomeScout service-payment purpose, production secret management, monitoring, and an operational reconciliation procedure. No legal, regulatory, settlement, or compliance review is claimed.
- Database migration verification for this phase is SQLite-only. PostgreSQL 17 migration/API verification for Phases 6–12 remains outstanding.
- No authenticated emulator walk-through, live Safaricom integration, retry worker, settlement reconciliation, charge reversal, refund workflow, rent collection, or escrow capability is included.

## Phase boundary

Phase 12 is complete for the implemented architecture, code, tests, and Android shell. Live Daraja validation remains blocked on credentials and public callback hosting. Stop after Phase 12.
