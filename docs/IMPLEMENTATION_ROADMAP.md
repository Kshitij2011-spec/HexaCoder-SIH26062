# SIH26062 — Official Implementation Roadmap

## Build Sequence Philosophy
The development sequence for HexaCoders builds foundational domain reality before higher-level presentation layers. 

> **CRITICAL RULE**: Do not skip ahead simply because a later UI feature appears easier or faster to build. The system's value is in state integrity and reasoning. Without the underlying domain, event journal, and constraint engine, UI screens are merely shallow mockups.

---

## Roadmap Phases

### [COMPLETED] Phase 0: Repository Bootstrap & Engineering Constitution
- Audit environment, tools, and runtime capabilities.
- Establish architectural principles and strict engineering rules.
- Author canonical documentation (`PROJECT_CONTEXT`, `DOMAIN_MODEL`, `ARCHITECTURE`, etc.).
- Scaffold baseline repository layout.
- Initial Git milestone checkpoint (`1218878`).

### [COMPLETED] Phase 1: Database Schema, Migrations & Synthetic Baseline Seed
- Configure Supabase / PostgreSQL schema with PostGIS extension.
- Author authoritative DDL migration `20260917000000_expedition_operational_schema.sql`.
- Author deterministic synthetic seed generator (`supabase/seed.sql`) matching 45th ISEA parameters.
- 24/24 unit and database schema tests verified passing (`2cd861f`).

### [COMPLETED] Phase 1.5: Two-Person Development Architecture & Split-Readiness Foundation
- Establish balanced two-person vertical track engineering model:
  - **Track A (Person A)**: Planning, Decision, Controls, Platform Integration.
  - **Track B (Person B)**: Logistics, Resources, Assets, Incident Response.
- Define git workflow (`a/*`, `b/*` branches, pre-PR rebase, squash-and-merge on `main`).
- Establish strict cross-domain contract protocol and non-intrusion rules.
- Scaffolding frontend architecture directories (`frontend/src/`).
- Create unified verification test script (`scripts/verify.ps1`).
- Author PR template, CODEOWNERS, and collaboration contracts.

### [COMPLETED] Phase 1.75: Shared Supabase Development Environment & Real Database Verification
- Dedicated development Supabase project created (`HexaCoders SIH26062 DEV`, project ref: `tywtsmvccifkugoecrmd`, region: `ap-south-1` Mumbai).
- Legacy project isolation confirmed: old `krishi-sahayak` project completely untouched.
- Applied canonical DDL migration (`20260917000000_expedition_operational_schema.sql`) to live PostgreSQL 17.6 database: 35 tables, 14 enums, spatial types, immutability trigger, foreign keys, and indexes created.
- Applied deterministic synthetic baseline seed (`supabase/seed.sql`) to live database across 4 transactional batches with zero errors.
- Verified live database counts: 1 expedition, 3 missions, 2 teams, 6 people, 10 locations, 3 cargo consignments, 8 packages, 5 transport legs, 10 inventory items, 11 stock lots, 6 assets, 5 maintenance records, 8 documents, 6 time windows, 17 dependencies, 10 operational events, 6 constraints, 2 incidents, 2 response actions.
- Verified Hero Chain relational connectivity in real DB: `EXP-26-A` → `M-08` → `I-42` → `C-117` → `PKG-117-01` → `T-08`.
- Verified operational event immutability on live DB (UPDATE and DELETE attempts rejected by trigger exception `P0001`).
- Verified domain invariants on live DB: inventory allocation formula, time window sequencing, and transport temporal validity.
- Verified foreign key rejection behavior on invalid insert attempt.
- Configured backend environment connection (`DATABASE_URL`, `SUPABASE_DB_URL`, `API_BASE_URL`) and non-leaking DB health check helper (`get_db_health()`).
- Documented project details in `docs/SUPABASE_DEVELOPMENT.md` and updated team workflow policies.

### [COMPLETED] Phase 1.9: Foundation Hardening, Security Baseline, CI & Final Split Readiness
- Reconciled migration lineage: `20260917000000_expedition_operational_schema.sql` confirmed authoritative initial schema; eliminated typo references.
- Authored and applied security baseline migration `20260918000001_enable_rls_security_baseline.sql` enabling Row Level Security (RLS) on all 35 public operational tables with zero permissive public policies.
- Verified real Supabase DEV PostgreSQL catalog: `rowsecurity = true` across all 35 tables; PostgREST direct access blocked while preserving private FastAPI access.
- Created automated GitHub Actions CI workflow (`.github/workflows/ci.yml`) testing Python 3.13 backend and schema assertions without database secrets.
- Authored safe development environment validation script (`scripts/check-env.ps1`) detecting required variable names without printing secret values.
- Documented branch protection policy and out-of-band credential sharing protocol in `docs/GIT_WORKFLOW.md` and `docs/ENVIRONMENT_STRATEGY.md`.
- Disambiguated polar domain terminology and hero codes (`I-42` as scientific instrument/asset, `C-117` as cargo consignment) in `docs/DOMAIN_LANGUAGE.md`.
- Evaluated final split-readiness status as `SPLIT READY`.

