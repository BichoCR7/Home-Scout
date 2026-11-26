# HomeScout Android release checklist

Do not distribute the unsigned Phase 15 APK or a build without a reviewed backend and map configuration.

## Identity and build

- [ ] Confirm release application ID `ke.co.homescout` and owner-approved HomeScout logo/wordmark.
- [ ] Increase `versionCode` monotonically and set a reviewed `versionName` using `HOMESCOUT_VERSION_CODE` / `HOMESCOUT_VERSION_NAME`.
- [ ] Set HTTPS `HOMESCOUT_API_BASE_URL` for the actual release API. Verify the release build has no cleartext traffic.
- [ ] Provision an upload keystore outside the repository; inject `HOMESCOUT_RELEASE_STORE_FILE`, `HOMESCOUT_RELEASE_STORE_PASSWORD`, `HOMESCOUT_RELEASE_KEY_ALIAS`, and `HOMESCOUT_RELEASE_KEY_PASSWORD` through a protected CI secret store.
- [ ] Confirm the upload certificate and Play App Signing setup. Keep the Play signing certificate fingerprint available for Google API restrictions.
- [ ] Confirm the chosen OpenFreeMap tile service's current terms, attribution, and reliability suitability; establish a supported/self-hosted tile option if a production SLA is needed.
- [ ] Run `:app:bundleRelease` for a signed Play App Bundle, or the approved signed APK task for controlled direct distribution. Check signature, package ID, version, manifest, and artifact checksum. Never upload an unsigned build.
- [ ] Preserve the release keystore, secrets, artifact and checksums under owner-approved access/retention; ensure no secret entered build logs or committed files.

## API, data, and integrations

- [ ] Deploy only after the PostgreSQL 17 Phases 6–14 migrations and representative API workflows pass on isolated staging; verify Alembic head and rollback/restore plan.
- [ ] Confirm production account/session signing keys and separate stable finance, trust, message, and (if enabled) AI encryption keys are backed up and access-controlled.
- [ ] Replace local file storage with durable private object storage, access policies, encryption, malware scanning, retention/deletion, and restore tests before handling real uploads.
- [ ] Verify SMTP STARTTLS account verification/password reset and sender domain.
- [ ] Keep Daraja and AI disabled until their separate sandbox/privacy/merchant approval gates are satisfied. Never use fake successful transaction or AI output in a demonstration.
- [ ] Verify database TLS, least-privilege users, backups, point-in-time recovery, and a restore rehearsal.
- [ ] Configure health monitoring, redacted log collection, rate/latency/error alerts, incident ownership, and support escalation.

## Functional and privacy review

- [ ] Test the signed release on supported Android versions and multiple phone sizes; cover login, search, property detail, map fallback/live map, saves, comparison, SmartRent, trust/safety, viewing, services, Profile and permissions.
- [ ] Verify OpenFreeMap styles and visible attribution on release devices. Confirm area-search rate limits/caching across all backend workers; satellite, terrain, Places, and nearby amenities are not included.
- [ ] Verify no real user/customer records or credentials appear in screenshots, demo accounts, logs, diagnostics, or presentation material.
- [ ] Review privacy notice, consent, retention/deletion, support operation, data processors, incident response, and the relevant Kenyan data-protection obligations with a qualified professional; this checklist is not a legal compliance opinion.
- [ ] Get explicit owner approval before public store submission, direct distribution, pilot, production payment enablement, or production data import.

## Current status (2026-11-24)

- Debug build and Phase 15 unsigned release assembly pass. Release packaging preflight blocks distribution packaging without signing credentials and an HTTPS API configuration.
- No release signing key, production API, Daraja credentials, AI provider, SMTP account, production host, or PostgreSQL 17 Phase 6–14 validation is configured. Map tiles currently use a public service with no SLA.
- A signed AAB/APK has not been produced or submitted. No public or controlled distribution occurred.
