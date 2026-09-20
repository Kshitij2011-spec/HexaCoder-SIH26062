# Milestone A10 — Architectural & Product Preflight Audit

**Date**: 2026-09-20  
**Repository Baseline**: `75c3c483096d3bf3db157ea97a31d2cd3104f9e0` (`main == origin/main`, working tree clean)  
**Track**: Track A (Planning, Decision, Controls, Platform Integration)  
**Mode**: READ-ONLY Architectural & Product Preflight  

---

## 1. Baseline Verification

The repository baseline was verified prior to audit execution:

```powershell
git fetch origin --prune
git checkout main
git pull --ff-only origin main
git status --short
git rev-parse HEAD
git rev-parse origin/main
git diff --check
```

### Verification Output
- **Branch**: `main`
- **HEAD Commit**: `75c3c483096d3bf3db157ea97a31d2cd3104f9e0`
- **Remote Commit**: `75c3c483096d3bf3db157ea97a31d2cd3104f9e0` (`origin/main`)
- **Status**: Working tree completely CLEAN.
- **Git Diff Check**: 0 whitespace, merge conflict, or syntax issues.
- **Migrations Intact**: 10 authoritative migrations present in `supabase/migrations/`.
- **Test Baseline**: 248 backend pytest assertions and 143 frontend vitest assertions passing green.

---

## 2. Repository Capability Matrix

The platform has integrated Milestones A1–A9 and B1–B9:
- **A5**: Operational Control Tower Overview & Mission Readiness Matrix
- **A6**: Closed-Loop Disruption Cockpit & Approval Workflow
- **A7**: Incident → Replan Escalation
- **A8**: Client-Side Offline / Store-and-Forward Sync Outbox
- **A9**: Polar Utility & Consumables Runway Engine

Below is the authoritative, repository-grounded capability classification across all 14 operational domains:

