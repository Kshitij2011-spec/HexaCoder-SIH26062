# SIH26062 — Project Context

## Project Information
- **Project**: HexaCoders
- **Problem Statement ID**: SIH26062
- **Title**: Integrated Polar Expedition Logistics and Asset Management System
- **Domain**: Polar Operations / Antarctic Logistics & Asset Governance

---

## 1. The Operational Problem

Polar expeditions (such as the Indian Antarctic Expeditions to Maitri and Bharati stations, Larsemann Hills, and Schirmacher Oasis) operate in one of the most unforgiving environments on Earth. 

Key real-world operational challenges include:
1. **Severe Environmental Windows**: Sea-ice conditions, blizzard seasons, catabatic wind events, and sub-zero temperatures dictate strict, non-negotiable temporal windows for ship arrival, offloading, overland traversing, and air operations (DROMLAN).
2. **Extreme Supply Chains**: Resupply vessels sail months in advance from ports like Cape Town or Mormugao. Once the shipping window shuts, missing cargo or spares cannot simply be re-ordered.
3. **Complex Interdependencies**: A single failure in a logistics asset propagates catastrophic downstream impacts. For example, a specialized piston ring missing from an air cargo consignment halts a PistonBully snowcat; without the snowcat, fuel bladders cannot be hauled to fuel depot Alpha; without fuel depot Alpha, an inland glaciological science mission cannot deploy.
4. **Isolated Operational Silos**: Historically, personnel rosters, cargo manifests, warehouse inventory at stations, transport bookings, and field missions are managed via disconnected spreadsheets, radio logs, and independent records.

---

## 2. Tracking vs. Operational Decision Support

Most software built for logistics stops at **passive tracking**:
- Showing a list of cargo boxes.
- Showing an inventory table with current counts.
- Displaying a map with a pin for a vessel or station.

Passive tracking fails when conditions change. Knowing that a container is delayed by 72 hours in Cape Town is useless unless the expedition leader knows:
- *Which specific missions depend on the contents of that container?*
- *Are there qualified personnel sitting idle awaiting that equipment?*
- *Does the delay violate the weather window for the sea-ice runway?*
- *Can station spares be reallocated to preserve the high-priority ice-core drilling mission?*
- *What actionable options exist, and what trade-offs must the expedition leader decide upon?*

**The core product concept is a CONNECTED EXPEDITION OPERATIONAL STATE SYSTEM.**

The central question answered by the platform at any given second is:
> **“What is the current expedition state, what changed, what does it affect, what constraints are now violated, what options exist, and what should the operator approve?”**

---

## 3. The Core Reasoning Chain

The platform operates on a continuous, deterministic reasoning cycle:

```
STATE
  ↓
EVENT
  ↓
DEPENDENCIES
  ↓
IMPACT
  ↓
CONSTRAINTS
  ↓
REPLAN
  ↓
HUMAN APPROVAL
  ↓
UPDATE
  ↓
AUDIT
```

1. **STATE**: The current comprehensive operational state across people, assets, cargo, inventory, locations, missions, and transport.
2. **EVENT**: A discrete, auditable occurrence (e.g., `CargoDelayed`, `AssetDamaged`, `WeatherWindowClosed`, `PersonMedicalHold`).
3. **DEPENDENCIES**: The graph of semantic relationships linking entities (e.g., `Mission X REQUIRES Asset Y`, `Asset Y DEPENDS_ON Cargo Z`).
4. **IMPACT**: Computation of derived statuses across all connected nodes in the dependency chain.
5. **CONSTRAINTS**: Verification against hard rules (survival limits, fuel minimums, minimum crew qualifications, weather windows, equipment availability).
6. **REPLAN**: Automated synthesis of actionable mitigation options and recommendations when hard constraints are violated.
7. **HUMAN APPROVAL**: Explicit review, justification, and sign-off by the authorized expedition officer.
8. **UPDATE**: Atomic state transition applied across affected entities.
9. **AUDIT**: Immutable recording of the full event chain, decisions made, and rationale.

---

## 4. Master Interdependency Scenarios

