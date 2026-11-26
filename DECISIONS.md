# HomeScout Kenya — Architecture Decisions

This log records established choices and material changes. Proposals and open questions remain clearly labeled as such.

## D-001 — Preserve the specified technology stack

- **Status:** Accepted as the project baseline.
- **Decision:** Use Kotlin, Jetpack Compose, Material 3, and Gradle for Android; Python, FastAPI, SQLAlchemy, Alembic, Uvicorn, and Pytest for the backend; SQLite in development; PostgreSQL 17 in production; Argon2 for password hashing; and M-Pesa Daraja for payments.
- **Reason:** These are explicit project requirements.
- **Tradeoffs:** Exact versions and integration behavior need to be selected and validated during implementation. SQLite and PostgreSQL differ, so production-relevant migrations and queries need PostgreSQL verification.
- **Alternatives considered:** None; no change was proposed.

## D-002 — Start with a modular single Android app and backend service

- **Status:** Accepted and implemented for Phases 1–2.
- **Decision:** Begin with one Android app and one FastAPI service, organized into feature and responsibility boundaries. Split services or Gradle modules only when a measured need justifies it.
- **Reason:** It provides clear separation without assuming scale or adding early operational complexity.
- **Tradeoffs:** A single deployment has shared release and scaling boundaries; package discipline is needed to prevent coupling. Feature packages may grow as authorized work proceeds.
- **Alternatives considered:** Microservices and multi-module Android from day one; deferred because no concrete need is established.

## D-003 — Treat this as a new project with no inherited implementation

- **Status:** Accepted for the current workspace baseline.
- **Decision:** Establish documentation and architecture proposals without importing unrelated project code.
- **Reason:** The supplied workspace had no HomeScout source, and the user clarified this is a new project starting from the beginning.
- **Tradeoffs:** Implementation setup remains for a future authorized phase.
- **Alternatives considered:** Reusing the nearby ShuleWise code; rejected because it is a separate product and was not authorized as a base.

## D-004 — Five primary tabs and secondary destinations

- **Status:** Accepted and implemented in Phase 1.
- **Decision:** Keep the bottom bar to five items: Home, Discover, Areas, Finance, and Profile. Map, Services, and AI Assistant remain secondary destinations.
- **Reason:** The owner requested five tabs maximum and a clear mobile shell.
- **Tradeoffs:** Secondary sections require entry points within the app; not every destination is visible in the persistent bar.
- **Alternatives considered:** Placing all eight requested destinations in the bottom bar; not used because it would crowd navigation.

## D-005 — Use the owner's house-and-location-pin logo consistently

- **Status:** Accepted and implemented in Phase 1.
- **Decision:** Use the owner's navy rounded-square house-and-location-pin mark with cream lines and a terracotta pin center. Pair it with the HomeScout wordmark and “Find your next place” tagline. Keep the vector asset and shared Compose logo component consistent across splash, launcher, app shell, and future phases.
- **Reason:** The owner designated the supplied logo image as the project logo and asked for it to remain consistent throughout the project.
- **Tradeoffs:** The supplied image is a brand presentation rather than a standalone vector asset, so the app uses a simplified vector adaptation of its house, location pin, colors, and wordmark.
- **Alternatives considered:** A standalone letter monogram; superseded by the owner's supplied logo.

## D-006 — Treat property photos and listing facts as separate demo content

- **Status:** Accepted and implemented in Phase 1.
- **Decision:** Use online Unsplash stock photos for visual polish, while marking all property records as sample/demo content. Provide a local fallback if photos cannot load.
- **Reason:** The owner requested online imagery; no verified HomeScout listing photos or feed exist.
- **Tradeoffs:** Photos require internet and could be unavailable; they must never be presented as evidence for an actual property.
- **Alternatives considered:** Reusing third-party booking-platform listing photos; not selected.

## D-007 — Use HomeScout as the project and product name

- **Status:** Accepted; effective immediately and for the remainder of the project.
- **Decision:** Refer to the app as **HomeScout** in product UI, source naming, and project documentation. Use the `ke.co.homescout` Android namespace/application ID.
- **Reason:** The owner explicitly selected HomeScout as the permanent project name and the supplied logo already carries that name.
- **Tradeoffs:** The source project is isolated in its own HomeScout folder; old attachment/session labels do not define the product name.
- **Alternatives considered:** Retaining the prior working title; superseded by the owner's instruction.

