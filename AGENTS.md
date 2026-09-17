# SIH26062 — HexaCoders Engineering Constitution

## PROJECT IDENTITY
- **Project**: SIH26062 — Integrated Polar Expedition Logistics and Asset Management System
- **Team**: HexaCoders
- **Product**: Antarctic & Polar Expedition Operational Logistics Platform

## CENTRAL THESIS
> "Build an expedition operations platform in which a change to any important logistics object can be understood in context, propagated across its dependencies, checked against expedition constraints, and converted into a human-approved operational update."

---

## NON-NEGOTIABLE ARCHITECTURAL RULES

1. **Modular Monolith**: Build a modular monolith for the MVP. Do not create microservices.
2. **Frontend**: React + TypeScript + Vite.
3. **UI System**: Tailwind CSS + shadcn/ui + Lucide icons.
4. **Data Fetching**: TanStack Query (React Query) for server state management and caching.
5. **Backend**: Python 3.13+ + FastAPI + Pydantic v2.
6. **Database**: PostgreSQL with Supabase as the platform foundation.
7. **Spatial**: PostGIS extensions where geographic/polar coordinates and spatial boundaries are modeled.
8. **Testing**: pytest for backend unit/integration tests; Playwright for true end-to-end browser verification.
9. **Core Value**: The primary value of the software lies in **relationships, events, constraints, state propagation, and replanning**.
10. **AI/ML Role**: AI/ML functionality is secondary, advisory, and optional. The deterministic rules, dependency engine, and constraint solver are the primary engines.
11. **Strictly Forbidden Infrastructure**:
    - NO Kafka / distributed stream clusters (use transactional event tables + background workers).
    - NO Kubernetes (use Docker / standard container deployments).
    - NO microservice splits.
    - NO blockchain / web3 tokens.
    - NO heavy 3D game engines or virtual globes unless explicitly specified in future requirements.
    - NO SCADA / station telemetry replacement (this is an expedition logistics platform, not a generator monitoring tool).

---

## DOMAIN & OPERATIONAL CONCEPTS

The system is centered on **EXPEDITION OPERATIONAL STATE**.

### Core Domain Entities
- `EXPEDITION`
- `MISSION`
- `PERSON`
- `TEAM`
- `CARGO CONSIGNMENT`
- `CARGO PACKAGE`
- `INVENTORY / STOCK`
- `ASSET`
- `TRANSPORT LEG`
- `LOCATION`
- `INCIDENT`
- `DOCUMENT`
- `ASSIGNMENT`
- `OPERATIONAL EVENT`
- `TIME WINDOW`
- `CONSTRAINT`
- `REPLAN`
- `RECOMMENDATION`
- `APPROVAL`
- `RESPONSE ACTION`

---

## CORE ENGINEERING RULES

### 1. The Event Rule
Every meaningful operational mutation **MUST** emit an immutable operational event (`OperationalEvent`).
- No silent database updates.
- Every state change captures: `event_id`, `event_type`, `entity_type`, `entity_id`, `previous_state`, `new_state`, `timestamp`, `source`, `actor`, `location`, `evidence`, `correlation_id`.
- Event history is permanent and auditable.

### 2. The Dependency Rule
Entities are connected through strict, semantic relationships.
- Allowed relationship types:
  `REQUIRES`, `SUPPORTS`, `ASSIGNED_TO`, `LOCATED_AT`, `MOVES_VIA`, `CONTAINS`, `DELIVERED_TO`, `RESERVED_FOR`, `REPLENISHED_BY`, `AFFECTS`, `DEPENDS_ON`, `CONSTRAINED_BY`, `OPERATED_BY`, `OCCURS_AT`, `BELONGS_TO`.
- Never create generic, untyped `linked_to_everything` references.

### 3. The Replanning Rule
Do not trigger replanning loops after every trivial event. Replanning occurs strictly when:
- A meaningful state change occurs,
- **AND** a dependency chain is affected,
- **AND** a hard constraint is violated,
- **OR** an authorized expedition operator manually requests replanning.

### 4. The Human Approval Rule
- **The system recommends; the operator approves.**
- Autonomous execution of high-consequence operational decisions (e.g., flight diversions, cargo abandonment, mission cancellation, personnel reallocations) is strictly prohibited.
- Every approval record must explicitly persist:
  - Who approved (`approver_id`, role)
  - When (`timestamp`)
  - Decision (`APPROVED`, `REJECTED`, `MODIFIED`)
  - Operator comment / justification
  - Resulting operational state mutation & correlation event

### 5. Data Honesty & Provenance Rule
- **Never claim live integration** with Indian National Centre for Polar and Ocean Research (NCPOR), Maitri/Bharati station telemetry, live vessel AIS/GPS feeds, or live Indian Antarctic Programme databases.
- The MVP operates exclusively with synthetic, benchmark, and scenario datasets.
- Every piece of data displayed or emitted must be labeled with its provenance:
  `MEASURED`, `DERIVED`, `FORECAST`, `SCENARIO`, `SYNTHETIC / DEMO`, or `ADVISORY`.
- Arbitrary fake scores (e.g., "87% mission readiness") are forbidden unless backed by an explicit, transparent, deterministic formula.

### 6. Security Rule
- Never commit secrets, API keys, passwords, service tokens, or private credentials into source code, documentation, git history, frontend code, or log outputs.
- Use `.env` files (git-ignored) and `.env.example` templates.

### 7. Verification Rule
- Never consider a feature complete simply because TypeScript compiles, pytest passes, or a build succeeds.
- Interactive user workflows must be verified end-to-end using real browser interaction via the Playwright tool.

### 8. Git & Milestone Discipline
- Never blindly rewrite functional subsystems.
- Do not push to remote repositories or deploy without explicit instructions.
- Commit in coherent, verifiable milestones with descriptive messages.
