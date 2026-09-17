# SIH26062 — Operational Event Contract & Schema Specification

## 1. The Core Event Rule
Every state-changing operational action in the system **MUST** emit an immutable `OperationalEvent`. 

No domain service may silently update database records without emitting an event into the `operational_events` table within the same database transaction.

---

## 2. Authoritative Event Schema

Every event emitted across Track A and Track B conforms strictly to this contract:

```json
{
  "event_id": "UUID (Unique technical identifier for this event)",
  "event_type": "string (Controlled event name, e.g. 'CargoDelayed')",
  "entity_type": "string (Entity category: 'EXPEDITION', 'MISSION', 'CARGO', 'ASSET', etc.)",
  "entity_id": "UUID (Target entity primary key)",
  "previous_state": "string or null (State prior to mutation)",
  "new_state": "string (State resulting from mutation)",
  "timestamp": "ISO-8601 UTC string (e.g. '2026-12-18T12:00:00Z')",
  "source": "string ('USER_ACTION', 'SYSTEM', 'SCHEDULED_CHECK', 'EXTERNAL_ADVISORY')",
  "actor_type": "string ('PERSON', 'USER', 'SYSTEM')",
  "actor_id": "UUID or null (Identifier of user or person performing mutation)",
  "location_id": "UUID or null (Operational node where event occurred)",
  "evidence": "JSONB object (Structured supporting payload, sensor snapshot, or justification)",
  "correlation_id": "UUID (Traces root-cause event across cascading downstream mutations)",
  "data_provenance": "data_provenance ('SYNTHETIC_DEMO', 'DERIVED', 'MEASURED', 'SCENARIO')"
}
```

---

## 3. Canonical Event Vocabulary Registry

Developers are strictly forbidden from inventing ad-hoc event names in feature code. All events must be selected from the following canonical registry:

### 3.1 Expedition & Mission Events (Track A)
- `ExpeditionCreated`, `ExpeditionMobilized`, `ExpeditionActivated`, `ExpeditionHoldDeclared`, `ExpeditionClosed`
- `MissionProposed`, `MissionApproved`, `MissionScheduled`, `MissionStarted`, `MissionBlocked`, `MissionCompleted`, `MissionDeferred`, `MissionCancelled`

### 3.2 Personnel & Team Events (Track A)
- `PersonNominated`, `PersonCleared`, `PersonMedicalHold`, `PersonUnavailable`, `PersonDispatched`, `PersonArrived`
- `TeamFormed`, `TeamCleared`, `TeamDeployed`, `TeamReturned`

### 3.3 Logistics & Transport Events (Track B)
- `CargoRequested`, `CargoDeclared`, `CargoApproved`, `CargoPacked`, `CargoDispatched`, `CargoInTransit`, `CargoDelayed`, `CargoArrived`, `CargoReceived`, `CargoDamaged`, `CargoLost`
- `PackagePacked`, `PackageLoaded`, `PackageTransferred`, `PackageReceived`, `PackageDamaged`
- `TransportLegPlanned`, `TransportLegBooked`, `TransportLegDeparted`, `TransportLegDelayed`, `TransportLegDiverted`, `TransportLegArrived`, `TransportLegCancelled`

### 3.4 Inventory & Asset Events (Track B)
- `StockReceived`, `StockReserved`, `StockReleased`, `StockIssued`, `StockConsumed`, `StockQuarantined`, `StockDamaged`, `StockoutDetected`
- `AssetRegistered`, `AssetReserved`, `AssetDeployed`, `AssetMaintenanceStarted`, `AssetMaintenanceCompleted`, `AssetDamaged`, `AssetRetired`

### 3.5 Incident & Response Events (Track B)
- `IncidentDetected`, `IncidentTriaged`, `IncidentDeclared`, `ResponseActionAssigned`, `IncidentActive`, `IncidentStabilized`, `IncidentResolved`, `IncidentClosed`

### 3.6 Intelligence & Decision Events (Track A)
- `ConstraintViolated`, `RequirementInfeasibleDetected`, `ReplanTriggered`, `RecommendationGenerated`, `PlanApproved`, `PlanRejected`

---

## 4. Procedure for Introducing New Event Types

If an emerging operational scenario requires an event type not currently registered:
1. **Submit RFC / Issue**: Document the proposed event name, triggering condition, affected entities, and expected downstream dependency effects.
2. **Review with Co-Developer**: Person A and Person B verify that the event does not duplicate an existing lifecycle verb.
3. **Update Migration & Registry**: Add the event to `EVENT_CONTRACT.md` and include it in automated schema tests.