## D-008 — Keep foundational backend schema portable

- **Status:** Accepted and implemented in Phase 2. Phase 2/3 migrations and selected API flows passed locally on PostgreSQL 17.12; new feature migrations still require PostgreSQL verification before release.
- **Decision:** Use SQLAlchemy UUID and JSON types, standard relational constraints, Alembic migrations, SQLite for local development, and psycopg 3 URLs for the PostgreSQL 17 target. The running app never performs schema creation.
- **Reason:** Phase 2 requires a SQLite development foundation prepared for PostgreSQL.
- **Tradeoffs:** SQLite tests do not establish PostgreSQL operational compatibility; run migration and behavior checks against PostgreSQL before production readiness.
- **Alternatives considered:** Database-specific extensions/types and startup auto-create; not used.

## D-009 — Restrict Phase 2 models to platform foundations

- **Status:** Accepted and implemented in Phase 2.
- **Decision:** Add only account/profile, role/permission, application setting, audit, and in-app notification persistence foundations. Defer authentication and product feature models/endpoints to their authorized phases.
- **Reason:** Keep this phase focused on backend infrastructure and avoid premature feature schema.
- **Tradeoffs:** Later feature phases will need their own approved schema and migration work.
- **Alternatives considered:** Implementing property, finance, or payment models now; deferred.

## D-010 — Centralize the Android API base address

- **Status:** Accepted and implemented in Phase 2.
- **Decision:** Generate one `BuildConfig.API_BASE_URL` from Gradle property `homescout.apiBaseUrl` or environment variable `HOMESCOUT_API_BASE_URL`, accessed through `ApiConfiguration`.
- **Reason:** Let Android development target a configured backend without scattering URL strings or embedding production credentials.
- **Tradeoffs:** Build variants still need an API address supplied by the developer/release environment; Phase 3 now uses that address for identity and account requests.
- **Alternatives considered:** Hardcoding local/production URLs in source or including backend secrets in the client; not used.

## Open decisions

- MVP scope, success measures, user and verification model.
- Role approval evidence and any additional identity checks.
- Hosting, CI, secret management, object storage, messaging provider, and monitoring.
- Payment products, fees, refunds/disputes, and operational reconciliation.
- Whether any AI capability is needed; none is approved or planned for implementation yet.

## D-011 — Email/password identity with verified email

- **Status:** Accepted and implemented in Phase 3.
- **Decision:** Use email/password registration with Argon2id, email verification before sign-in, generic reset requests, single-use account-action codes, ten-minute HS256 access tokens, and 30-day database-backed refresh sessions that rotate and can be revoked.
- **Reason:** It supplies a complete account lifecycle without adding phone/SMS provider dependencies that were not configured.
- **Tradeoffs:** Email ownership is verified; identity, property ownership, tenancy, or provider credentials are not. Live email delivery needs SMTP setup. Developers may expose action codes only in isolated development/test and only by explicitly changing a setting.
- **Alternatives considered:** Phone OTP and external identity providers; deferred because no provider/account was supplied.

## D-012 — Scoped role catalog and controlled elevation

- **Status:** Accepted and implemented in Phase 3.
- **Decision:** Seed Guest as a virtual role plus nine persistent roles and an explicit permission catalog. All new accounts start as tenants; a chosen landlord/provider/manager role is stored as a request only. Operations staff grant elevated roles through audited, password-confirmed, scoped administration. Scope types are restricted by role, self-escalation is prohibited, and the final Super Admin cannot be removed.
- **Reason:** Separate role requests from actual authority and reduce cross-account/resource access.
- **Tradeoffs:** The catalog is an initial capability model. Future feature services must still verify real ownership, membership, and participation for their resources.
- **Alternatives considered:** Granting the selected role directly at registration or making all roles global; rejected because either would allow self-selected privilege or overly broad scope.

## D-013 — Encrypt Android account tokens with Android Keystore

- **Status:** Accepted and implemented in Phase 3.
- **Decision:** Persist the access/refresh pair as AES-GCM ciphertext in private app preferences; generate and retain the AES key in Android Keystore. The server stores only refresh/action token verifiers.
- **Reason:** Keep session persistence local while protecting the token material from plain preference storage.
- **Tradeoffs:** A Keystore-key loss or invalid ciphertext clears the local session; local logout also attempts server revocation.
- **Alternatives considered:** Plain SharedPreferences or hardcoding a client secret; not used.

