# SIH26062 — Two-Person Engineering Collaboration Model

## 1. Executive Summary & Philosophy

HexaCoders is engineered by a balanced two-person engineering team. 

To maximize velocity during Smart India Hackathon development while preserving architectural cohesion, the project establishes a **low-coordination, asynchronous, PR-driven engineering model**.

Neither developer is a "secondary" or "junior" engineer. Both own substantial, high-impact vertical product domains.

```
                    ┌────────────────────────────┐
                    │      MAIN (INTEGRATION)    │
                    │   Production Source of Truth│
                    └──────────────▲─────────────┘
                                   │
                     Squash Merge via Reviewed PR
                                   │
              ┌────────────────────┴────────────────────┐
              │                                         │
 ┌──────────────────────────┐             ┌──────────────────────────┐
 │      PERSON A TRACK      │             │      PERSON B TRACK      │
 │ Branch: a/<feature-name> │             │ Branch: b/<feature-name> │
 │                          │             │                          │
 │ • Expedition & Missions  │             │ • Cargo & Logistics      │
 │ • Teams & Personnel Plan │             │ • Inventory & Stock Lots │
 │ • Constraints & Replans  │             │ • Fleet Assets & Spares  │
 │ • Approvals Engine       │             │ • Incidents & Emergency  │
 │ • Control Tower Portal   │             │ • Offline Sync & Queues  │
 │ • Shared Platform Lead   │             │ • Domain Workspaces      │
 │ • Prod Deployment Owner  │             │                          │
 └──────────────────────────┘             └──────────────────────────┘
```

---

## 2. Role Definitions

### 2.1 Person A: Project Head / Integration & Deployment Owner
- **Primary Domain**: Decision Intelligence, Expedition Lifecycle, Human Approval Engine, Control Tower Overview.
- **Platform Responsibilities**:
  - Integration lead for the shared platform and modular monolith architecture.
  - Final merge authority into the `main` branch.
  - **Exclusive Authority**: Production cloud deployment (Render backend, Vercel frontend, Supabase production infrastructure).
  - **Exclusive Authority**: Management of production environment variables and production secrets.
  - Releases, milestone tags, and submission runbooks.

### 2.2 Person B: Parallel Engineering Developer
- **Primary Domain**: Physical Logistics, Multi-Modal Transport, Fleet Asset Maintenance, Station Inventory, Incident Response, Offline Synchronization Engine.
- **Platform Responsibilities**:
  - Full end-to-end domain ownership for assigned vertical tracks (backend services, API routes, database operations, and frontend feature workspaces).
  - Authors independent unit, integration, and Playwright tests for Track B domains.
  - Proposes and reviews cross-domain contracts, schema evolutions, and shared UI primitives via PRs.
  - Operates autonomously for long development stretches without being blocked by Person A.

---

## 3. The Balanced Two-Track Product Architecture

The codebase is split vertically into two balanced product tracks sharing a unified database, event model, and design system:

| Aspect | Track A (Person A) | Track B (Person B) |
| :--- | :--- | :--- |
| **Operational Focus** | *Operational Command & Strategic Decisions* | *Physical Execution & Resource Availability* |
| **Key Domains** | Expeditions, Missions, Personnel Readiness, Teams, Time Windows, Constraints, Replanning, Recommendations, Approvals, Control Tower | Cargo Consignments, Packages, Transport Legs, Locations, Inventory Lots, Assets, Maintenance, Emergency Incidents, Response Actions, Offline Sync |
| **User Workspaces** | Control Tower Overview, Mission Planning & Readiness Board, Replan Review & Human Approval Dialog | Cargo Manifest Hub, Inventory & Depot Stockroom, Fleet Maintenance Bay, Emergency Incident Command, Field Sync Monitor |
| **Cross-Domain Contract Role** | Exposes Mission Requirements, Constraint Rules, and Approval State Mutations | Exposes Cargo ETAs, Asset Availability, Stock Balances, and Incident Restrictions |

---

## 4. Shared Platform Layer

The **Shared Platform** is not a third developer; it is the shared foundation that both developers co-own and conform to:
1. **Database & Migrations**: PostgreSQL schema, enums, triggers, and deterministic seed in `supabase/`.
2. **Operational Event System**: Standard event schema (`OperationalEvent`), central event type registry, and immutability triggers.
3. **Semantic Dependency Graph**: Authoritative 15-verb relationship vocabulary (`REQUIRES`, `SUPPORTS`, `AFFECTS`, etc.).
4. **API Conventions**: Standardized `/api/v1/` REST routes, unified `{ data, meta, errors }` responses, and centralized error handling.
5. **UI Design System**: Tailwind CSS tokens, shadcn/ui components, Lucide icons, and semantic polar color palettes.
6. **Verification Tooling**: pytest suites, Playwright browser test runners, and unified verification scripts (`scripts/verify.ps1`).

---

## 5. Working Principles to Minimize Blocking

1. **No Casual Direct Pushes to `main`**: Neither developer routinely writes features directly on `main`. `main` always represents a clean, working, tested state.
2. **Contract-First Collaboration**: If Person A needs a cargo status, or Person B needs mission readiness, they consume public service contracts rather than reaching into each other's domain internals.
3. **Small, Focused Pull Requests**: PRs should encapsulate a single domain capability or milestone, accompanied by automated tests.
4. **Autonomous Local Environments**: Both developers run identical local setups (Python 3.13, Node 22, local seed data) without relying on each other's machines.
