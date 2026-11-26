# HomeScout Kenya — Roadmap

Phases 0–16 are complete for their implementation/preparation scope. The full project audit and local launch were completed on 2026-11-24; no subsequent phase was started. See FULL_PROJECT_AUDIT_REPORT.md for current verification and blockers. Do not start another phase without owner authorization. Owner-supplied phase briefs override earlier roadmap wording.

## Separate owner-supplied SmartRent workstream

This finance workstream extends HomeScout's existing SmartRent implementation and does not reset or renumber product Phases 0–16. SmartRent Phases 0–5 are complete: safety/inspection rules, existing-system audit, Finance UI/navigation redesign, finance data/calculation improvements, data-backed budgets/reminders, and private rent obligations with user-reported external payment records. SmartRent Phases 3 and 5 add Alembic migrations; Phase 5 reuses the existing Finance encryption. See `SMARTRENT_PHASE_1_REPORT.md` through `SMARTRENT_PHASE_5_REPORT.md`. Stop before SmartRent Phase 6 until the owner authorizes it.

## Phase 0 — Project intelligence and guardrails

- **Goal:** Establish project context, proposed architecture, persistent documentation, and development rules.
- **Dependencies:** Initial project brief.
- **Acceptance criteria:** Record new-project state and required stack; document architecture direction, risks, decisions, phases 0–19, and development rules.
- **Status:** Complete.

## Phase 1 — Design system and Android application shell

- **Goal:** Build the Material 3 design foundation, app navigation shell, and first public-facing home/discovery preview.
- **Dependencies:** Phase 0 and the owner's Phase 1 brief.
- **Acceptance criteria:** Kotlin/Compose Android build; specified palette and light/dark theme; reusable UI components; five bottom navigation destinations; all eight requested routes; animated startup splash and simple branded mark; Kenya-oriented home content and clearly labeled sample listings; placeholder future screens; no backend/auth/payments/maps; Gradle build and manual emulator rendering/navigation checks pass.
- **Status:** Complete. See `PHASE_1_REPORT.md`.

## Phase 2 — Backend foundation, database, and API architecture

- **Goal:** Establish the modular HomeScout API, portable foundation schema, migrations, health checks, tests, and central Android API address configuration.
- **Dependencies:** Phase 1 and owner-authorized Phase 2 brief.
- **Acceptance criteria:** Versioned FastAPI/Uvicorn service; SQLAlchemy/Alembic; environment-based SQLite/PostgreSQL configuration; foundational account/access/settings/audit/notification models; stable safe errors and logging; tested SQLite migrations/API; central Android API URL config; documentation and Android build verification.
- **Status:** Complete. SQLite tests/migrations, Ruff, Android BuildConfig generation, and Kotlin compilation passed during Phase 2. Android APK assembly and local PostgreSQL 17.12 migration/API checks subsequently passed during Phase 3. Production-host and automated PostgreSQL CI checks remain. Details are in `PHASE_2_REPORT.md` and `PHASE_3_REPORT.md`.

## Phase 3 — Identity, authentication, and authorization

- **Goal:** Implement account lifecycle, secure sessions, and role-aware access across the API and Android account area.
- **Dependencies:** Phases 1–2; approved identity, verification, recovery, and session policies.
- **Acceptance criteria:** Email/password registration and verification; sign-in, token refresh/revocation, password reset; server-side role, owner, and scoped authorization; restricted role administration; Android account integration; security and access tests; docs and phase report.
- **Status:** Complete. Local PostgreSQL 17.12 migration/API checks passed; production SMTP, hosting, and automated PostgreSQL CI remain unverified. See `PHASE_3_REPORT.md`.

## Phase 4 — Property and listing foundations

- **Goal:** Establish the Kenya location hierarchy and validated property/listing data foundations.
- **Dependencies:** Phases 2–3.
- **Acceptance criteria:** All 47 Kenyan counties and sourced county headquarters; priority towns and neighbourhoods; optional sourced coordinates; location search and hierarchy validation; portable property/media models and KES validation; owner-scoped draft creation/editing; public reads restricted to published, available, non-demo records; explicitly opt-in synthetic test records; Alembic migration, API tests, and documentation. No map integration, media upload, publication moderation, or full marketplace behavior.
- **Status:** Complete. See `PHASE_REPORT.md` and `PHASE_4_REPORT.md`.

