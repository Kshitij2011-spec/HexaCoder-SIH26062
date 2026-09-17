# SIH26062 — Canonical Domain Model

## Overview
This document defines the authoritative domain entities, states, semantic relationships, derived metrics, and state propagation mechanics for the **Integrated Polar Expedition Logistics and Asset Management System**.

---

## 1. Core Domain Entities & Lifecycles

### 1.1 EXPEDITION
- **Purpose**: Represents a multi-month or annual polar expedition campaign (e.g., 45th Indian Scientific Expedition to Antarctica - ISEA).
- **Key Fields**: `expedition_id`, `code`, `name`, `season`, `start_date`, `end_date`, `state`, `primary_station_id`, `leader_person_id`, `derived_readiness`.
- **Lifecycle States**:
  - Nominal: `DRAFT` → `PLANNED` → `MOBILIZATION` → `ACTIVE` → `CLOSEOUT` → `ARCHIVED`
  - Exception: `ON_HOLD`
- **Relationships**:
  - `CONTAINS` → `MISSION`
  - `OPERATED_BY` → `PERSON` (Leader / Command Team)
  - `LOCATED_AT` → `LOCATION` (Stations, Field camps)
- **Derived State**: `ExpeditionReadiness` (`READY`, `AT_RISK`, `BLOCKED`).
- **Business Rules**: An expedition cannot transition to `ACTIVE` if any mandatory life-support mission or baseline fuel resupply is in a `BLOCKED` state.

---

### 1.2 MISSION
- **Purpose**: A discrete scientific, logistical, traverse, or construction undertaking within an expedition.
- **Key Fields**: `mission_id`, `expedition_id`, `title`, `type` (SCIENTIFIC, LOGISTICS, TRAVERSE, EMERGENCY, MAINTENANCE), `priority` (CRITICAL, HIGH, STANDARD), `scheduled_start`, `scheduled_end`, `state`, `time_window_id`, `derived_readiness`.
- **Lifecycle States**:
  - Nominal: `PROPOSED` → `APPROVED` → `READY` → `SCHEDULED` → `IN_PROGRESS` → `COMPLETED`
  - Exceptions: `BLOCKED`, `DEFERRED`, `CANCELLED`
- **Relationships**:
  - `BELONGS_TO` → `EXPEDITION`
  - `REQUIRES` → `TEAM`
  - `REQUIRES` → `ASSET` (e.g., snowcats, scientific drills)
  - `REQUIRES` → `CARGO_PACKAGE` or `INVENTORY` (instruments, rations, fuel)
  - `CONSTRAINED_BY` → `TIME_WINDOW`
  - `OCCURS_AT` → `LOCATION`
- **Derived State**: `MissionReadiness` (`READY`, `AT_RISK`, `BLOCKED`).
- **Business Rules**: A mission automatically transitions derived readiness to `BLOCKED` if any required personnel is `UNAVAILABLE`, required asset is `UNSERVICEABLE`/`MAINTENANCE`, or required cargo is `DELAYED` beyond the hard time window.

---

### 1.3 PERSON
- **Purpose**: An individual deployed or planned for deployment to polar stations/field sites.
- **Key Fields**: `person_id`, `first_name`, `last_name`, `role`, `organization`, `passport_number`, `medical_clearance_date`, `polar_training_level`, `readiness_state`, `movement_state`.
- **Dual Lifecycle Architecture**:
  1. **Readiness State** (Medical / Training / Clearance):
     - `NOMINATED` → `CLEARANCE_PENDING` → `READY`
     - Exceptions: `NOT_CLEARED`, `UNAVAILABLE`
  2. **Movement State** (Physical Location / Transit):
     - `NOT_DEPLOYED` → `IN_TRANSIT` → `AT_STATION` → `FIELD` → `RETURNING` → `RETURNED`
- **Relationships**:
  - `ASSIGNED_TO` → `TEAM` or `MISSION`
  - `LOCATED_AT` → `LOCATION`
  - `MOVES_VIA` → `TRANSPORT_LEG`
- **Derived State**: `PersonnelReadiness` (`READY`, `PENDING`, `UNAVAILABLE`).
- **Business Rules**: Physical movement into `FIELD` is prohibited unless Readiness State is strictly `READY` with valid medical clearance.