| # | Domain / Subsystem | Repository Evidence & Implementation State | Status Taxonomy |
| :--- | :--- | :--- | :--- |
| **1** | **Mission Scheduling & Temporal Planning** | `MissionModel` (`start_at`, `end_at`, `required_by_at`, `priority`, `status`). `TimeWindowModel` (`open_at`, `close_at`, `hard_or_soft`, `subject_type`, `subject_id`). `MissionReadinessService._evaluate_time_windows()` checks status. In Control Tower, missions appear as readiness cards, but without a temporal schedule timeline, Gantt view, or forward-looking window conflict solver. | **IMPLEMENTED AND INTEGRATED (Basic)** / **FOUNDATION-ONLY (Temporal Horizon)** |
| **2** | **Personnel / Team Readiness & Field Safety** | `PersonModel` has dual-state tracking (`readiness_state`: NOMINATED, CLEARANCE_PENDING, READY, NOT_CLEARED, UNAVAILABLE; `movement_state`: NOT_DEPLOYED, IN_TRANSIT, AT_STATION, FIELD, RETURNING, RETURNED). `TeamModel` tracks team leader, mission, location, status. `assignments` table maps people to missions with certified roles (`LEAD_SAFETY_OFFICER`, `PRINCIPAL_INVESTIGATOR`). `evaluate_personnel_staffing()` in `rules.py` and `_evaluate_personnel()` in `readiness/mission.py` evaluate blockers. **HOWEVER**, `frontend/src/features/people` and `frontend/src/features/teams` are completely EMPTY. Control Tower has ZERO personnel visibility. `ReplanActionType.REASSIGN_PERSONNEL` is declared in `replanning/states.py` but has ZERO option generator or apply code in `replanning/service.py`. | **BACKEND-ONLY** / **IMPLEMENTED BUT NOT EXPOSED IN CONTROL TOWER** |
| **3** | **Incident Response & Propagation** | Full Track B domain (`IncidentModel`, `IncidentReferenceModel`, `IncidentPropagationModel`, `IncidentActionModel`). Escalation to replanning integrated in A7 (`IncidentEscalationBanner`, `incident_escalation.py`). | **IMPLEMENTED AND INTEGRATED** |
| **4** | **Inventory / Resource Continuity & Runway** | Track B inventory domain (`InventoryItemModel`, `InventoryStockLotModel`, `InventoryTransactionModel`). Integrated into Control Tower in A9 (`runway.py`, `ResourceRunwayPanel.tsx`, `RESOURCE_RUNWAY_HORIZON` constraint rule). | **IMPLEMENTED AND INTEGRATED** |
| **5** | **Offline Synchronization & Reconciliation** | Track B sync domain (`OfflineOperationModel`, `sync_service.py`). Integrated in A8 (`frontend/src/lib/sync/`, `OfflineSyncIndicator.tsx`, `OfflineSyncDrawer.tsx`, `OfflineSyncSection.tsx`). | **IMPLEMENTED AND INTEGRATED** |
| **6** | **Operational Event Journal** | `OperationalEventModel`, `EventRepository`, `EventService`, DB immutability trigger `fn_prevent_operational_event_mutation`. Rendered live in Control Tower `OperationalEventsFeed.tsx`. | **IMPLEMENTED AND INTEGRATED** |
| **7** | **Consequential Audit** | `AuditLogModel`, `AuditRepository`, `AuditService`. Rendered in Control Tower `ConsequentialAuditTimeline.tsx`. | **IMPLEMENTED AND INTEGRATED** |
| **8** | **Replanning & Approval Pipeline** | `ReplanModel`, `ReplanOptionModel`, `RecommendationModel`, `ApprovalModel`. Modals in Control Tower: `InitiateReplanModal`, `MitigationOptionsExplorer`, `ApprovalModal`, `DecisionQueuePanel`. | **IMPLEMENTED AND INTEGRATED** |
| **9** | **Science / Instrument Continuity** | Track B assets domain (`AssetModel`, `MaintenanceRecordModel`). Evaluated in `_evaluate_assets()` in `readiness/mission.py`. Replan option `REASSIGN_ASSET` implemented. Exposed in `frontend/src/features/assets/AssetsPage.tsx`. | **IMPLEMENTED AND INTEGRATED** |
| **10** | **Station Utility / Resource Continuity** | Integrated in A9 via the Polar Consumables Runway Engine for station fuels, water, life-support rations, and critical spares. | **IMPLEMENTED AND INTEGRATED** |
| **11** | **Operational Handover / Watch Continuity** | Continuous 24/7 polar station command shifts (Station Commander / Ops Watch). No formal shift handover briefing, snapshot, or dual-officer sign-off event currently exists. | **TRULY MISSING** |
| **12** | **Cross-Domain Operational Timeline** | `OperationalTimelineService` in Track B (`operations/timeline.py`, 34KB) aggregates events, audits, offline operations, and incident propagations for Person B resources with 1-hop relation discovery. `useOperationalTimeline.ts` exists on frontend, but has NO UI page or Control Tower integration. | **BACKEND-ONLY** / **IMPLEMENTED BUT NOT EXPOSED** |
| **13** | **Multi-Leg Resupply Horizon Sync** | In A9, `next_inbound_at` on `InventoryStockLotModel` is a static field rather than dynamically derived from `TransportLegModel.estimated_arrival_at` carrying `CargoConsignmentModel`. | **PARTIALLY DECOUPLED** |
| **14** | **Station Telemetry & SCADA Replacement** | Direct physical sensor feeds, generator frequency monitoring, live AIS feeds. | **OUT OF SCOPE** (Constitution Rule 11 & Rule 5) |

---

## 3. Remaining Gaps Identified

1. **The Human Operational Blind Spot**:
   Expedition operations are fundamentally about human survival and field safety. While the backend has extensive data structures for people (`PersonModel`), functional teams (`TeamModel`), dual-state transitions (`PersonReadiness`, `PersonMovement`), and mission role assignments, the Control Tower presents **zero visibility into expedition personnel**. Operators cannot see who is deployed in the field, who is at station, who is awaiting medical clearance, or whether field teams have experienced fatal safety officer / specialist dropouts.
2. **Unimplemented `REASSIGN_PERSONNEL` Replan Action**:
   In `backend/app/domains/replanning/states.py`, `ReplanActionType.REASSIGN_PERSONNEL` is an authoritative enum value. However, inside `backend/app/domains/replanning/service.py`, `generate_options()` has candidate generators for `MODIFY_TRANSPORT`, `RESCHEDULE_MISSION`, `DEFER_ACTIVITY`, and `REASSIGN_ASSET`, but **zero logic for `REASSIGN_PERSONNEL`**. Furthermore, `apply()` has no handler for personnel reassignments. If a field team member falls ill or is placed on medical hold (`NOT_CLEARED`), the mission readiness drops to `BLOCKED`, but the operator cannot resolve the blocker through the closed-loop replanning pipeline!
