# SIH26062 — Module Ownership Matrix

This document defines the primary and secondary ownership across all functional domains, infrastructure components, and shared platforms in the **HexaCoders** repository.

---

## 1. Domain & Responsibility Matrix

| Domain / Component | Primary Owner | Secondary / Consumer | Scope of Primary Ownership |
| :--- | :--- | :--- | :--- |
| **Expeditions** | **Person A** | Person B | Lifecycle, campaign boundaries, expedition readiness derivation |
| **Missions** | **Person A** | Person B | Mission readiness, time window adherence, priority scheduling |
| **People & Rosters** | **Person A** | Person B | Readiness state vs movement state, polar qualifications, medical flags |
| **Teams** | **Person A** | Person B | Field team assembly, leadership assignments, staffing minimums |
| **Time Windows** | **Person A** | Person B | Hard/soft window evaluation, environmental window tracking |
| **Constraints Engine** | **Person A** | Person B | Rule evaluation, threshold violations, safety floor triggers |
| **Replanning Engine** | **Person A** | Person B | Problem formulation, alternative generation, trade-off analysis |
| **Recommendations** | **Person A** | Person B | Multi-option recommendation packages (A, B, C) |
| **Approvals Engine** | **Person A** | Person B | Human-in-the-loop review, justification persistence, state mutation |
| **Control Tower UI** | **Person A** | Person B | Unified operational overview dashboard, alert feeds, mission matrix |
| **Cargo Consignments** | **Person B** | Person A | Manifesting, tracking, delay logging, customs clearance |
| **Cargo Packages** | **Person B** | Person A | Package dimensions, RFID/barcode tagging, handling classes |
| **Transport Legs** | **Person B** | Person A | Multi-modal legs (Air, Vessel, Traverse), ETD/ETA projections |
| **Locations & Nodes** | **Person B** | Person A | Station, depot, runway hierarchy, accessibility statuses, PostGIS coordinates |
| **Inventory Catalog** | **Person B** | Person A | Item definitions, SKU catalog, categories, criticality ratings |
| **Stock Lots** | **Person B** | Person A | Stock tracking, reservations, derived available calculations |
| **Fleet & Assets** | **Person B** | Person A | Machinery, vehicles, operating hours, asset availability derivation |
| **Maintenance** | **Person B** | Person A | Scheduled service, spare part consumption, work orders |
| **Incidents** | **Person B** | Person A | Emergency detection, declaration, lockdown propagation |
| **Response Actions** | **Person B** | Person A | Emergency checklists, responder tasks, resolution audits |
| **Offline Sync Engine** | **Person B** | Person A | Client-side IndexedDB queue, store-and-forward sync, conflict resolution |
| **Domain Workspaces UI** | **Person B** | Person A | Feature workspaces (Cargo Hub, Depot Stockroom, Fleet Bay, Incident HQ) |
| **Operational Event Platform** | **Person A** | Person B | Central event bus, immutability trigger, event schemas |
| **Semantic Dependency Platform** | **Person A** | Person B | Graph traversal utilities, adjacency query optimization |
| **Audit Platform** | **Person A** | Person B | User action logging, before/after JSONB snapshots |
| **Authentication & RBAC** | **Person A** *(Initial)* | Person B *(Consumer)* | JWT auth, role middleware, security context |
| **Production Deployment** | **Person A ONLY** | *No Prod Authority* | Vercel production, Render production, live domains |
| **Production Secrets** | **Person A ONLY** | *No Prod Authority* | Production database keys, service tokens, environment vaults |
| **Supabase Production Config** | **Person A ONLY** | Person B *(Dev use)* | Platform project settings, production extensions |
| **Unit & Integration Tests** | **Person A + B** | Both | Both author and maintain tests for their respective domains |
| **Playwright E2E Tests** | **Person A + B** | Both | Person A owns hero planning flows; Person B owns logistics/incident flows |

---

## 2. Rules of Ownership

1. **Primary Ownership is Not Code Exclusivity**:
   - The primary owner is responsible for domain architectural integrity, schema consistency, documentation, and prompt review of incoming PRs.
   - The secondary developer is fully empowered to inspect, propose changes, and submit PRs to any domain.
2. **Contract Stability**:
   - The primary owner must ensure public domain contracts (API endpoints, event types, Pydantic schemas) are documented and versioned before deprecation or modification.
3. **Production Boundary**:
   - Person A has sole authority to trigger production deployments and modify production environment variables.
   - Person B develops and tests against local and shared development instances.
