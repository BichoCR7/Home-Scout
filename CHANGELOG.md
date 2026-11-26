# HomeScout Kenya — Changelog

Changes are recorded by date and phase. This is a new project; no application features have been released.

## 2026-11-26 — Role-specific dashboards and navigation

- Connected the signed-in home destination to the server's active role. Tenants keep the housing-discovery homepage; landlords, real-estate agents, property managers, service providers, roommates, moderators, admins, and Super Admins now see distinct workspaces with role-relevant actions.
- Added server-backed workspace switching in the profile drawer. The UI offers only roles assigned to the account, and the existing backend endpoint validates each selection.
- Adapted the bottom bar and profile-drawer links by active role, with no more than five primary destinations. Service, Trust, and Operations screens can open directly to the selected role's booking, maintenance, moderation, report, support, or audit section.
- `:app:assembleDebug` passed. Installed package `ke.co.homescout.latest` with `adb install -r`; `am start -W` returned `Status: ok`, and the app process remained running. The device's top-resumed activity still reported TikTok, so the HomeScout screen was not visually confirmed on-device. No roles were granted, no app data was cleared, and no automated tests were run.
- This is a post-Phase 16 Android update, not a new phase. No production deployment or GitHub push occurred.

## 2026-11-26 — Role dashboard startup crash repair

- Reproduced the HomeScout Latest launch crash from Android logcat. The role-navigation fallback dereferenced a null `Destination` item while drawing the bottom navigation bar.
- Replaced that fallback with explicit tenant tabs so the app no longer depends on the shared destination list during role navigation setup.
- Rebuilt successfully and installed the updated `ke.co.homescout.latest` package with `adb install -r`, without uninstalling or clearing app data. `am start -W` returned `Status: ok`; the HomeScout process stayed running, the phone reported HomeScout MainActivity as top-resumed, and a device screenshot showed the signed-in Profile screen rendered. No new fatal exception appeared in logcat.

## 2026-11-26 — Android Areas discovery connection

- Replaced the Android Areas placeholder with county → town/city → neighbourhood browsing, popular-location shortcuts, API search, and a clearly identified local reference directory when the API is unavailable.
- Connected location choices to Discover using the existing property search API and county/town/neighbourhood filters. Corrected Discover restoration and clearing for those location filters.
- Added a labelled town-level retry when a synthetic development listing lacks its neighbourhood foreign key, while retaining county/town filters and the selected area text search.
- Verified the local API returns all 47 counties and Kilimani location data. Tapped Kilimani on the Samsung SM-S938B and confirmed Discover returned the matching synthetic listing with its “DEMO · NOT AVAILABLE” label; no crash appeared in the inspected logcat.
- `:app:assembleDebug` passed. Installed and launched package `ke.co.homescout.latest` beside the existing app, with the launcher label “HomeScout Kenya Latest”; the existing package was not removed or cleared. ADB reverse to port 8766 is active for this development install.
- Development builds alone allow cleartext traffic for the local reverse-tunnel URL; the release manifest setting remains false. No production API address or secret was added.
- This is a post-Phase 16 targeted Android update, not a new phase. No deployment or GitHub push occurred.

## 2026-11-26 — Automatic loading and home-detail repair

- SmartRent now refreshes when its Finance destination becomes active again, so returning to Finance automatically retries stale or failed section data.
- Added short automatic retries for transient network, timeout, rate-limit, and server errors; persistent or non-transient failures still show a clear recovery action.
- Home details now render as soon as the selected listing arrives. Similar homes, trust indicators, and saved status are isolated as optional data, and the core listing gets an automatic retry for temporary network/server failures. Confirmed the Ngong demo listing returns 200 for its details while the production-only similar-homes route returns 404 for that demo ID.
- Confirmed the local API returned successful responses for all 11 Finance and document reads. Android compilation remains unverified: the wrapper could not reach Gradle repositories and Android Studio's Gradle daemon failed with a file-already-exists error.

## 2026-11-25 — Owner-supplied SmartRent Phase 5 rent and payment records

- Added encrypted, user-owned rent obligations with due dates, partial external-payment reports, payment references, and remaining amounts derived from the user's reports.
- Added account scoping, idempotent report submission, amount bounds, and a guard against editing the obligation below already reported payments.
- Added rent tracking to the existing HomeScout Payments route, separate from Daraja-confirmed service-booking transaction history, with clear unverified states and provider availability.
- Added Alembic revision `2f4b5d7a1c90`. No live rent checkout, receipt, or provider confirmation was added. See `SMARTRENT_PHASE_5_REPORT.md`.