3. **Static Replenishment Horizon Coupling**:
   Consumables runway forecasting in A9 depends on `next_inbound_at`, which is currently stored directly on `InventoryStockLotModel` rather than dynamically traversing the multi-leg transport network.
4. **Binary Time-Window Enforcement**:
   Temporal windows (`TimeWindowModel`) are evaluated as binary point-in-time checks (`status == "OPEN"`), rather than as a projected forward-looking schedule horizon that prevents missions from being rescheduled into closed weather/seasonal windows.
5. **No Formal Watch Handover Protocol**:
   Control Tower has 10 operational panels, but no unified shift transition protocol or certified handover dossier when watch duty changes between officers.

---

## 4. False or Stale Assumptions from Previous Milestones

1. **Stale Code Comment in Mission Readiness Service**:
   In `backend/app/services/readiness/mission.py` (line 275), the code comments: `"reason": "Assets module under development by Track B"`.
   *Fact*: Track B fully implemented the Assets and Maintenance domain in Milestone B4. The table `assets` is populated, active, and tested.
2. **False Assumption that Replan Engine Supports All Defined Action Types**:
   `ReplanActionType` declared `REASSIGN_PERSONNEL`, `ADJUST_CARGO_PLAN`, `SPLIT_ACTIVITY`, and `CANCEL_ACTIVITY`.
   *Fact*: Only `RESCHEDULE_MISSION`, `MODIFY_TRANSPORT`, and `DEFER_ACTIVITY` are actually executable in `apply()`. `REASSIGN_PERSONNEL` was declared but completely neglected.
3. **Assumption that Frontend Workspaces Exist for All Core Domains**:
   The repository contains directories `frontend/src/features/people` and `frontend/src/features/teams`.
   *Fact*: Both directories are completely empty. Operators have zero interface to inspect or manage people or teams outside of raw backend API requests.
4. **Assumption that Offline Sync Outbox Represents All Pending Operations**:
   A8 implemented client-side store-and-forward for offline mutations.
   *Fact*: The offline outbox only supports the mutation actions wired into the offline client. If personnel reassignments or new actions are added, they must be registered in the sync client.

---

## 5. Candidate Generation for Milestone A10

Below are 4 distinct, repository-grounded candidate directions for Milestone A10:

---

### Candidate 1: Personnel & Field Team Deployment Safety Engine
- **Operational Problem**:
  In Antarctic field logistics (45th ISEA), human safety and qualified team staffing are non-negotiable hard constraints. Field traverses and glaciology missions (e.g. `M-08` at Schirmacher Oasis) require verified team composition invariants: minimum headcounts, certified safety officers / guides, no personnel on medical hold or suspended, and strict tracking of movement states (`AT_STATION` vs `FIELD`). When a key team member is placed on medical hold or injured, mission readiness is blocked, but operators currently have no visibility into personnel deployment in Control Tower and no closed-loop replanning capability to reassign or substitute qualified personnel from the station complement.
- **Exact Repository Evidence**:
  - `backend/app/domains/people/models.py`: `PersonModel` (`readiness_state`, `movement_state`, `role`, `team_id`, `current_location_id`, `last_confirmed_location_id`).
  - `backend/app/domains/teams/models.py`: `TeamModel` (`code`, `name`, `leader_person_id`, `mission_id`, `location_id`, `status`).
  - `backend/app/domains/replanning/states.py`: `ReplanActionType.REASSIGN_PERSONNEL` defined in enum.
  - `backend/app/domains/replanning/service.py`: `generate_options()` lacks `REASSIGN_PERSONNEL` generator; `apply()` lacks `REASSIGN_PERSONNEL` execution.
  - `backend/app/services/constraints/rules.py`: `evaluate_personnel_staffing()` evaluates team headcount and unavailable members.
  - `backend/app/services/readiness/mission.py`: `_evaluate_personnel()` evaluates assigned teams and member readiness.
  - `frontend/src/features/people/` and `frontend/src/features/teams/`: Both empty directories.
  - `frontend/src/features/control-tower/`: Zero personnel or field team widgets.
- **Existing Backend Foundation**:
  - `PersonModel`, `TeamModel`, `PersonService`, `TeamService`, `PersonRepository`, `TeamRepository`, `validate_readiness_transition`, `validate_movement_transition`, `validate_team_transition`, events, audit logs.
- **Existing Frontend Foundation**:
  - None (empty directories).
