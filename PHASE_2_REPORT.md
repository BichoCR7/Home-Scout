# HomeScout Kenya — Phase 2 Report

**Phase:** 2 — Backend foundation, database, and API architecture  
**Date:** 2026-11-23  
**Status:** Implementation complete. Phase 3 and later were not started.

## Completed

- Added a modular FastAPI service in `backend/` with API v1 routing, application factory, dependency injection, request IDs, configuration, logging, and stable error responses.
- Added `GET /api/v1/health` liveness and `GET /api/v1/health/ready` database readiness endpoints. Development API docs use OpenAPI; interactive docs are disabled for production settings.
- Added Pydantic environment configuration using the `HOMESCOUT_` prefix, secure database URL handling, CORS origin validation, SQLite development defaults, and a production PostgreSQL URL requirement.
- Added SQLAlchemy engine/session setup for SQLite and PostgreSQL via psycopg 3. SQLite foreign-key enforcement is enabled for local development. SQL schema creation is not run at application startup.
- Added foundational account/profile, role/permission assignment, application setting, audit event, and in-app notification models with a portable initial Alembic migration.
- Added pytest coverage for configuration validation, API health/error behavior, SQLite database initialization and constraints, model relationships, and migration upgrade/downgrade.
- Prepared Android API address configuration through a single `BuildConfig.API_BASE_URL` sourced from Gradle property `homescout.apiBaseUrl` or environment variable `HOMESCOUT_API_BASE_URL`. No API client, request, backend secret, or hardcoded environment URL was added.
- Updated the project architecture, rules, context, roadmap, tasks, decisions, changelog, README, and this report. The Phase 1 report remains archived at `PHASE_1_REPORT.md`.

## Verification

| Check | Result |
|---|---|
| `python -m pytest -q --tb=short --basetemp=.pytest-temp` in `backend/` | Passed: 15 tests. Pytest emitted one Starlette/httpx deprecation warning from the installed test-client integration. |
| `python -m ruff check app tests migrations` | Passed: no findings. |
| `python -m ruff format --check app tests migrations` | Passed: all 35 Python files formatted. |
| Alembic SQLite upgrade/downgrade | Passed as part of the migration test; all foundation tables were created and removed, with the Alembic version table correctly left at base. |
| Android `:app:generateDebugBuildConfig` and `:app:compileDebugKotlin --rerun-tasks` | Passed. The new central API configuration was generated and compiled. |
| Android `:app:assembleDebug :app:testDebugUnitTest` | Repeatedly attempted, but blocked at `:app:compileDebugJavaWithJavac` by Windows `java.nio.file.AccessDeniedException` while Java closed/read cached SDK or dependency JARs. The same failure occurred using isolated and shared Gradle caches and after requesting access to those paths. No source compilation diagnostic was produced. |
| Android unit tests | No Android unit-test source exists; the combined Gradle run stopped before the test task. Phase 1 recorded `testDebugUnitTest` as `NO-SOURCE`. |
| PostgreSQL 17 integration | Not run during Phase 2 because no server was available at that time. Post-implementation verification on 2026-11-23 used PostgreSQL 17.12 for clean migration, populated Phase 2-to-3 migration, downgrade/re-upgrade, and API smoke checks; see the Phase 3 report. |

Gradle also printed a non-fatal SDK metadata notice: installed command-line tooling recognizes SDK XML through version 3 while the SDK includes version 4 metadata.

## Scope limits

Phase 2 establishes backend infrastructure only. It does not implement authentication, authorization enforcement, property APIs, finance products, payments, maps, bookings, notifications delivery, or Android networking. The user and role schema is foundational and does not itself authenticate or authorize a request. PostgreSQL 17.12 migrations and selected API flows have now been verified locally; production hosting, CI coverage, and SMTP delivery remain unverified. Full Android packaging was unverified during Phase 2 due to the JDK file-access failure documented above; Phase 3 later achieved an APK build from an isolated temporary workspace.

## Main files

- Backend setup and dependency pins: `backend/pyproject.toml`, `backend/requirements.lock.txt`, `backend/.env.example`, `backend/README.md`.
- API entry and runtime configuration: `backend/app/main.py`, `backend/app/core/`, `backend/app/api/v1/`.
- Persistence: `backend/app/db/`, `backend/app/models/`, `backend/migrations/`.
- Backend checks: `backend/tests/`.
- Android endpoint configuration: `app/build.gradle.kts`, `app/src/main/java/ke/co/homescout/data/remote/ApiConfiguration.kt`.

## Phase 1 history

Phase 1 design-system and Android shell results are preserved in `PHASE_1_REPORT.md`.