## 2026-11-25 — Owner-supplied SmartRent Phase 4 Finance dashboard

- Added the monthly cash-flow dashboard, user-defined category limits and record-backed actual spending, upcoming user-entered expense reminders, contextual finance insights, savings progress, and owner-scoped manual-record deletion.
- Reused the existing AES-GCM encrypted Finance profile and owner-scoped record store; no schema migration or duplicate data model was required. Reminders are excluded from actual spending and are not payment confirmation.
- Backend full suite passed (103 tests); Android unit tests, debug assembly, lint, and targeted Ruff checks passed. The connected phone rejected the in-place APK update because its installed debug package has a different signing certificate; installed app data was preserved. See `SMARTRENT_PHASE_4_REPORT.md`.

## 2026-11-25 — Owner-supplied SmartRent Phase 3 calculations

- Extended the existing encrypted Finance profile and calculation engine for annual and multiple recurring income sources, user-stated daily work schedules, normalized income breakdowns, housing/non-housing totals, rent-to-income ratios, and monthly surplus/deficit.
- Added weekly savings pace and planned completion estimates, a rent-choice simulator endpoint and Plan UI, and honest known-cost subtotals/missing categories in property comparisons.
- Made manual contribution retries safe using per-goal/contributor request UUIDs and additive migration `e43a91c7b205`. Stateless finance calculations no longer depend on the private-data encryption key; encrypted reads/writes still fail closed.
- Redesigned the Finance overview with a housing snapshot, real cost breakdown, allocation indicator, user-record-based six-month chart, recent housing notes, savings progress, and clearer payment-method boundaries in HomeScout's theme.
- Excluded receipt copies from monthly cost totals and added a regression test. Finance API errors now identify stale endpoints and session/API failures, and Overview no longer repeats its load error in the page content.
- Updated local Android Studio and phone API configuration to port 8766 after the previous 8765 listener returned 404 for the Phase 3 route. Installed and launched the refreshed debug APK on the Samsung phone; the phone was locked during the final visual check. See `SMARTRENT_PHASE_3_REPORT.md` and `ANDROID_DEVICE_SETUP.md`.

## 2026-11-25 — Owner-supplied SmartRent Phase 2 UX

- Reorganized Finance into six clear sections with focused Budget and Tools sub-tabs, while preserving the five primary HomeScout destinations and existing finance operations.
- Added a concise overview backed by saved assessment and savings-goal data, a distinct Payments information view that links to existing transaction history, and collapsible optional budget details/rule-based tips.
- Removed the oversized introductory card stack, ten-chip navigation row, and duplicate all-tools catalogue. Added a navigation routing unit test; Android unit tests and debug APK assembly passed.
- No backend, database, payment, authentication, or AI capabilities were added or changed. See `SMARTRENT_PHASE_2_REPORT.md`.

## 2026-11-24 — Owner-supplied SmartRent Phase 1 audit

- Audited HomeScout's existing Finance, calculations, savings, marketplace, payment, document, lease, safety, notification, map, profile, and Assistant systems.
- Added `SMARTRENT_PHASE_1_REPORT.md` with capabilities to reuse, current boundaries, integration dependencies, safe extension points, and likely files for future phases.
- Confirmed the existing Finance foundation should be extended in place. No new app, screen, database, payment flow, or later-phase feature was started; HomeScout product roadmap Phases 0–16 remain unchanged.

## 2026-11-24 — Post-phase repair and validation

- Corrected HomeScout authentication branding/provider layout and added an optional public browsing entry; provider sign-in remains unconfigured and is not faked.
- Replaced the prior map provider with MapLibre/OpenFreeMap; real vector tiles rendered in the Android emulator. No key or billing is required; this does not provide satellite imagery or Google Places.
- Improved owner-scoped profile editing through the existing profile endpoint. Save/reload and cross-account isolation are covered by the backend suite.
- Kept existing authorized user-to-user messaging and the five primary tabs.
- Added an illustrative KES budget, optional utilities field, backend-calculated preview that does not persist data, and explicit save action for the signed-in user's finance profile.
- Fixed Finance's shared load failure: dashboard/profile, plans, goals, records/documents, lessons, comparisons, leases, and alerts now load independently. A failed section no longer hides other Finance tools; its own content and retry state remain visible.
- Added Android regression tests for isolated section failures and configured stable development-only finance/auth keys in ignored `backend/.env`. No keys are embedded in the app or committed.
- Latest validation: backend full suite **94 passed**, targeted SmartRent suite **8 passed**, Ruff passed, and **9 Android unit tests passed**; debug assembly succeeded. The updated APK was installed in place on the Samsung SM-S938B and Finance opened without the old shared error or missing-key message. Local API health is ready/database ok with ADB reverse active.
- The emulator package has a different signer and remains untouched. Public inventory remains empty because demo homes are draft-only. See `EXPERIENCE_REPAIR_REPORT.md` for remaining boundaries.
- See `EXPERIENCE_REPAIR_REPORT.md` for limitations and verification boundaries.

