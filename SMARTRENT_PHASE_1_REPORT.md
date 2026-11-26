# HomeScout SmartRent — Phase 1 Audit & Integration Map

**Date:** 2026-11-24  
**Status:** Phase 1 complete. Audit only; no feature implementation from later SmartRent phases was started.  
**Workstream:** The owner-supplied SmartRent plan. This is separate from the completed HomeScout product roadmap phases 0–16.

## Audit summary

HomeScout already contains a substantial SmartRent implementation from product Phase 8 and supporting functionality from product Phases 7, 9, 10, 12, and 13. The next steps must extend those existing services and screens, not create a second finance dashboard, ledger, payment database, property comparison system, document store, or AI assistant.

The existing SmartRent screen has been repaired to load its API-backed sections independently. Its prior shared failure state no longer needs a replacement screen: Overview, Plan, Savings, Compare, Discover, Learn, Records, Lease, and Alerts already have distinct Compose content and backend operations. Phase 1 of this workstream therefore found no reason to replace the current architecture.

## Capability audit

| Capability | Existing HomeScout functionality to reuse | Current boundary or improvement area |
|---|---|---|
| Finance dashboard and user profile | Authenticated `/api/v1/finance/dashboard` and `/profile`; owner-scoped encrypted finance profile; Compose Overview with editable inputs, affordability preview, save action, and illustrative example | It is a housing-planning snapshot, not a full bank-account dashboard or categorized spending budget. The example is not saved unless the user explicitly saves it. |
| Affordability and RentScore | Decimal-based backend calculation engine, variable-income handling from user-entered history, transparent affordability categories, housing budget suggestions, and explicit non-credit-score disclosure | Continue to reuse tested calculation rules; do not introduce a second formula or market RentScore as a credit score. |
| Budget, expense, and utility records | Finance profile totals, manual categorized housing records, move-in plans, and a utility summary calculated from user-entered amounts | No separate category-budget allocation/editor or connected utility-provider pricing/history exists. Estimates must remain clearly identified as user-entered. |
| Moving costs and savings | Owner-scoped move-in plans, individually entered cost lines, goal targets/dates, virtual contributions, progress, simulations, and explicitly shared goal records | Savings are virtual trackers and do not hold or transfer money. Preserve existing records and contribution history. |
| Property comparison and discovery | Existing marketplace/listing model, saved properties, up-to-four-property comparisons with user-entered recurring/one-time costs, true-cost totals, and budget-based discovery | Comparison intentionally excludes demo, draft, and unavailable homes. There are currently no bundled public listings; do not substitute synthetic listings as real inventory. |
| Rent and payment history | Finance manual records are private notes, and the personal hub supports uploaded documents/receipts linked to records. Separate payment service provides authenticated transaction history and reconciliation. | Real Daraja support is narrowly scoped to eligible accepted fixed-price service bookings, not rent. It is disabled locally and no credentials are configured. A manual entry never confirms a payment. |
| Payment methods | Finance manual-record form labels methods for recording user-entered history; backend Daraja client, transaction state, callback evidence, idempotency, and verification already exist for M-Pesa service orders | Visa/Mastercard/PayPal and tenancy rent settlement are not implemented. No card data is collected. Do not show those providers as active or claim a payment succeeded without provider verification. |
| Savings and shared goals | Encrypted goals and contributions; optional named-account sharing with explicit contribution permission and restricted field disclosure | Do not add a second goals store or broaden sharing to budgets, records, or profiles. |
| AI assistance | Existing consent-based HomeScout Assistant, contextual SmartRent intent, encrypted conversation history, server-side provider architecture, opt-in authorized context, and a deterministic rule-based budget-coach preview | The Assistant provider is disabled/unconfigured. The budget coach preview is not generative AI. No AI reply should be fabricated or personalized as AI when unavailable. |
| Documents and receipts | Existing owner-scoped private document upload/download/delete in Personal Hub; Finance records can reference a document | General personal-document storage is separate from finance-payload encryption; use the established upload/authorization path and avoid copying files into a second store. |
| Lease, verification, trust, and safety | Lease Guardian stores user-entered rent/deposit, dates, notes, obligations, and questions. Existing Phase 9 stores actual manual verification/review state and rental safety records. | Lease Guardian is an organizer, not a signed tenancy ledger or legal interpreter. Verification must come from current review records; never infer it from the lease or payment. |
| Notifications | Finance alerts are persisted, user-scoped in-app records; existing notification infrastructure is available | There is no external push/email delivery or scheduled reminder worker. Upcoming rent/payment must not be invented from a profile target or lease note. |
| Maps, locations, and profiles | Existing MapLibre/OpenFreeMap map, Kenya location catalog/search, account/profile APIs, secure session handling, and five-item primary navigation | Do not add a separate finance map/profile/navigation stack. Transport and utility prices are not sourced merely by having a map. |