### Phase 2: Authentication, Roles & Security Baseline (Shared / Person A initially)
- JWT-based authentication using FastAPI security utilities.
- Role-Based Access Control (RBAC):
  - `EXPEDITION_LEADER`
  - `LOGISTICS_OFFICER`
  - `SCIENCE_COORDINATOR`
  - `STATION_COMMANDER`
  - `FIELD_OPERATOR`
- Audit trail middleware capturing user identity and IP/timestamp on every mutating request.


### Phase 3: Core Expedition, Mission, Person & Team Services
- Domain models and FastAPI endpoints for Expedition lifecycle.
- Dual-state Person tracking (Readiness State vs Movement State).
- Team assembly and qualification verification logic.
- Mission scheduling, priority tagging, and boundary checks.

### Phase 4: Cargo, Package, Transport Leg & Location Modules
- Manifesting and multi-package consignment management.
- Multi-modal transport legs (DROMLAN air bridge, icebreaker voyage, overland traverse).
- Waypoint and location tracking with PostGIS coordinate validation.
- Tracking cargo states (`DISPATCHED`, `IN_TRANSIT`, `ARRIVED`, `RECEIVED`).

### Phase 5: Inventory & Asset Management
- Warehouse and depot inventory management.
- Implementation of strict derivation formula for `quantity_available`.
- Asset maintenance tracking, operating hours, and lifecycle transitions.
- Reservation engine linking stock and assets to specific missions.

### Phase 6: Operational Event System
- Creation of the core `event_service`.
- Immutable append-only event persistence.
- Structured event schemas for all domain transitions.
- Internal event dispatcher / pub-sub mechanism.

### Phase 7: Semantic Dependency Engine & State Propagation
- Recursive graph traversal for upstream/downstream impact analysis.
- Implementation of `dependency_service` and `impact_service`.
- Dynamic propagation of delays and state changes across related nodes.

### Phase 8: Deterministic Readiness Calculation Service
- Implementation of `readiness_service`.
- Transparent, non-arbitrary computation of:
  - `ExpeditionReadiness` (`READY`, `AT_RISK`, `BLOCKED`)
  - `MissionReadiness` (`READY`, `AT_RISK`, `BLOCKED`)
  - `CargoRisk` (`ON_TRACK`, `AT_RISK`, `LATE`, `MISSED`)
  - `InventoryExposure` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
  - `AssetAvailability` (`AVAILABLE`, `LIMITED`, `UNAVAILABLE`)

### Phase 9: Constraint Evaluation Engine
- Implementation of `constraint_service`.
- Real-time rule evaluation (life-support safety floors, fuel minimums, mandatory team qualifications, time-window closures).
- Constraint violation event generation.

### Phase 10: Replanning, Recommendation & Human Approval Engine
- Formulation of mitigation alternatives upon constraint violations.
- Implementation of `replanning_service` and `approval_service`.
- Multi-option recommendation packages with trade-off explanations.
- Structured human review and approval sign-off pipeline.

### Phase 11: Control Tower Interface (Frontend)
- Real-time operational overview dashboard.
- High-visibility active constraint violation alerts.
- Expedition timeline and multi-mission readiness matrix.
- Clean integration with TanStack Query and shadcn/ui.

### Phase 12: Dedicated Domain Workspaces (Frontend)
- Cargo & Manifest Workspace.
- Inventory & Depot Stock Workspace.
- Personnel & Team Deployment Workspace.
- Fleet & Heavy Asset Maintenance Workspace.

### Phase 13: Polar Incident & Emergency Response Module
- Emergency incident declaration workflow (`DETECTED` → `DECLARED` → `RESOLVED`).
- Dynamic safety lockdown propagation.
- Action checklist and responder assignment tracking.

### Phase 14: Offline Queue & Sync Service
- Client-side mutation queuing in IndexedDB for low-bandwidth / blackout scenarios.
- Store-and-forward reconciliation logic in `sync_service`.
- Conflict resolution strategies for asynchronous reconnects.

### Phase 15: Hero Scenario Integration & Verification
- End-to-end execution of Scenario A: "Flight delay in Cape Town cascading into mission block, constraint breach, automated replanning, and human sign-off".
- Full browser validation with Playwright recording.

### Phase 16: Emergency Scenario Integration & Verification
- End-to-end execution of severe weather incident and emergency asset reallocation.
- Playwright browser validation.

### Phase 17: Hardening, Performance Optimization & Deployment Preparation
- Final test suite execution (100% passing Unit, Integration, and E2E specs).
- Frontend production bundle optimization on Vite.
- Backend container configuration for Render deployment.
- Final documentation and demonstration runbook.
