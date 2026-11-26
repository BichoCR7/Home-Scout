# HomeScout Kenya — Phase 7 Report

**Phase:** 7 — User profile, saved items, activity, schedule, notifications, and personal hub  
**Date:** 2026-11-23  
**Status:** Implementation complete for the authorized Phase 7 scope.  
**Product name:** HomeScout.

## Scope delivered

### Account profile and settings

- Added authenticated profile reads and edits for name, phone, location, and bio, plus private profile-photo upload/read. Profile output includes the account ID, assigned roles, active role, and explicit email/phone verification state.
- Added appearance, notification, and accessibility preferences. The app applies light/dark appearance and larger-text preferences through its existing theme controls.
- Added active-role switching limited to roles already granted by an authorized operator. This is a switch between assignments; it does not create or approve a new role.
- Added account-data export and a password-reauthenticated account-deletion request. A deletion request remains pending for an operational processor; it does not erase data immediately.

### Saved items, collections, and activity

- Added persistent personal saves for properties, searches, neighbourhoods, service providers, financial lessons, and comparisons, with notes and collection assignment. Property saves and marketplace searches remain connected to their existing account-backed records.
- Added create/edit/delete for personal collections and explicit collection sharing. Owners can see and revoke share access; shared users receive only their allowed read/edit capability. Collection create/edit responses now match read responses for owner edit and sharing metadata.
- Added saved-search list, edit, delete, alert enablement, search-history display/clear, and reopening of saved search filters in Discover.
- Added account-scoped activity history, filters, date-range selection, continuation actions, and clear-history controls. Marketplace saves, searches, comparisons, enquiries, reports, property details, schedule entries, and relevant account actions feed the activity timeline where supported.

### Schedule, notifications, and records

- Added personal schedule entries with day/week/month agenda views, create/edit/reschedule, completion, delete, appointment/task categories, explicit timezone handling, and Africa/Nairobi defaults.
- Added in-app notification filters, read, read-all, dismiss, and preferences, with direct navigation for supported routes.
- Added user-entered KES records with categories validated against the user's assigned roles. Records are labeled as user-entered and do not prove that a payment was processed.

### Private documents, support, and the Android hub

- Added authenticated document upload/list/download/delete with private local storage, a configurable size limit, and file signature/type validation.
- Added searchable help articles, support ticket creation/history/replies, feedback/report-a-problem entry points, About, privacy/accessibility preferences, data export, and account-deletion request controls.
- Added Profile secondary routes for profile, saved items, collection details, activity, schedule, notifications, records, documents, support, About, assistant placeholder, and settings. Role-aware controls retain existing authorized listing-management and restricted admin routes.
- Kept the five permanent tabs: Home, Discover, Areas, Finance, and Profile. The AI Support Assistant is clearly inactive; it does not claim AI responses.

## Backend and migration

- Added modular SQLAlchemy entities and APIs for preferences, saved hub items, collections/shares, activity, schedule entries, documents, manual records, support tickets/messages, and deletion requests. Extended profiles and in-app notifications with fields needed by the personal hub.
- Added Alembic migration `235804d0dd81_add_personal_hub_private_records_and_`. The migration and tests use portable SQLAlchemy types and were validated on SQLite.
- All hub APIs require a valid account session. Personal records are scoped to their owner; shared collections are the only explicit cross-account read/edit path. User role switching is restricted to existing assignments. Deletion requests require password confirmation.
- Added central settings `HOMESCOUT_PRIVATE_DOCUMENT_STORAGE_DIR` (default `./var/private-documents`) and `HOMESCOUT_PRIVATE_DOCUMENT_MAX_BYTES` (default 15 MiB). Files use generated private keys and are served only after ownership checks.

## Validation

- Backend Pytest: **49 passed**. One upstream Starlette/httpx test-client deprecation warning was emitted.
- Ruff lint: passed. Ruff format check: passed; 85 backend Python files already formatted.
- Coverage includes profile/preferences/role assignments/export, private and shared collections, owner-versus-viewer collection metadata and access, schedule timezone/ownership/validation, private document type and ownership, manual KES records, support ticket ownership, activity isolation, notification ownership, and reauthenticated deletion requests. Existing migration tests include the Phase 7 upgrade path on SQLite.
- Android `:app:testDebugUnitTest` and `:app:assembleDebug`: passed against final Phase 7 source. Gradle compiled the Compose application, ran the four existing map/query unit tests, and produced the debug APK.
- Android build emitted the existing toolchain warnings: Gradle 8.13 is deprecated for a future Kotlin plugin, and AGP 8.13.2 has not been validated by Android tooling against compile SDK 37. The build itself succeeded.
- No emulator/device interaction or responsive visual rendering check was performed for this phase. PostgreSQL 17 has not been used to apply the Phase 6 or Phase 7 migrations.

## Limits and follow-up

- Schedule reminder times are stored as preferences; there is no scheduler or reminder delivery worker. In-app notification persistence and user controls exist, but external push/email and automatic event producers for future feature phases are not implemented.
- Private documents and profile photos use development local disk storage. Production object storage, encryption/key management, malware scanning, backup, retention, and access lifecycle still need configuration and operational review.
- Support ticket intake and account history are available; staff support queue, staffing process, and response-time commitments are outside this phase.
- Manual KES entries are personal notes only. Payment processing, provider-confirmed receipts, and service orders remain outside this phase.
- Account deletion is a reauthenticated request that stays pending; automated deletion and retention handling are not included.
- The AI Assistant is an inactive placeholder. No AI provider, data processing, terms, or legal/privacy promises were added.
- Collections and user documents are private by default. Collection sharing is explicit; full collaboration management beyond the recorded owner/recipient permissions is not included.
- PostgreSQL 17 checks recorded for earlier phases cover Phases 2–4 only. Phase 6 and Phase 7 schema migrations still need PostgreSQL 17 verification. Production hosting, backup/restore, and automated PostgreSQL CI are also unverified.
- Existing Home/Discover sample content remains illustrative. No live inventory, confirmed payments, external notifications, or production document storage is claimed.

## Stop point

Phase 7 is complete. Do not begin Phase 8 or another phase until the owner authorizes it.
