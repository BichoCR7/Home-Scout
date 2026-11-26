# HomeScout API

HomeScout's versioned FastAPI backend includes the foundation, identity and authorization, Kenyan location/property data, marketplace, personal hub, SmartRent, trust/safety, communications/collaboration, moving/home services, Phase 12 M-Pesa transaction APIs, the Phase 13 HomeScout Assistant, and Phase 14 staff operations. It uses environment-backed settings, SQLAlchemy, Alembic, SQLite for local development, and psycopg for the PostgreSQL 17 production target.

Phase 16 deployment preparation is documented in the repository-root `DEPLOYMENT_GUIDE.md`. `Dockerfile` builds a non-root API image; migrations remain a separate release job. The image has not been built or deployed in the current environment.

## Requirements and setup

- Python 3.12 or newer.
- SQLite locally; PostgreSQL 17 is the production target.

```powershell
cd C:\Users\edris\Documents\Codex\HomeScout\backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -e '.[dev]'
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The `.env` file is ignored by Git. For local verification without an SMTP server, set `HOMESCOUT_AUTH_DEV_EXPOSE_TOKENS=true` in a private development `.env`; this makes one-time account action tokens appear in API responses. It is restricted to `development` and `test`, is false by default, and must remain disabled outside isolated local development. A configured SMTP sender can deliver verification and reset codes instead.

## API surface

- `GET /api/v1/health` — liveness.
- `GET /api/v1/health/ready` — database readiness.
- `/api/v1/assistant` — server configuration status, explicit provider-processing consent, owner-private conversation history, and contextual assistant messages. See the HomeScout Assistant section below.
- `POST /api/v1/auth/register` — create an unverified account and record its requested role. Every self-registration receives only the tenant role.
- `POST /api/v1/auth/email/verify` and `POST /api/v1/auth/email/resend` — verify or resend the one-time email code.
- `POST /api/v1/auth/login`, `/refresh`, and `/logout` — sign in, rotate refresh credentials, and revoke the current refresh session.
- `POST /api/v1/auth/password-reset/request` and `/confirm` — generic reset requests and one-time password changes.
- `GET/PATCH /api/v1/auth/me` — read or update the current account profile.
- `GET /api/v1/auth/sessions` and `DELETE /api/v1/auth/sessions/{id}` — list and revoke only the current user’s sessions.
- `/api/v1/admin/roles` and `/api/v1/admin/users` — protected role catalog and basic email-prefix search.
- `POST /api/v1/admin/users/{id}/roles` and `/roles/{code}/revoke` — audited, password-confirmed scoped role changes.
- `/api/v1/admin/operations` — permission-gated platform overview, basic user lookup/status restriction, non-demo listing moderation, service/provider publication and service-review moderation, locations, support queue/detail/assignment/replies/escalation, message-report moderation, support category activation, allow-listed settings, and administrative audit history. See the Phase 14 report for privacy and role limits.
- `GET /api/v1/admin/operations/reviews/services` and `PATCH /reviews/services/{id}/moderation` — staff review queue and audited clear/hold/remove decisions; hidden reviews are omitted from public service-review reads.
- `GET /api/v1/locations/counties`, `/counties/{id}/towns`, `/towns/{id}/neighbourhoods`, and `/locations/search?q=...` — Kenya reference data and hierarchical search.
- `POST /api/v1/locations/towns` and `/locations/neighbourhoods` — add reference locations with `location:manage:global`; coordinate pairs require a source.
- `GET /api/v1/properties` and `/properties/{id}` — public reads for published, available, non-demo properties. Filters include county/town/neighbourhood IDs, location/listing text query, rent, exact/minimum bedrooms, building/unit type, furnishing, repeated amenities, verified-only, map viewport, and sorting. `include_demo=true` explicitly opts into clearly marked synthetic test records; Android map calls never opt into demo rows.
- `GET /api/v1/properties/mine`, `POST /api/v1/properties`, `PATCH /api/v1/properties/{id}`, and `GET /api/v1/properties/{id}/preview` — owner/authorized-agent listing workflows and private preview. Creation starts as a draft and never implies verification.
- `POST /api/v1/properties/{id}/media`, `DELETE /api/v1/properties/{id}/media/{media_id}`, and `GET /api/v1/properties/media/{media_id}` — size-limited JPEG/PNG/WebP uploads, authorized removal, and public-or-authorized retrieval.
- `PATCH /api/v1/properties/{id}/availability`, `POST /publish`, `POST /archive`, and `DELETE /api/v1/properties/{id}` — availability and listing lifecycle. Publishing requires available state and an uploaded, non-illustrative photo; only drafts can be deleted.
- `/api/v1/marketplace/saved`, `/compare`, `/search-history`, and `/alerts` — authenticated save/list, comparison of 2–4 public homes, capped filter history, and saved-search alert records. Alert delivery is not implemented.
- `/api/v1/marketplace/listing-mandates` — landlord grants/revokes scoped authorization for active agent accounts.
- `/api/v1/marketplace/properties/{id}/enquiries`, `/enquiries/sent`, `/enquiries/received`, and `/enquiries/{id}` — authenticated enquiry submission and authorized status workflow.
- `/api/v1/marketplace/properties/{id}/reports` and `/reports/mine` — submit/list own listing reports. `received` means recorded; moderation is handled through the Phase 9 permission-gated queue.
- `/api/v1/trust/safety-guide` and `/trust/indicators/{property_id}` — public safety guidance and property indicators based only on stored verification/account-contact records.
- `/api/v1/trust/verifications/mine`, `POST /verifications`, `/verifications/queue`, and `/verifications/{case_id}/review` — owner-scoped submission/history and authorized manual review, including evidence, expiry, and resubmission.
- `/api/v1/trust/listing-reports/mine`, `/listing-reports/{id}/evidence`, `/moderation/queue`, and `/moderation/{report_type}/{report_id}/review` — private reports/evidence and permission-gated human review/escalation/resolution; listing visibility changes only on an explicit moderator decision.
- `/api/v1/trust/viewings` and `/viewings/{id}/{action}` — private safe-viewing records, explicit consent-based account sharing, check-in/out, and cancellation.
- `/api/v1/trust/safety-reports` and `/safety-reports/mine` — private incident reports and status history.
- `/api/v1/trust/moderation/{report_type}/{report_id}/evidence/{document_id}/download` and `/verifications/{case_id}/evidence/{evidence_id}/download` — audited evidence access for authorized reviewers.
- `/api/v1/hub/profile`, `/profile/photo`, `/profile/active-role`, and `/preferences` — account profile/photo, already-assigned role switching, and personal preferences.
- `/api/v1/hub/saved` and `/collections` — private saved items and collections; collection sharing is explicit and owner-controlled. Shared users only receive access granted to their account.
- `/api/v1/hub/activity`, `/schedule`, and `/notifications` — account-scoped activity/filtering, timezone-aware agenda entries, and in-app notification read/dismiss controls.
- `/api/v1/hub/records` — user-entered KES notes; records do not establish completed payments.
- `/api/v1/hub/documents` — authenticated private document upload/list/download/delete.
- `/api/v1/hub/support/articles` and `/support/tickets` — help search and account-owned support ticket history/replies; no staff queue is included.
- `/api/v1/hub/account/export` and `/account/deletion-requests` — account export and password-reauthenticated pending deletion requests.
- `/api/v1/finance/profile`, `/assessment`, `/rent-score`, `/health-check`, `/dashboard`, and `/coach` — owner-scoped budget inputs, transparent housing-planning estimates, private summary, and deterministic budget tips.
- `/api/v1/finance/discovery`, `/move-in/plans`, `/savings/goals`, `/savings/simulate`, `/comparisons`, and `/utilities/estimate` — budget-based published listing discovery, move-in cost plans, virtual savings trackers and simulations, live-listing comparisons with user-entered costs, and summaries of user-entered utility values.
- `/api/v1/finance/records`, `/lessons`, `/lease-guardian`, and `/alerts` — private manual housing notes, lessons/quizzes/progress, lease/deposit organization, and in-app alerts. Manual payment notes do not confirm payments; goal contributions are virtual records only.
- `/api/v1/communications/inbox` and `/communications/property-enquiries/{id}/conversation`, `/roommate-interests/{id}/conversation`, `/groups/{id}/conversation` — participant inbox and relationship-gated direct/group conversation access.
- `/api/v1/communications/conversations/{id}/messages`, `/archive`, `/communications/blocks`, `/communications/blocks/{user_id}`, `/communications/messages/{id}/reports`, and `/messages/{message_id}/attachments/{document_id}` — encrypted history/send, archive, current block list and block/unblock, report, and participant-authorized retrieval of linked private documents.
- `/api/v1/viewings/requests`, `/viewings/calendar`, `/viewings/{id}/actions`, and `/viewings/journals` — host-confirmed request/calendar/status transitions, private viewing journal CRUD, explicit share/revoke, and owner/authorized-recipient photo reads.
- `/api/v1/comparisons` — private comparison board CRUD for up to five eligible published homes with encrypted user-entered cost and note fields.
- `/api/v1/roommates/me`, `/roommates/suggestions`, and `/roommates/interests` — opt-in profile, filtered suggestions with limited candidate data, and connection requests/acceptance.
- `/api/v1/collaboration/groups` and `/collaboration/groups/{id}/...` — invited memberships, shared filters/homes/votes/comments/comparisons/tasks/moving goals and per-member financial consent. Group records are returned only to active members; membership sharing can be revoked.
- `GET /api/v1/payments/configuration` — public non-secret enabled/mode/purpose status.
- `POST /api/v1/payments/service-bookings` — idempotent payer-owned STK request for an accepted fixed-price service order; requires `Idempotency-Key` and tenant/roommate permission.
- `GET /api/v1/payments/me`, `GET /payments/{id}`, and `POST /payments/{id}/reconcile` — payer-only history/detail/status query. An STK prompt or API response never means successful payment.
- `GET /api/v1/payments/provider-orders` — provider's own order payment status without payer phone or receipt details.
- `GET /api/v1/payments/reconciliation-queue` — admin/super-admin view of pending/ambiguous transaction summaries.
- `POST /api/v1/payments/daraja/callback` — bounded, schema-validated, idempotent callback processing followed by authenticated server-side Daraja STK Query.
- `/docs` and `/openapi.json` — available in development; disabled in staging and production.

The migration seeds all 47 counties, county headquarters, and the Phase 4 priority towns/neighbourhoods. It intentionally stores no coordinates for those rows because no coordinate source was recorded. Test-only synthetic property fixtures use KES, remain draft/unverified/availability-unknown, and use illustrative stock imagery. They are not automatically inserted into development or production databases.

Authentication uses Argon2id password hashes, short-lived HS256 access tokens, database-backed revocable sessions, and random high-entropy refresh/action tokens stored as SHA-256 verifiers. Refresh credentials rotate after use. Role checks are server-side and deny by default. Self-registration can request an operational role, but this is recorded as a request and never grants that role. Scoped assignments restrict staff-granted operational roles. Role changes require an active verified target, reauthentication, and an audit record; an operator cannot change their own roles.

## First Super Admin

After applying migrations, create the first administrator interactively:

```powershell
.\.venv\Scripts\python.exe -m app.cli create-super-admin --email admin@example.com
```

The CLI prompts for a password without echoing it or accepting it as a command argument. It refuses to create another bootstrap Super Admin after one exists. Subsequent changes use the audited role-management API.

## Environment and production configuration

All backend settings use the `HOMESCOUT_` prefix. Staging and production require:

- a PostgreSQL URL in production;
- a stable authentication signing key of at least 32 bytes, supplied through a secret manager;
- a stable URL-safe base64 finance encryption key that decodes to exactly 32 bytes, supplied through a secret manager;
- a separate stable URL-safe base64 trust encryption key that decodes to exactly 32 bytes, supplied through a secret manager;
- a separate stable URL-safe base64 message encryption key that decodes to exactly 32 bytes, supplied through a secret manager;
- an SMTP host and sender address with STARTTLS enabled;
- matching SMTP username and password values if authenticated SMTP is used.

Never commit `.env`, signing keys, database credentials, SMTP credentials, passwords, refresh tokens, or email action tokens. The Android app receives only an API base address, not backend secrets. SMTP delivery was not tested against a real provider because no provider credentials were supplied.

SmartRent endpoints need `HOMESCOUT_FINANCE_ENCRYPTION_KEY` configured in development to read/write private finance payloads; staging and production reject startup without it. Generate a 32-byte key once and store the same stable value in the environment/secret manager:

```powershell
py -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

