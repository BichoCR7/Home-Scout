# HomeScout Kenya — Project Context

**Status:** HomeScout product Phases 0–16 implementation/preparation scope completed and full-project audit performed on 2026-11-24. A separate owner-supplied SmartRent sequence has completed Phases 0–5. No deployment, signed release, store submission, or distribution occurred.
**Last updated:** 2026-11-25

**Latest follow-up:** SmartRent Phase 5 adds private rent obligations, due dates, partial user-reported external payments, account-scoped records, and explicit provider availability. HomeScout does not collect rent or confirm external rent reports. See `SMARTRENT_PHASE_5_REPORT.md` for the phase boundary and verification.

## Owner-supplied SmartRent Phase 5 — 2026-11-25

Finance now includes private rent reminders and payment reports backed by an additive SQLAlchemy/Alembic schema extension. Obligation/report payloads use the existing AES-GCM Finance key, account ownership is enforced server-side, and request UUIDs make report retries idempotent. The Android Payments screen keeps rent tracking separate from Daraja-confirmed service-booking transaction history. Manual reports remain user-reported and unverified. M-Pesa is disabled for rent; card and PayPal checkout are not configured. See `SMARTRENT_PHASE_5_REPORT.md`.

## Product vision

Build a Kenya-first Android service that helps people find housing and navigate renting with more safety, financial access, and support for moving and property services.

## Product goals

- Make housing discovery useful for Kenyan renters and property owners.
- Support safer rental decisions and trustworthy interactions.
- Improve access to rental-related financial services.
- Connect users to moving and property services as those phases are authorized.
- Keep the product usable on common Android devices and variable connectivity.

These goals are initial direction from the project brief. Product requirements, market assumptions, and success measures still need validation.

## Target users

Initial user groups to validate:

- Renters searching for a home.
- Landlords and property managers listing homes.
- Rental service providers, such as movers and property service professionals.
- HomeScout operations and support staff.

Do not assume a particular user is verified or trusted until a product workflow defines and performs the relevant checks. Email verification confirms access to an email address; it does not verify a person, property, tenancy, or provider.

## Owner-supplied SmartRent Phase 4 — 2026-11-25

Finance Overview now summarizes saved monthly income, manual expenses, housing costs, remaining amount, affordability context, budget categories, upcoming reminders, saved-data insights, and savings progress. User-defined category limits are held in the existing encrypted Finance profile; monthly actuals are derived from that user's manual finance records. Optional due dates are reminder plans, never payment evidence, and do not add to actual expense totals. Owner-scoped record deletion was added. Existing encrypted JSON storage was extended compatibly, so no Alembic migration was needed. Backend full suite passed 103 tests; Android unit tests/build/lint and Ruff passed. The phone rejected the APK update due to a debug signing-certificate mismatch; the installed app and data were preserved. See `SMARTRENT_PHASE_4_REPORT.md`.

## Core feature areas

The product areas include housing discovery, authorized property listings, rental safety, financial inclusion, communication, moving, home services, approved service payments, contextual housing guidance, and staff operations. Phase 13 adds the HomeScout Assistant with explicit consent, optional permission-checked context, encrypted owner-scoped history, and a disabled-by-default server provider. Phase 14 adds audited, permission-gated operations for support, accounts, listings, services, categories, locations, settings, and message-report moderation, plus links to the existing verification and safety workflows. Trust and provider approval states reflect HomeScout's manual review records; they do not imply external identity, title, tenancy, business-license, or insurance checks. No real Daraja credentials, AI provider credentials, assistant encryption key, or transaction evidence are configured; there is no rent custody, escrow, provider payout, outbound alert service, or production provider inventory. See `ROADMAP.md` and `PHASE_14_REPORT.md`.

## Technology stack

Established by the project brief and Phases 1–11:

- Android: Kotlin, Jetpack Compose, Material 3, Gradle.
- Backend: Python, FastAPI, SQLAlchemy, Alembic, Uvicorn, Pytest.
- Development database: SQLite.
- Production database target: PostgreSQL 17.
- Password hashing: Argon2id.
- API bearer tokens: short-lived HS256 access tokens plus database-backed rotating refresh sessions.
- Android token storage: AES-GCM ciphertext with a non-exportable Android Keystore key.
- Payments: M-Pesa Daraja API, reserved for the authorized payments phase.