- **New Technical Work Required**:
  - Backend:
    1. Implement deterministic `REASSIGN_PERSONNEL` candidate option generator in `replanning/service.py`: when a mission's assigned team has unready or disqualified personnel, query the station complement for cleared, unassigned/available personnel matching required role/qualifications and generate an explainable candidate substitution option.
    2. Implement `REASSIGN_PERSONNEL` application handler in `replanning/service.py` using `TeamService` / `PersonService` public contracts, emitting `TeamMemberReassigned` and `ReplanApplied` operational events.
    3. Add a Personnel & Field Team Deployment read model in `ControlTowerService`: station complement counts, field deployment headcounts, team composition safety checks, readiness breakdown.
    4. Expose `GET /api/v1/control-tower/personnel/{expedition_id}` or include in overview.
  - Frontend:
    1. Create `PersonnelDeploymentPanel.tsx` in `frontend/src/features/control-tower/components/`: displays station complement vs field deployed personnel, team readiness badges, medical clearance status, and a button to initiate replanning or reassign personnel.
    2. Add `reassign_personnel` workflow in `InitiateReplanModal.tsx` and support `REASSIGN_PERSONNEL` in `MitigationOptionsExplorer.tsx`.
    3. Unit tests for backend replanning option generation, approval, and application for personnel reassignment.
    4. Component and E2E browser tests for personnel deployment panel and substitution workflow.
- **Cross-Track Integration Value**:
  - Bridges Track A's People & Teams domains with Control Tower and closed-loop Replanning.
  - Reuses existing Track A `replanning`, `approval`, `audit`, `events`, `readiness`, and `constraints` services.
- **Implementation Scope**:
  - Focused, cohesive, high-leverage. Pure Track A code.
- **Demo / Hero Scenario**:
  - Schirmacher Oasis survey `M-08` requires Lead Field Safety Officer `PERS-R04-04` (Kavita Deshmukh).
  - Safety officer is placed on medical hold (`PersonMedicalHold` event emitted, readiness state -> `NOT_CLEARED`).
  - Mission `M-08` readiness immediately drops to `BLOCKED`.
  - Disruption detected in Control Tower Personnel Deployment Panel.
  - Operator initiates replan. Engine detects qualification gap and generates `OPT-01`: Reassign certified engineer/officer `PERS-R02-01` (Vikramaditya Rao) or standby specialist from station complement.
  - Operator reviews option rationale, selects recommendation, enters approval comment (`"Approved temporary safety guide reassignment from Maitri station crew"`).
  - Replan applied: Person assigned to team, mission readiness restored to `READY`, immutable event and audit logged.
- **Provenance Risk**: Low (`SYNTHETIC_DEMO` / `DERIVED`).
- **Scope Risk**: Low (uses existing tables and existing domain models).
- **Governance Implications**: High (preserves the Human Approval Rule: system recommends substitute, human operator approves).
- **Migration Requirement**: NO migrations required.
- **Track B Coupling**: Zero. Pure Track A domain ownership.

---

### Candidate 2: Environmental Window & Seasonal Boundary Temporal Planning Engine
- **Operational Problem**:
  Antarctic operations are strictly bound by seasonal boundaries, flight weather windows, sea-ice clearance windows, and daylight duration. Rescheduling a mission or delaying transport can push operations past environmental closing dates.
- **Exact Repository Evidence**:
  - `backend/app/domains/time_windows/models.py`: `TimeWindowModel` with 6 seeded windows (`MISSION_WINDOW`, `SEA_ICE_OFFLOAD`, `RUNWAY_WINDOW`, `TRAVERSE_WINDOW`, `WEATHER_FORECAST`).
  - `backend/app/services/constraints/rules.py`: `evaluate_time_window()` does a static point-in-time check (`tw.status == "OPEN"`).
- **Existing Backend Foundation**:
  - `TimeWindowModel`, `TimeWindowRepository`, `TimeWindowService`, `TimeWindowCreate`/`Update`.
- **Existing Frontend Foundation**:
  - None.
- **New Technical Work Required**:
  - Backend: Temporal horizon solver that projects mission start/end dates and transport ETAs against all overlapping time windows, checking for boundary violations.
  - Updating `RESCHEDULE_MISSION` in replanning to validate candidate dates against hard time windows.
  - Frontend: Gantt/Timeline visualizer for missions and environmental windows.