---

### 1.4 TEAM
- **Purpose**: A configured group of personnel assigned to perform specific tasks or missions.
- **Key Fields**: `team_id`, `name`, `lead_person_id`, `state`, `min_members`, `required_specialties`.
- **Lifecycle States**:
  - Nominal: `FORMING` → `READY` → `DEPLOYED` → `FIELD` → `RETURNED`
- **Relationships**:
  - `CONTAINS` → `PERSON`
  - `SUPPORTS` → `MISSION`
- **Business Rules**: A team cannot enter `READY` if any mandatory specialized qualification role (e.g., Polar Field Medic, Senior Snowcat Operator) is vacant.

---

### 1.5 CARGO CONSIGNMENT
- **Purpose**: A batch of cargo booked under a single manifest for transit to or within Antarctica.
- **Key Fields**: `consignment_id`, `expedition_id`, `manifest_number`, `shipper`, `destination_location_id`, `weight_kg`, `volume_cbm`, `hazardous_class`, `state`, `derived_risk`.
- **Lifecycle States**:
  - Nominal: `REQUESTED` → `DECLARED` → `APPROVED` → `PACKED` → `READY` → `DISPATCHED` → `IN_TRANSIT` → `ARRIVED` → `RECEIVED`
  - Exceptions: `HELD`, `DELAYED`, `DAMAGED`, `LOST`, `REJECTED`
- **Relationships**:
  - `CONTAINS` → `CARGO_PACKAGE`
  - `MOVES_VIA` → `TRANSPORT_LEG`
  - `DELIVERED_TO` → `LOCATION`
- **Derived State**: `CargoRisk` (`ON_TRACK`, `AT_RISK`, `LATE`, `MISSED`).
- **Business Rules**: Hazardous consignments cannot be loaded on combined passenger transport legs without explicit safety waiver documentation.

---

### 1.6 CARGO PACKAGE
- **Purpose**: An individual crate, pallet, ISO container, or fuel bladder within a consignment.
- **Key Fields**: `package_id`, `consignment_id`, `barcode_rfid`, `dimensions`, `weight_kg`, `temperature_class` (AMBIENT, CHILLED, FROZEN), `state`.
- **Lifecycle States**:
  - Nominal: `PACKED` → `LOADED` → `IN_TRANSIT` → `RECEIVED` → `ISSUED` → `RETURNED`
  - Exceptions: `HELD`, `DAMAGED`, `LOST`
- **Relationships**:
  - `BELONGS_TO` → `CARGO_CONSIGNMENT`
  - `REPLENISHED_BY` / `CONVERTS_TO` → `INVENTORY`
  - `RESERVED_FOR` → `MISSION` or `ASSET`

---

### 1.7 INVENTORY / STOCK
- **Purpose**: Goods, rations, fuel, medical supplies, and spare parts stored at station warehouses, field depots, or in transit.
- **Key Fields**: `stock_id`, `sku`, `name`, `category` (FUEL, FOOD, MEDICAL, SPARES, SURVIVAL, SCIENCE), `location_id`, `quantity_physical`, `quantity_reserved`, `quantity_quarantined`, `quantity_available`, `reorder_threshold`, `unit_of_measure`.
- **Lifecycle & Storage States**:
  - Lifecycle: `ON_ORDER` → `INBOUND` → `AVAILABLE` → `RESERVED` → `ISSUED` → `CONSUMED`
  - Side States: `TRANSFERRED`, `QUARANTINED`, `DISPOSED`
- **Crucial Derivation Rule**:
  `quantity_available` is **NEVER** manually edited. It is derived:
  $$\text{Quantity Available} = \text{Quantity Physical} - (\text{Quantity Reserved} + \text{Quantity Quarantined} + \text{Quantity Consumed})$$
- **Derived State**: `InventoryExposure` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Business Rules**: Fuel reserves below 45 days consumption trigger `InventoryExposure = CRITICAL` and raise an immediate operational constraint violation.

---