Android build baseline uses AGP 8.13.2, Kotlin 2.4.21, Compose BOM 2024.12.01, Gradle 8.13, compile SDK 37, target SDK 36, Build Tools 36.0.0, and min SDK 26. Backend dependencies and a resolved lock file are in `backend/`.

## Current project state

HomeScout is isolated in `C:\Users\edris\Documents\Codex\HomeScout`, separate from RentWise. Phase 1 created the Compose shell and visual design system. It has five persistent bottom tabs, the owner-supplied HomeScout logo, an animated splash, sample KES housing cards, a local search preview, clearly labeled later-phase placeholders, and online illustrative photography with local fallbacks.

Phase 2 created a modular FastAPI foundation, configuration, SQLite/PostgreSQL URL handling, SQLAlchemy models, Alembic migrations, health endpoints, safe errors, and centralized Android API URL configuration.

Phase 3 added email/password registration, email verification and resend, sign-in, refresh rotation, sign-out, password reset, self-profile read/update, current-user session management, role and permission catalogs, scoped authorization, protected role administration, audit events for sensitive actions, and an interactive first-Super-Admin CLI. The Android Profile destination connects to these API flows and encrypts tokens locally. The app remains browseable as a guest; backend protected routes require a valid account session.

Phase 4 added Kenya's country/county/town/neighbourhood reference hierarchy, all 47 counties and county headquarters, priority areas, source-aware coordinates, property/media schema, location search, public published-property reads, and landlord-owned draft create/edit operations. Synthetic property data exists only in test fixtures and is explicitly opt-in, illustrative, draft, unverified, and availability-unknown.

Phase 5 originally integrated Google Maps/Places; the post-phase repair replaced it with MapLibre Native, OpenFreeMap styles, and a backend-proxied, user-triggered Nominatim search. Real vector tiles were visually confirmed in the Android emulator on 2026-11-24. No map key or billing is needed; the public tile service has no SLA, and satellite/terrain imagery and Places search are not included. The rest of the project includes Phase 6 marketplace discovery and listing tools; Phase 7 personal-hub workflows; Phase 8 private SmartRent planning; Phase 9 human verification and safety; Phase 10 authorized conversations, viewings, roommate discovery, comparison, private viewing journals, and shared search groups; Phase 11 service discovery, bookings, moving plans, room setup, and maintenance; Phase 12 Daraja STK Push/query, transaction status, callback evidence, and Android history/request surfaces for accepted fixed-price service orders; Phase 13 the consent-based, server-side HomeScout Assistant with encrypted owner-scoped history and opt-in authorized context; and Phase 14 the audited operations API and secondary Android staff console. Message bodies and private comparison/journal data are AES-GCM encrypted at rest with dedicated environment keys. Group and journal access is membership/owner scoped with explicit revocable sharing; financial amounts are shared only after each participating account consents. The bottom bar uses at most five destinations and now adapts to the server-selected active role; tenants retain the standard Home, Discover, Areas, Finance, and Profile tabs while other assigned roles receive their own work-focused dashboard and tabs. Role switching remains restricted to roles assigned to that account, and backend authorization remains authoritative. Twenty development-only synthetic listings support distinct-image testing; they remain draft, unverified, availability-unknown, and coordinate-free, so public discovery/map does not present them as real homes. SQLite migration/workflow tests pass through Phase 14; PostgreSQL 17.12 validation covers Phases 2–4 only. Production storage, third-party verification, push/email reminders, real Daraja and AI credentials, and live listings remain unconfigured or out of scope. See `MAPS_SETUP.md` and `EXPERIENCE_REPAIR_REPORT.md`.

Backend tests live in `backend/tests/`; Android map-state/query tests live in `app/src/test/`.

## Architecture direction

Keep one Android app and one Python API, organized into feature and responsibility boundaries. Keep domain rules outside the UI and HTTP handlers. See `ARCHITECTURE.md` for boundaries and the phase limits.