## D-014 — Isolate HomeScout in its own project directory

- **Status:** Accepted and implemented.
- **Decision:** Keep HomeScout source and documentation under `C:\Users\edris\Documents\Codex\HomeScout`, separate from RentWise.
- **Reason:** The owner explicitly stated HomeScout is a different app and needs its own folder.
- **Tradeoffs:** The initial pasted-attachment/session path may retain an older working-title label; it is not the product source directory.
- **Alternatives considered:** Keeping both apps in one source folder; rejected by the owner.

## D-015 — Source Kenyan reference data and keep demo properties non-operational

- **Status:** Accepted and implemented in Phase 4.
- **Decision:** Seed the official 47-county code/name set and county headquarters from government references; seed additional priority towns and neighbourhoods from the owner's brief. Keep seeded coordinates empty unless a specific source is recorded. Store synthetic property examples only in test fixtures, mark them `is_demo`, and constrain them to draft, unverified, and availability-unknown states. Public property reads require published and available non-demo records; callers must explicitly request demo rows.
- **Reason:** Location names and coordinates need traceable provenance, and synthetic examples must not be confused with real rental inventory or verification.
- **Tradeoffs:** Initial neighbourhood coverage is focused on owner-prioritized areas. Location editors can add reference rows with admin permission; coordinate sources must be supplied with coordinate pairs.
- **Alternatives considered:** Seeding fabricated coordinates or inserting demo listings into every production database; rejected to avoid unsupported geographic and property claims.

## D-016 — Use real Google Maps and Places for map exploration (superseded by D-031)

- **Status:** Historical Phase 5 decision; superseded by D-031 in the post-phase map repair.
- **Decision:** Use Maps Compose and the Google Maps SDK for road, satellite, hybrid, and terrain views. Use Places SDK (New) for Kenya-restricted place autocomplete and on-demand nearby amenities. Use device location only after an explicit permission action. Render property markers only from public published/available/non-demo API records with paired coordinates and recorded coordinate provenance; use Google Maps Compose Utilities for marker clustering.
- **Reason:** County/town/neighbourhood seed data deliberately has no unsourced coordinates, so the map must start from a real user-selected Places result or user-granted device position.
- **Tradeoffs:** Google Cloud project setup, restricted keys, billing, internet, and a source of real published inventory are required to exercise full map behavior. Places requests are billed according to current Google terms/pricing; nearby searches run only when the user selects a category. No Google-derived location data is persisted by the app.
- **Alternatives considered:** Static screenshots, decorative tiles, guessed Kenyan coordinates, runtime-seeded demo markers, or an alternate map provider; not used.

## D-017 — Keep Maps Platform keys externally configured and API-restricted (superseded by D-031)

- **Status:** Historical Phase 5 decision; superseded by D-031. The current public OpenFreeMap integration uses no Android map key.
- **Decision:** Supply the Maps SDK and Places SDK client keys via `HOMESCOUT_MAPS_API_KEY` and `HOMESCOUT_PLACES_API_KEY` or documented Gradle properties. Use separate Android-app-restricted keys with matching package/signing SHA-1 and API restrictions. Keep backend credentials out of Android. Show an explicit configuration fallback when the Maps key is missing.
- **Reason:** Android SDK client keys must reach the client process, so protection comes from Android application and API restrictions, not by pretending the value can be hidden in a shipped APK.
- **Tradeoffs:** Developers must configure debug and release signing fingerprints and watch billing/quotas in Google Cloud. No key was supplied during Phase 5, so live service verification remains pending.
- **Alternatives considered:** Source literals, unrestricted Cloud keys, or a server credential bundled in Android; rejected.

## D-018 — Publish only available, photo-backed, non-demo listings

- **Status:** Accepted and implemented in Phase 6.
- **Decision:** Public search/detail expose only non-demo listings that are published and available. A listing can be published only after it is marked available and has at least one uploaded, non-illustrative image. Publishing leaves verification status unchanged.
- **Reason:** Avoid presenting unavailable or synthetic homes as live inventory, and keep verification claims separate from listing completeness.
- **Tradeoffs:** A new database has no discoverable homes until an authorized owner/agent creates and publishes actual content. Public search is available-only; owners and authorized agents manage availability.
- **Alternatives considered:** Automatically publishing samples, treating upload as verification, or exposing drafts in public search; rejected.