- **Scope Risk**: Moderate to High (building a responsive temporal Gantt UI in React without heavy third-party chart libraries can be complex).
- **Migration Requirement**: NO migrations required.
- **Track B Coupling**: Low to Moderate (crosses into transport legs).

---

### Candidate 3: Operational Watch Handover & Shift Continuity Dossier
- **Operational Problem**:
  Polar station ops rooms operate 24/7 in watches. Incoming officers need an authoritative, certified shift handover briefing synthesizing open disruptions, active replans, pending approvals, runway deficits, and field personnel.
- **Exact Repository Evidence**:
  - All data is present in `ControlTowerService.get_overview()`, but there is no formal handover protocol, briefing generator, or handover audit event.
- **Existing Backend Foundation**:
  - `ControlTowerService`, `AuditService`, `EventService`.
- **Existing Frontend Foundation**:
  - Control Tower overview cards.
- **New Technical Work Required**:
  - `OperationalHandoverService` compiling snapshot of all active operations.
  - Formal dual-officer sign-off workflow emitting `WatchHandoverLogged` event.
  - Handover Dossier modal/drawer.
- **Assessment**:
  - Highly valuable for operational continuity, but is largely a synthesizing readout and sign-off rather than an operational constraint-solving/state-propagation engine.

---

### Candidate 4: Multi-Leg Resupply Horizon & Inbound Cargo Horizon Synchronizer
- **Operational Problem**:
  In A9, `ResourceRunwayService` calculates consumables runway using a static `next_inbound_at` date on stock lots. In reality, inbound replenishment is carried by transport legs (`TransportLegModel` → `CargoConsignmentModel`). When vessel `T-08` is delayed, stock lot runway deficits should dynamically adjust.
- **Exact Repository Evidence**:
  - `TransportLegModel`, `TransportCargoAssignmentModel`, `CargoConsignmentModel`, `CargoPackageModel`, `InventoryStockLotModel`.
- **Assessment**:
  - Strong integration, but tightly couples Track A runway engine with Track B transport, cargo, and inventory internals. Modifying Track B domain relationships risks boundary violations under the Two-Person Parallel Development Rule.

---

## 6. Neutral Candidate Comparison Matrix

| Dimension | Candidate 1: Personnel & Field Team Deployment Safety Engine | Candidate 2: Environmental Window & Temporal Planning Engine | Candidate 3: Operational Watch Handover & Shift Continuity Dossier | Candidate 4: Multi-Leg Resupply Horizon & Cargo Chain Synchronizer |
| :--- | :--- | :--- | :--- | :--- |
| **Operational Relevance** | **CRITICAL**: Human life safety and qualified team staffing are polar hard constraints. | **HIGH**: Environmental windows govern polar execution feasibility. | **HIGH**: Operational continuity for 24/7 station command. | **MEDIUM-HIGH**: Dynamically connects cargo transport with consumables runway. |
| **Technical Depth** | **HIGH**: Closes unfulfilled `REASSIGN_PERSONNEL` replan generator/apply pipeline; dual-state personnel transitions; staffing invariant checks. | **HIGH**: Temporal window projection and schedule boundary conflict solver. | **MEDIUM**: Read-model synthesis and formal sign-off event recording. | **MEDIUM-HIGH**: Multi-table graph traversal across transport, consignments, packages, and lots. |
| **Existing Foundation** | **EXTENSIVE**: Complete backend models (`PersonModel`, `TeamModel`, `AssignmentModel`), repositories, services, and tests exist; `REASSIGN_PERSONNEL` enum already declared. | **MODERATE**: `TimeWindowModel` and basic CRUD service exist; basic point-in-time check in `rules.py`. | **HIGH**: `ControlTowerService.get_overview()` already gathers almost all constituent facts. | **MODERATE**: Separate models exist; no existing service linking transport arrival to lot replenishment. |
| **Integration Leverage** | **MAXIMUM**: Connects People & Teams (completely invisible currently) into Control Tower, Readiness Engine, Constraints, and Replan/Approval closed loop. | **HIGH**: Connects Time Windows with Missions, Transport Legs, and Replan Rescheduling. | **MEDIUM-HIGH**: Packages Control Tower into an auditable watch handover event. | **MEDIUM**: Links Track B Transport to Track A/B Inventory Runway. |
| **Hero-Demo Clarity** | **EXCEPTIONAL**: Medical hold / safety officer disqualification → Mission blocked → Replan generates qualified station substitute → Operator approves → Mission restored to ready. | **HIGH**: Transport delay pushes arrival past sea-ice closure → Temporal alert → Replan. | **HIGH**: Watch officer logs shift handover notes → Incoming officer reviews & signs off. | **MEDIUM**: Vessel delay shifts runway deficit date forward. |
| **Implementation Scope** | **BALANCED**: Read-model aggregation, option generator/apply handler, and Control Tower widget. | **LARGE**: Requires temporal calendar/Gantt UI and multi-window projection engine. | **COMPACT**: Dossier read model, sign-off workflow, modal. | **COMPLEX**: Cross-domain coupling between cargo, transport, inventory. |
| **Scope Risk** | **LOW**: Uses existing tables, existing schemas, and standard REST endpoints. | **MEDIUM-HIGH**: Risk of complex calendar/Gantt UI bloat. | **LOW**: Straightforward read-model and event emission. | **HIGH**: Modifies Track B domain logic and contracts. |
| **Data-Honesty Risk** | **ZERO**: All roles, states, and qualifications use explicit synthetic parameters and deterministic rules. | **LOW**: Deterministic ISO date window checks. | **ZERO**: Deterministic operational snapshot with explicit provenance. | **LOW-MEDIUM**: Requires assumptions on cargo unpacking lead times. |
| **Migration Requirement** | **NONE**: All tables (`people`, `teams`, `assignments`, `replans`, `approvals`) exist. | **NONE**: `time_windows` table exists. | **NONE**: `audit_logs` and `operational_events` exist. | **NONE** or minor foreign key index. |
| **Track-B Coupling** | **ZERO**: `people`, `teams`, `replanning`, `control_tower` are strictly Track A domains. | **LOW**: Mostly Track A missions and time windows. | **ZERO**: Pure Track A aggregation. | **HIGH**: Deep traversal into Track B cargo and transport tables. |