## 2026-11-23 — Phase 0

- Established initial product context, architecture proposal, development rules, and Phase 0–16 roadmap.
- Recorded that the project starts without an Android app, backend, database, migrations, integrations, or tests.
- No application code or dependencies added.

## 2026-11-23 — Phase 1

- Created the Kotlin/Jetpack Compose/Material 3 Android app shell and reusable design system.
- Added a branded animated startup, the owner-supplied HomeScout logo adaptation for splash/launcher/app shell, and five-item bottom navigation.
- Added home and local sample discovery previews plus honest placeholders for future destinations.
- Added online Unsplash illustrative photos with offline fallback and source notes.
- Built the debug APK and checked rendering/navigation on an Android emulator.
- No backend, authentication, payments, database, or future service behavior implemented.
- Adopted the owner's navy house-and-location-pin logo and established it as the persistent brand mark for splash, launcher, app shell, and future phases.
- Adopted **HomeScout** as the permanent product name for the remainder of the project; Android namespace/application ID now use `ke.co.homescout`.

## 2026-11-23 — Phase 2

- Added the modular FastAPI backend, validated environment configuration, SQLAlchemy session/engine setup, API v1 health/readiness endpoints, safe error responses, request IDs, and privacy-conscious logging.
- Added portable foundational SQLAlchemy models and the initial Alembic migration for accounts, profiles, role-based permissions, application settings, audit events, and in-app notifications.
- Added SQLite development support, PostgreSQL/psycopg 3 URL preparation, pinned Python dependencies, setup documentation, and tests for configuration, database behavior, API behavior, and migration upgrade/downgrade.
- Added centralized Android `API_BASE_URL` build configuration from Gradle property/environment without implementing networking or embedding credentials.
- Verified backend tests/lint, Alembic migration behavior, Android BuildConfig generation, and Kotlin compilation. Full Android assembly was blocked in javac by a Windows `AccessDeniedException` reading a cached JAR; PostgreSQL live-server validation remains pending before production readiness.
- Kept HomeScout as the product name and did not implement authentication or property, finance, payment, map, or other future-phase APIs.

## 2026-11-23 — Phase 3

- Added a server-backed email/password lifecycle with Argon2id hashes, single-use email verification and password-reset codes, throttled sign-in, JWT access tokens, rotating refresh sessions, revocation, and profile/session APIs.
- Added a seeded role and scoped permission catalog, deny-by-default authorization, owner/scope checks, restricted role administration, audit events, and a one-time interactive Super Admin bootstrap CLI.
- Connected Android Profile screens to the API for registration, verification/resend, sign-in, reset, active sessions, and permission-gated administration. Account tokens are encrypted by AES-GCM with an Android Keystore key.
- Kept the five primary navigation tabs, HomeScout logo/name, sample property content, and later-phase placeholders.
- Moved the project into its dedicated `C:\Users\edris\Documents\Codex\HomeScout` folder, separate from RentWise.
- Updated Phase 3 documentation and preserved the Phase 2 report.
- Verified PostgreSQL 17.12 clean and populated migrations, downgrade/re-upgrade, and key authentication API flows against a disposable local instance.

## 2026-11-23 — Phase 4

- Added the Kenya country/county/town/neighbourhood hierarchy and seeded all 47 counties, county headquarters, priority towns, and priority neighbourhoods from documented sources.
- Added portable property and media persistence, KES and room-count validation, source-required coordinates, location search/relationships, and owner-scoped draft create/edit APIs.
- Added published/non-demo public property reads and opt-in demo fixtures that remain draft, unverified, and availability-unknown.
- Added Alembic migration and SQLite/API tests; backend suite passed with 37 tests and Ruff passed.
- No media upload, verification/moderation, or marketplace flow was started.

## 2026-11-23 — Phase 5