## D-019 — Keep uploaded listing photos behind a storage interface

- **Status:** Accepted and implemented in Phase 6 for local development.
- **Decision:** Accept JPEG, PNG, and WebP uploads within a configurable size limit and write UUID-keyed files through `LocalMediaStorage`, outside public web roots. Serve a file only when the listing is public or the requester is authorized for that property. Keep the storage directory configurable.
- **Reason:** Provide a usable local listing workflow without coupling business logic to a cloud vendor or making draft media public.
- **Tradeoffs:** Local disk storage is not a production backup, CDN, object storage, malware scan, or image processing solution. Those operational controls remain required before launch.
- **Alternatives considered:** Store uploaded bytes in the relational database, expose arbitrary client URLs, or select a cloud vendor without an owner decision; not used.

## D-020 — Persist search alerts and listing reports without claiming delivery or moderation

- **Status:** Accepted and implemented in Phase 6.
- **Decision:** Store validated alert filters and let authenticated users submit one report per property. Report submissions remain `received`; alert records remain active until deleted. Do not claim alert delivery, report review, moderation, or verification until their operational workflows exist.
- **Reason:** Establish accountable API records and UI entry points while avoiding false claims about external notifications or staff action.
- **Tradeoffs:** Alerts do not trigger email/push delivery and reports have no review queue in this phase.
- **Alternatives considered:** Displaying alerts as delivered or reports as actioned without supporting workers/staff tools; rejected.


## D-021 — Keep personal hub data private and distinguish records from completed services

- **Status:** Accepted and implemented in Phase 7.
- **Decision:** Scope profile preferences, saves, activity, schedule, manual records, documents, support tickets, exports, and deletion requests to the authenticated account. Collections are private unless the owner explicitly shares them with a selected account and grants read/edit permission. Role switching selects only a role already assigned by an authorized operator. Store schedules in the user's explicit timezone, defaulting to `Africa/Nairobi`. Keep manual KES entries labeled as user-entered, and keep deletion requests pending until a separately authorized operational process handles them.
- **Reason:** Personal data needs clear ownership and permission boundaries; a reminder, record, or request should not be presented as a delivered or completed external service.
- **Tradeoffs:** The phase provides local private-file storage, in-app notification controls, and stored reminder preferences, but no production object store, reminder worker, push/email delivery, payment processor, or deletion worker.
- **Alternatives considered:** Public-by-default collections, user self-assignment of elevated roles, fabricated payment confirmations, or claims of external delivery without providers/workers; rejected.

## D-022 — Keep SmartRent planning private, explainable, and non-transactional

- **Status:** Accepted and implemented in Phase 8.
- **Decision:** Encrypt finance payloads with AES-GCM using an environment-held 32-byte key and authenticate each payload against its owner's account UUID. Keep finance access server-side and owner-scoped; share savings goals only by explicit owner action. Show the assumptions for housing-readiness estimates, allow planning without a payslip, and label simulated savings and manual rent records as virtual/user-entered. Keep utility summaries input-based and describe lease tools as organizers, not advice. Do not add payments, credit decisions, lending, funds custody, or AI processing in this phase.
- **Reason:** Housing-planning figures are sensitive, while deterministic estimates and manually entered records must not be mistaken for credit underwriting, confirmed money movement, legal advice, or external service results.
- **Tradeoffs:** A stable secret and key-recovery/rotation procedure are operational requirements. Relational metadata remains queryable; Phase 7 private-document bytes still use local development storage and are not covered by finance-field encryption. PostgreSQL 17 production validation remains pending.
- **Alternatives considered:** Plaintext finance columns, a client-shipped encryption key, automatic sharing, credit scoring, storing/transferring user funds, or claiming provider/legal/AI behavior without an approved service; rejected.

## D-023 — Make rental trust claims evidence-backed and reviewable