The generated value is a secret. Do not paste it into source control, chat, Android configuration, logs, or API responses. Back it up using the organization's secret-management procedure: losing it makes encrypted finance payloads unreadable. Rotating it requires an explicit re-encryption plan; simply replacing the key does not decrypt existing records.

Trust verification uploads, report narratives, and private viewing details use `HOMESCOUT_TRUST_ENCRYPTION_KEY`. It may be absent at development startup, but encrypted trust operations fail closed until configured; staging and production require it. Generate a distinct 32-byte key with the same command above; do not reuse the finance key. Losing it makes encrypted trust records unreadable, so define key custody, backup, and re-encryption before production. Internal moderation notes are stored as plaintext in the development database, omitted from API responses, and have no moderation-history read endpoint in this phase.

Property uploads use `HOMESCOUT_MEDIA_STORAGE_DIR` (default: `backend/var/property-media`) and `HOMESCOUT_MEDIA_MAX_IMAGE_BYTES` (development default: 10 MiB). `LocalMediaStorage` confines generated object keys to that directory and does not expose the filesystem path through API responses. This is a development storage backend. Configure durable private object storage, access policy, backups, scanning, and lifecycle rules before production.

Private profile photos and personal documents use `HOMESCOUT_PRIVATE_DOCUMENT_STORAGE_DIR` (default: `./var/private-documents`) and `HOMESCOUT_PRIVATE_DOCUMENT_MAX_BYTES` (default: 15 MiB). Uploads use generated keys and allowed file-signature checks; document download and delete require the owning account. Phase 9 verification and trust evidence bytes are AES-GCM encrypted at rest; owners and authorized reviewers receive decrypted downloads, with reviewer reads audited. Other personal documents remain unencrypted at rest in development storage. The configured local directory is for development. Production storage, managed key custody, malware scanning, backups, retention, and access lifecycle need a managed solution and operational policy.

