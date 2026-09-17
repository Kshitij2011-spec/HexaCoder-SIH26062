# SIH26062 — Database Foundation & Schema Specification

## 1. Overview & Architectural Principles

This document defines the canonical PostgreSQL relational database schema for the **Integrated Polar Expedition Logistics and Asset Management System** (HexaCoders — SIH26062).

The database serves as the single source of truth for all operational states, relationship topologies, immutable event journals, constraints, replanning packages, and offline sync queues.

### Core Database Principles
1. **Relational Foundation**: All concrete operational relationships (e.g., Mission to Expedition, Package to Consignment, Stock Lot to Item) use enforced foreign keys.
2. **Deterministic Primary Keys**: Technical identity is separated from operator-facing identity:
   - Technical Primary Keys: PostgreSQL `UUID` (`gen_random_uuid()`).
   - Human-Readable Codes: Enforced unique strings (e.g., `EXP-26-A`, `M-08`, `C-117`, `T-08`, `I-42`, `R-04`).
3. **UTC Timestamps**: All timestamps use `TIMESTAMPTZ` stored in UTC. Default timestamps (`created_at`, `updated_at`) are managed by the database.
4. **Authoritative vs. Derived Values**:
   - **Authoritative**: Discrete lifecycle states (e.g. `expedition_status`, `mission_status`, `on_hand_quantity`, `reserved_quantity`).
   - **Derived (Non-Stored)**: Dynamic metrics like `Available Quantity = on_hand - (reserved + quarantined + damaged)`, `MissionReadiness` (`READY`, `AT_RISK`, `BLOCKED`), and `CargoRisk` (`ON_TRACK`, `AT_RISK`, `LATE`, `MISSED`) are computed deterministically by the shared domain engine and are **never** directly editable.
5. **Event Immutability**: The `operational_events` table is append-only. Modification and deletion triggers prevent data tampering.
6. **Data Provenance**: Every domain entity and event carries an explicit `data_provenance` tag.

---

## 2. Controlled Enums & Types

The schema creates 20 controlled PostgreSQL ENUM types to prevent invalid states:

| Enum Name | Allowed Values | Purpose |
| :--- | :--- | :--- |
| `data_provenance` | `MEASURED`, `DERIVED`, `FORECAST`, `SCENARIO`, `SYNTHETIC_DEMO`, `PUBLIC_SOURCE`, `ADVISORY` | Data origin transparency |
| `expedition_status` | `DRAFT`, `PLANNED`, `MOBILIZATION`, `ACTIVE`, `CLOSEOUT`, `ARCHIVED`, `ON_HOLD` | Expedition lifecycle |
| `mission_status` | `PROPOSED`, `APPROVED`, `READY`, `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED`, `DEFERRED`, `CANCELLED` | Mission operational lifecycle |
| `person_readiness` | `NOMINATED`, `CLEARANCE_PENDING`, `READY`, `NOT_CLEARED`, `UNAVAILABLE` | Personnel qualification/medical state |
| `person_movement` | `NOT_DEPLOYED`, `IN_TRANSIT`, `AT_STATION`, `FIELD`, `RETURNING`, `RETURNED` | Personnel physical location state |
| `team_status` | `FORMING`, `READY`, `DEPLOYED`, `FIELD`, `RETURNED` | Team readiness lifecycle |
| `cargo_status` | `REQUESTED`, `DECLARED`, `APPROVED`, `PACKED`, `READY`, `DISPATCHED`, `IN_TRANSIT`, `ARRIVED`, `RECEIVED`, `HELD`, `DELAYED`, `DAMAGED`, `LOST`, `REJECTED` | Cargo consignment state |
| `cargo_package_status`| `PACKED`, `LOADED`, `IN_TRANSIT`, `RECEIVED`, `ISSUED`, `RETURNED`, `HELD`, `DAMAGED`, `LOST` | Individual package handling state |
| `inventory_status` | `ON_ORDER`, `INBOUND`, `AVAILABLE`, `RESERVED`, `ISSUED`, `CONSUMED`, `TRANSFERRED`, `QUARANTINED`, `DISPOSED` | Stock lot operational state |
| `asset_status` | `AVAILABLE`, `RESERVED`, `DEPLOYED`, `IN_USE`, `MAINTENANCE`, `SERVICEABLE`, `UNSERVICEABLE`, `RETIRED` | Fleet and equipment availability |
| `transport_status` | `PLANNED`, `BOOKED`, `READY`, `DEPARTED`, `IN_TRANSIT`, `ARRIVED`, `CLOSED`, `DELAYED`, `DIVERTED`, `CANCELLED` | Transport leg schedule state |
| `location_status` | `AVAILABLE`, `RESTRICTED`, `INACCESSIBLE`, `CLOSED` | Operational site access |
| `incident_status` | `DETECTED`, `TRIAGED`, `DECLARED`, `RESPONSE_ASSIGNED`, `ACTIVE`, `STABILIZED`, `RESOLVED`, `CLOSED` | Emergency incident lifecycle |
| `document_status` | `REQUIRED`, `DRAFT`, `SUBMITTED`, `APPROVED`, `REJECTED`, `EXPIRED`, `MISSING` | Compliance & permit verification |
| `assignment_status` | `PROPOSED`, `APPROVED`, `ACTIVE`, `COMPLETED`, `CANCELLED` | Resource/personnel allocation |
| `recommendation_status`| `PROPOSED`, `APPROVED`, `REJECTED`, `NEEDS_REVISION`, `IMPLEMENTED` | Replan option workflow |
| `approval_decision` | `APPROVED`, `REJECTED`, `MODIFIED` | Human-in-the-loop decision |
| `constraint_severity`| `INFO`, `WARNING`, `CRITICAL` | Operational constraint impact |
| `hard_soft_constraint`| `HARD`, `SOFT` | Constraint rigidity |
| `incident_severity` | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | Life safety & asset impact |
| `dependency_relationship_type` | `REQUIRES`, `SUPPORTS`, `ASSIGNED_TO`, `LOCATED_AT`, `MOVES_VIA`, `CONTAINS`, `DELIVERED_TO`, `RESERVED_FOR`, `REPLENISHED_BY`, `AFFECTS`, `DEPENDS_ON`, `CONSTRAINED_BY`, `OPERATED_BY`, `OCCURS_AT`, `BELONGS_TO` | Semantic relationship graph |