- **Status:** Accepted and implemented in Phase 9.
- **Decision:** Store verification submissions and supporting evidence as private, owner-scoped records; only an authorized human reviewer can approve/reject them, set expiry, and record an audited decision. Protect trust evidence and private narratives with a separate environment-held AES-GCM key. Keep reports allegation-only until a reviewer decides, and change listing visibility only through an explicit reviewed moderation action. Expose trust indicators from actual records without claiming property ownership, legal identity, tenancy, user reviews, or a trust score. Share safe-viewing details only to a selected account after explicit consent.
- **Reason:** Housing fraud reports and verification evidence are sensitive. A report should initiate review, not establish guilt; a HomeScout review must not be represented as an external identity, title, tenancy, or license check.
- **Tradeoffs:** The phase supplies internal workflows, not an external identity-check provider, staffed service-level commitments, emergency response, phone verification, or notification delivery. Production needs a defined evidence/review policy, secure private object storage, key custody/rotation, malware scanning, retention, and access auditing.
- **Alternatives considered:** Automatic fraud labels, public report details, unreviewed verification badges, inferred trust scores, or sharing viewing details without consent; rejected.

## D-024 — Keep communication and housing collaboration authorized and private

- **Status:** Accepted and implemented in Phase 10.
- **Decision:** Create conversations only from an existing authorized relationship: a property enquiry, accepted roommate connection, or active shared-search group. Encrypt message bodies and private journal/comparison/financial collaboration payloads at rest using a distinct environment-held 32-byte AES-GCM key. Enforce participant and group membership on every read/write, provide participant blocking/reporting, cap message reads/sends, and make private journals owner-only until explicitly shared; allow owners to revoke journal shares. Keep roommate profiles opt-in and suppress contact details in candidate results. Keep viewing status `requested` until the assigned host confirms, and require explicit consent from each participant before revealing shared financial goal amounts.
- **Reason:** Messages, housing preferences, viewing notes, and budgets can expose sensitive information. Access should arise from a concrete relationship and user action rather than public discoverability or implied consent.
- **Tradeoffs:** Server-side encryption at rest is not end-to-end encryption; the server decrypts message content for authorized participants. External push/email delivery, moderation operations for message reports, voice-note recording/upload, production object storage, and PostgreSQL 17 migration validation are not included in this phase.
- **Alternatives considered:** Public contact details, arbitrary user-to-user direct messages, automatic viewing confirmation, public journal/default group sharing, financial sharing without consent, or describing server-side encryption as end-to-end encryption; rejected.

## D-025 — Keep service bookings, provider claims, maintenance, and moving plans scoped

- **Status:** Accepted and implemented in Phase 11.
- **Decision:** Derive provider approval labels only from the current HomeScout manual verification record. Keep service requests pending until the provider acts, preserve each authorized lifecycle change in booking history, and expose booking/order records only to their customer and provider. Treat service order amounts as estimates/records, not payment confirmations. Keep moving plans owner-private. Allow maintenance requests only to residents with explicit current property-owner/manager access and limit provider access to requests assigned to that provider; revoke access when the grant is revoked.
- **Reason:** Provider approval, booking acceptance, payment, and tenancy are separate facts that must be represented only after the relevant action and system record exists.
- **Tradeoffs:** Verification remains an internal manual review, local media storage is development-only, and there is no calendar/reminder transport or payment processing. PostgreSQL 17 migration validation remains pending.
- **Alternatives considered:** Publicly seeded provider profiles, fake approval or reviews, automatic booking confirmation, payment claims from order records, and maintenance access based only on a supplied property ID; rejected.

## D-026 — Keep Daraja backend-only, idempotent, and limited to approved service orders

- **Status:** Accepted and implemented in Phase 12.
- **Decision:** Keep Daraja credentials and STK operations on FastAPI; default the integration off; scope payments to a customer's provider-accepted fixed-price service order with an integer KES amount; require explicit authorization for live merchant collection; never accept Android's claim of success. Store payer phone as HMAC plus last four digits, use per-user idempotency and one active/successful transaction per order, treat callbacks as untrusted and verify their checkout with authenticated STK Query, and expose only role-appropriate transaction history. Keep ambiguous STK request timeouts pending and do not retry them automatically.
- **Reason:** Payment status must come from the provider, repeated client/callback delivery must not duplicate charges, and service booking/order records must not be confused with rent custody or provider payouts.
- **Tradeoffs:** No live integration can be exercised without Daraja sandbox credentials and a public HTTPS callback; callback payload alone cannot authenticate itself. Server-side query plus cooldown and manual reconciliation reduce that risk but do not replace production security review, merchant onboarding, reconciliation operations, or legal approval. Refund/reversal initiation and provider settlement are not included.
- **Alternatives considered:** Daraja secrets in Android; payment success asserted by client/callback alone; arbitrary amount payments; automatic retries after an ambiguous prompt; rent collection/escrow; rejected.