- Integrated Maps Compose with actual Google Maps SDK rendering, roadmap/satellite/hybrid/terrain modes, fullscreen, list/map switching, price markers, clustering, selected-property previews, and filters.
- Added Places SDK (New) Kenya area autocomplete and user-triggered nearby amenities. Added on-demand Android location permission and fused location positioning.
- Extended published property list filters for map viewport bounds, minimum bedrooms, furnishing, rent, and verified-only. Map reads exclude demo properties and marker parsing requires paired coordinates with a source.
- Added a clear missing-key fallback, API-key setup and restriction documentation, Android unit tests, backend API tests, and Phase 5 reporting.
- Upgraded Kotlin to 2.4.21 for Google SDK metadata compatibility and set the debug package suffix `ke.co.homescout.debug` while preserving the release ID `ke.co.homescout`.
- Verified Android compilation, four map unit tests, debug packaging, emulator startup, five-tab shell navigation, Discover-to-Map entry, and the no-key fallback. Backend Pytest passed (39 tests); Ruff lint/format passed.
- Live Maps/Places API calls remain pending owner-configured restricted Google Cloud keys and billing; see `MAPS_SETUP.md` and `PHASE_5_REPORT.md`.

## 2026-11-23 — Phase 6

- Added a marketplace Alembic migration for normalized amenities, saved properties, search history, saved-search alerts, listing mandates, enquiries, reports, and uploaded-media metadata.
- Added backend search by Kenyan location hierarchy, KES rent, bedrooms, property/unit type, furnishing, amenity, verified status, map viewport, and sort order. Public reads remain limited to available, published, non-demo listings.
- Added listing details/similar listings/private preview, save and compare APIs, enquiries, report intake, and scoped landlord/authorized-agent listing management.
- Added configurable local media storage and size/type/path controls for JPEG, PNG, and WebP upload, delete, and authorized reads. Production object storage remains unconfigured.
- Connected Android Discover, detail, and listing-management screens to the central API address. Added responsive adaptive result cards, edit/upload/private preview/publish/archive/draft deletion, saves, compare, enquiry, reports, saved-search records, and clear sample-data fallbacks.
- Preserved five primary tabs; all new marketplace screens are secondary routes. HomeScout remains the product name and owner-supplied logo is unchanged.
- Backend tests passed (42) and Ruff lint/format passed. Android unit tests and debug APK assembly passed. Emulator update was blocked by a signature mismatch with the already installed debug package; its local data was left untouched.
- Phase 6 SQLite migration/tests passed. PostgreSQL 17 checks from prior phases cover only Phases 2–4; Phase 6 PostgreSQL migration validation remains pending. See `PHASE_6_REPORT.md`.

## 2026-11-23 — Phase 7

- Added the personal-hub Alembic migration for user preferences, saved items/collections/shares, activity, schedule, manual records, private documents, support tickets/messages, and account-deletion requests; extended profile and in-app notification data.
- Added owner-scoped APIs for profile/photo, preferences, assigned-role switching, saves, collection sharing, activity, Africa/Nairobi schedule entries, in-app notifications, manual KES records, private documents, searchable support, export, and reauthenticated deletion requests.
- Added secondary Profile routes for personal information, saved items, collection management, activity, schedule, notifications, records, documents, help/support, About, settings, accessibility, and account privacy actions.
- Preserved five primary tabs and HomeScout visual identity. Role switching uses existing assignments only; the AI Assistant stays inactive.
- Backend tests passed (49); Ruff lint/format checks passed. Android unit tests and debug APK assembly passed.
- Phase 7 migration verification used SQLite. Phase 6 and Phase 7 migrations still need PostgreSQL 17 verification. Private files use local development storage; external notifications, reminder delivery, actual payments, automated deletion, and a staff support queue are not claimed.
- See `PHASE_7_REPORT.md` for exact scope, checks, and limits.

## 2026-11-23 — Phase 8

- Added owner-scoped SmartRent finance profiles and notes with AES-GCM payload encryption and a required environment-based key for staging/production.
- Added deterministic housing-readiness and budget estimates, move-in planning, virtual savings goals/contributions/shares, simulation, live-listing budget discovery and cost comparisons, user-entered utility summaries, manual housing records, financial lessons/quizzes, lease/deposit organization, and in-app alerts.
- Integrated the finance experience into the existing HomeScout Finance tab and centralized API configuration; retained the five-tab primary navigation.
- Added the Phase 8 Alembic migration, encryption configuration, API, tests, and documentation. Backend tests: 55 passed; Android unit tests and debug APK assembly passed.
- PostgreSQL 17 verification was not available for the Phase 8 migration; SQLite tests passed. No lending, credit decision, funds custody, payment integration, or active AI provider was added.
- See `PHASE_8_REPORT.md` for scope and verification limits.