## Integration map

### Reuse

- Android Finance entry and subsections: `app/src/main/java/ke/co/homescout/features/finance/SmartRentScreen.kt`.
- Existing M-Pesa transaction history/status and service-booking request UI: `PaymentsScreen.kt` and `data/remote/PaymentsApi.kt`.
- Central authenticated API configuration/client, account/session handling, Material 3 theme/components, and five primary tabs.
- Backend SmartRent routes, schemas, service, data access, encrypted models, and calculations under `backend/app/api/v1/endpoints/smartrent.py`, `backend/app/schemas/smartrent.py`, `backend/app/services/smartrent.py`, `backend/app/services/finance_calculations.py`, `backend/app/data_access/smartrent.py`, and `backend/app/models/smartrent.py`.
- Existing payment service and Daraja adapter under `backend/app/services/payments.py`, `backend/app/services/daraja.py`, and `backend/app/api/v1/endpoints/payments.py`.
- Existing marketplace comparisons/discovery, Personal Hub document storage, and Assistant routes/services; no duplicate endpoint or table should be introduced without a concrete gap.

### Improve if later authorized

- Finance subsection hierarchy and visual density: the current screen contains all Finance flows in one large Compose source file and a horizontally scrolling ten-section selector. Prefer small, incremental component extraction and clearer navigation while preserving behavior and accessibility.
- Explain the distinction between saved planning inputs, manual notes, provider-confirmed transactions, unavailable external services, and empty account data.
- Add budget/expense controls only after mapping them to the existing finance profile and manual-record schemas, so totals are not double-counted.
- Preserve per-section loading/error states already added; a failure in one API endpoint must not hide other financial tools.

### Not present or externally blocked

- Category-level monthly budget allocations and a user-editable recurring expense ledger beyond profile totals and manual records.
- Rent obligations tied to a confirmed tenancy and rent payment processing; recurring payment reminders/workers; payment methods for cards/PayPal.
- Connected utility price feeds or location-based transport cost data.
- Live AI finance replies until a provider, model, server API key, and assistant encryption key are configured.
- Real M-Pesa execution until an authorized Daraja app, merchant configuration, production-safe callback host, and operational approval are supplied. Current local configuration reports M-Pesa disabled and no provider credentials.

## Dependencies and safe integration points

1. Authenticated finance data relies on the existing account session and stable `HOMESCOUT_FINANCE_ENCRYPTION_KEY`. The current local development configuration has a key; staging/production require separately provisioned, backed-up secrets. Key loss makes encrypted finance values unreadable.
2. Financial calculations should remain in `finance_calculations.py`, use `Decimal`, validate inputs in the existing schemas, and keep backend results authoritative. UI previews must disclose when values are illustrative and must not write unless the user selects Save.
3. A real payment flow requires an authorized business purpose and server/provider confirmation. Existing Daraja infrastructure only covers service orders and does not authorize HomeScout to collect, hold, or escrow rent.
4. Property costs can use the existing listing/compare data only. Missing costs remain unknown or explicitly user-estimated; do not silently treat unknown values as sourced zeroes.
5. Use the Personal Hub upload and authorization path for receipts. Keep verification evidence, payment receipts, private finance payloads, and ordinary user documents within their current access boundaries.
6. Use the existing Assistant only after configured provider/consent checks; it must respect the existing private-context controls and must not invent prices, listings, payment status, or advice outcomes.

## Likely files for later phases

- UI/navigation: `SmartRentScreen.kt`, `PaymentsScreen.kt`, possibly dedicated Finance composables under `features/finance/`, existing routes and design-system components.
- Calculations/contracts: `backend/app/services/finance_calculations.py`, `services/smartrent.py`, `schemas/smartrent.py`, `api/v1/endpoints/smartrent.py`, corresponding `data_access` and `models` only for demonstrated schema gaps.
- Existing adjacent systems: marketplace/discovery, payments/Daraja, Personal Hub/document uploads, and Assistant. Changes should stay scoped to the phase being authorized.
- Verification: `backend/tests/test_smartrent.py`, payment and assistant tests when relevant, Android `app/src/test`, plus targeted build/API checks.

## Phase boundary

Phase 1 audit is complete. This report is the integration map requested by the supplied SmartRent plan. No new UI, database, payment integration, demo financial records, or other Phase 2+ implementation was started. The existing HomeScout product Phases 0–16 remain historical and unchanged; the supplied SmartRent workstream is tracked separately.
