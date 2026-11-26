# HomeScout deployment preparation

**Status:** Preparation only. No hosting provider or production account has been selected, no cloud resources were created, and no service was deployed.

This guide describes a provider-neutral production shape for the HomeScout Android app and FastAPI API. Before a pilot, choose the hosting, PostgreSQL, secret-management, private-storage, SMTP, monitoring, and incident-response providers and verify their current controls and contracts.

## Current production gates

- PostgreSQL 17 is the production target, but Phases 6–14 migrations have not been executed on PostgreSQL 17. Phase 15 verified the full Alembic chain only on SQLite.
- The backend has no selected production host, object store, secret manager, monitoring service, or backup/restore process.
- Current uploads use local filesystem storage. Do not accept real user documents or operate multiple API replicas until storage is moved to a durable private object store with encryption, access controls, malware scanning, retention, and tested backups.
- SMTP, M-Pesa Daraja, and the HomeScout Assistant have no production credentials or live service evidence. MapLibre/OpenFreeMap needs no map key and rendered vector tiles on the QA emulator on 2026-11-24; its public tile service has no SLA. This confirms a road map only, not satellite imagery, and does not guarantee production uptime.
- Android release packaging fails closed without the release signing inputs and HTTPS API URL. No current signing key or production API values are configured.

## Backend runtime

`backend/Dockerfile` provides a non-root, Python 3.12 container built from a dedicated pinned runtime dependency lock. It starts Uvicorn on port 8000 with one worker by default. It does not run Alembic automatically and does not copy `.env`, tests, local databases, or `var/` uploads into the image. Docker/Podman was not installed in the current environment, so the image itself has not been built or scanned.

Build and tag an immutable image in the chosen CI system, scan it, and deploy it behind a managed TLS endpoint:

```text
cd backend
docker build --pull -t homescout-api:<immutable-build-tag> .
```

Inject environment values from a secret manager. Do not mount a developer `.env` file in a hosted service. Configure the platform's reverse proxy to forward only trusted headers and allow only the proxy network to supply them. Do not expose Uvicorn directly to the public Internet. Keep `/docs`, `/redoc`, and `/openapi.json` disabled in staging/production as the current settings do.

Health probes:

- Liveness: `GET /api/v1/health`
- Readiness: `GET /api/v1/health/ready` (requires database connectivity)

The service logs request IDs, method, response status, and elapsed time without request bodies. It does not include an application metrics exporter, alert routing, distributed tracing setup, or a production incident platform. Add managed log collection, uptime checks, database/API saturation metrics, error-rate and latency alerts, and on-call ownership before pilot. Never put authorization headers, database URLs, personal information, payment payloads, or provider secrets in logs.

## PostgreSQL 17 and migrations

1. Provision a managed PostgreSQL 17 database in a private network. Require TLS certificate verification (`sslmode=verify-full` where supported), strong separate credentials, least-privilege runtime and migration roles, and provider-managed patching.
2. Configure `HOMESCOUT_DATABASE_URL` with the `postgresql+psycopg` scheme. URL-encode reserved characters in credentials; do not print the resulting URL in CI output.
3. Use an isolated staging database first. Run the full migration chain, API tests, constraints/index review, representative search and authorization workflows, and backup/restore rehearsal on PostgreSQL 17. The current evidence covers Phases 2–4 only; SQLite success is not PostgreSQL evidence.
4. Take a backup and record the current Alembic revision. Run the migration as a one-off release job using the same immutable image and secret set, then verify the resulting revision. The app factory does not create or upgrade schema at startup.
5. Deploy the API only after the migration job succeeds. Keep database rollback/forward-fix procedures and a tested restore point for every schema change.

Example migration job (adapt to the chosen host's job runner; inject secrets securely):

```text
python -m alembic upgrade head
```

Do not run this command concurrently from every API replica. No managed PostgreSQL host or backup was provisioned in Phase 16.

## Backend environment and key custody

`backend/.env.production.example` is a names-only checklist with unusable placeholders. It is not a deployable environment file. Production requires at least:

| Setting | Production handling |
|---|---|
| `HOMESCOUT_ENVIRONMENT` | `production` |
| `HOMESCOUT_DATABASE_URL` | PostgreSQL 17 private TLS URL, secret-managed |
| `HOMESCOUT_AUTH_SIGNING_KEY` | Random stable value, at least 32 bytes; secret manager |
| `HOMESCOUT_FINANCE_ENCRYPTION_KEY` | Unique stable URL-safe Base64 32-byte key; back up under key custody |
| `HOMESCOUT_TRUST_ENCRYPTION_KEY` | Separate stable 32-byte key |
| `HOMESCOUT_MESSAGE_ENCRYPTION_KEY` | Separate stable 32-byte key |
| `HOMESCOUT_AI_ENCRYPTION_KEY` | Separate key required only before enabling the Assistant |
| `HOMESCOUT_AUTH_DEV_EXPOSE_TOKENS` | `false` |
| `HOMESCOUT_SMTP_HOST`, `HOMESCOUT_SMTP_FROM` | Approved sender and authenticated STARTTLS transport |
| `HOMESCOUT_SMTP_USERNAME`, `HOMESCOUT_SMTP_PASSWORD` | Inject together if SMTP authentication is used |
| `HOMESCOUT_CORS_ORIGINS` | Empty unless a reviewed web client needs exact HTTPS origins |
| `HOMESCOUT_LOG_LEVEL` | `INFO` or stricter; avoid debug in production |

Keep each encryption key stable and backed up. Loss of a key makes the corresponding encrypted records unreadable; replacing a key without a data re-encryption plan is not a safe rotation. Keep staging and production keys distinct. The API does not expose secrets to Android.

Use managed object storage for `HOMESCOUT_MEDIA_STORAGE_DIR` and `HOMESCOUT_PRIVATE_DOCUMENT_STORAGE_DIR` before real users upload files. The current API implements local storage only, so a mounted volume is a temporary single-instance bridge, not the required durable/scalable production storage architecture.

## Map services

The Android client now uses MapLibre Native and OpenFreeMap public vector styles. No Google key, account, or billing is needed. The current style set provides road-oriented vector maps; it does not provide satellite/terrain imagery, Places search, or nearby business results. OpenFreeMap requires attribution and offers no SLA/warranty, so evaluate a supported or self-hosted tile service before a production launch. See `MAPS_SETUP.md`.

Kenyan area search is user-triggered and proxied through FastAPI to the configurable `HOMESCOUT_MAP_GEOCODER_URL`, defaulting to public Nominatim. Nominatim permits moderate user-triggered usage under a strict application-wide one-request-per-second limit, requires an identifying User-Agent, and disallows autocomplete/bulk queries. The current cache and limiter are process-local; before deploying multiple API workers, use shared caching/rate-limiting or a supported/self-hosted geocoder. Review the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/) and OpenFreeMap terms before release.

