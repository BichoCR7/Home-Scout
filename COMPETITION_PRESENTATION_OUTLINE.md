# HomeScout competition presentation outline

**Format:** 8–10 slides plus a 4–6 minute guided product-shell demo. No unverified market-size statistics or provider claims are included.

## 1. HomeScout: housing decisions, with more clarity

- Kenya-first rental discovery and renter support.
- Tagline: “Find your next place.”
- Show the official navy house-and-location-pin logo and the five-tab Android shell.

## 2. The renter problem

- Finding a home involves fragmented search, uncertain costs, safety checks, and moving coordination.
- Renters need to consider affordability and move-in expenses alongside the listed rent.
- Present these as product problem statements from the project brief; add validated research and citations before presenting any numeric market claim.

## 3. Who HomeScout is designed to help

- Renters first, with permission-scoped flows for landlords, agents, service providers, and operations staff.
- Kenya-first locations, county/estate context, and KES amounts.
- Avoid claims about market share, user adoption, or supply not supported by evidence.

## 4. One housing journey

- Discover homes and locations.
- Compare costs and plan move-in.
- Use safety guidance and organize a viewing.
- Prepare moving tasks and find services as providers join.
- Clearly label the currently shown Kilimani/Lavington/Ruaka cards as synthetic preview content.

## 5. SmartRent and financial inclusion

- Explainable affordability and move-in planning, savings goals, and financial learning.
- RentScore is a HomeScout housing-planning indicator, not a credit score or lending decision.
- Savings goals and manual entries do not represent money held or transferred.
- No rent custody, escrow, credit underwriting, or loan approval.

## 6. Trust and safety

- Evidence-submission and human-review workflows; allegations are not proof.
- Viewing safety guidance and private, consent-based sharing.
- No external identity/property title/tenancy check or automatic fraud verdict is claimed.

## 7. AI and maps, with clear boundaries

- HomeScout Assistant is server-side, consent-based, owner-scoped, and disabled without provider configuration.
- MapLibre Native with OpenFreeMap public styles is the current no-key map setup; it has no SLA and still needs on-device rendering verification.
- The selected vector styles do not provide satellite/hybrid imagery, Google Places, or nearby businesses. Show only a live map if it has actually loaded, and preserve visible provider attribution.

## 8. Architecture and safeguards

- Android: Kotlin, Jetpack Compose, Material 3, five primary tabs.
- API: FastAPI, SQLAlchemy, Alembic; SQLite in development, PostgreSQL 17 production target.
- Authorization, encrypted sensitive records, server-controlled payment state, explicit demo-data boundaries.
- Explain that PostgreSQL Phase 6–14 migration checks and live provider tests remain outstanding.

## 9. Demonstration

- Use `COMPETITION_DEMO_GUIDE.md` and the exact signed candidate build.
- Present only the reduced honest path until the full demo gates are met.
- Never show real user data, keys, fake verifications, false booking/payment states, or unconfigured live-service claims.

## 10. Limitations, launch gates, and roadmap

- No production hosting/data, durable object storage, production signing, live listings, restricted Maps project, Daraja transaction, AI provider, production SMTP, or full end-to-end journey is configured.
- Next: PostgreSQL 17 migration/recovery suite, isolated demo data pipeline, object-storage adapter, provider sandbox tests, release signing and verified AAB, accessibility/end-to-end pass, and owner-approved controlled pilot.
- Close with a specific request for feedback/partnership rather than claiming launch readiness.

## Suggested presentation narration

“HomeScout is being prepared as a Kenya-first housing companion. We focus on the choices around finding a home too: affordability, safety, and moving. The product shell and backend workflows are built, but this preview is not live inventory. We are preparing the PostgreSQL, Maps, release signing, and provider gates before any controlled pilot. The demonstration labels each synthetic example and shows what is active versus what still needs configuration.”
