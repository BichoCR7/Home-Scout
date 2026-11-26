# HomeScout Kenya — Phase 11 Report

**Phase:** Moving services, home services, and service provider marketplace  
**Status:** Implemented and verified on SQLite and the Android debug build  
**Date:** 2026-11-24

## Delivered

- Added service-provider profiles and service offerings for movers, cleaners, plumbers, electricians, internet providers, furniture providers, handymen, home maintenance, and other home services.
- Added search by category, county, text, price range, and current provider approval; provider comparisons; public profile summaries; provider profile images; and actual completed-booking reviews.
- Added authenticated customer/provider bookings with pending, accepted, rejected, proposed-reschedule, cancelled, and completed states. A booking starts pending, and only provider or customer actions advance it. Completion requires an authorized provider action.
- Added order records tied to service bookings. These record service-request estimates/status and do not process or confirm payments.
- Added private moving plans, checklist tasks and deadlines, a 60-day calendar view, KES budget items, and room/furniture planning.
- Added property-resident access grants managed by the owner/property manager and maintenance requests with category, priority, private photo references, provider assignment, status history, and completion records. Provider access is limited to assigned requests; revoking resident access also removes access to older related records.
- Connected the Android secondary Services screen to the API for discovery, comparison, provider profile/offering management, bookings, move planning, room setup, and maintenance. The five primary navigation tabs remain unchanged.
- Added the Phase 11 Alembic migration, role permissions, backend API, validation, behavior tests, documentation, and this report.

## Verification

- Backend Pytest: **64 passed**, with one upstream Starlette/httpx test-client deprecation warning.
- Ruff lint and format checks passed across backend application code, tests, and migrations.
- Android `:app:compileDebugKotlin`, `:app:testDebugUnitTest`, and `:app:assembleDebug` completed with **BUILD SUCCESSFUL**. The JDK emitted a caught `AccessDeniedException` while closing an Android SDK archive; Javac’s Gradle task was up-to-date and the build completed. Existing Gradle/Android plugin compatibility advisories remain.
- SQLite Alembic migration to the new head and Phase 11 service workflows passed through the test suite.

## Limits

- The Phase 11 migration has not been run against PostgreSQL 17.12.
- Provider approval reflects only the current HomeScout manual verification record. It is not external identity, business-license, or insurance verification.
- Provider images and maintenance attachments use the existing local development document/media stores; durable object storage, malware scanning, backup, and lifecycle operations are not configured.
- Booking dates are requests until provider action; no calendar/email/push delivery or background reminder worker is connected.
- Service order records are not payment transactions. No payment credentials, money movement, refunds, or settlement are included.
- Moving budget amounts are private planning inputs and are not confirmed quotes. No live provider inventory or real-world availability is represented unless an actual provider has entered it.
- No authenticated emulator walkthrough or external provider/notification integration was performed.

## Phase boundary

Phase 11 is complete. Phase 12 payments and unrelated roadmap work remain unimplemented.