## D-027 — Keep HomeScout Assistant server-side, consent-based, and owner-scoped

- **Status:** Accepted and implemented in Phase 13.
- **Decision:** Keep AI provider credentials only in backend environment/secret management and default the provider off. Require an explicit, versioned privacy consent before sending a prompt. Encrypt conversation titles and message bodies with AES-GCM under a stable server key; owner-scope history and rate limits. Add personal or shared context only when the user selects it and current authorization permits it. Public listing context includes only currently published, available, non-demo homes. Do not save a failed prompt or fabricate a response when the provider is missing or unavailable.
- **Reason:** Housing conversations may reveal personal finances, location, schedules, or private relationships. A server-side assistant should receive only the context the account holder asks to include and is authorized to access.
- **Tradeoffs:** AI remains unavailable until a compatible provider, model, stable encryption key, and policy are configured. Server-side encryption protects database contents at rest but does not make conversations end-to-end encrypted; the configured provider receives the selected prompt/context. Retention, production key custody/rotation, privacy/legal review, provider data terms, PostgreSQL 17 validation, and live model evaluation remain operational requirements.
- **Alternatives considered:** Client-shipped model keys, silent context sharing, storing prompt text unencrypted, giving one role another role's private records, canned responses presented as AI, or provider calls before consent; rejected.

## D-028 — Keep staff operations permission-gated and auditable

- **Status:** Accepted and implemented in Phase 14.
- **Decision:** Add operational controls under a separate versioned admin API and secondary Android route. Check existing role permissions server-side for every read and change. Require current-password confirmation for account restrictions, prevent self-restriction and last-Super-Admin suspension, revoke active sessions on suspension, and record reasons and administrative actions. Hide held/removed service reviews from public reads and audit staff review decisions. Limit operational metrics to current record counts, exclude demo homes, and avoid personal financial details. Keep configurable platform settings on a fixed allow-list.
- **Reason:** Support, listing, service, account, and moderation operations affect other users and require traceable, scoped access while minimizing data exposure.
- **Tradeoffs:** This phase supplies operational tools but not staffing policies, response-time commitments, external notification delivery, custom analytics, or a production incident-management system. PostgreSQL 17 migration validation and emulator rendering remain outstanding.
- **Alternatives considered:** Client-only staff gating, arbitrary settings edits, unlogged moderation, exposing full ticket conversations in queue lists, or treating reports as proof of wrongdoing; rejected.

## D-029 — Fail release packaging without signing and production endpoints

- **Status:** Accepted and implemented in Phase 16.
- **Decision:** Configure Android release signing only from environment-injected values and an absolute keystore path outside the checkout. Gate APK/AAB release packaging on signing configuration and an HTTPS HomeScout API base URL. Never log secret values or distribute unsigned artifacts.
- **Reason:** A release should not silently package against an empty/local endpoint or create an artifact that appears ready for distribution when it is unsigned.
- **Tradeoffs:** No release APK/AAB can be packaged until the owner configures a protected signing key and API address. This phase validates the fail-closed gate but cannot validate an owner-held key, signed artifact, Play Console upload, or production server.
- **Alternatives considered:** Debug-signing a release, committing signing credentials or server secrets, letting a missing API address pass, or distributing the unsigned Phase 15 artifact; rejected.

## D-030 — Keep verification-evidence uniqueness consistent across model and migration

- **Status:** Accepted and implemented during the 2026-11-24 full project audit.
- **Decision:** A verification submission may reference a document only once. Enforce that invariant in request validation and SQLAlchemy metadata, matching the unique constraint already present in the Phase 9 database migration.
- **Reason:** Alembic must compare the model to the existing database accurately, while invalid duplicate evidence references should be rejected before persistence.
- **Tradeoffs:** Duplicate document IDs now receive a validation error; no new migration or data rewrite was needed.

## D-031 — Use a no-key map tile service for HomeScout