---

## 7. Selected Milestone A10 Direction

### **Direction**: Milestone A10 — Personnel & Field Team Deployment Safety Engine

### Architectural Rationale
1. **Closing the Only Unimplemented Replan Action Type**:
   `ReplanActionType.REASSIGN_PERSONNEL` was declared in `backend/app/domains/replanning/states.py` in Phase 10 / Milestone A4, but was left completely unimplemented in both `generate_options()` and `apply()`. Every other primary action type (`MODIFY_TRANSPORT`, `RESCHEDULE_MISSION`, `REASSIGN_ASSET`, `DEFER_ACTIVITY`) has complete generator and application logic. `REASSIGN_PERSONNEL` is the single outstanding unfulfilled contract in the replanning engine.
2. **Eliminating the Primary Blind Spot in Control Tower**:
   Expedition logistics are ultimately executed by human teams in hostile environments. The Control Tower currently monitors campaigns, disruptions, incidents, offline sync, consumable runway, mission readiness, active constraints, and audit trails. But it has **zero visibility into expedition personnel or field teams**.
3. **Completing the 4 Pillars of Closed-Loop Disruption Management**:
   - Logistics & Transport: A6 Closed-Loop Disruption Cockpit (`MODIFY_TRANSPORT`, `RESCHEDULE_MISSION`)
   - Asset & Physical Incidents: A7 Incident Escalation Cockpit
   - Utilities & Consumables: A9 Consumables Runway Engine
   - **Human & Field Safety: A10 Personnel & Field Team Deployment Safety Engine (`REASSIGN_PERSONNEL`)**
4. **Architectural Purity & Zero Migration**:
   - `PersonModel` already tracks `readiness_state`, `movement_state`, `role`, `team_id`, and `current_location_id`.
   - `TeamModel` already tracks `leader_person_id`, `mission_id`, `location_id`, and `status`.
   - `assignments` already links personnel to missions with explicit roles (`LEAD_SAFETY_OFFICER`, `PRINCIPAL_INVESTIGATOR`).
   - No database migrations or schema alterations required.
   - 100% Track A domain ownership: zero Track B code intrusion.

---

## 8. A10 Hero Scenario