## M-Pesa Daraja

The integration remains **disabled**. No sandbox transaction, production merchant onboarding, callback delivery, or reconciliation was exercised.

- First create an owner-controlled sandbox app in the [Safaricom Daraja portal](https://developer.safaricom.co.ke/), validate the current STK Push/STK Query contract, and use an internet-reachable HTTPS callback in a non-production environment.
- Keep all consumer credentials, shortcode/passkey, and the independent phone-HMAC key in the backend secret manager. Never add them to Gradle or Android.
- Exercise pending, failure, timeout, duplicate callback, authenticated query, replay/idempotency, and reconciliation paths against sandbox records before any live enablement.
- Production requires merchant onboarding/go-live approval, confirmed business authority for the limited service-booking collection use case, an HTTPS public callback, restricted production credentials, monitoring, settlement/reconciliation ownership, and separate legal/operational review.
- Set `HOMESCOUT_MPESA_ENABLED=true` only after those gates. Set `HOMESCOUT_MPESA_ENVIRONMENT=production` only in production, and do not enable `HOMESCOUT_MPESA_SERVICE_COLLECTION_AUTHORIZED` without explicit recorded authorization. HomeScout does not collect rent, custody funds, escrow, pay providers, or initiate refunds.

## HomeScout Assistant

The Assistant is currently disabled and has no provider/key/encryption configuration. Keep `HOMESCOUT_AI_ENABLED=false` until the selected provider, model, HTTPS endpoint, server-side API key, separate history-encryption key, retention/privacy terms, rate limits, and user notice/consent have been reviewed. Confirm selected context obeys existing user authorization and test no-provider, rate-limit, timeout, error, and data deletion behavior before enabling it. Never ship the provider key in Android. No live model request was made.

## Android release build

The production package is `ke.co.homescout`; the debug package is `ke.co.homescout.debug`. The current version is `0.1.0` / version code `1`; this is not evidence of a submitted store build. Set a unique increasing `HOMESCOUT_VERSION_CODE` and reviewed `HOMESCOUT_VERSION_NAME` for each release.

The app module reads release signing inputs only from CI environment variables:

- `HOMESCOUT_RELEASE_STORE_FILE` — absolute path to a protected upload keystore outside the checkout.
- `HOMESCOUT_RELEASE_STORE_PASSWORD`
- `HOMESCOUT_RELEASE_KEY_ALIAS`
- `HOMESCOUT_RELEASE_KEY_PASSWORD`

Release packaging is blocked if signing or an HTTPS `HOMESCOUT_API_BASE_URL` is absent. Build an Android App Bundle for a Play track only after the release checklist is satisfied:

```text
./gradlew :app:bundleRelease
```

The current machine has no configured signing key/production API URL, so this command is expected to stop at `preflightRelease`. The unsigned Phase 15 APK is not distributable. For Google Play, use an upload key and enroll/configure Play App Signing; for a controlled direct APK handoff, separately sign and verify with an approved protected key. Do not share a local/debug key. Keep keystore and passwords out of source, `.properties`, artifacts, build logs, and chat. See [Android app signing](https://developer.android.com/studio/publish/app-signing).

## Deployment, rollback, and restore procedure

1. Review code and dependency/image scan results; build an immutable candidate image and AAB.
2. Run backend tests/lint, Android debug checks, signed release build checks, current Android API compatibility checks, and the complete PostgreSQL 17 staging migration/API suite.
3. Confirm secrets, separate encryption keys, tile/geocoder service suitability and limits, SMTP, storage, privacy notices/retention, incident contacts, and data-processing/provider terms.
4. Back up and verify a restore point; run Alembic as a single release job.
5. Deploy to private staging behind TLS, run readiness/critical user-journey checks, inspect only redacted logs, then get explicit owner release approval.
6. For rollback, redeploy the previous immutable API image and compatible Android artifact. Do not automatically downgrade a production schema; use a reviewed forward-fix or restore plan after assessing new writes.
7. A controlled pilot is a separate user-authorized phase. This guide does not authorize deployment, submission, payments, data import, or distribution.

## Phase 16 outcome

This document, the Docker image definition, signing preflight, release checklist, competition demo guide, presentation outline, and Phase 16 report are preparation artifacts only. Nothing was deployed, submitted, signed with a production key, or connected to a paid provider.