## Design identity

The Phase 1 palette is Navy Blue `#10243A`, Primary Blue `#2563EB`, Green `#16A34A`, White `#FFFFFF`, Background `#F6F8FB`, Muted Text `#64748B`, Dark Text `#172033`, Amber `#F59E0B`, and Red `#DC2626`. The official logo is the owner's navy rounded-square house-and-location-pin mark with cream strokes and a terracotta pin center, paired with the HomeScout wordmark and “Find your next place” splash tagline. Keep this identity consistent unless the owner explicitly changes it.

The Compose theme follows system light/dark mode. Home photos are illustrative Unsplash stock images, not HomeScout listing evidence. See `PHOTO_CREDITS.md`.

## Security and privacy

Phase 15 ran 88 backend tests, Ruff, a complete SQLite Alembic upgrade, an installed-environment dependency scan, Bandit, Android debug/release compilation, lint/unit/APK checks, and a five-tab emulator smoke check. It fixed Android API-level theme resource use, target SDK 36, Windows SDK path parsing, and small green status text contrast. The release artifact was unsigned. See `PHASE_15_REPORT.md`.

Phase 16 adds a non-root backend container definition and pinned runtime dependency lock, production environment template, deployment guide, Android release-signing/HTTPS/API-key preflight, version configuration, release checklist, competition demo guide, and presentation outline. A dead Home safety shortcut now opens Trust & Safety. These are preparation changes only: no host, production PostgreSQL, storage, provider credentials, signing key, or live demo account was configured. Phases 6–14 migrations remain unverified on PostgreSQL 17; the full demo and production release are not ready. See `DEPLOYMENT_GUIDE.md`, `RELEASE_CHECKLIST.md`, `COMPETITION_DEMO_GUIDE.md`, `COMPETITION_PRESENTATION_OUTLINE.md`, and `PHASE_16_REPORT.md`.

- Store secrets outside source control and never expose them in client builds, logs, or normal API responses.
- Hash passwords with Argon2id; never store recoverable passwords.
- Store only hashes of random refresh/action tokens in the backend database.
- Authenticate and authorize on the server for protected operations; client-hidden UI is never authorization.
- Keep role selection during self-registration as a requested role only; grant tenant access until an authorized operator approves an elevated role.
- Use scoped role assignments and audit sensitive role changes.
- Development action-token response exposure is disabled by default and is rejected outside development/test environments.
- Require signing keys and SMTP with STARTTLS for staging/production; production requires PostgreSQL.
- Minimize personal data, define retention/deletion behavior, and protect data in transit and at rest.
- Treat identity, tenancy, payment, and property claims as sensitive; do not use unsupported trust badges.

Specific legal, regulatory, data residency, and payment obligations require review before launch. No compliance assessment has been completed.

## Constraints and open questions

- Build only the phase explicitly authorized; do not begin the next phase automatically.
- No SMTP provider credentials, production signing key, deployment environment, or production data were supplied.
- PostgreSQL 17 is the production target. PostgreSQL 17.12 migration and representative API checks passed for Phases 2–4 on 2026-11-23. Phase 6–14 migrations still need PostgreSQL 17 runs. Production hosting, backups, restore, and automated PostgreSQL CI remain unverified.
- Daraja code defaults to disabled. Sandbox/production credentials, a public HTTPS callback deployment, Safaricom sandbox request evidence, merchant collection authorization, refund/reversal operations, and legal/operational policy were not supplied or configured.
- Operational policy for approval and evidence of elevated roles still needs definition.
- Independent identity/property ownership checks, phone/SMS verification, hosting, managed storage, analytics, external review criteria, evidence retention/appeals, and Assistant provider/privacy/retention review need operating decisions before production.
- The Home screen still contains sample content. Discover uses the backend only when an API base address is configured; otherwise it labels its sample homes as illustrative.

## Full-project audit snapshot — 2026-11-24