```text
REAL OPERATIONAL INPUT
↓
Dr. Kavita Deshmukh (PERS-R04-04), Polar Field Safety Officer assigned to Glaciology Mission M-08,
develops cold-weather acute injury and is placed on MEDICAL HOLD (readiness_state: NOT_CLEARED).
Event emitted: PersonMedicalHold.
↓
SYSTEM DETECTION / AGGREGATION
↓
MissionReadinessService evaluates Mission M-08.
Blocker detected: "Team member 'PERS-R04-04' is in state 'NOT_CLEARED'".
Mission M-08 readiness drops to BLOCKED.
Control Tower Personnel Deployment Panel highlights:
- Station Complement: 5 Cleared, 1 Medical Hold
- Field Teams: Glaciology Science Team TEAM-45-A has 1 unready member (Field Safety Officer).
↓
IMPACT / REASONING
↓
Operator initiates closed-loop replanning for personnel gap.
Replanning engine triggers deterministic candidate option generator:
Identifies that Lead Field Safety Officer qualification is unmet on TEAM-45-A.
Queries station complement for cleared personnel with polar field qualification / experience at Maitri.
Generates explainable ReplanOption:
- OPT-01: Reassign cleared station specialist (e.g. PERS-R02-01 Vikramaditya Rao or available safety standby)
  to TEAM-45-A as acting Field Safety Officer.
Option Feasibility: FEASIBLE. Rationale: "Cleared personnel present at station base available for field deployment."
↓
OPERATOR DECISION
↓
Operator inspects mitigation options in MitigationOptionsExplorer.
Reviews trade-off: Preserves M-08 schedule without mission cancellation.
Selects Recommendation: "Reassign Field Safety Officer for Mission M-08".
↓
HUMAN APPROVAL
↓
Operator opens ApprovalModal.
Selects Decision: APPROVED.
Enters justification: "Approved temporary safety guide reassignment from Maitri station crew to restore M-08 field deployment safety."
Approval record persisted with approver ID, timestamp, and justification.
↓
EXPLICIT APPLICATION
↓
Operator clicks Apply Approved Changes.
Replanning engine executes ReplanApply:
- Calls TeamService / PersonService to update team assignment.
- Emits immutable operational event: TeamMemberReassigned and ReplanApplied.
- Updates Replan and Recommendation status to APPLIED.
↓
AUDIT / EVENT MEMORY
↓
Mission M-08 readiness deterministically re-evaluates to READY.
Personnel Deployment Panel updates: TEAM-45-A restored to 100% qualified readiness.
Audit timeline captures full chain:
PersonMedicalHold → ReplanRequested → RecommendationApproved → ReplanApplied → TeamMemberReassigned.
```

---

## 9. Acceptance Criteria for Milestone A10

1. **Deterministic Personnel Replan Option Generator**:
   - `ReplanningService.generate_options()` must inspect assigned personnel readiness for impacted missions.
   - When an assigned team member is `NOT_CLEARED` or `UNAVAILABLE`, generate a deterministic `REASSIGN_PERSONNEL` option if an eligible cleared person exists in the expedition station complement.
   - If no eligible candidate exists, generate an explainable `NOT_EVALUABLE` or `INFEASIBLE` option with explicit missing qualification details.
2. **Controlled Personnel Reassignment Application**:
   - `ReplanningService.apply()` must implement `ReplanActionType.REASSIGN_PERSONNEL.value`.
   - Reassignment must execute strictly through domain models/services, enforcing expedition isolation.
   - Emits immutable operational event (`TeamMemberReassigned` or `PersonAssignedToTeam`) and audit log.
   - Must be fully idempotent (re-applying an already APPLIED recommendation is a safe no-op).
3. **Control Tower Personnel & Field Team Deployment Panel**:
   - Control Tower Overview must include a dedicated `PersonnelDeploymentPanel` (or `PersonnelPostureSummary`).
   - Surfaces:
     - Station complement count vs field deployed count.
     - Medical clearance breakdown (Cleared vs Medical Hold / Unavailable).
     - Team status (Forming, Active, Deployed, Disbanded) and assigned mission.
     - Visual badge indicating whether team staffing and required roles are fully met.
     - Direct button to initiate replanning when a team member is unready.
4. **Data Provenance & Honesty**:
   - All personnel counts and states must display explicit provenance tags (`DERIVED` or `SYNTHETIC_DEMO`).
   - Zero fabricated external biometric or live telemetry feeds.
   - Dual-state tracking: zero private medical diagnostic information displayed.
5. **Full Test Suite Integrity**:
   - Existing 248 backend pytest assertions and 143 frontend vitest assertions must remain 100% green.
   - Comprehensive unit and integration tests added for personnel option generation, approval, application, and Control Tower rendering.
   - End-to-end browser verification via Playwright demonstrating the full hero scenario.

---