## M-Pesa Daraja setup

Daraja is backend-only and **disabled by default**. The app never contains a Daraja consumer key, consumer secret, shortcode passkey, or phone-hash key. Use the [Safaricom Daraja Developers Portal](https://developer.safaricom.co.ke/) to create a sandbox app and review its current app-specific STK Push/STK Query contract before sending a request. The portal documents sandbox app creation/testing and developer onboarding. Its live API pages are dynamic; the endpoint and field assumptions in this client still need validation against the selected app's current documentation.

Set values only in the backend environment/secret manager, not source control:

- `HOMESCOUT_MPESA_ENABLED=true`
- `HOMESCOUT_MPESA_ENVIRONMENT=sandbox` for development, or `production` only in a production deployment.
- `HOMESCOUT_MPESA_TRANSACTION_TYPE=CustomerPayBillOnline` for a PayBill shortcode or `CustomerBuyGoodsOnline` for a Till, as provided by Safaricom for the selected merchant.
- `HOMESCOUT_MPESA_CONSUMER_KEY`, `HOMESCOUT_MPESA_CONSUMER_SECRET`, `HOMESCOUT_MPESA_BUSINESS_SHORTCODE`, and `HOMESCOUT_MPESA_PASSKEY` from the selected Daraja app/merchant.
- `HOMESCOUT_MPESA_CALLBACK_BASE_URL` as a public HTTPS origin/path reachable by Safaricom. The backend appends `/api/v1/payments/daraja/callback`; do not add this suffix twice.
- `HOMESCOUT_MPESA_PHONE_HASH_KEY` as an independently generated random secret with at least 32 bytes; it HMACs the submitted MSISDN and callback payload digest.
- `HOMESCOUT_MPESA_SERVICE_COLLECTION_AUTHORIZED=true` only after explicit merchant/business/legal approval for HomeScout to collect the specified service-order payments. Production mode requires it.
- `HOMESCOUT_MPESA_REQUEST_TIMEOUT_SECONDS` and `HOMESCOUT_MPESA_RECONCILIATION_COOLDOWN_SECONDS` for bounded calls and status checks.

Use Daraja sandbox credentials and sandbox shortcode/passkey to test, with an HTTPS callback accessible from the internet (localhost is not reachable by Safaricom). Production requires the Safaricom merchant onboarding/go-live process, production app keys and shortcode/passkey, a stable public HTTPS callback, restricted secret-manager access, monitoring, reconciliation, merchant settlement controls, and explicit approved use cases. Never use production keys in local development. Merchant onboarding, fees, and settlement terms depend on the business agreement; confirm them with Safaricom rather than assuming terms.

The implemented purpose is limited to an accepted customer-owned service booking with a fixed whole-KES amount. HomeScout does not collect rent, hold funds in escrow, transfer provider payouts, or initiate refunds/reversals. Callbacks are untrusted, matched to a pending checkout, deduplicated, and checked using authenticated STK Query before state changes. Ambiguous submission timeouts remain pending and are not automatically retried. A provider receipt is displayed only when verified transaction data contains one. `reversed` is stored only if an authenticated provider status explicitly reports reversal; reversal/refund initiation is not included.

## Android API address

Set the Gradle property `homescout.apiBaseUrl` or environment variable `HOMESCOUT_API_BASE_URL`; the Gradle property takes precedence. For a local Android emulator only:

```powershell
$env:HOMESCOUT_API_BASE_URL = 'http://10.0.2.2:8000'
```

Debug builds allow HTTP for local emulator development. Release builds keep Android’s platform cleartext defaults; configure HTTPS endpoints for release. `BuildConfig.API_BASE_URL` is read only through `data/remote/ApiConfiguration.kt`.

## Tests and lint

Run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check app tests migrations
.\.venv\Scripts\python.exe -m ruff format --check app tests migrations
```

Tests cover health/API behavior, settings, database/migration lifecycle, account and scoped authorization, location/property and marketplace behavior, personal-hub access, SmartRent encryption/calculations, Phase 9 verification/review/safety, Phase 10 collaboration privacy, Phase 11 services/booking/moving/maintenance, Phase 12 payment idempotency/callback verification/reconciliation/privacy, Phase 13 Assistant configuration/consent/encrypted history/context/failure behavior, and Phase 14 staff authorization, support privacy, account restrictions, listing and service-review moderation, settings, audit, and verification integration. Phases 6–14 migration coverage runs on SQLite.

Phase 10 message bodies and selected collaboration payloads use `HOMESCOUT_MESSAGE_ENCRYPTION_KEY`, a distinct environment-held URL-safe base64 key that decodes to 32 bytes. Staging/production startup requires this key; local protected operations fail closed if it is absent. For local development, keep its generated value stable in the ignored `backend/.env` and restart Uvicorn after changing it. Back it up under a key-custody procedure. Loss makes encrypted Phase 10 data unreadable; changing it requires an explicit re-encryption plan. Do not reuse the finance or trust key. In development, linked private-document attachment files and journal photos use the Phase 7 local document store and are not encrypted by this Phase 10 payload cipher. Messages are encrypted at rest but are not end-to-end encrypted. Push/email delivery, a moderation queue for message reports, and voice-note recording/upload are not included. Apply the schema with `python -m alembic upgrade head`.

## PostgreSQL 17 status

Models and Alembic migrations use portable UUID, JSON, constraints, and SQLAlchemy operations. SQLite migration and behavior tests pass through Phase 14. PostgreSQL 17.12 validation on 2026-11-23 passed for the migration chain through Phase 4: populated upgrade/downgrade/re-upgrade, county data, location search, landlord drafts, public exclusion, and illustrative media. The Phase 6–14 migrations have not yet been run on PostgreSQL 17. PostgreSQL 16 and 18 Windows services are present in the current environment, but neither was used as a substitute. Phase 2/3 health and identity API checks are documented in `PHASE_3_REPORT.md`. Production-host, backup/restore, Phases 6–14 PostgreSQL migrations, and automated PostgreSQL CI runs remain unverified.

## Phase 9 trust and safety

The versioned trust API provides:

- Public safety guidance and property trust indicators derived from stored records only.
- Owner-scoped verification submissions for landlords, agents, service providers, and properties. Submissions require uploaded evidence and enter a manual review queue. Authorized administrators approve/reject, record a private reason, and may set expiry; rejected cases can be resubmitted. This is an internal HomeScout review, not third-party identity, title, tenancy, or license verification.
- Owner-private listing and safety reports with encrypted details and evidence references. Authorized reviewers can review, escalate, resolve, dismiss, and explicitly hide/restore/remove a reported listing. Report allegations alone do not alter a user's standing or property visibility.
- Exact normalized-address duplicates and rent outliers as review prompts only; these do not automatically label, restrict, or remove a user/listing.
- Owner-private safe-viewing plans with trusted-contact data, optional explicit sharing with a selected HomeScout account, status transitions/check-in/out, and incident reporting. No external message or reminder delivery is included.

Configure `HOMESCOUT_TRUST_ENCRYPTION_KEY` in `backend/.env` for local trust writes and reads. Startup permits it to be absent in development, but encrypted trust operations fail closed until set; staging and production require it. Generate a URL-safe base64 32-byte key with the same command documented for the finance key, store a distinct stable key in a secret manager, and back it up under an approved key-custody process. Losing it makes encrypted trust data unreadable. Do not put it in Android or source control.

Run the schema migration with `python -m alembic upgrade head`. Phase 9 creates verification, evidence, history, safe-viewing, incident, report-review, and trust-evidence tables and extends property/report/document records. Phase 9–14 migration and workflow coverage runs on SQLite; PostgreSQL 17 verification for Phases 6–14 remains outstanding.

## Phase 10 communications and collaboration

Migration `dd6548872d4f` adds relationship-gated conversations and encrypted message bodies, participant/attachment/report/block state, host-confirmed viewing requests/history, encrypted private viewing journals with photo references and revocable shares, private comparison boards, opt-in roommate profiles/interests, and shared search groups with votes, comments, tasks, comparisons, moving goals, and member financial consent. Messages can start only from a property enquiry, accepted roommate connection, or group membership. Every protected read/write checks current participant, owner, or group-member access. Message sends are rate-limited to 30 in five minutes per account. Viewing status remains `requested` until the assigned host confirms.

The Android collaboration screen is available from Profile and property details. It uses existing in-app notifications and schedule entries; no push/email transport or background reminder delivery is implemented. Optional free-text message-report details are stored unencrypted, and report intake has no Phase 10 moderation queue. Voice-note file capture/upload and PostgreSQL 17 checks for this migration are not included. Phase 10 migration and behavior tests run on SQLite.

## Phase 11 services, bookings, moving, and maintenance

The service API lives under `/api/v1/services`:

- `GET /offerings`, `/offerings/compare`, `/offerings/{service_id}`, and `/offerings/{service_id}/reviews` — public service discovery, comparisons, and reviews. Filters include text, category, county/town, KES price range, approval-record state, and sort order.
- `/providers/me`, `/providers/me/offerings`, and `/providers/me/images` — authenticated provider profile, offering, and provider-image management. Public provider routes return only published profiles and active offerings. Approval is derived from current HomeScout review records, not from a third-party check.
- `POST /bookings`, `GET /bookings`, `/bookings/{id}/history`, and `PATCH /bookings/{id}` — create a pending request and manage customer/provider lifecycle actions. Access is limited to the customer and provider. The provider can accept, reject, propose another time, and complete; customers can accept/decline reschedules and cancel within the allowed state transitions.
- `/orders` and `/bookings/{id}/review` — participant-scoped order summaries and one review by the customer after completion. Order amounts are estimates/records only and are not payment transactions.
- `/properties/{property_id}/residents` and `/resident-properties` — owner/authorized-manager grants and resident view of properties where an active grant exists. A property ID alone never grants resident access.
- `/maintenance`, `/maintenance/{id}`, `/maintenance/{id}/assignment`, `/maintenance/{id}/actions`, and `/maintenance/{id}/photos/{document_id}` — tenant requests and photos, manager-authorized assignment, participant-scoped status/history, and assigned-provider access. Resident grant revocation also blocks reads of previous related records.
- `/move-plans`, `/move-plans/{id}/tasks`, `/move-calendar`, `/move-plans/{id}/budget`, and `/move-plans/{id}/room-setup` — owner-private task/deadline, calendar, KES planning budget, and furniture setup records.

Migration `74f53d9373ba` adds provider profiles, offerings, county/town service areas, images, bookings/events, orders, reviews, resident access, maintenance records/photos/history, and private move plan/task/budget/room setup records. It also adds least-privilege role permissions. The Android app exposes the workflow through a secondary Services destination; the five primary tabs are unchanged. Provider images use the existing local development media store and maintenance images use the Phase 7 private document store. No remote push/email/calendar worker, live provider feed, payment provider, or production object store is configured. Run `python -m alembic upgrade head` to apply the migration. PostgreSQL 17 validation and authenticated emulator inspection for Phase 11 have not been performed; see `PHASE_11_REPORT.md`.

## Phase 13 HomeScout Assistant

The Assistant API is under `/api/v1/assistant`:

- `GET /configuration` reports only whether the provider is configured and the current privacy notice/version; it never returns a secret.
- `GET/PUT /privacy` reads, grants, or withdraws the account's consent to send selected prompts/context to the configured provider. Consent must match the active policy and provider configuration.
- `GET /conversations`, `GET /conversations/{id}`, `PATCH /conversations/{id}`, and `DELETE /conversations/{id}` list, read, rename, and delete only the signed-in owner's history.
- `POST /messages` calls the configured provider only after consent and permission checks. It accepts an intent, an optional public property/comparison selection, and optional saved-property, finance, schedule, work, or active shared-search context.

Provider calls stay on FastAPI. The implemented adapter supports OpenAI-compatible Responses API and Chat Completions protocols. For the OpenAI Responses API, the request sets `store: false`; provider retention and data-use terms still depend on the selected provider/account and must be reviewed. Use the provider's current official API documentation and data-processing terms before configuring production.

The local default is intentionally unavailable. To configure a development provider, set these values only in `backend/.env` or a private environment/secret manager:

```dotenv
HOMESCOUT_AI_ENABLED=true
HOMESCOUT_AI_PROVIDER=openai_compatible
HOMESCOUT_AI_API_PROTOCOL=responses
HOMESCOUT_AI_API_BASE_URL=https://api.openai.com/v1
HOMESCOUT_AI_MODEL=<provider-approved-model-id>
HOMESCOUT_AI_API_KEY=<server-side-secret>
HOMESCOUT_AI_ENCRYPTION_KEY=<stable-url-safe-base64-32-byte-key>
HOMESCOUT_AI_REQUEST_TIMEOUT_SECONDS=30
HOMESCOUT_AI_REQUESTS_PER_MINUTE=10
HOMESCOUT_AI_HISTORY_MESSAGES=16
```

Use `chat_completions` only when the selected compatible provider supports that protocol. A local HTTP endpoint is allowed only for loopback development; staging and production require HTTPS. The key field accepts any string as the provider credential. Generate the separate conversation encryption key with a trusted Python installation using `python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`. Store the resulting value in the backend secret store, never in Android, Gradle properties shipped with the APK, logs, or source control. Keep it stable and backed up under an approved key-custody process; loss makes saved assistant conversations unreadable. Key rotation requires re-encryption planning.

Apply migration `c13a7f08e3b1` using `python -m alembic upgrade head`. It creates owner-scoped consent, conversations, encrypted messages, and per-user rate-window records, and adds `assistant:use:self` and `assistant:history:self` grants. Context is off by default. Available context is limited to public current listings, the user's own saved homes, that user's SmartRent and moving records, schedule items and participant viewings, owner/assigned work and participant bookings, and shared-search records when the account is an active member. Private messages, private journals, unrelated member profiles, and another user's private records are not included. Work, finance, schedule, saved-home, and group context options are explicit for each request.

The configured provider receives the user prompt, bounded same-conversation history, and only the selected context. Encrypted history is AES-GCM protected at rest with authenticated user/conversation/message identifiers. Encryption at rest is not end-to-end encryption: the server decrypts authorized history for provider calls. The per-user default request cap is 10/minute. Input, history, provider response size, timeout, and output length are bounded. On provider/configuration failure, the API returns an unavailable/error state and does not save the new prompt or invent a reply.

The Android app contains no AI key. The global `Ask HomeScout` action and Home, public property details, SmartRent, Profile, and Help entry points all navigate to the secondary Assistant screen. It keeps the permanent Home, Discover, Areas, Finance, and Profile tabs. No assistant call is made until the user has accepted the displayed notice and sends a message. Review privacy/retention terms, provider data terms, and the user notice before enabling real users. No live provider call was made during Phase 13; SQLite migration/tests passed, while PostgreSQL 17 migration validation remains outstanding.

## Phase 14 platform operations

Staff controls are available under `/api/v1/admin/operations`; apply the latest migration using the standard `python -m alembic upgrade head` command. Endpoint permissions come from active role assignments and are checked by the API, regardless of what the Android console displays. Account restrictions require the operator's current password, cannot target the operator, protect administrative accounts, and revoke active sessions when suspending an account. Platform settings use an allow-list and require the Super Admin capability. Message-report detail access is audited; staff queue responses omit message bodies. Support queue summaries also omit ticket messages until an authorized, audited detail request.

The operations overview counts current operational records, including service-review holds, and excludes demo listings; it does not expose personal finance data or imply platform-wide profitability. Verification and property/safety report moderation remain in the previously authorized Trust & Safety flows, accessible from the Android Operations console. The Phase 14 migration and tests have been validated on SQLite only; PostgreSQL 17 validation remains outstanding. See `PHASE_14_REPORT.md`.
