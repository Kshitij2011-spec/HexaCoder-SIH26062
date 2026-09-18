# SIH26062 — Track A: Operational Impact & Reasoning Engine Contract

**Contract ID**: `CONTRACT-TRACK-A-REASONING-001`  
**Version**: `1.0.0`  
**Author**: PERSON A (Track A Owner)  
**Status**: APPROVED FOR INTEGRATION  
**Relevant Domains**: Platform, Dependencies, Impact Propagation, Constraints, Mission Readiness, Expedition Readiness  
**Target Consumers**: Person B (Logistics, Cargo, Transport, Inventory, Assets, Incidents), Person A (Control Tower, Replanning)

---

## 1. Executive Summary & Purpose

The **Reasoning & Impact Engine** establishes the foundational operational intelligence layer of the polar logistics platform. It operates deterministically over the PostgreSQL database foundation to:
1. Navigate semantic dependency graphs with bounded, cycle-safe traversals.
2. Propagate state mutations (e.g. transport delay, equipment breakdown) downstream to discover affected cargo, scientific instruments, and polar missions.
3. Evaluate operational invariants and threshold rules via deterministic Python evaluators.
4. Derive evidence-backed readiness states (`READY`, `AT_RISK`, `BLOCKED`) for missions and expeditions without arbitrary or fake scores (no "87%").
5. Process operational events emitted by domain services to identify candidate constraint violations and blast radii.

---

## 2. Core Operational Entities & Interfaces

### 2.1 DependencyService
- **Location**: `backend/app/services/dependencies/service.py`
- **Authoritative Table**: `public.dependencies`
- **Canonical Vocabulary** (15 types strictly enforced):
  `REQUIRES`, `SUPPORTS`, `ASSIGNED_TO`, `LOCATED_AT`, `MOVES_VIA`, `CONTAINS`, `DELIVERED_TO`, `RESERVED_FOR`, `REPLENISHED_BY`, `AFFECTS`, `DEPENDS_ON`, `CONSTRAINED_BY`, `OPERATED_BY`, `OCCURS_AT`, `BELONGS_TO`.
- **Public Service Methods**:
  - `get_outgoing_dependencies(entity_type, entity_id, relationship_type=None) -> List[DependencyEdge]`
  - `get_incoming_dependencies(entity_type, entity_id, relationship_type=None) -> List[DependencyEdge]`
  - `traverse_graph(entity_type, entity_id, direction=OUTGOING, max_depth=3) -> DependencyGraphResult`
- **Traversal Constraints**:
  - Bounded Depth: Default `3`, maximum clamp `5`.
  - Cycle Safety: Visited set tracking `(entity_type, entity_id)` guarantees termination without recursion limit errors.

### 2.2 ImpactService
- **Location**: `backend/app/services/impact/service.py`
- **Public Service Method**:
  - `calculate_impact(entity_type, entity_id, change_summary, depth=3, correlation_id=None) -> ImpactResult`
- **Output Structure**:
  - `WHAT_CHANGED`: `change_summary`
  - `AFFECTED_ENTITIES`: `List[AffectedEntity]` (with entity code, relationship, depth, and traversal direction)
  - `RELATIONSHIP_PATHS`: `List[DependencyPath]` (concrete chain of hops from root)
  - `WHY_IT_MATTERS`: `reasons: List[str]` (purely derived from stored dependency linkages; zero LLM hallucinations)
  - `POTENTIAL_CONSTRAINTS`: `List[ConstraintEvaluationResult]` (evaluated constraints on all reachable nodes)

### 2.3 ConstraintService
- **Location**: `backend/app/services/constraints/service.py`
- **Authoritative Table**: `public.constraints`
- **Tri-State Evaluation Outcomes**:
  - `SATISFIED`: Invariant verified against active database state.
  - `VIOLATED`: Hard or soft operational rule breach detected.
  - `NOT_EVALUABLE`: Required dependency or domain data is absent or provider module is under development.
- **Rule Registry** (`backend/app/services/constraints/rules.py`):
  - `MISSION_REQUIRED_BY`: Compares mission schedule & time windows against mandated `required_by_at` deadline.
  - `MISSION_RESOURCE_REQUIRED`: Verifies that mandatory equipment, teams, and cargo required by mission exist and are serviceable.
  - `PERSONNEL_STAFFING`: Enforces minimum team headcount floors, role presence, and medical/readiness clearance.
  - `CARGO_ETA_DEADLINE`: Verifies consignment arrival precedes sea-ice or runway operational cutoff dates.
  - `TRANSPORT_CAPACITY`: Reconciles leg payload against capacity limits.
  - `ASSET_AVAILABILITY`: Checks operational status and maintenance operating hour thresholds.
  - `INVENTORY_AVAILABILITY`: Checks unreserved warehouse stock against station minimum safety reserve floors.
  - `DOCUMENT_VALIDITY`: Verifies Antarctic Treaty / Madrid Protocol EIA permits and authorizations.
  - `LOCATION_ACCESS`: Checks weather and physical seasonal entry windows.
  - `TIME_WINDOW`: Verifies temporal execution window bounds.