## 2026-11-24 — Phase 9

- Added manual verification cases for landlords, agents, service providers, and properties with encrypted evidence uploads, submission history, expiry, rejection notes, and resubmission.
- Added private listing/safety reports, encrypted narratives, evidence linking, reviewer audit logs, moderation queues, escalation, and explicit property hide/restore/remove decisions. Reports alone do not label users or change listing visibility.
- Added duplicate-address and rent-outlier review prompts only; no automatic fraud verdict or trust score.
- Added private safe-viewing plans, trusted-contact data, consent-based account sharing, check-in/out, incident reporting, and safety guidance. No external reminder or contact service is claimed.
- Added HomeScout Trust & safety under the existing Profile tab and a property-detail entry point; the five primary tabs remain unchanged.
- Added Phase 9 migration and tests, encryption-key configuration, documentation, and report. Existing SQLite reference data was preserved during the upgrade.
- PostgreSQL 17 verification for Phase 9 remains pending. Android compile/unit test and backend full-suite results are in `PHASE_9_REPORT.md`.

## 2026-11-24 — Phase 10

- Added participant-only messaging for property enquiries, accepted roommate connections, and shared groups. Message content is AES-GCM encrypted at rest under the separate `HOMESCOUT_MESSAGE_ENCRYPTION_KEY`; sends enforce blocks and a per-user rate limit. Added attachments by authorized private-document reference, unread state, archive, reports, audit records, and in-app notifications.
- Added viewing request, host-confirm, reschedule, accept/decline, cancel, completion, history, and in-app agenda/reminder records. Requests stay pending until the assigned listing host confirms.
- Added private comparison boards limited to five eligible public homes; encrypted personal notes and cost inputs; opt-in roommate profiles, budget/location/lifestyle/timing filters, interest acceptance, and privacy-limited suggestions.
- Added active-member shared search groups, revocable membership, shared properties/votes/comments/comparisons, tasks, moving goals, and explicit member financial consent.
- Added encrypted owner-private viewing journals, photo references from private documents, and explicit revocable journal sharing. Voice-note upload and external message/reminder delivery were not implemented.
- Added the Android secondary collaboration route and property-detail entry points, keeping the five primary tabs unchanged; added migration `dd6548872d4f`, backend tests, project documentation, and Phase 10 report.
- Backend Pytest: 61 passed; scoped Ruff checks passed. Android Kotlin compilation, unit tests, and debug APK assembly passed. Phase 10 SQLite migration passed; PostgreSQL 17 validation remains pending.

## 2026-11-24 — Phase 11

- Added service provider profiles and offerings for moving and home services, county/town service areas, provider media, discovery filters, comparisons, and completed-service reviews. Approval indicators come only from current HomeScout manual verification records.
- Added customer/provider booking and service order records with pending, accept/reject, proposed reschedule, cancellation, and provider-completed states. Order records do not process or confirm payment.
- Added owner-private moving plans, deadline checklist/calendar, KES budgets, and room/furniture setup.
- Added explicit owner/manager resident-access grants and maintenance requests with private photos, assignment, participant-restricted reads, status history, and completion records.
- Connected an Android Services secondary route without changing the five primary tabs; added the Phase 11 migration, backend tests, documentation, and report.
- Backend Pytest: 64 passed; Ruff check/format passed; Android Kotlin compile, unit tests, and debug APK assembly completed successfully. PostgreSQL 17 verification remains pending for this migration.

## 2026-11-24 — Phase 12

- Added backend-only Daraja OAuth, STK Push and STK Query clients with environment/credential validation, disabled-by-default configuration, and fixed Safaricom sandbox/production hosts.
- Added service-booking payment transactions and callback evidence, KES validation, scoped permissions, idempotency, duplicate-order constraints, HMAC phone minimization, audit events, provider-safe history, and admin reconciliation summaries.
- Added callback validation/deduplication and authenticated status-query verification; success, failure, cancellation, expiry, and supported reversal states are backend-controlled. Network-ambiguous prompts stay pending without automatic resend.
- Added Android M-Pesa request UI for eligible accepted fixed-price service orders and a payment history/status screen under Finance. The five primary bottom tabs remain unchanged.
- No Daraja credentials/public callback host were supplied; payments remain disabled and no sandbox/live transaction was sent. No rent collection, escrow, provider payout, refund, or reversal request was implemented.
- Added Phase 12 setup documentation, decision record, tests, and report. See `PHASE_12_REPORT.md`.