- **Status:** Accepted and implemented in the post-phase map repair on 2026-11-24; end-to-end tile rendering still requires device/emulator verification.
- **Decision:** Replace the Google Maps/Places Android integration with MapLibre Native and OpenFreeMap public vector styles. Use standard/bright/light/dark styles; do not advertise satellite, hybrid, terrain, Places, or nearby business search. Keep public-map attribution visible. Proxy explicit, Kenya-filtered area lookups through the HomeScout API to configurable Nominatim, with request caching and a rate limit. Show honest loading/error states and never fabricate property coordinates or map markers.
- **Reason:** The owner requested a free map that can be used without Google Maps credentials or billing. OpenFreeMap documents public use without keys or a usage-view cap and allows commercial use; Nominatim provides user-triggered geocoding under strict usage limits.
- **Tradeoffs:** OpenFreeMap has no SLA and its service may change; Nominatim is low-volume and requires application-wide rate limiting, caching, attribution, and a switchable/self-hosted alternative at production scale. Vector styles do not supply satellite imagery or a Places API. Current process-local geocoder limits must be shared across workers before horizontal scaling.
- **Alternatives considered:** Google Maps/Places with owner-provided billing and keys, static/decorative maps, guessed coordinates, or using Nominatim for autocomplete/bulk lookups; rejected for this repair.
- **References:** [OpenFreeMap](https://openfreemap.org/); [OpenFreeMap mobile quick start](https://openfreemap.org/quick_start/); [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/).
- **Alternatives considered:** Removing the database constraint or creating a new migration for an already-present constraint; rejected.

## D-032 — Keep SmartRent math explainable, decimal-based, and encrypted at rest

- **Status:** Accepted and implemented for owner-supplied SmartRent Phase 3.
- **Decision:** Normalize monthly, annual, twice-monthly, biweekly, weekly, and daily income using explicit user assumptions; recent monthly totals cover all sources and override source normalization to avoid double-counting. Use Decimal calculations and disclose unknown comparison costs. Stateless calculations do not require the private finance encryption key, but finance profiles/goals/contributions remain encrypted and fail closed without it. Updated clients provide a stable request UUID for contribution retries; enforce it per goal/contributor with an additive database constraint.
- **Reason:** Users need auditable estimates and retry safety without turning the encrypted profile into plaintext or treating unentered costs as zero.
- **Tradeoffs:** Daily pay defaults to five chosen workdays/week until the user changes the schedule. Recent totals are assumed to include all income sources. Older clients that omit request UUIDs remain accepted for compatibility but cannot receive retry-idempotency guarantees.
- **Alternatives considered:** Credit scoring, hidden income haircuts, counting recent totals in addition to recurring sources, inventing missing fees, storing unencrypted fallback records, or deduplicating contributions by amount alone; rejected.

## D-033 — Keep SmartRent budget planning account-scoped and separate from payment evidence

- **Status:** Accepted and implemented in owner-supplied SmartRent Phase 4.
- **Decision:** Store monthly category limits in the existing AES-GCM encrypted Finance profile and derive actual spending from the authenticated user's manual finance records. Treat optional due dates as user-entered reminder plans, exclude them from actual expense totals, and never infer a successful/confirmed payment from them. Allow only the record owner to delete their entry. Reuse the current encrypted JSON payloads and relational record IDs; no migration is needed.
- **Reason:** Budget limits, actuals, and reminders answer different questions. The dashboard must help users plan without turning a reminder into a transaction or exposing another account's private finances.
- **Tradeoffs:** Category actuals reflect only manual records entered into HomeScout; they are not a bank feed, verified account statement, or complete financial ledger. Reminder delivery is in-app only and is not scheduled externally.
- **Alternatives considered:** Seeding example values as personal data, counting planned reminders as expenses, trusting the Android client to scope deletions, or building a duplicate budget database; rejected.

## D-034 — Track rent obligations and reports without handling rent funds

- **Status:** Accepted and implemented in owner-supplied SmartRent Phase 5.
- **Decision:** Store account-private rent reminders and user-reported external payment entries in encrypted payloads. Enforce ownership in backend queries/constraints, use an idempotency UUID for submission retries, and show balances only as arithmetic against reports. Leave entries unverified and do not issue rent receipts. M-Pesa remains service-booking-only; card and PayPal rent checkout stay unavailable without provider credentials and authorization.
- **Reason:** Users can organize due dates and remember what they report paying without HomeScout misrepresenting a user statement as a landlord/provider confirmation or acting as an unauthorized rent collector.
- **Tradeoffs:** These records are personal tracking, not proof of payment or a verified ledger. Editing/removing reports changes the displayed balance-from-reports. External confirmation, transfers, landlord acknowledgements, and rent custody are out of scope.
- **Alternatives considered:** Fabricated demo payments, client-declared success states, rent escrow, or reusing service-booking Daraja credentials for rent; rejected.