### 1.8 ASSET
- **Purpose**: High-value, reusable equipment (snowcats, PistonBullys, generators, skidoos, cranes, sledges, scientific radar systems).
- **Key Fields**: `asset_id`, `serial_number`, `name`, `asset_type`, `location_id`, `state`, `operating_hours`, `last_maintenance_date`, `next_maintenance_due`, `derived_availability`.
- **Lifecycle States**:
  - Nominal: `AVAILABLE` → `RESERVED` → `DEPLOYED` → `IN_USE` → `MAINTENANCE` → `SERVICEABLE`
  - Exceptions: `UNSERVICEABLE`, `RETIRED`
- **Relationships**:
  - `LOCATED_AT` → `LOCATION`
  - `OPERATED_BY` → `PERSON`
  - `ASSIGNED_TO` → `MISSION`
  - `DEPENDS_ON` → `INVENTORY` (Spares, Lubricants)
- **Derived State**: `AssetAvailability` (`AVAILABLE`, `LIMITED`, `UNAVAILABLE`).
- **Business Rules**: An asset cannot be transitioned to `IN_USE` if `operating_hours >= next_maintenance_due` without maintenance supervisor override.

---

### 1.9 TRANSPORT LEG
- **Purpose**: A planned or executed movement of cargo and personnel via air (DROMLAN / Twin Otter), sea (Chartered Icebreaker), or overland traverse.
- **Key Fields**: `leg_id`, `mode` (AIR, SEA, OVERLAND_TRAVERSE), `carrier_vessel_code`, `departure_location_id`, `arrival_location_id`, `etd`, `atd`, `eta`, `ata`, `state`, `derived_feasibility`.
- **Lifecycle States**:
  - Nominal: `PLANNED` → `BOOKED` → `READY` → `DEPARTED` → `IN_TRANSIT` → `ARRIVED` → `CLOSED`
  - Exceptions: `DELAYED`, `DIVERTED`, `CANCELLED`
- **Relationships**:
  - `MOVES_VIA` (supports) → `CARGO_CONSIGNMENT`, `PERSON`
  - `CONSTRAINED_BY` → `TIME_WINDOW`
- **Derived State**: `TransportFeasibility` (`FEASIBLE`, `CONSTRAINED`, `UNAVAILABLE`).

---

### 1.10 LOCATION
- **Purpose**: A geographical node in the polar network (Station, Field Camp, Fuel Depot, Anchorage, Airfield Runway, Waypoint).
- **Key Fields**: `location_id`, `name`, `code` (e.g., IN-MAITRI, IN-BHARATI, ZA-CPT), `coordinates` (Lat/Lon/Alt), `type`, `capacity_pob` (Persons On Board), `fuel_capacity_litres`, `state`.
- **Lifecycle States**:
  - `AVAILABLE` → `RESTRICTED` → `INACCESSIBLE` → `CLOSED`
- **Relationships**:
  - `LOCATED_AT` (Target of entities)

---

### 1.11 INCIDENT
- **Purpose**: An unplanned emergency, equipment breakdown, extreme weather event, or medical crisis.
- **Key Fields**: `incident_id`, `title`, `severity` (LOW, MEDIUM, HIGH, LIFE_SAFETY), `state`, `detected_timestamp`, `location_id`, `commander_person_id`.
- **Lifecycle States**:
  - Nominal: `DETECTED` → `TRIAGED` → `DECLARED` → `RESPONSE_ASSIGNED` → `ACTIVE` → `STABILIZED` → `RESOLVED` → `CLOSED`
- **Relationships**:
  - `OCCURS_AT` → `LOCATION`
  - `AFFECTS` → `PERSON`, `ASSET`, `MISSION`, `TRANSPORT_LEG`
  - `SUPPORTS` → `RESPONSE_ACTION`

---

### 1.12 DOCUMENT
- **Purpose**: Regulatory, customs, environmental clearance (Madrid Protocol EIA), or medical records required for expedition legality and safety.
- **Key Fields**: `document_id`, `title`, `doc_type`, `entity_type`, `entity_id`, `state`, `expiry_date`, `verified_by`.
- **Lifecycle States**:
  - Nominal: `REQUIRED` → `DRAFT` → `SUBMITTED` → `APPROVED`
  - Exceptions: `REJECTED`, `EXPIRED`, `MISSING`

---