The existing SQLite database was backed up before applying its pending Phase 13 and Phase 14 migrations, then upgraded from f12a0a1c9e60 to d14a9c2e5f81 (head). SQLite integrity is ok, and Alembic reports no model/schema drift. The current backend test suite passes 89 tests; Ruff and Python dependency consistency checks pass. The backend is running locally at http://127.0.0.1:8765, with emulator access at http://10.0.2.2:8765. The API returns 47 counties and zero public property listings. See FULL_PROJECT_AUDIT_REPORT.md.

The latest debug APK configuration uses the physical-phone API address `http://127.0.0.1:8766`; the prior debug build was installed and launched on the Samsung SM-S938B with `adb reverse tcp:8766 tcp:8766` active. Android reported the HomeScout activity resumed, the process remained alive, and no fatal HomeScout exception appeared in recent logcat. The emulator's separately installed package uses a different signing certificate and its app/data were preserved. The emulator displayed real OpenFreeMap tiles. Profile editing saves to the signed-in user's existing profile record, and backend tests cover reload and cross-account isolation. Authorized user-to-user conversations remain available through the existing collaboration flow. See `EXPERIENCE_REPAIR_REPORT.md` for exact verification boundaries. Daraja, Assistant, production email/storage, and PostgreSQL migrations after Phase 4 remain unverified.

## Physical phone install — 2026-11-24

The debug APK was installed and launched successfully on the connected Samsung SM-S938B running Android 17. This is the emulator-configured build: its API base URL is http://10.0.2.2:8765, which will not route to the development backend from a physical phone. App launch is confirmed; phone-to-backend communication is not. See FULL_PROJECT_AUDIT_REPORT.md.

## Authentication entry flow update — 2026-11-24

The existing splash now transitions to an authentication entry instead of starting at Home. Session restoration completes before app routes render; valid sessions route to Home and missing/invalid sessions see Log in/Create account. Existing backend-connected identity forms remain in use. Password inputs support show/hide and start masked. The installed phone debug build uses `http://127.0.0.1:8765` with ADB reverse; the phone's health request returned ready/database ok. Reapply `adb reverse tcp:8765 tcp:8765` after reconnecting. Local development code exposure is enabled in ignored `backend/.env` so verification and reset can be completed without SMTP; never enable it outside development/test. See AUTH_FLOW_FIX_REPORT.md and ANDROID_DEVICE_SETUP.md.

## Startup crash repair — 2026-11-24

The owner reported that HomeScout closed after splash. Device logcat identified a NullPointerException in dynamically registered NavHost placeholder destinations. The route was made explicit. The rebuilt APK was installed on the Samsung phone and visually verified at the Log in/Create account entry; no new fatal crash was logged. See AUTH_FLOW_FIX_REPORT.md.

## Finance section reliability repair — 2026-11-24

SmartRent now fetches each Finance section independently and retains the selected section's content when another API request fails. Section-specific retry/error cards replaced the shared “Your finance data did not load” blank state. Android regression tests cover isolation of Overview and Records failures. The ignored local `backend/.env` contains development-only encryption/auth keys; no key is included in Android or tracked source. The backend readiness check is healthy. Final debug APK installed/launched on the Samsung SM-S938B; Android unit tests: 9 passed, debug assembly passed; backend full suite: 94 passed, SmartRent subset: 8 passed. No new phase started.

## Owner-supplied SmartRent Phase 3 — 2026-11-25

Finance now models additional recurring income sources and annual income in the existing encrypted profile, with daily normalization based on the user's selected workdays (five days/week by default). Recent monthly history is treated as total income across all sources and takes precedence over normalized sources, preventing double-counting. Calculations return explicit housing/non-housing totals, income ratios, and surplus/deficit. Savings goals can calculate weekly/monthly needs to a target date and a planned completion estimate. Property comparisons show known subtotals and unentered categories rather than treating missing costs as zero. A separate rent-choice simulator projects current versus alternative housing costs after one-time moving costs. Contribution retries are idempotent when clients submit the same request UUID; Alembic migration `e43a91c7b205` adds this key without altering existing finance records. Stateless calculators remain available without a finance encryption key; private finance persistence still requires the server-side key and never falls back to plaintext. See `SMARTRENT_PHASE_3_REPORT.md`.