## 2026-11-24 — Phase 13

- Added disabled-by-default server-side OpenAI-compatible provider support for Responses and Chat Completions, validated secret configuration, bounded requests, HTTPS deployment requirements, and an unavailable state with no fabricated responses.
- Added consent/versioning, owner-private AES-GCM conversation history, rename/delete/withdraw controls, per-account request limits, and the Phase 13 Alembic migration/RBAC grants.
- Added explicitly selected property, saved-home, finance, schedule, authorized work, and active shared-search context. Public home context is filtered to published, available, non-demo records; private messages, journals, and member profiles are excluded.
- Added the Android conversational screen, context toggles, history controls, privacy consent, honest configuration/error/loading states, global Assistant action, and Home/property/SmartRent/Profile/Help entry points. Preserved the five primary tabs.
- Updated the HomeScout documentation and Phase 13 report. Backend full suite: 81 passed with one upstream deprecation warning; Ruff and Android compile/unit/build checks passed. No provider call, PostgreSQL 17 migration run, or emulator rendering walkthrough was performed.

## 2026-11-24 — Phase 14

- Added permission-gated `/api/v1/admin/operations` endpoints for operational counts, basic user status, non-demo listing and service-review moderation, provider/service publication, locations, support tickets, message reports, support categories, allow-listed settings, and audit history.
- Added password reauthentication and audit-reason capture for account restrictions, self-restriction and last-active-Super-Admin protections, and session revocation on suspension. Support queue summaries withhold message content until an audited staff detail view; reported message access is also audited.
- Added the Phase 14 migration `d14a9c2e5f81` for support assignment, priority, escalation, action history, service-review moderation status, and service-management grants. Added the Android Operations console as a secondary Profile route without changing five bottom tabs.
- Connected existing Trust & Safety and role workflows rather than duplicating their verification, safety-report, and role-elevation rules. Public reads omit held/removed service reviews; operational metrics use actual current database counts and exclude demo listings and personal finance data.
- Updated the HomeScout documentation and Phase 14 report. Backend full suite: 88 passed with one upstream deprecation warning; Ruff lint/format passed; Android compile, unit tests, and debug APK assembly passed. SQLite only; no PostgreSQL 17 migration run or emulator rendering walkthrough was performed.

## 2026-11-24 — Phase 15

- Ran the backend suite (88 passed), Ruff, a complete SQLite migration upgrade, installed-environment dependency audit, and Bandit high/medium scan.
- Updated Android target SDK to 36, version-qualified API 27 navigation-bar styling, escaped the local Windows SDK path, and improved contrast for success/status text; added a contrast regression test.
- Android debug Kotlin compilation, lint (0 errors, 30 warnings), unit tests, and debug APK assembly passed. An API 37 emulator smoke check reached all five primary tabs.
- Android debug and release APK assembly passed after pinning Build Tools 36.0.0 and retrying release compilation with permitted SDK access; the release artifact is unsigned. PostgreSQL 17 after Phase 4, live integrations, and production readiness remain unverified.
- Added the Phase 15 QA/security/accessibility report and updated project status docs. See `PHASE_15_REPORT.md`.

## 2026-11-24 — Phase 16

- Added provider-neutral deployment/release preparation, production environment template, a non-root Python 3.12 backend container definition, Docker build exclusions, and a separate pinned runtime dependency lock. No container image or production deployment was created.
- Added Android release version inputs and a release preflight requiring external protected signing inputs, HTTPS API configuration, and Maps/Places client keys. Verified the preflight blocks `bundleRelease` without exposing values; no signed APK/AAB was made.
- Added `DEPLOYMENT_GUIDE.md`, `RELEASE_CHECKLIST.md`, `COMPETITION_DEMO_GUIDE.md`, `COMPETITION_PRESENTATION_OUTLINE.md`, and `PHASE_16_REPORT.md`.
- Connected the Home Trust & Safety shortcut to its existing screen.
- Android debug compilation, release source compilation, unit tests, and debug APK assembly passed. Android lint could not download missing AndroidX dependencies in the restricted environment. PostgreSQL 17 migrations after Phase 4 and all live integrations remain unverified; no demo or release distribution occurred.

## 2026-11-24 — Full project audit and local launch

