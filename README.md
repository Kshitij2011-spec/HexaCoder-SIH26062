# HEXACODERS — SIH26062

## Integrated Polar Expedition Logistics and Asset Management System

An operational decision support platform for polar expeditions in which changes to logistics, assets, cargo, or personnel are propagated across dependencies, validated against operational constraints, and resolved through human-approved updates.

---

## 1. Development Status
**Current Status**: `DATABASE FOUNDATION / PHASE 1 (Completed)`

The database schema, migration scripts, constraints, immutability triggers, and deterministic synthetic seed data (45th ISEA baseline) have been established and verified. Full database design documentation is available in [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md). Application business logic, UI screens, and authentication are scheduled for subsequent phases as detailed in [IMPLEMENTATION_ROADMAP.md](docs/IMPLEMENTATION_ROADMAP.md).

---

## 2. Technology Stack & Direction

- **Architecture**: Modular Monolith
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, Lucide Icons
- **State Management & Caching**: TanStack Query v5
- **Backend API**: Python 3.13+, FastAPI, Pydantic v2
- **Database**: PostgreSQL 16+ with PostGIS, hosted on Supabase platform
- **ORM / Query**: SQLAlchemy 2.0 (Async), psycopg3
- **Testing & Verification**: pytest (Unit & Integration), Playwright (End-to-End Browser Verification)
- **Deployment Targets**: Vercel (Frontend), Render (Backend Service)

---

## 3. Data Honesty & Provenance Statement

This system operates under strict data classification standards:
- All data points are tagged as `MEASURED`, `DERIVED`, `FORECAST`, `SCENARIO`, `SYNTHETIC / DEMO`, `PUBLIC SOURCE`, or `ADVISORY`.
- The MVP operates with curated **synthetic, benchmark, and scenario datasets** modeling the 45th Indian Scientific Expedition to Antarctica (ISEA).
- The platform does not use arbitrary fake scores or unexplainable percentages.

---

## 4. Operational Boundary & Disclaimer

> **Notice**: This project is an academic engineering prototype developed for the Smart India Hackathon. It does **not** have direct access to, or authorized communication links with, internal operational networks of the National Centre for Polar and Ocean Research (NCPOR), the Ministry of Earth Sciences (MoES), or live military/scientific polar communication channels.

---

## 5. Verification Approach

Every user-facing workflow and core logic engine is validated through a three-tier testing strategy:
1. **Unit Testing**: Validates entity state machines, derivation math, constraint evaluations, and event schema compliance via pytest.
2. **Integration Testing**: Verifies multi-step cascading pipelines (e.g., cargo delay → mission block → constraint violation) via FastAPI TestClient and PostgreSQL transactions.
3. **E2E Browser Testing**: Validates real interactive operator journeys and human-approval workflows using genuine Playwright browser automation.

---

## 6. Implementation Roadmap Overview

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 0** | Repository Bootstrap, Audit & Engineering Constitution | **Completed** |
| **Phase 1** | Database Schema, Migrations & Synthetic Seed | **Completed** |
| **Phase 2** | Authentication, Roles & Security Baseline | Pending |
| **Phase 3** | Expedition, Mission, Person & Team Services | Pending |
| **Phase 4** | Cargo, Package, Transport Leg & Location Modules | Pending |
| **Phase 5** | Inventory & Asset Management | Pending |
| **Phase 6** | Operational Event Journal System | Pending |
| **Phase 7** | Semantic Dependency Engine & State Propagation | Pending |
| **Phase 8** | Deterministic Readiness Calculation Service | Pending |
| **Phase 9** | Constraint Evaluation Engine | Pending |
| **Phase 10** | Replanning, Recommendation & Human Approval Engine | Pending |
| **Phase 11** | Control Tower Interface | Pending |
| **Phase 12** | Domain Workspaces (Cargo, Inventory, People, Assets) | Pending |
| **Phase 13** | Polar Incident & Emergency Response Module | Pending |
| **Phase 14** | Offline Queue & Sync Service | Pending |
| **Phase 15** | Hero Scenario: Cargo Delay & Human Replanning | Pending |
| **Phase 16** | Emergency Scenario: Blizzard Incident Response | Pending |
| **Phase 17** | Hardening, Performance & Verification | Pending |

Refer to [docs/IMPLEMENTATION_ROADMAP.md](docs/IMPLEMENTATION_ROADMAP.md) for full phase details.

---

## 7. Documentation Index
- [AGENTS.md](AGENTS.md) — Engineering Constitution & Coding Agent Constraints
- [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) — Canonical Database Schema, Enums, Constraints & Hero Seed Specification
- [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) — Domain Problem, Scenarios & Operational Concept
- [docs/DOMAIN_MODEL.md](docs/DOMAIN_MODEL.md) — Canonical Entities, Dual States, Events & Propagation
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Modular Monolith Architecture & Boundaries
- [docs/ENGINEERING_RULES.md](docs/ENGINEERING_RULES.md) — Non-negotiable Rules & Prohibitions
- [docs/DATA_PROVENANCE.md](docs/DATA_PROVENANCE.md) — Data Classifications & Boundary Statement
- [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) — Unit, Integration & Playwright Test Plans
- [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md) — 8-Step Engineering & Git Loop
