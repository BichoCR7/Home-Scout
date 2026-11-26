# HomeScout Kenya — Codex Development Rules

## Project rules

- Treat the project documents and actual source as the persistent source of truth.
- This is a new project; do not import or claim code from another project as HomeScout functionality.
- Keep the HomeScout source and documentation in its own project folder, separate from RentWise or any other app.
- Refer to the product as HomeScout. Do not reintroduce RentWise as its name in app UI or current project documentation.
- Preserve working behavior once implementation exists. Inspect before changing files.
- Use Kotlin, Jetpack Compose, Material 3, and Gradle on Android; Python, FastAPI, SQLAlchemy, Alembic, Uvicorn, and Pytest on the backend; SQLite for development; PostgreSQL 17 for production; Argon2id for password hashing; M-Pesa Daraja for payments unless a justified change is documented in `DECISIONS.md`.
- Avoid unnecessary rewrites, dependencies, abstractions, and monolithic files.
- Do not invent requirements, data, trust claims, or completed functionality. Clearly label any approved demo data.
- Keep all preview listings and local-only search behavior labeled as sample/demo content; do not imply availability, provider verification, or transaction support.
- Keep backend schema changes in Alembic; never create or modify production schema automatically during application startup.
- Use `HOMESCOUT_` environment-backed settings for backend configuration. Never log database URLs, credentials, raw request bodies, or unfiltered exception details.
- Configure the Android API address centrally through the Gradle property `homescout.apiBaseUrl` or `HOMESCOUT_API_BASE_URL`; never hardcode environment URLs throughout feature code, and never put backend secrets in an Android build.
- Persist Android session tokens only as encrypted data protected by Android Keystore. Keep development action-token exposure disabled by default and unavailable outside development/test.
- Keep the primary bottom navigation at five destinations maximum. Secondary destinations must remain clearly reachable and must not be presented as implemented product services unless they are implemented in an authorized phase.
- Treat the owner's latest supplied navy house-and-location-pin logo as the official HomeScout visual mark. Use the shared `HomeScoutLogo` component in branded Compose UI and `app/src/main/res/drawable/ic_homescout.xml` for Android launcher/system splash uses. Keep the logo shape, navy/cream/terracotta treatment, and HomeScout wordmark consistent across phases unless the owner explicitly changes the brand.

## Phase execution and scope

- Implement only the phase explicitly authorized by the owner.
- At phase start, read `CODEX_RULES.md`, `PROJECT_CONTEXT.md`, `ROADMAP.md`, `TASKS.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, relevant entries in `DECISIONS.md`, and the latest `PHASE_REPORT.md`; then inspect relevant source and restate the authorized scope.
- Resolve routine implementation choices using the project decisions and document material choices. Ask only when a missing decision materially blocks safe or correct work.
- Do not automatically start the next phase.
- At phase end, report incomplete items and blockers honestly; do not describe plans as implementation.

## Engineering and verification

- Use modular feature and responsibility boundaries; keep business rules out of UI widgets and HTTP route handlers.
- Add tests for changed behavior and run relevant existing tests. Run Android compilation, Python tests, lint, type checks, and production build checks when applicable and available.
- Do not claim a check passed unless it was run and its result observed. If no code exists or a tool is unavailable, state why a check does not apply or could not run.
- Fix regressions caused by changes and inspect the final diff for accidental scope expansion.
- Do not create controls that imply unsupported behavior.

## Security and privacy

- Keep secrets out of source, logs, client builds, and documentation. Use environment configuration or secret management.
- Validate inputs; enforce authentication and authorization server-side; check resource ownership.
- Use Argon2 for passwords. Avoid logging passwords, tokens, payment details, or unnecessary personal data.
- Minimize collected data and define consent, retention, deletion, and access controls for sensitive features.
- Payment state must be established by the backend through verified provider interactions, not client claims.

## Documentation

- Keep `PROJECT_CONTEXT.md`, `ROADMAP.md`, `TASKS.md`, `ARCHITECTURE.md`, `CODEX_RULES.md`, `CHANGELOG.md`, `DECISIONS.md`, and `PHASE_REPORT.md` current.
- At each phase end, update roadmap and task status, changelog, and phase report. Add decisions when architecture or an established choice materially changes.
- Keep claims tied to inspected files, observed commands, or approved product requirements.

## Post-Phase 16 audit boundary

- The owner authorized a full audit, targeted repair, build, and local launch after Phase 16. Record this work in FULL_PROJECT_AUDIT_REPORT.md; it does not authorize a new product phase, deployment, publication, or distribution.
- Preserve existing SQLite and emulator data. Never remove the installed app to work around a signing mismatch; use the same signing identity or a separate application ID.
- Continue using HomeScout naming, the owner's logo, and the five-destination primary navigation.
