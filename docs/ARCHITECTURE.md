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

## 3. Modular Backend Structure & Strict Layering

```
backend/
├── app/
│   ├── api/                     # FastAPI Route Controllers & Envelope Wrappers
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
│   │   │   ├── events.py
│   │   │   ├── dependencies.py
│   │   │   ├── constraints.py
│   │   │   ├── planning.py
│   │   │   ├── recommendations.py
│   │   │   ├── approvals.py
│   │   │   └── sync.py
│   │   └── api_router.py
│   ├── core/                    # App configuration, security, auth guards
│   │   ├── config.py
│   │   └── security.py
│   ├── db/                      # Session management, engine, base metadata
│   │   ├── database.py
│   │   └── base.py
│   ├── domains/                 # Independent Product Domain Modules
│   │   ├── expeditions/         # Track A: Expedition domain models, schemas, repos
│   │   ├── missions/            # Track A: Mission domain models, schemas, repos
│   │   ├── people/              # Track A: Person domain models, schemas, repos
│   │   ├── teams/               # Track A: Team domain models, schemas, repos
│   │   ├── cargo/               # Track B: Cargo Consignments & Package models
│   │   ├── transport/           # Track B: Transport Leg & Manifest models
│   │   ├── locations/           # Track B: Station & field depot models
│   │   ├── inventory/           # Track B: Stock Lot & inventory balance models
│   │   ├── assets/              # Track B: Durable Asset & maintenance models
│   │   └── incidents/           # Track B: Polar Incident & response action models
│   ├── services/                # Cross-Cutting & Decision Engines
│   │   ├── events/              # Event Journal, immutability & listeners
│   │   ├── dependencies/        # Semantic graph traversals & cycle checks
│   │   ├── constraints/         # Operational constraint evaluation engine
│   │   ├── planning/            # Deterministic replanning & impact engine
│   │   ├── recommendations/     # Mitigation solver & recommendation generator
│   │   ├── approvals/           # Human-in-the-loop approval state machine
│   │   ├── audit/               # Provenance & tamper-evident audit logs
│   │   └── sync/                # Store-and-forward offline synchronization
│   └── main.py                  # Application entry point & lifespan
├── tests/                       # Backend test suite (pytest)
├── requirements.txt
└── pyproject.toml
```

### 3.1 Strict Domain Non-Intrusion Rule
**Domain modules MUST NOT import or depend on another domain's private internal implementations.**
- A feature in `domains/cargo/` cannot directly manipulate private state in `domains/missions/`.
- Cross-domain interactions must occur strictly through:
  1. **Shared Services** (e.g., `services/dependencies/`, `services/events/`).
  2. **Public Domain Interfaces / Contracts** (e.g. `mission_service.get_mission_manifest_requirements()`).
  3. **Versioned REST API Endpoints** (`/api/v1/...`).

---

## 4. Frontend Architecture & Modular Boundaries

```
frontend/
├── src/
│   ├── app/                     # App shell, root routing, global layout, navigation
│   ├── components/
│   │   ├── shared/              # Shared high-level domain-agnostic UI (OperationalTable, StatusBadge)
│   │   └── ui/                  # Design system primitives (shadcn / Radix primitives)
│   ├── features/                # Domain-specific feature modules
│   │   ├── expeditions/         # Track A: Expedition management views
│   │   ├── missions/            # Track A: Mission tracking & readiness
│   │   ├── people/              # Track A: Roster and polar medical/skills
│   │   ├── teams/               # Track A: Field team formation & assignments
│   │   ├── planning/            # Track A: Replanning workspace & constraint matrix
│   │   ├── control-tower/       # Track A: Integrated situational dashboard
│   │   ├── cargo/               # Track B: Cargo manifests & hazmat handling
│   │   ├── transport/           # Track B: Multimodal transport legs & tracking
│   │   ├── locations/           # Track B: Station & field depot management
│   │   ├── inventory/           # Track B: Stock lot tracking & fuel levels
│   │   ├── assets/              # Track B: Vehicle & machinery maintenance
│   │   ├── incidents/           # Track B: Polar incidents & response actions
│   │   └── sync/                # Track B: Offline sync & local queue drawer
│   └── lib/
│       ├── api/                 # Single shared API client & TanStack Query base
│       ├── hooks/               # Shared React hooks (auth, spatial, keyboard)
│       └── types/               # Shared TypeScript schemas and contract types
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
