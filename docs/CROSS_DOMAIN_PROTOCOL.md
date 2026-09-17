# SIH26062 — Cross-Domain Coordination Protocol

## 1. Core Mandate: Contract-First Isolation

In a high-velocity two-person team, tight coupling between domain implementations creates merge conflicts, test breakages, and cognitive friction.

> **The Golden Rule**: 
> A developer must **NEVER** modify another developer's private domain internals (e.g. database models, private service helpers, or internal state machines) merely to make their own feature compile or pass tests.

Instead, all interactions between Track A (Decision & Planning) and Track B (Logistics & Resources) must occur through **explicit public domain contracts**.

---

## 2. The 6-Step Cross-Domain Protocol

When Developer X requires data, state recalculation, or capabilities residing in Developer Y's domain:

```
[1. Identify Contract Need] ──▶ [2. Document Requirement] ──▶ [3. Propose Public Contract]
                                                                      │
[6. Continue Independently] ◀── [5. Merge Contract PR] ◀── [4. Peer Review & Consensus]
```

1. **Identify Needed Contract**: Clearly define what data fields, query parameters, or state transitions are required.
2. **Document the Interface**: Create or update the Pydantic DTO schema in `backend/app/schemas/contracts/` or TypeScript contract in `frontend/src/lib/types/contracts/`.
3. **Expose / Stub Public Interface**: The owning developer (or requesting developer via PR) implements or stubs the public method on the domain service interface.
4. **Peer Review**: Both developers review the contract shape, ensuring it respects domain encapsulation and data provenance rules.
5. **Merge Contract Change**: The contract is merged to `main` (or into a `shared/*` branch).
6. **Continue Independently**: Both developers resume autonomous implementation against the agreed-upon public contract.

---

## 3. Concrete Protocol Scenarios

### Scenario 1: Person B (Cargo) Needs Mission Impact Information
- **Problem**: When a cargo consignment is delayed, Person B's logistics workspace needs to display which missions are impacted.
- **Forbidden Action**: Person B directly querying internal mission tables, mutating `missions.status`, or refactoring Person A's mission service classes.
- **Protocol Resolution**:
  1. Person B specifies the need: `GET /api/v1/missions/impact-summary?cargo_id={uuid}` or a call to `mission_service.get_mission_impact_for_cargo(cargo_id)`.
  2. Person A provides a stable public Pydantic schema: `MissionImpactSummary(mission_id, mission_code, title, required_by_at, derived_readiness)`.
  3. Person B consumes this contract in the cargo workspace. Person A is free to refactor mission internals without breaking Person B's cargo UI.

### Scenario 2: Person A (Planning Engine) Needs Cargo ETAs
- **Problem**: When evaluating replan alternatives, Person A's constraint solver needs projected arrival dates for scientific instruments on transport legs.
- **Forbidden Action**: Person A writing raw SQL joins against `cargo_packages`, `transport_cargo_assignments`, and `transport_legs` directly inside the replanning algorithm.
- **Protocol Resolution**:
  1. Person A requests a public query method on `cargo_service`: `cargo_service.get_consignment_eta_projection(consignment_id)`.
  2. Person B implements and guarantees the contract: `CargoEtaProjection(consignment_id, code, estimated_arrival_at, transport_mode, status, is_delayed)`.
  3. Person A uses this clean DTO in the constraint solver. If Person B later redesigns transport assignment mechanics or splits packages, Person A's planning engine remains unaffected.

---

## 4. Contract Violation Safeguards

- Code reviews will reject any PR where Domain A imports private internal symbols from Domain B (`from backend.app.domains.b.internal...`).
- Cross-domain access is restricted to:
  1. Shared platform services (`event_service`, `dependency_service`, `audit_service`).
  2. Public domain service interfaces (`DomainService.get_public_contract(...)`).
  3. Versioned REST endpoints (`/api/v1/...`).