---

## 3. Entity Relationship Topology

```
                   ┌───────────────────┐
                   │    EXPEDITION     │
                   └─────────┬─────────┘
                             │ 1:N
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
 ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
 │   MISSION   │      │    TEAM     │      │    CARGO    │
 └──────┬──────┘      └──────┬──────┘      └──────┬──────┘
        │ 1:N                │ 1:N                │ 1:N
        ▼                    ▼                    ▼
 ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
 │ ASSIGNMENT  │      │   PERSON    │      │   PACKAGE   │
 └─────────────┘      └──────┬──────┘      └─────────────┘
                             │
                             ▼
                      ┌─────────────┐
                      │  LOCATION   │
                      └──────┬──────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
 ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
 │    ASSET    │      │ STOCK LOT   │      │  TRANSPORT  │
 └─────────────┘      └─────────────┘      └─────────────┘

 CROSS-CUTTING AUDIT & INTELLIGENCE ENGINES:
 ┌────────────────────────────────────────────────────────┐
 │ dependencies       (Semantic Adjacency Graph)          │
 │ operational_events (Immutable Append-Only Audit Trail) │
 │ constraints        (Deterministic Safety Rules)        │
 │ replans            (Triggered Operational Packages)    │
 │ recommendations    (Multi-Option Mitigations)          │
 │ approvals          (Human Sign-Off & Justification)    │
 │ incidents          (Emergency Response Framework)      │
 │ sync_queue         (Offline Store-and-Forward Engine)  │
 └────────────────────────────────────────────────────────┘
```

---

## 4. Detailed Table Specifications

### 4.1 Core Operations
- **`expeditions`**: Root campaign record. Contains season, date bounds (`planned_end_at >= planned_start_at`), status, priority (1–5), and provenance.
- **`locations`**: Self-referencing hierarchical physical sites (Station, Field Camp, Port, Anchorage, Airfield). Contains optional latitude/longitude bounds (-90 to 90, -180 to 180) and location accessibility status.
- **`missions`**: Discrete scientific and logistics undertakings bound to an expedition. Unique constraint: `UNIQUE(expedition_id, code)`. Contains required-by date, location FK, priority (1–5).
- **`teams`**: Field and support teams with required roles. Circular reference with `people` is decoupled by creating `teams` with nullable `leader_person_id` and linking `people.team_id`, followed by foreign key constraint attachment.
- **`people`**: Personnel deployed in expedition. Explicitly separates `readiness_state` (Medical/Training clearance) from `movement_state` (Physical transit/station/field). Contains no private medical diagnoses.
- **`assignments`**: Polymorphic allocation table connecting People, Assets, Inventory, and Cargo to Missions with start/end windows and roles.

### 4.2 Logistics & Supply Chain
- **`cargo_consignments`**: Manifest-level tracking with origin/destination location FKs, required-by date, estimated arrival, compliance status, and priority.
- **`cargo_packages`**: Physical shipping units (crates, pallets, ISO containers) linked to consignments. Positive dimension and weight checks (`>= 0`).
- **`transport_legs`**: Multi-modal legs (AIR, VESSEL, OVERLAND_TRAVERSE). Strictly validates `arrival_window_open >= departure_window_open` and `planned_arrival_at >= planned_departure_at`.
- **`transport_cargo_assignments`**, **`transport_person_assignments`**, **`transport_asset_assignments`**: Explicit junction tables for referential integrity across transport manifests.