### Scenario A: Cargo Delay Cascading into Mission Re-planning
- **Initial Event**: Air transport leg carrying high-precision seismometer replacement sensors from Cape Town is delayed by 5 days due to blizzard conditions at Troll Airfield.
- **Dependency Flow**:
  - Transport Leg `TL-202` delayed → Cargo Consignment `CC-SEIS-09` ETA pushed past Jan 18.
  - Package `PKG-441` contains sensor units `SKU-SEIS-01`.
  - Mission `MSN-DEEP-CRUST` has an open field-work weather window ending Jan 24.
  - Mission requires minimum 7 days setup time once sensors arrive.
- **Constraint Violation**: Window closes before minimum operational setup is possible (`HardTimeWindowExceeded`).
- **Replanning Option**: Replan engine suggests deferring `MSN-DEEP-CRUST` to Window 2 (February) and reassigning the assigned snowcat `ASSET-PB-02` to support the fuel traverse for `MSN-GLACIER-SURVEY`.
- **Approval**: Expedition leader reviews options, accepts Option A, inputs justification, and approves.

### Scenario B: Spare Shortage & Critical Asset Maintenance
- **Initial Event**: Routine pre-traverse inspection of Snowcat `ASSET-PB-01` reveals hydraulic hose blowout (`AssetDamaged`).
- **Dependency Flow**:
  - Asset enters `MAINTENANCE`.
  - Required repair part: `SKU-HYD-HOSE-08` (qty: 2).
  - Station warehouse inventory shows physical count = 1 available, 1 reserved for Generator GenSet-2 emergency backup.
- **Constraint Violation**: Generator safety rule requires 1 spare hose reserved at all times (`CriticalLifeSupportReserve`).
- **Replanning Option**: System discovers compatible secondary hose `SKU-HYD-HOSE-09` in field container `FC-04`, currently unreserved, but requires 4 hours technical testing.
- **Approval**: Chief Mechanical Engineer approves substitution; inventory reservation updates atomically.

### Scenario C: Personnel Medical Disqualification
- **Initial Event**: Glaciologist Dr. Sharma suffers severe frostbite and is medically categorized as `UNAVAILABLE`.
- **Dependency Flow**:
  - Person readiness becomes `UNAVAILABLE`.
  - Team `TEAM-POLAR-SURVEY-A` drops below mandatory minimum personnel requirement (minimum 3, currently 2).
  - Mission `MSN-ICE-RADAR` readiness transitions to `BLOCKED`.
- **Replanning Option**: Replan engine scans station roster for qualified substitutes holding Glacier Safety Cert Level 2. Recommends Dr. Roy (currently on standby).
- **Approval**: Science Coordinator and Expedition Leader approve team roster modification.

### Scenario D: Transport Leg Diverted
- **Initial Event**: Supply Vessel `MV Vasiliy Golovnin` encounters impenetrable fast ice near Maitri approach and is diverted to emergency anchorage point 40km east.
- **Dependency Flow**:
  - Offload coordinates shift by 40km.
  - Offload travel time for snowcat sledges increases from 2 hours to 8 hours per transit.
  - Total diesel consumption for offload traverse increases by 3,200 Litres.
- **Constraint Violation**: Remaining station fuel reserve dips below the mandatory 30-day blizzard safety floor during transport.
- **Replanning Option**: Stage offload in two phases; prioritize food and fuel bladders first; delay non-critical container offloading.

---

## 5. What the Product IS and IS NOT

### The Product IS:
- A **Connected Expedition Operational State System**.
- An operational decision support platform for polar expedition leadership, station logistics coordinators, and mission planners.
- A deterministic engine for relationship tracking, event auditing, constraint enforcement, and replan recommendations.
- A resilient platform designed to maintain consistent state under low-bandwidth, intermittent satellite connectivity.

### The Product IS NOT:
- A station SCADA system or live generator telemetry monitor.
- A 3D digital twin or generic station visualizer.
- A simple CRUD database for boxes and barcodes.
- A live connection to Indian governmental/NCPOR defense systems (all MVP operational data is synthetic/benchmark).
- An autonomous AI system that issues commands without human approval.