## 10. File-Level Anticipated Change List

### Backend (Track A Owned)
- `[MODIFY] backend/app/domains/replanning/service.py`:
  - Add `_generate_personnel_reassignment_options()` in `generate_options()`.
  - Add `REASSIGN_PERSONNEL` handling block in `apply()`.
- `[MODIFY] backend/app/domains/control_tower/schemas.py`:
  - Add `PersonnelDeploymentSummary`, `PersonnelPostureItem`, `TeamDeploymentItem` schemas.
- `[MODIFY] backend/app/domains/control_tower/service.py`:
  - Add `get_personnel_posture(expedition_id)` method aggregating station complement, field deployments, and team readiness.
  - Include personnel posture in `get_overview()`.
- `[MODIFY] backend/app/domains/control_tower/router.py`:
  - Expose `/control-tower/personnel/{expedition_id}` endpoint (or enriched overview).
- `[NEW] tests/test_a10_personnel_safety_replan.py`:
  - Unit & integration tests for personnel disqualification, option generation, human approval, and application.

### Frontend (Track A Owned)
- `[NEW] frontend/src/features/control-tower/components/PersonnelDeploymentPanel.tsx`:
  - High-visibility operational panel displaying station complement, field teams, and readiness status.
- `[MODIFY] frontend/src/features/control-tower/ControlTowerPage.tsx`:
  - Mount `PersonnelDeploymentPanel` with `onInitiateReplan` handler.
- `[MODIFY] frontend/src/lib/types/api.ts`:
  - TypeScript types for `PersonnelDeploymentSummary`, `TeamDeploymentItem`, `PersonnelPostureItem`.
- `[NEW] frontend/src/features/control-tower/components/__tests__/PersonnelDeploymentPanel.test.tsx`:
  - Vitest component test for personnel posture display and replan initiation.

---

## 11. Scope Guard

### Strictly Forbidden in Milestone A10
- **NO Database Migrations**: Do not alter database DDL or author new SQL migrations. All needed columns and tables already exist in `public.people`, `public.teams`, and `public.assignments`.
- **NO Track B Domain Modifications**: Do not modify internal logic in `cargo`, `transport`, `inventory`, `assets`, or `incidents`.
- **NO Microservices or External Message Brokers**: All communication remains within the FastAPI modular monolith.
- **NO Telemetry / Medical Telemetry Simulation**: No fabricated heart rates, pulse oximetry, or biometric sensor feeds. Only discrete operational readiness states (`READY`, `CLEARANCE_PENDING`, `NOT_CLEARED`, `UNAVAILABLE`).
- **NO Autonomous Mutation**: Reassignment options require explicit human approval via `ApprovalModal`.

---

## 12. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Expedition Isolation Leakage** | Low | High | Ensure candidate replacement query explicitly filters `PersonModel.expedition_id == target_expedition_id`. |
| **Replan Application Idempotency Failure** | Low | High | Follow established pattern in `replanning/service.py`: check `rec.status == "APPLIED"` before applying changes. |
| **Empty Candidate Pool** | Low | Medium | If no candidate with matching role is available, generate option with `feasibility_state: NOT_EVALUABLE` or `INFEASIBLE` explaining that no qualified replacement is at station. |
| **Control Tower UI Clutter** | Medium | Medium | Maintain standard design system spacing, collapsible cards, and consistent dark mode token hierarchy (`slate-900`, `cyan-400`, `rose-400`). |

---

## 13. Exact Implementation Prerequisites

1. Confirm baseline remains clean on `main` at `75c3c483096d3bf3db157ea97a31d2cd3104f9e0`.
2. Create dedicated feature branch:
   ```powershell
   git checkout -b a/personnel-safety-engine
   ```
3. Verify dev environment and database health via `get_db_health()`.
4. Implement backend option generator and application handler first.
5. Verify with targeted pytest suite.
6. Implement frontend types and `PersonnelDeploymentPanel`.
7. Verify with vitest suite and Playwright browser session.

---

```text
A10 PREFLIGHT COMPLETE

Repository: CLEAN
Main SHA: 75c3c483096d3bf3db157ea97a31d2cd3104f9e0

Selected Direction:
Milestone A10 — Personnel & Field Team Deployment Safety Engine

Blocking Issues:
NONE

Source Code Modified: NO
Branch Created: NO
Migrations Created: NO
Commit Created: NO
PR Created: NO

Status: READY FOR IMPLEMENTATION
```