### 1.13 ASSIGNMENT
- **Purpose**: The binding of a Person or Asset to a specific Team, Mission, or Incident Response role.
- **Key Fields**: `assignment_id`, `assignee_type` (PERSON, ASSET), `assignee_id`, `target_type` (MISSION, TEAM, INCIDENT), `target_id`, `start_time`, `end_time`, `state`.
- **Lifecycle States**:
  - `PROPOSED` → `APPROVED` → `ACTIVE` → `COMPLETED` → `CANCELLED`

---

### 1.14 TIME WINDOW
- **Purpose**: A first-class operational entity representing environmental, operational, or logistical temporal bounds.
- **Key Fields**: `window_id`, `subject_type` (e.g., AIRFIELD_RUNWAY, SEA_ICE_OFFLOAD, SCIENCE_WINDOW), `subject_id`, `open_time`, `close_time`, `is_hard` (boolean), `status` (OPEN, CLOSING_SOON, CLOSED, EXPIRED).
- **Business Rules**: A hard time window closure automatically invalidates any associated scheduled transport leg or mission readiness.

---

### 1.15 SUPPORTING OPERATIONAL ENTITIES
- **CONSTRAINT**: A rule evaluated against current state (e.g., `FuelReserveFloor`, `MinTeamStaffing`, `HazardousSegregation`, `TimeWindowAdherence`).
- **REPLAN**: A structured operational recommendation package triggered when a hard constraint is broken.
- **RECOMMENDATION**: Specific alternative proposed by the replan engine (e.g., "Reallocate Snowcat PB-02 to Mission Gamma").
- **APPROVAL**: The auditable decision record authored by an authorized operator accepting or rejecting a recommendation.
- **RESPONSE ACTION**: Action item dispatched during an incident response workflow.

---

## 2. Authoritative Operational Event Model

Operational events are **immutable, auditable, and append-only**. Event history is never truncated or overwritten.

### 2.1 Event Schema
```json
{
  "event_id": "uuid-v4",
  "event_type": "string (e.g., CargoDelayed, AssetUnavailable)",
  "entity_type": "string (e.g., CARGO_CONSIGNMENT, ASSET)",
  "entity_id": "string",
  "previous_state": "string or null",
  "new_state": "string",
  "timestamp": "ISO-8601 UTC string",
  "source": "string (USER_ACTION, SCHEDULED_CHECK, EXTERNAL_ADVISORY)",
  "actor": "string (person_id or SYSTEM)",
  "location": "string (location_id or coordinates)",
  "evidence": "object / jsonb (metadata, telemetry snapshot, notes)",
  "correlation_id": "uuid-v4 (links cascading event chains)"
}
```

### 2.2 Standard Operational Event Types
- **Logistics**: `CargoRequested`, `CargoDispatched`, `CargoDelayed`, `CargoReceived`, `CargoDamaged`, `CargoLost`
- **Transport**: `TransportLegPlanned`, `TransportDeparted`, `TransportDelayed`, `TransportDiverted`, `TransportArrived`, `TransportCancelled`
- **Personnel**: `PersonNominated`, `PersonCleared`, `PersonUnavailable`, `PersonArrived`, `PersonMedevacRequested`
- **Assets & Spares**: `AssetReserved`, `AssetDeployed`, `AssetUnavailable`, `MaintenanceStarted`, `MaintenanceCompleted`, `StockReserved`, `StockoutDetected`
- **Missions**: `MissionScheduled`, `MissionBlocked`, `MissionStarted`, `MissionCompleted`, `MissionDeferred`
- **Incidents**: `IncidentDetected`, `IncidentDeclared`, `ResponseActionDispatched`, `IncidentStabilized`, `IncidentResolved`
- **Planning**: `ConstraintViolated`, `ReplanTriggered`, `PlanRecommendationGenerated`, `PlanApproved`, `PlanRejected`

---

## 3. State Propagation Model

The deterministic state propagation pipeline is executed in shared backend domain services:

```
[Operational State Change Trigger]
              ↓
  1. Emit & Persist OperationalEvent
              ↓
  2. Query Semantic Dependency Graph
              ↓
  3. Identify Impacted Upstream/Downstream Objects
              ↓
  4. Recalculate Derived States (Readiness, Exposure, Risk)
              ↓
  5. Evaluate Constraints against Recalculated State
              ↓
  6. Are any Hard Constraints Violated?
     ├── NO  → Terminate pipeline, broadcast updated state
     └── YES → Formulate Planning Problem
                    ↓
               Generate Viable Replan Recommendations
                    ↓
               Queue for Human Review & Sign-Off
                    ↓
               Operator Approves / Modifies / Rejects
                    ↓
               Apply Approved Mutation via OperationalEvent
```

---

## 4. Derived State Specifications

Core derived states must never be arbitrary or manually editable. They are strictly calculated based on clear criteria:

| Derived Field | Allowed Values | Derivation Criteria |
| :--- | :--- | :--- |
| **Expedition Readiness** | `READY`, `AT_RISK`, `BLOCKED` | `BLOCKED` if any critical life-support/fuel mission is BLOCKED; `AT_RISK` if any non-critical mission is BLOCKED or critical cargo delayed; else `READY`. |
| **Mission Readiness** | `READY`, `AT_RISK`, `BLOCKED` | `BLOCKED` if required personnel missing, required asset unserviceable, or cargo missed; `AT_RISK` if required cargo delayed but within soft window; else `READY`. |
| **Cargo Risk** | `ON_TRACK`, `AT_RISK`, `LATE`, `MISSED` | `ON_TRACK` if ETA <= ETD Window; `AT_RISK` if ETA within 48h of Hard Window; `LATE` if ETA > Window but Mission deformable; `MISSED` if Window passed. |
| **Inventory Exposure** | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | `CRITICAL` if Available <= Emergency Reserve Floor; `HIGH` if Available <= Reorder Threshold; `MEDIUM` if lead time exceeds resupply window; else `LOW`. |
| **Asset Availability** | `AVAILABLE`, `LIMITED`, `UNAVAILABLE` | `UNAVAILABLE` if state in (`MAINTENANCE`, `UNSERVICEABLE`, `RETIRED`); `LIMITED` if maintenance due in < 20 operating hours; else `AVAILABLE`. |
| **Personnel Readiness** | `READY`, `PENDING`, `UNAVAILABLE` | `UNAVAILABLE` if medical hold or not cleared; `PENDING` if clearance in review; else `READY`. |
| **Transport Feasibility** | `FEASIBLE`, `CONSTRAINED`, `UNAVAILABLE` | `UNAVAILABLE` if leg cancelled or destination runway closed; `CONSTRAINED` if weather window deteriorating; else `FEASIBLE`. |

> **Prohibition**: Arbitrary fake percentages (e.g. "87% ready") are forbidden unless backed by an explicit, transparent, deterministic scoring equation.

---

## 5. Master Dependency Chains

```
CHAIN A — PLANNING
MISSION
  ├── REQUIRES → PEOPLE (Team Members, Specialists)
  ├── REQUIRES → ASSETS (Snowcats, Drilling Rigs)
  ├── REQUIRES → CARGO (Equipment, Consumables)
  ├── REQUIRES → INVENTORY (Fuel, Rations, Spares)
  ├── MOVES_VIA → TRANSPORT (Flight legs, Traverses)
  └── CONSTRAINED_BY → TIME WINDOW (Weather windows, Sea ice)

CHAIN B — LOGISTICS
CARGO CONSIGNMENT
  ├── CONTAINS → CARGO PACKAGE
  ├── MOVES_VIA → TRANSPORT LEG
  ├── DELIVERED_TO → LOCATION
  └── REPLENISHES → INVENTORY (Warehouse stock at Station)

CHAIN C — INCIDENT
INCIDENT
  ├── OCCURS_AT → LOCATION
  ├── AFFECTS → PEOPLE (Casualties, Responders)
  ├── AFFECTS → ASSETS (Damaged equipment)
  ├── REQUIRES → RESOURCES (Emergency fuel, Medical kits)
  └── TRIGGERS → RESPONSE ACTION & REPLAN

CHAIN D — RESOURCE & MAINTENANCE
ASSET
  ├── REQUIRES → MAINTENANCE
  ├── DEPENDS_ON → SPARE PARTS (Inventory)
  ├── REPLENISHED_BY → RESUPPLY CARGO
  └── IMPACTS → MISSION READINESS
```
