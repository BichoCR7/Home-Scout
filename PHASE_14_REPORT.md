# HomeScout Kenya — Phase 14 Report

**Phase:** 14 — Admin dashboard, moderation, platform management, and operations  
**Status:** Complete for the authorized operational API, controls, and Android console.  
**Boundary:** Phase 14 only. Stop here.

## Delivered

- Added a staff operations API under `/api/v1/admin/operations` for operational counts, basic user search and status, non-demo listing review, service-provider/offering publication, locations, support, message reports, approved support categories, allow-listed platform settings, and administrative audit history.
- Added permission checks for each operation. Account restrictions require the staff member's current password, prohibit self-restriction, revoke sessions when an account is suspended, protect administrative accounts, and prevent suspension of the last active Super Admin. System settings are limited to approved keys and are Super Admin controlled by the existing RBAC catalog.
- Added auditable support assignment, status/priority/escalation, staff replies, category activation, listing/provider/offering/location changes, message-report decisions, and platform-setting updates. Staff queue summaries omit ticket conversation bodies until an authorized staff member opens a ticket; report access to encrypted message content is permission-gated and audited.
- Added service-review moderation with visible, held, and removed states. Only visible reviews are returned publicly; every staff decision records an audit event and reason.
- Added staff-only operational counts based on current database rows, including service-review moderation workload. Demo listings are excluded. The overview does not read personal financial records or infer business performance.
- Added migration `d14a9c2e5f81` for support-ticket assignment, priority and escalation fields, support action history, service-review moderation status, and the platform service-management permission grants.
- Added the Android Operations console as a secondary Profile route. It links the existing Trust & Safety and role-management workflows rather than duplicating their review rules, and keeps the five primary tabs unchanged.
- Updated backend setup/API documentation, architecture, roadmap, tasks, project context, decisions, changelog, and phase reports using the HomeScout name.

## Scope and limitations

- Verification cases, property/safety reports, and role assignments continue to use their Phase 3/9 workflows, linked from the operations console. Service reviews and reported messages have staff controls here; this phase does not create a universal community moderation queue or duplicate the existing verification evidence or role-elevation workflows.
- Analytics are operational record counts only. No cross-user financial analytics, custom reports, or fabricated metrics are included.
- Configurable settings are an explicit allow-list; secrets and arbitrary integrations are not editable in the dashboard. Provider and listing states reflect stored records, not external verification or ownership proof.
- Support operations and in-app staff replies are implemented; there is no staffing rota, service-level commitment, outbound email/push delivery, or production incident tool.
- The migration and backend behavior were validated on SQLite. PostgreSQL 17 was not available/run for this Phase 14 migration; previous PostgreSQL checks through Phase 4 do not cover it.
- Android compile, JVM unit tests, and debug APK assembly passed. No emulator/device rendering walkthrough was performed.

## Validation

- Backend Pytest full suite: **88 passed**, with one upstream Starlette/httpx deprecation warning.
- Ruff lint: passed.
- Ruff formatting check: passed; **144 files already formatted**.
- Android `:app:compileDebugKotlin`, `:app:testDebugUnitTest`, and `:app:assembleDebug`: **BUILD SUCCESSFUL**.
- Migration lifecycle, access denial, minimized overview fields, support queue/message privacy, replies and audit, account reauthentication/self-restriction/session revocation, listing and service-review moderation, Super Admin setting controls, and verification-workflow integration are covered by automated tests.

## Stop point

Phase 14 is complete. Do not begin a later phase without the owner's next phase instruction.
