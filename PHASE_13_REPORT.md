# HomeScout Kenya — Phase 13 Report

**Phase:** 13 — HomeScout Assistant, housing guidance, and contextual intelligence  
**Status:** Complete for the authorized backend architecture, consent/privacy controls, and Android application entry points.  
**Boundary:** Phase 13 only. Stop here.

## Delivered

- Added a modular FastAPI Assistant service with a server-only, configurable OpenAI-compatible Responses API or Chat Completions adapter. Provider configuration is environment-based and the feature is disabled by default.
- Added versioned processing consent, a privacy notice, explicit context controls, owner-only conversation history, rename/delete, consent withdrawal, per-account rate limiting, bounded request/history/output sizes, and neutral provider-error handling.
- Added AES-GCM encryption for conversation titles and message bodies with user/conversation/message-bound associated data. Provider keys are `SecretStr` settings and are never returned by the configuration endpoint or included in Android.
- Added the Phase 13 Alembic migration `c13a7f08e3b1` for consent, conversations, messages, and per-user rate windows, plus role-scoped `assistant:use:self` and `assistant:history:self` permissions.
- Added typed intents for property search/explanation/comparison, SmartRent budgeting and affordability, move-in cost and savings planning, financial learning, viewing preparation, lease explanation, scam awareness, neighbourhood discovery, moving/schedule assistance, app navigation, role-specific work support, shared house hunting, irregular-income budgeting, RentScore explanation, and property-cost explanations.
- Added permission-checked data context for published available homes; the user's own saved homes, SmartRent data, schedules/viewings; owned or assigned listings and participant bookings; owner moving plans/tasks; and shared-search facts when the user is an active group member. All private context is off by default. Private messages, private journals, and other members' private profiles are not sent.
- Added the Android conversation screen with consent, privacy/history controls, new/rename/delete actions, context selection, group selection, loading/error/unavailable/sign-in states, and contextual property/application links. The Assistant is available from the global action and Home, public property details, SmartRent, Profile, and Help. Home, Discover, Areas, Finance, and Profile remain the five bottom tabs.
- Updated project setup, architecture, decisions, task tracking, changelog, roadmap, and phase reports using the HomeScout product name.

## Configuration before live use

The current local setup has **no provider credentials, model selection, or Assistant encryption key**, so it cannot generate replies. No live provider request was made. Configure the following in `backend/.env` for local development or, preferably, through a private server environment/secret manager:

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

To create a random 32-byte URL-safe base64 key, run this locally and store its output in the backend secret store:

```powershell
python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Never put either secret in Android, the APK, source control, or logs. Keep the encryption key stable and backed up securely; losing it makes stored Assistant conversations unreadable. Key rotation needs a re-encryption plan. Staging and production provider endpoints require HTTPS. The local default remains `HOMESCOUT_AI_ENABLED=false` until deliberately configured.

See [`backend/README.md`](backend/README.md#phase-13-homescout-assistant) for API routes and setup. For the Responses protocol, review the selected provider's current API and data-processing terms; OpenAI's [Responses API reference](https://developers.openai.com/api/reference/resources/responses/methods/create) is one provider reference. This implementation requests `store: false` when using Responses, but that setting does not replace review of provider retention, account data controls, or legal/privacy requirements.

## Validation

- Backend full Pytest suite: **81 passed**, with one upstream Starlette/httpx test-client deprecation warning.
- Backend Ruff lint: passed.
- Backend Ruff format check: passed.
- Android `:app:compileDebugKotlin`: passed.
- Android `:app:testDebugUnitTest`: passed.
- Android `:app:assembleDebug`: passed; Gradle reported existing Android Gradle Plugin/SDK compatibility warnings.
- Migration lifecycle, provider-offline behavior, configuration validation, consent, encrypted/owner-only history, rename/delete, request rate limiting, selected property context, active-group membership checks, and private role-work context are covered by backend tests.

## Limits and operational requirements

- The provider is unavailable in the checked-in local configuration. Live response quality, provider-specific behavior, and any sandbox were not tested.
- Phase 13 migrations and behavior tests were run on SQLite. PostgreSQL 17 validation for migration `c13a7f08e3b1` was not performed; earlier PostgreSQL checks through Phase 4 do not cover it.
- Android compilation and unit tests passed, but no emulator/device rendering walkthrough was performed for this phase.
- The typed intent list guides responses; it does not make the assistant a source of legal, credit, lending, or financial decisions. Replies may be wrong. The app tells users these limitations and instructions prohibit invented inventory, pricing, verification, availability, payment, booking, legal, neighbourhood-statistic, or financial facts.
- Prompts and bounded history are sent to the configured provider after consent. Selected account data also leaves HomeScout when its context control is enabled. Database encryption is at rest, not end-to-end encryption. Conversation retention/deletion operations and provider data terms need review before production enablement.
- No all-user analytics, embeddings, background ingestion, or cross-account conversation search were added.

## Stop point

Phase 13 is complete. Do not begin a later phase without the owner's next phase instruction.