### 4.3 Inventory & Fleet Assets
- **`inventory_items`**: Abstract catalog definitions (SKU, item code, category, unit, criticality).
- **`inventory_stock_lots`**: Physical stock batches at locations. Enforces deterministic quantity constraints:
  - `on_hand_quantity >= 0`, `reserved_quantity >= 0`, `quarantined_quantity >= 0`, `damaged_quantity >= 0`
  - `reserved_quantity <= on_hand_quantity`
  - `reserved_quantity + quarantined_quantity + damaged_quantity <= on_hand_quantity`
  - *Note*: `available_quantity` is **never stored**; it is derived dynamically as `on_hand - (reserved + quarantined + damaged)`.
- **`inventory_transactions`**: Controlled ledger tracking receipts, reservations, releases, issues, and transfers with reference tracking.
- **`assets`**: Heavy machinery, vehicles, and scientific instruments. Contains condition, maintenance state, location, and spare dependency.
- **`maintenance_records`**: Service records for assets with spare consumption tracking.

### 4.4 Intelligence & Decision Support
- **`time_windows`**: First-class operational temporal bounds with `close_at > open_at` and `hard_or_soft` flag.
- **`dependencies`**: Semantic relationship graph connecting entities with explicit relationship types (`REQUIRES`, `SUPPORTS`, `AFFECTS`, `DEPENDS_ON`, `CONSTRAINED_BY`, etc.).
- **`constraints`**: Evaluated deterministic rules mapping to trusted application rule codes (`MISSION_RESOURCE_REQUIRED`, `CARGO_ETA_DEADLINE`, `ASSET_AVAILABILITY`, etc.).
- **`operational_events`**: Immutable event stream storing before/after state transitions, actors, timestamps, correlation IDs, and evidence payloads. Protected by a database trigger preventing `UPDATE` or `DELETE`.
- **`replans`**, **`recommendations`**, **`recommendation_alternatives`**: Persisted mitigation packages containing multi-alternative options (Reschedule, Substitute, Alternative Transport) with impact and trade-off matrices.
- **`approvals`**: Explicit human operator decisions (`APPROVED`, `REJECTED`, `MODIFIED`) with approver identity, timestamp, and justification.
- **`incidents`**, **`response_actions`**, **`incident_people`**, **`incident_assets`**, **`incident_missions`**, **`incident_cargo`**: Complete emergency incident response lifecycle and affected entity matrices.

### 4.5 Audit & Resilience
- **`audit_log`**: Application-level action audit capturing actor, action, before/after JSONB snapshots, and correlation IDs (distinct from the operational domain event journal).
- **`sync_queue`**, **`sync_conflicts`**: Offline store-and-forward queue with priority tiers (`P0` to `P3`) and conflict resolution payloads for intermittent satellite communication.

---

## 5. Soft-Delete & Immutability Policy

1. **No Destructive Deletes**: Operational entities (missions, cargo, assets, transport) must never be hard-deleted from production databases. Invalidation is performed via lifecycle status transitions (`CANCELLED`, `RETIRED`, `ARCHIVED`).
2. **Immutable Event Journal**: Trigger `trg_operational_events_immutable` aborts any `UPDATE` or `DELETE` attempt against `operational_events`.
3. **Audit Immutability**: The `audit_log` is strictly append-only.

---

## 6. Deterministic Hero Demo Scenario

The seeded database contains the complete baseline for the 45th Indian Scientific Expedition to Antarctica (ISEA) with stable operational codes:
- **Expedition**: `EXP-26-A` ("45th Indian Antarctic Research Expedition 2026", `ACTIVE`)
- **Mission**: `M-08` ("Coastal Geophysics & Glacier Survey", `READY`)
- **Asset**: `I-42` ("Broadband Seismometer & Cryo-Radar Array", `AVAILABLE`)
- **Cargo Consignment**: `C-117` ("High-Precision Sensor Replacement Unit", `IN_TRANSIT`)
- **Transport Leg**: `T-08` ("Chartered Polar Vessel MV Vasiliy Golovnin Leg 08", `IN_TRANSIT`, on-schedule)
- **Team**: `R-04` ("Geophysics Field Survey Team 4", 4 ready personnel including team leader, senior geophysicist, cryo-technician, polar field guide)
- **Hard Constraint**: `CONST-M08-RESOURCE` enforcing that Mission `M-08` requires Asset `I-42` on station before window closure.
