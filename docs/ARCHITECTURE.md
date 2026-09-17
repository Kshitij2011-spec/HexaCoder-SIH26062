# SIH26062 — System Architecture

## Architecture Philosophy: Modular Monolith

HexaCoders is designed as a **Modular Monolith**. 

Microservice architectures introduce network partitions, distributed transactions, consensus complexities, and operational overhead that are hazardous in low-bandwidth, high-reliability polar deployments. 
A cleanly decoupled modular monolith running within a single unified backend runtime guarantees:
- Transactional integrity across state transitions and event emission.
- Low-latency graph and dependency traversals.
- Simple local development and robust automated testing without complex orchestration.
- Seamless deployment to cloud infrastructure (Render) or station-local edge servers.

---

## 1. High-Level System Topology

```
┌────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                            │
│                                                                        │
│   React 19 + TypeScript + Vite + Tailwind CSS + shadcn/ui + Lucide     │
│   State & Cache Management: TanStack Query v5                          │
│   Offline Persistence: IndexedDB (Client Queue)                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS / REST / WebSockets
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        API & ROUTING LAYER                             │
│                                                                        │
│   FastAPI (Python 3.13+)                                               │
│   Pydantic v2 Request/Response Schemas & Validation                    │
│   JWT Role-Based Access Control (RBAC)                                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       DOMAIN SERVICES LAYER                            │
│                                                                        │
│  ┌───────────────────────┐  ┌──────────────────────┐  ┌─────────────┐  │
│  │     event_service     │  │  dependency_service  │  │ sync_service│  │
│  └──────────┬────────────┘  └──────────┬───────────┘  └──────┬──────┘  │
│             │                          │                     │         │
│  ┌──────────▼────────────┐  ┌──────────▼───────────┐  ┌──────▼──────┐  │
│  │      impact_service   │  │  constraint_service  │  │audit_service│  │
│  └──────────┬────────────┘  └──────────┬───────────┘  └─────────────┘  │
│             │                          │                               │
│  ┌──────────▼────────────┐  ┌──────────▼───────────┐                   │
│  │   readiness_service   │  │  replanning_service  │                   │
│  └───────────────────────┘  └──────────┬───────────┘                   │
│                                        │                               │
│                             ┌──────────▼───────────┐                   │
│                             │   approval_service   │                   │
│                             └──────────────────────┘                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLAlchemy 2.0 Async / psycopg3
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       PERSISTENCE LAYER                                │
│                                                                        │
│   PostgreSQL 16+ (Hosted on Supabase Platform)                         │
│   - Relational Domain Schema                                           │
│   - PostGIS (Spatial Nodes, Geofences, Traverses)                      │
│   - Transactional Event Journal (Immutable Operational Events)        │
│   - Dependency Edge Table (Semantic Adjacency Graph)                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer Boundaries & Authority

### 2.1 UI is Never the Source of Truth
The frontend is strictly a visualization and interaction layer. 
- The UI **NEVER** computes authoritative operational states.
- The UI **NEVER** mutates derived flags directly.
- The UI submits intentions (e.g. `RecordTransportDelay`, `SubmitApproval`), and the domain layer processes the mutation, fires events, re-evaluates dependencies, and responds with the canonical state.

### 2.2 Shared Domain Services
Rather than scattering logic across isolated CRUD endpoints, business rules are encapsulated in cohesive domain services:

1. **`event_service`**: Authors and persists immutable `OperationalEvent` records within database transactions. Broadcasts events to internal listeners.
2. **`dependency_service`**: Maintains and traverses the semantic relationship graph (`REQUIRES`, `CONSTRAINS`, `DELIVERED_TO`, etc.) linking logistics, personnel, assets, and missions.
3. **`impact_service`**: Performs graph traversals on state changes to determine all upstream and downstream affected entities.
4. **`readiness_service`**: Deterministically recalculates derived states (`ExpeditionReadiness`, `MissionReadiness`, `PersonnelReadiness`, `AssetAvailability`, `InventoryExposure`).
5. **`constraint_service`**: Evaluates active operational constraints against the current system state.
6. **`replanning_service`**: Generates alternative mitigation plans and recommendations when hard constraints are violated.
7. **`approval_service`**: Enforces the human-in-the-loop requirement, verifying approver permissions, recording justifications, and committing approved operational plans.
8. **`audit_service`**: Provides tamper-evident chronological retrieval of operational chains and correlation IDs.
9. **`sync_service`**: Manages store-and-forward synchronization for field operators working under intermittent connectivity.

---

## 3. Modular Backend Structure

```
backend/
├── app/
│   ├── api/                     # FastAPI Route Controllers
│   │   ├── v1/
│   │   │   ├── expeditions.py
│   │   │   ├── missions.py
│   │   │   ├── people.py
│   │   │   ├── teams.py
│   │   │   ├── cargo.py
│   │   │   ├── inventory.py
│   │   │   ├── assets.py
│   │   │   ├── transport.py
│   │   │   ├── locations.py
│   │   │   ├── incidents.py
│   │   │   ├── documents.py
│   │   │   ├── events.py
│   │   │   ├── dependencies.py
│   │   │   ├── constraints.py
│   │   │   ├── planning.py
│   │   │   ├── recommendations.py
│   │   │   ├── approvals.py
│   │   │   └── sync.py
│   │   └── api_router.py
│   ├── core/                    # App configuration, security, DB session
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   ├── models/                  # SQLAlchemy ORM Models
│   ├── schemas/                 # Pydantic Schemas (DTOs)
│   ├── services/                # Shared Domain Engine Services
│   │   ├── event_service.py
│   │   ├── dependency_service.py
│   │   ├── impact_service.py
│   │   ├── constraint_service.py
│   │   ├── readiness_service.py
│   │   ├── replanning_service.py
│   │   ├── approval_service.py
│   │   ├── audit_service.py
│   │   └── sync_service.py
│   └── main.py                  # Application entry point
├── tests/                       # Backend test suite
├── requirements.txt
└── pyproject.toml
```

---

## 4. Frontend Architecture & Modular Boundaries

```
frontend/
├── src/
│   ├── assets/                  # Static assets & icons
│   ├── components/              # Shared UI components
│   │   ├── ui/                  # shadcn/ui primitives (Button, Dialog, etc.)
│   │   ├── layout/              # Header, Sidebar, Navigation
│   │   └── common/              # Status badges, Provenance tags
│   ├── features/                # Domain-centric feature modules
│   │   ├── control-tower/       # Unified operational overview & alerts
│   │   ├── expeditions/         # Expedition setup and monitoring
│   │   ├── missions/            # Mission readiness & timeline view
│   │   ├── cargo/               # Consignments & package tracking
│   │   ├── inventory/           # Stock levels, reserves, alerts
│   │   ├── assets/              # Fleet & heavy machinery maintenance
│   │   ├── personnel/           # Rosters, certifications, teams
│   │   ├── transport/           # Movement legs & schedules
│   │   ├── incidents/           # Emergency response workflows
│   │   └── replanning/          # Recommendation review & approval modal
│   ├── hooks/                   # Custom React hooks (TanStack Query wrappers)
│   ├── lib/                     # API client, utility functions
│   ├── types/                   # TypeScript domain contracts
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## 5. Persistence & Data Integrity Model

1. **Foreign Key Integrity**: Strict referential integrity is enforced at the database level. Soft-deletes or tombstone states are used where operational continuity requires historical references.
2. **Immutable Event Journal**: The `operational_events` table is append-only. Triggers or application service rules prevent `UPDATE` or `DELETE` statements on event records.
3. **Graph Representation**: Dependencies are stored in a dedicated `entity_dependencies` table:
   - `from_entity_type`, `from_entity_id`
   - `relationship_type` (e.g., `REQUIRES`, `SUPPORTS`)
   - `to_entity_type`, `to_entity_id`
   - `metadata` (JSONB)
   This allows efficient recursive CTE (Common Table Expression) queries for arbitrary dependency depth traversal without needing a dedicated graph database like Neo4j for the MVP.