## Phase 5 — Google Maps and property location exploration

- **Goal:** Add genuine Google Maps SDK map, satellite, hybrid and terrain modes; search Kenyan areas; explore published property locations and nearby amenities.
- **Dependencies:** Phases 1–4; Google Cloud project, billing, API keys, and signing fingerprints are required to activate live Google services.
- **Acceptance criteria:** Maps Compose integration; restricted external API keys; Kenya-restricted Places search; consent-based device location; sourced-coordinate-only listing markers and clustering; price previews, KES filters and map/list switching; nearby Places search; clear unconfigured/error/empty states; tested backend map filters and Android state; setup documentation and phase report.
- **Status:** Original Phase 5 implementation was completed and later replaced after the owner requested a free provider. The current client uses MapLibre/OpenFreeMap and Nominatim via the HomeScout API; no Google key is needed. OpenFreeMap vector tiles rendered in the Android emulator on 2026-11-24. No satellite/terrain imagery or Google Places results are provided. See `MAPS_SETUP.md` and `EXPERIENCE_REPAIR_REPORT.md`.

## Phase 6 — Property marketplace, search, discovery, and listing management

- **Goal:** Deliver functional property discovery and authorized listing workflows using the actual HomeScout backend.
- **Dependencies:** Phases 1–5; the Phase 6 owner brief.
- **Acceptance criteria:** Search by Kenyan county/town/neighbourhood, rent, bedrooms, property/unit type, furnishing and amenities; sort and persist search history; published-only detail, save, compare, similar-property discovery and map entry; role- and ownership-scoped landlord/agent listing creation, edits, photo upload, preview, availability, publish/archive/delete; enquiries and listing reports; clearly distinguish demo data from eligible inventory; automated API, database/migration, Android build and behavior checks; docs and phase report.
- **Status:** Complete. See `PHASE_6_REPORT.md`.

## Phase 7 — Profile, saved items, activity, schedule, notifications, and personal hub

- **Goal:** Build the owner-scoped HomeScout account and personal hub for assigned user roles.
- **Dependencies:** Phases 1–6 and the owner's Phase 7 brief.
- **Acceptance criteria:** Editable profile and preferences; safe switching among assigned roles; saved items and private/shareable collections; activity history; East Africa Time agenda; in-app notifications and preferences; role-scoped manual records; private documents; help/support tickets; About, accessibility, privacy, export, and reauthenticated deletion-request flows; Android secondary routes within the five-tab shell; tests, documentation, and phase report.
- **Status:** Complete. See `PHASE_7_REPORT.md`.

## Phase 8 — SmartRent financial inclusion and housing planning

- **Goal:** Add private, transparent housing-budget tools and financial learning within the existing five-tab HomeScout shell.
- **Dependencies:** Phases 1–7 and the owner's Phase 8 brief.
- **Acceptance criteria:** Owner-scoped encrypted financial inputs; explainable housing readiness and budgeting; move-in planning; virtual savings goals and simulation; explicit goal sharing; live-listing cost comparison and budget discovery; manual rent records; private-document references; Kenyan financial learning; utility summaries; lease/deposit organizer; in-app alerts; Android finance experience; tests, docs, and phase report. No lending, credit decisions, payment processing, AI provider, or funds custody.
- **Status:** Complete. SQLite and Android build/unit checks passed. PostgreSQL 17 verification is pending because no PostgreSQL 17 service was available. See `PHASE_8_REPORT.md`.

## Phase 9 — Rental safety and trust

- **Goal:** Provide manual verification, rental safety, reporting, and human moderation workflows.
- **Dependencies:** Phases 3–8 and the owner's Phase 9 brief.
- **Acceptance criteria:** Evidence-backed verification; encrypted private uploads; reviewer history/expiry/resubmission; owner-private reports and evidence; permission-gated review queue; non-automatic fraud signals; consent-based safe-viewing sharing/check-in/out; Android Profile secondary route; tests and phase report.
- **Status:** Complete. No external identity or ownership database is integrated. See `PHASE_9_REPORT.md`.

## Phase 10 — Messaging, viewings, house comparison, roommates, and shared searches

