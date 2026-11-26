# HomeScout — Post-phase repair report

**Date:** 2026-11-24  
**Scope:** Repair and verify the existing HomeScout Android app and backend after Phase 16. This is follow-up maintenance, not a new phase.

## Changes completed

- Improved the existing authentication entry screen's logo contrast and social-provider button layout. Provider buttons do not claim to sign users in without provider credentials. Public Home and Discover browsing can be entered through a clearly labeled guest option; account-specific actions remain protected.
- Replaced the former Google map client with MapLibre Native and OpenFreeMap's public vector style, following the owner's request for an accessible map without a Google key. The emulator visibly rendered real vector tiles and labels. Attribution is shown. No satellite imagery, terrain imagery, Google Places, SLA, or production uptime guarantee is provided by this setup.
- Kept location lookup behind the existing HomeScout API and made it an explicit-search, Kenya-limited proxy to Nominatim. It is subject to the provider's low-volume usage policy.
- Expanded the existing profile editor for personal details and saved changes through the authenticated, owner-scoped profile endpoint. API tests cover save/reload and account isolation. Email and verification status remain read-only.
- Made the existing Finance overview usable with a labeled illustrative KES budget, live non-persistent assessment preview, optional monthly utilities field, and explicit save-to-account action. Preview calculations reuse the backend's existing affordability rules and do not write to the financial profile. No database migration or duplicate finance model was added.
- Preserved the existing user-to-user collaboration/messaging feature and its participant authorization. Private conversations still require sign-in; no new messaging implementation is claimed in this repair.
- Preserved the five-item bottom navigation, HomeScout logo/name, and existing app architecture.

## Verification observed

- Backend full suite: **93 passed**.
- Android unit-test results: **6 passed**, 0 failures.
- Android debug APK assembly completed and the APK was installed in place on the connected Samsung SM-S938B; package data was preserved.
- Ruff check and format: passed; **131 Python files** already formatted.
- Android `:app:testDebugUnitTest`: passed.
- Android `:app:assembleDebug`: passed.
- Map view: actual OpenFreeMap vector tiles and labels visibly rendered in the Android emulator in the existing MapLibre build.
- Local backend health check: ready with database available.
- Profile save/reload and account-isolation behavior are included in the passing backend tests.

## Finance section reliability repair — 2026-11-24

- Replaced SmartRent's all-or-nothing refresh with parallel, independently handled loads. A failed dashboard/profile request no longer prevents Plan, Savings, Compare, Learn, Records, Lease, or Alerts from rendering; each section retains its own fallback data and section-specific retry message.
- Removed the shared “Your finance data did not load” blank state. The selected section now shows its own load error above that section's content, and successful sections keep their loaded data. Overview forms and the other section forms remain available during an API failure.
- Kept the roles tied to their existing workflows: Overview affordability and budget coaching; Plan move-in costs and utility/savings simulations; Savings goals and contributions; Compare housing costs; Discover budget-based live listings; Learn lessons; Records manual housing/payment notes and documents; Lease notes and dates; Alerts; and AI handoff to the existing HomeScout assistant. AI replies still require provider configuration, and payment status does not claim success without Daraja confirmation.
- Added Android regression tests showing an Overview error does not discard successful Plan/Savings/Compare data and a Records error stays scoped to Records.
- Set stable local development-only finance-encryption and auth-signing keys in the ignored `backend/.env`, then restarted the local API. No keys were added to Android or tracked source. The API readiness endpoint reports `ready` with `database: ok`.

## Latest verification — 2026-11-24

- Android `:app:testDebugUnitTest` and `:app:assembleDebug`: **BUILD SUCCESSFUL**. XML test reports: **9 tests, 0 failures, 0 errors**.
- Backend full suite: **94 passed** (2 upstream/cache warnings in that run); targeted SmartRent suite: **8 passed**. Ruff lint and format checks passed.
- Updated APK installed in place on the Samsung SM-S938B; its package data was preserved. The app process remained alive. A phone UI smoke check opened Finance in the active account session and found no shared finance-load message or encryption-key warning; the screen exposed interactive finance inputs/actions. This was not a manual walk-through of every Finance section.
- ADB reverse and the local API readiness check were active during the phone smoke check. No HomeScout fatal exception appeared in the inspected logcat.

## Remaining issues and boundaries

- The latest debug APK is built with `http://127.0.0.1:8765` and was installed on the connected Samsung SM-S938B on 2026-11-24. `adb reverse tcp:8765 tcp:8765` is active and the local API readiness endpoint returns `ready`/`database: ok`.
- The app is running on the phone. Finance was opened during a non-sensitive UI smoke check; the former shared error and missing-key message were absent. Recent logcat contained no fatal exception for HomeScout.
- Finance preview and persistence require signing in. The sample budget is illustrative and stays on-screen only; it is not saved unless the user chooses the explicit save action. Backend API tests verify preview uses the same assessment logic and leaves the stored profile unconfigured.
- The final Gradle test and assemble rerun completed successfully. Non-blocking warnings remain for Gradle 8.13/Kotlin compatibility, compile SDK 37 support, and SDK XML version skew.
- The attached emulator also has the same package installed under a different signing certificate. Its app/data were left intact; no uninstall or data reset was performed. The latest APK was installed on the phone, not over the emulator copy. Use the same signing key or a separate application ID for an emulator update.
- A separate emulator build must use `http://10.0.2.2:8765` rather than the phone address. The phone install and launch are confirmed, but authenticated Discover/API workflows were not end-to-end exercised in this smoke check.
- All Finance sections were not manually exercised on the phone. SmartRent aggregation tests cover section isolation; existing backend tests cover finance calculations and account-scoped persistence. Example finance amounts remain labeled illustrative and are saved only through the user's explicit save action.
- The 20 synthetic property records are development-only drafts with unknown availability and no coordinates. They remain excluded from public search and map markers, so there is no public inventory until real authorized listings are published.
- The free map is a real interactive road map, not a satellite map. Live Nominatim requests, OAuth providers, production email, M-Pesa, AI provider calls, and production deployment were not verified in this follow-up.
- The build reports non-blocking toolchain warnings for Gradle/Kotlin compatibility, compile SDK 37 support in the installed Android Gradle Plugin, and SDK XML version skew.

## Files and setup

- Map provider and usage details: [`MAPS_SETUP.md`](MAPS_SETUP.md)
- Phone API forwarding: [`ANDROID_DEVICE_SETUP.md`](ANDROID_DEVICE_SETUP.md)
- Full audit history and install boundary: [`FULL_PROJECT_AUDIT_REPORT.md`](FULL_PROJECT_AUDIT_REPORT.md)

No GitHub push, deployment, release signing, or app-data removal occurred.