- Audited the existing HomeScout phases 0–16 without restarting the project or opening a later development phase.
- Backed up the existing SQLite database, applied pending additive migrations to head, confirmed SQLite integrity and Alembic metadata consistency, and repaired verification-evidence model/schema alignment with duplicate-ID validation.
- Current backend verification: 89 Pytest tests passed; Ruff lint and format checks passed; pip check found no broken requirements. The live API reports healthy database readiness and all 47 counties; no public property listings are present.
- Started Uvicorn at 127.0.0.1:8765. The debug APK was previously built with the emulator bridge URL, but updating the installed package was blocked by a signing mismatch; no installed app data was removed.
- Documented remaining limits: fresh Gradle and pip-audit reruns were blocked by network access, PostgreSQL 17 migrations after Phase 4 remain unverified, live Maps/Daraja/AI are unconfigured, and no production deployment or signed distribution occurred.
- Added FULL_PROJECT_AUDIT_REPORT.md.

## 2026-11-24 — Physical Android installation

- Installed the HomeScout debug APK on the connected Samsung SM-S938B running Android 17 and launched its main activity successfully.
- Kept the existing emulator app untouched after its signature mismatch.
- Recorded that the installed APK uses the emulator-only API host and therefore needs a physical-device API configuration before phone-to-backend communication can be tested.

## 2026-11-24 — Authentication entry flow

- Kept the existing splash and added a branded Log in/Create account entry screen.
- Gated app navigation on refresh-token/session restoration; valid sessions open Home, while unauthenticated sessions remain in authentication.
- Reused the existing backend-backed sign-in, registration, verification, password reset, encrypted token storage, and logout flows.
- Android unit tests and APK build passed; targeted backend auth tests passed (8). Installed and launched updated debug APK on the connected phone; emulator-only API address prevents physical-device backend requests.

## 2026-11-24 — Fix HomeScout startup crash

- Reproduced the phone's “HomeScout Kenya keeps stopping” issue from the owner's screenshot and captured its Android crash log.
- Replaced dynamic placeholder destination registration in the Compose NavHost with an explicit Neighbourhoods route, preventing the null Destination crash during startup.
- Rebuilt and installed the debug APK on the Samsung SM-S938B. Verified MainActivity remained resumed, no fatal crash was logged, and the authentication entry screen was visible.

## 2026-11-24 — Phone API setup and password visibility

- Built the debug APK with the centralized API base set to `http://127.0.0.1:8765` and installed it on the connected Samsung SM-S938B.
- Forwarded the local backend through ADB reverse and confirmed the phone received `{"status":"ready","database":"ok"}` from the health endpoint.
- Added accessible show/hide controls to shared password fields; verified the registration field masks its value when hidden.
- Gradle Android unit tests and debug APK assembly passed. See `ANDROID_DEVICE_SETUP.md` for reconnect and rebuild steps.

## 2026-11-24 — Local account verification and reset

- Enabled one-time verification/reset code exposure in the ignored local development `.env`; production settings remain guarded.
- Improved Android messages so the local registration and password-reset code actions are explicit and usable without an SMTP server.
- Created a synthetic local test account and verified registration, email-code verification, login, password reset, and login with the new password through the real backend.
- Confirmed SMTP is not configured, so no external email was sent. See `AUTH_FLOW_FIX_REPORT.md` and `ANDROID_DEVICE_SETUP.md`.

## 2026-11-26 — Finance session, messaging, and dashboard follow-up

- Added a shared authenticated API retry path: on an access-token 401, the app refreshes once with its encrypted refresh token, persists the rotated token pair, and retries the original request. Concurrent expired-token requests reuse the same rotated token. Invalid refresh sessions still return the user to sign-in; network errors do not erase the saved session.
- Applied the renewal path to identity and personal-hub requests, including SmartRent preview/save and the Messages inbox/thread/send flows.
- Added a direct Discover entry from the empty Messages inbox so users can start an authorized chat by enquiring about a home; existing property-enquiry and roommate acceptance rules still govern conversation creation.
- Updated the Finance overview to show readable six-month recorded-cost bars with monthly values and up to three active savings objectives with actual saved/target amounts, progress, and any recorded target/pace dates. No synthetic financial activity was added.
- Kept unsent message drafts and attachments when a send fails; clear them only after the backend accepts the message.
- Android `:app:compileDebugKotlin`, `:app:assembleDebug`, and `:app:lintDebug` passed. Lint reported 0 errors and 29 warnings, mostly existing naming/toolchain/dependency notices. Local API readiness returned `ready/database ok`. No automated test suite was run for this change.
- The physical Samsung phone was connected, but `adb install -r` rejected the APK because its signing certificate differs from the installed package. The installed app and its data were preserved; no uninstall, data clear, or alternate package was used. The new debug APK is at `app/build/outputs/apk/debug/app-debug.apk` but is not installed on the phone.
- Follow-up: found that the installed package matches the user's local Android debug key, re-signed the same build with that key, and installed it in place successfully. ADB confirmed `MainActivity` resumed and the HomeScout process stayed active; local API readiness was `ready/database ok`. No uninstall or data clear occurred.