- **Goal:** Provide authorized communication and renter collaboration with explicit privacy boundaries.
- **Dependencies:** Phases 3–9 and the owner's Phase 10 brief.
- **Acceptance criteria:** Participant-authorized encrypted messaging, report/block/archive, attachment access checks, host-confirmed viewing lifecycle, history/calendar and in-app updates, private five-home comparisons, opt-in roommate discovery, member-scoped shared searches/tasks/goals, two-party financial consent, private viewing journals with revocable sharing, Android entry points, migration/tests/docs/report.
- **Status:** Complete. SQLite/API tests and Android compile, unit tests, and debug assembly passed. PostgreSQL 17 migration and authenticated emulator flow are not verified. See `PHASE_10_REPORT.md`.

## Phase 11 — Moving services, home services, and provider marketplace

- **Goal:** Connect users with home-service providers and support service requests, moving plans, room setup, and authorized maintenance workflows.
- **Dependencies:** Phases 1–10 and the owner's Phase 11 brief.
- **Acceptance criteria:** Searchable category/county/pricing/approval filters; provider profiles, offerings, service areas and images; comparison and evidence-backed reviews; participant-authorized booking/order lifecycle; private moving checklist, calendar, KES budget and room planning; owner/manager-granted resident maintenance access, assigned-provider access, photos, status history; Android secondary screen; migration, tests, documentation and report.
- **Status:** Complete. SQLite/API tests, Ruff, Android compilation/unit tests/debug assembly passed. PostgreSQL 17 migration check and authenticated emulator walkthrough remain outstanding. See `PHASE_11_REPORT.md`.

## Phase 12 — M-Pesa payments

- **Goal:** Add approved payment flows through M-Pesa Daraja.
- **Dependencies:** Phase 11; provider account, sandbox credentials, and transaction/refund policies.
- **Acceptance criteria:** Backend-held credentials and initiation; verified callbacks; idempotent state transitions; reconciliation and failure paths; sandbox evidence and security review.
- **Status:** Complete for backend-first service-booking STK Push architecture, sandbox/live configuration gates, transaction history, callback verification, idempotency and reconciliation. Daraja sandbox execution and production enablement remain pending owner credentials, callback hosting, merchant authorization and review. See `PHASE_12_REPORT.md`.

## Phase 13 — HomeScout Assistant and contextual intelligence

- **Goal:** Provide a privacy-conscious housing assistant through a server-side configurable AI provider and explicit, permission-checked context.
- **Dependencies:** Phases 1–12; provider credentials, stable encryption key, privacy policy, retention decision, and operational approval before live use.
- **Acceptance criteria:** Server-only provider configuration; consent and privacy controls; encrypted owner-scoped conversation history; per-user rate limits; role-scoped, opt-in context; real public listing facts and property links; no fabricated responses when unavailable; Android assistant screen and relevant entry points; tests, docs, and report.
- **Status:** Complete for architecture, controls, and UI. The provider is disabled until server credentials and encryption key are configured; no live model call was made. Phase 13 tests passed on SQLite; PostgreSQL 17 migration validation and emulator rendering remain outstanding. See `PHASE_13_REPORT.md`.

## Phase 14 — Admin dashboard, moderation, and platform operations

- **Goal:** Provide least-privilege, audited tools for staff support, account/listing/service operations, operational metrics, approved settings, locations, and moderation entry points.
- **Dependencies:** Phases 1–13; operational staff roles and procedures.
- **Acceptance criteria:** Permission-gated operational overview; minimized user records; reauthenticated and audited account restrictions; non-demo listing moderation; existing verification and safety workflows; message and service-review moderation; support assignment/replies/escalation; controlled provider/category/location/settings actions; audit history; Android secondary console; migration, tests, docs, and phase report.
- **Status:** Complete for the authorized operations API and Android console. SQLite backend tests (88 passed), Ruff, Android compilation/unit tests, and debug APK assembly passed. PostgreSQL 17 validation for the Phase 14 migration and an emulator rendering walkthrough were not performed. See `PHASE_14_REPORT.md`.

## Phase 15 — Quality assurance, security, performance, and accessibility

