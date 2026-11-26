# HomeScout competition demonstration guide

## Honest demo status

The application shell runs on an API 37 emulator, and Home/Discover/Areas/Finance/Profile navigation was smoke-checked. The Home screen includes three illustrative, synthetic housing cards; its own copy says they are previews, not available listings. These local cards are not backed by a demo marketplace, are not eligible for publish/save/compare, and do not appear as map markers.

The requested full 25-step live journey is **not currently demo-ready**. No authorized demo API/database/account, searchable demo inventory, Daraja setup, AI provider, or seeded service providers are present. MapLibre/OpenFreeMap road-map tiles rendered on the QA emulator, but no satellite imagery or Places service is included; the latest phone-configured APK was not installed in this session. Do not describe a sample card as an available home, a road map as satellite imagery, an unconfirmed viewing as booked, a savings record as money moved, or an unavailable assistant as live AI.

## Before a live competition run

1. Use a physically isolated staging environment with a separate PostgreSQL 17 database, no production data, disabled payments, and a purge plan. Demo records must be synthetic, carry a visible `DEMO` disclosure, remain isolated from production analytics and user search, and never be marked verified or available as real inventory.
2. Resolve Phase 15/16 gates: run Phases 6–14 migrations and API workflows on PostgreSQL 17; create private demo accounts through the authorized bootstrap flow; configure SMTP or a tested demonstration account flow; prepare demo-only fixture records through an explicit staging seed process. Do not add test fixtures to production or bypass normal RBAC in a release app.
3. Rehearse the MapLibre/OpenFreeMap road map with network access and visible attribution. It requires no key or billing, but the public provider has no SLA. If the competition requires satellite imagery or Places, select and configure a separately approved provider; do not imply OpenFreeMap supplies those features.
4. Keep Daraja disabled for the demonstration. Use only transaction fixtures clearly labeled as synthetic if UI evidence is necessary; do not initiate a real charge or claim a payment succeeded.
5. Keep the Assistant disabled until a provider, server-side key, separate encryption key, explicit user consent/context, provider privacy terms, and failure handling have been approved and exercised. Otherwise narrate the honest unavailable state.
6. Use demo-only accounts, synthetic addresses, synthetic contact details, and fictional amounts. Remove real email/phone numbers and personal photos from slides, screenshots, logs, emulator, database, and screen recording.
7. Rehearse the exact signed candidate build and save a local offline fallback deck/video with an explicit “recorded demonstration” label. Do not show a mock map image as if it were a live Google map.

## Requested 25-step journey and present readiness

The route names below describe the intended presentation path. “Blocked” means the required data/provider/account has not been configured here, not that the feature is complete.

| # | Demonstration step | HomeScout route / evidence | Current readiness |
|---:|---|---|---|
| 1 | Open HomeScout | Launch the app; show the HomeScout splash and Home tab. | **Ready on the QA emulator.** |
| 2 | Search Kilimani, Nairobi | Home search → Discover; enter Kilimani. | **Partial.** Search UI exists; no API-backed listings are seeded. |
| 3 | Explore demo listings | Home’s clearly identified illustrative preview cards. | **Partial.** Three local preview cards only; not a searchable demo inventory and not actually available homes. |
| 4 | Explore the live map | Map secondary route; inspect the road map and attribution. | **Partial.** Real OpenFreeMap vector tiles rendered in the QA emulator; no satellite mode, Places, public SLA, or live property inventory is available. Latest phone build was not installed in this follow-up. |
| 5 | Select a property marker | Map marker and preview. | **Blocked.** Map excludes demo/unpublished/unsourced property rows; no real inventory or sourced marker coordinates. |
| 6 | Review property details | Property detail route from a published result. | **Blocked for this demo.** No published listing exists. |
| 7 | Save the property | Sign in, then save from detail. | **Blocked for this demo.** Requires demo account, API, and a non-demo published property. |
| 8 | Compare up to three properties | Finance/compare or comparison route. | **Blocked for this demo.** Requires at least two loaded eligible listings and authenticated API access. |
| 9 | Explore neighbourhood information | Areas tab. | **Partial.** Location reference/search infrastructure exists; no verified editorial neighbourhood profiles or live API setup. |
| 10 | Use RentScore | Finance → SmartRent. | **Blocked for this demo.** Needs authenticated API and stable finance encryption key; RentScore is an explainer, not a credit score. |
| 11 | Calculate move-in costs | Finance → move-in planning. | **Blocked for this demo.** Calculation workflow needs connected user/API state. |
| 12 | Create a savings goal | Finance → savings goals. | **Blocked for this demo.** Requires account, API and demo state; amounts are virtual/manual records, not a deposit. |
| 13 | Review financial literacy | Finance learning section. | **Partial.** The learning content is available in the Finance experience; do not imply personalized/regulated advice. |
| 14 | Explore trust and safety | Profile/secondary Trust & Safety route. | **Partial.** Safety guidance/checklist is demonstrable; verification status requires actual reviewed records. |
| 15 | Schedule a viewing | Property detail → viewing request. | **Blocked for this demo.** Requires an eligible listing and an actual host confirmation before describing as scheduled/confirmed. |
| 16 | Use the viewing checklist | Trust & Safety → Viewing guidance/checklist. | **Partial.** Guidance can be shown; no specific real viewing record exists. |
| 17 | Ask HomeScout AI if a home fits budget | Assistant, after consent and selected finance context. | **Blocked.** Provider and encryption configuration are absent; do not use a canned response as AI. |
| 18 | Explore moving services | Services secondary route. | **Blocked for this demo.** No real or synthetic provider marketplace is configured. |
| 19 | Organize moving tasks | Services → moving planner. | **Blocked for this demo.** Requires demo account/API setup; tasks and budgets must be labeled planning data. |
| 20 | Review personal Profile | Profile tab. | **Partial.** Screen is present; authenticated demo profile needs controlled setup. |
| 21 | Review saved homes | Profile → saved items. | **Blocked for this demo.** Requires account/API and eligible demo-environment listings. |
| 22 | Review activity | Profile → activity. | **Blocked for this demo.** Requires account/API activity records. |
| 23 | Review notifications | Profile → in-app notifications. | **Blocked for this demo.** No demo records are seeded; push/email delivery is not implemented. |
| 24 | Show a role-specific dashboard | Profile/Operations or assigned-role routes. | **Blocked for this demo.** Requires isolated, authorized demo roles and audited fixtures; never elevate a public demo user. |
| 25 | Demonstrate permissions | Compare allowed/denied behavior with controlled test accounts. | **Partial via backend automated tests only.** No live signed-device demo accounts or journey were prepared. |

## Recommended live presentation path today

1. Show the real HomeScout launch and five-tab interface.
2. Show the Home sample cards and point out the visible “sample” label and FAQ disclosure that the homes are not real listings.
3. Search Kilimani to show the current search screen, then state that live inventory is not yet loaded.
4. Open Map and show the configuration fallback; explicitly state that no live Google tiles are configured.
5. Show the available Finance learning and Trust & Safety guidance only where they render without claiming server data.
6. Finish with the architecture and release gate slides. State that the live listing, satellite, payment and AI journeys need separate integration setup and validation.

This reduced path is an honest product-shell demonstration, not the requested end-to-end competition journey. Run the full path only after the “Before a live competition run” gates have passed and the signed candidate has been rehearsed.