### 2.4 MissionReadinessService & ExpeditionReadinessService
- **Location**: `backend/app/services/readiness/`
- **Outcomes**: `READY`, `AT_RISK`, `BLOCKED`.
- **Deterministic Aggregation Rules**:
  - **BLOCKED**: Triggered by any hard constraint violation, disbanded team, or explicitly unserviceable/unavailable critical resource.
  - **AT_RISK**: Triggered by any soft constraint breach, personnel shortfall warnings, OR any required dependency/constraint that is `NOT_EVALUABLE` / `UNKNOWN` pending Track B data.
  - **READY**: Only achieved when all required personnel, assets, windows, and constraints are fully evaluated and satisfied with zero blockers, zero warnings, and zero unknowns.
  - **UNKNOWN Guard**: An unevaluable or missing dependency (`NOT_EVALUABLE` / `UNKNOWN`) can NEVER cause a mission or expedition to be reported as `READY`.
  - **Zero Fake Scores**: Prohibits synthetic percentage scores (no arbitrary "87% mission readiness").
  - **Zero Side-Effects**: Readiness evaluation is purely derived and never mutates authoritative primary table statuses.

### 2.5 OperationalImpactProcessor
- **Location**: `backend/app/services/impact/processor.py`
- **Entry Point**: `process_operational_event(event_id: UUID, depth: int = 3) -> ImpactResult`
- **Rule**: Pure read-only derived reasoning. Does NOT silently mutate primary lifecycle states.

---

## 3. Cross-Domain Protocol for Person B (Track B)

### 3.1 What Person B Can Consume
Person B's vertical domains (`locations`, `transport`, `cargo`, `inventory`, `assets`, `incidents`) may consume:
1. `DependencyService`: Query dependencies or traverse graph without building custom graph queries.
2. `ConstraintService`: Query and evaluate constraints bound to logistics entities (consignments, assets, stock lots).
3. `ImpactService`: Simulate the blast radius of transport delays or cargo exceptions.

### 3.2 What Person B Must Provide
To enable rich end-to-end reasoning as Person B develops Track B modules:
1. **Maintain Semantic Dependencies**:
   When creating cargo consignments, transport legs, or stock reservations, populate `public.dependencies` with canonical relationship types (`MOVES_VIA`, `CONTAINS`, `DELIVERED_TO`, `RESERVED_FOR`, `SUPPORTS`).
2. **Emit Operational Events**:
   Every state change (e.g. transport leg delayed, package damaged, inventory stock depleted) must call `EventService.append_event(...)` with:
   - `event_type`: e.g. `TransportLegDelayed`, `CargoPackageDamaged`, `StockLotDepleted`
   - `entity_type`: `TRANSPORT_LEG`, `CARGO_PACKAGE`, `INVENTORY_STOCK_LOT`
   - `entity_id`: UUID
   - `previous_state` & `new_state`
   - `correlation_id`: for distributed operational auditing
3. **No Duplicate Reasoning Logic**:
   Person B domains should NOT build independent impact traversal, readiness scoring, or constraint engines. The shared services in `backend/app/services/` are authoritative.

---

## 4. API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/entities/{entity_type}/{entity_id}/dependencies` | Outgoing direct dependencies |
| `GET` | `/api/v1/entities/{entity_type}/{entity_id}/dependents` | Incoming direct dependents |
| `GET` | `/api/v1/entities/{entity_type}/{entity_id}/impact` | Bounded multi-hop impact analysis |
| `GET` | `/api/v1/events/{event_id}/impact` | Event-driven impact evaluation |
| `GET` | `/api/v1/missions/{id}/readiness` | Mission readiness assessment |
| `GET` | `/api/v1/expeditions/{id}/readiness` | Campaign-wide expedition readiness |
| `GET` | `/api/v1/constraints` | List active constraints |
| `GET` | `/api/v1/constraints/evaluate` | Evaluate all operational constraints |
| `GET` | `/api/v1/constraints/{id}` | Get single constraint definition |
| `GET` | `/api/v1/entities/{entity_type}/{entity_id}/constraints` | Constraints evaluated for entity |
