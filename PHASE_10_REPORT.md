# HomeScout Phase 10 Report

**Phase:** Messaging, viewings, house comparison, roommates, and shared searches  
**Status:** Complete. Stop here; do not begin Phase 11 without owner authorization.  
**Product name:** HomeScout

## Delivered

- Added authenticated conversations for existing property enquiries, accepted roommate connections, and active shared-search groups. Server checks participant status and relationship on reads and writes. Message bodies use AES-GCM encryption at rest with a dedicated environment key; messages have timestamps, participant unread state, archive, blocking/unblocking, reporting, attachment references, in-app notification records, audit entries, and a limit of 30 sends per user per five minutes.
- Added attachment access only through the owning conversation and linked private-document record. Android can attach IDs from the user's existing private documents; this reuses Phase 7's development storage, and the underlying bytes are not encrypted by the Phase 10 message cipher.
- Added viewing requests, host confirmation, host-proposed rescheduling, renter acceptance/decline, cancellation, completion, status history, schedule entries, and in-app updates. A request remains pending until the assigned property host confirms it.
- Added owner-private comparison boards for up to five eligible published, available, non-demo homes. Comparison records include grounded listing information (rent/deposit, location, bedrooms/bathrooms, known size, furnishing, amenities, recorded utilities/security) and estimated move-in cost only when its inputs are known. User notes/cost inputs are encrypted. Transport information remains unavailable where no sourced data exists.
- Added opt-in roommate profiles with budget, area, lifestyle, and move-in timing preferences; filtered suggestions; connection interest and acceptance. Suggestions omit direct contact details. Messaging begins only after the connection is accepted.
- Added shared-search groups with invitations and revocable membership, shared filters and homes, votes, comments, group comparisons, tasks, moving goals, and in-app group messages. Financial goal amounts remain hidden from members until each member gives explicit consent; consent can be revoked.
- Added owner-private encrypted viewing journals with notes, pros/cons, rating, follow-up, checklist, and references to private photos. Journal access can be granted to a selected account and revoked by the owner.
- Added the Android Collaboration screen under Profile, property-detail routes for viewing and comparison, and entry points for messaging and shared housing plans. The existing five primary tabs remain unchanged.
- Added migration `dd6548872d4f`, Phase 10 API/services/schemas/tests, environment key validation, and project documentation.

## Verification

- Backend full suite: **61 passed**. One upstream Starlette/httpx test-client deprecation warning was emitted.
- Ruff check and format checks passed for all backend application code, tests, and migrations.
- SQLite migration `dd6548872d4f` is the active Alembic head; the full suite exercised migration lifecycle and Phase 10 API behavior.
- Android `:app:compileDebugKotlin`, `:app:testDebugUnitTest`, and `:app:assembleDebug` passed.
- The Android build displayed existing advisory warnings about Gradle 8.13 deprecation and Android Gradle Plugin 8.13.2 not having been tested against compile SDK 37. These did not fail compilation or assembly.
- No authenticated emulator walkthrough was performed. PostgreSQL 17 migration/behavior checks were not run for this phase.

## Configuration and limits

- Set `HOMESCOUT_MESSAGE_ENCRYPTION_KEY` to a stable, distinct URL-safe base64 secret decoding to exactly 32 bytes. Staging and production startup require it; Phase 10 private operations fail closed without it. Keep it out of Android and source control, back it up securely, and define rotation/re-encryption before production. Losing the key makes protected Phase 10 payloads unreadable.
- Message encryption is server-side encryption at rest, not end-to-end encryption. The API decrypts message bodies for authorized participants.
- Message-report category and optional free-text details are stored in the Phase 10 report record; report detail is not encrypted by the message-body cipher. The report endpoint acknowledges receipt, but Phase 10 does not add a message-report moderation queue.
- Message attachment files and viewing-journal photo files use the existing development private-document store and are not encrypted by the Phase 10 content cipher. Production requires managed private storage, key custody, backups, scanning, and retention controls.
- Notifications and viewing schedule records are in-app only. Push/email delivery, background reminders, SMS, and delivery-failure handling are not implemented.
- Voice-note capture/upload is not implemented. Journal photos are supported through private-document references.
- Roommate suggestions use opt-in profiles and basic user-provided filters; they are not a compatibility guarantee or background matchmaking service. No email/phone is exposed in suggestion results.
- Service-provider messaging has no separate provider marketplace flow yet; communication is available only through current authorized relationship types.
- PostgreSQL 17 verification for Phase 10 is outstanding. PostgreSQL 17.12 checks on record cover Phases 2–4; the feature migrations for Phases 6–10 still need a PostgreSQL run.
- No GitHub push was made.

## Changed areas

- Backend: Phase 10 models, encrypted payload service, schemas, communications/viewing/collaboration services and routers, RBAC grants, Alembic migration, tests, environment setting, and setup/API documentation.
- Android: secondary collaboration screen, Profile and property-detail navigation, comparison/viewing entry points, and in-app collaboration actions.
- Documentation: README, project context, architecture, roadmap, tasks, decision log, changelog, backend README, and current phase report.