- **Goal:** Review the existing HomeScout application comprehensively, fix critical/high issues within scope, verify supported build/test paths, and document limits without redesigning the application.
- **Dependencies:** Phases 1–14 and the owner-supplied Phase 15 brief.
- **Acceptance criteria:** Backend tests and SQLite migrations; Android compilation, lint, unit tests, debug APK, and emulator smoke checks; security/dependency scans; accessible contrast check; legal/privacy review limits; prioritized remaining risks and detailed report.
- **Status:** Complete for the available local environment. Backend 88 tests, Ruff, SQLite upgrade, Android debug/release compilation and APK builds, debug lint/unit checks, and API 37 emulator primary navigation smoke check passed. Fixed two Android lint errors, moved theme attributes to API-qualified resources, raised target SDK to 36, and corrected status-text contrast. PostgreSQL 17 for Phases 6–14, live providers, authenticated end-to-end UI automation, and production operations remain unverified. See `PHASE_15_REPORT.md`.

## Superseded proposal — Moving services (covered by Phase 11)

- **Goal:** Previously proposed moving-service work.
- **Dependencies:** Superseded by the owner-supplied Phase 11 brief.
- **Acceptance criteria:** Covered by Phase 11 moving plans and moving-provider workflows.
- **Status:** This earlier roadmap proposal was replaced by the owner-authorized Phase 11 implementation. It is not the current Phase 13.

## Superseded proposal — Property services (covered by Phase 11)

- **Goal:** Previously proposed property-service discovery and fulfillment.
- **Dependencies:** Superseded by the owner-supplied Phase 11 brief.
- **Acceptance criteria:** Service catalog/provider lifecycle, requests, maintenance, and authorization are covered by Phase 11.
- **Status:** This earlier roadmap proposal was replaced by the owner-authorized Phase 11 implementation. It is not a separate current phase.

## Superseded proposal — Operations, moderation, and support (originally Phase 15)

- **Goal:** Provide controlled internal operations tools.
- **Dependencies:** Phases 3–14; staff roles and operating procedures.
- **Acceptance criteria:** Least-privilege staff access; audit trail for sensitive actions; moderation/support workflows; privacy controls and operating documentation.
- **Status:** Replaced by the owner-authorized Phase 14 brief and implementation. See `PHASE_14_REPORT.md`.

## Phase 16 — Deployment preparation and competition demonstration

- **Goal:** Prepare, but do not deploy or distribute, HomeScout for a controlled release and competition presentation.
- **Dependencies:** Phases 1–15; owner-selected hosting, PostgreSQL 17, secret management, durable storage, release signing, and provider accounts before live operation.
- **Acceptance criteria:** Deployment guide and non-root container definition; production environment template; Android release signing/HTTPS/API-key preflight; release checklist; honest 25-step demo guide; competition presentation outline; current limitations and launch blockers documented.
- **Status:** Preparation complete. No host, production PostgreSQL, signing key, real provider key, or demo account was configured. No deployment or distribution occurred. PostgreSQL Phase 6–14 migration runs, durable private storage, live Google/Daraja/AI/SMTP tests, and the complete demo remain outstanding. See `PHASE_16_REPORT.md`.

## Phase 17 — Notifications and integrations

- **Goal:** Add approved outbound notifications and externally configured providers where selected and authorized.
- **Dependencies:** Relevant feature phases; vendor selection, consent, credentials, and operating policies.
- **Acceptance criteria:** Preferences and opt-outs; delivery/retry behavior; external secrets remain out of source and client; integration or sandbox evidence.
- **Status:** Not started.

## Superseded proposal — Assistant (covered by Phase 13)

- **Status:** The owner-supplied Phase 13 brief defined and authorized the initial HomeScout Assistant scope. No separate phase is included.

## Phase 18 — Quality, security, and production readiness

- **Goal:** Prepare the authorized MVP for a controlled release.
- **Dependencies:** Implemented MVP features and chosen integrations.
- **Acceptance criteria:** Relevant Android/backend tests; lint/type checks; PostgreSQL 17 migration and recovery evidence; privacy/security review; monitoring, deployment, incident, rollback, and release-build checks.
- **Status:** Not started. Phase 16 preparation does not substitute for PostgreSQL 17 migration/recovery evidence, live integration tests, deployment, or release operations.

## Phase 19 — Pilot and iteration

- **Goal:** Run an approved pilot and use measured feedback to prioritize follow-up.
- **Dependencies:** Phase 18 and explicit pilot authorization.
- **Acceptance criteria:** Defined cohort and success measures; privacy-respecting feedback/incident process; reviewed results and prioritized next changes.
- **Status:** Not started.