## 2026-11-26 — Discover results scrolling and refresh

- Replaced the fixed Discover controls plus nested results grid with one continuous vertical results list, so listings remain reachable by scrolling through the filters and results together.
- Added pull-to-refresh at the top of Discover. It repeats the current search with the active filters and refreshes the signed-in user's saved-property state; the existing retry action uses the same reload path.
- `:app:compileDebugKotlin` and `:app:assembleDebug` passed. The debug APK was signed with the device-matching local key and installed in place on Samsung SM-S938B without clearing app data. HomeScout MainActivity remained resumed. The local API readiness endpoint returned ready/database ok through ADB reverse.
- The UI gesture itself was not manually exercised on-device; no automated tests were run for this targeted repair.
- This is a post-Phase 16 repair. No production deployment or GitHub push occurred.

## 2026-11-26 — Profile navigation grid

- Replaced the Profile tab's stacked full-width shortcut buttons with a responsive action-card grid. The separate HomeScout hub now uses the same grid, so its account and workflow shortcuts are easier to scan.
- Tiles use existing HomeScout Material theme colors, accessible icon labels via the button title, short supporting text, and responsive column counts. Saved homes, activity, schedule, messages/shared plans, notifications, trust and safety, settings, and the account hub retain their original destinations. Listing management and platform operations remain role-gated.
- Android `:app:compileDebugKotlin` and `:app:assembleDebug` passed. The matching-signed debug APK installed in place on Samsung SM-S938B; `MainActivity` resumed and the HomeScout process remained active. No app data was cleared.
- Profile tile taps and responsive layouts were not manually exercised on-device; no automated tests were run for this visual update.
- This is a post-Phase 16 targeted repair. No production deployment or GitHub push occurred.

## 2026-11-26 — Profile page reference layout and top-bar avatar

- Added a tappable initials avatar to the upper-left app bar. It opens the signed-in Profile destination while preserving navigation state.
- Redesigned the signed-in Profile overview with a HomeScout navy identity panel, cream initials avatar, verified-email indicator, account-detail rows, current role chips, and a direct Edit profile details action. Existing session management, sign-out, and profile shortcut destinations remain available.
- Kept the Profile shortcut grid and role-gated listing/admin links. The profile page uses actual account email, status, verification and assigned roles; no follower counts or other sample account metrics were introduced.
- Android `:app:compileDebugKotlin` and `:app:assembleDebug` passed. Installed the matching-signed APK in place on Samsung SM-S938B with app data preserved. A focused device check tapped the top-left avatar and found the Profile page's Edit profile details action.
- The whole profile page was not exhaustively tested on-device; no automated tests were run for this UI update.
- This is a post-Phase 16 targeted repair. No production deployment or GitHub push occurred.

## 2026-11-26 — Profile drawer layout correction

- Replaced the top-left avatar's direct Profile navigation with a modal left-side drawer styled in HomeScout navy, with a close control, account initials/name/email/role/verification, and compact menu rows.
- Drawer actions navigate to Profile, saved homes, messages/viewings, schedule, SmartRent Finance, notifications, trust and safety, and settings. Listing management and platform operations appear only for the corresponding assigned roles. Sign-out requires confirmation.
- Removed the rejected two-column shortcut grid from the Profile tab. The tab now focuses on the account identity/details, profile editing, device sessions, sign-out and authorized administration. The separate account hub also uses compact single-column menu rows.
- Android `:app:compileDebugKotlin` and `:app:assembleDebug` passed. Installed the matching-signed debug APK in place on Samsung SM-S938B without clearing data; MainActivity remained active. A device check opened the drawer and confirmed the profile and HomeScout menu entries were visible.
- No automated tests were run for this visual/navigation update; not every drawer destination was tapped on-device.
- This is a post-Phase 16 targeted repair. No production deployment or GitHub push occurred.
