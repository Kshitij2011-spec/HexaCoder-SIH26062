# SIH26062 — Testing & Verification Strategy

## 1. Multi-Tier Verification Philosophy

Software controlling polar mission readiness cannot rely on superficial checks. 

Passing TypeScript compilation or a 200 OK healthcheck is merely syntactic correctness; it does not prove operational correctness.

Every capability must be verified across three distinct testing tiers:
1. **Unit Testing** (Fast, deterministic business logic tests)
2. **Integration Testing** (Multi-entity cascading dependency pipelines)
3. **End-to-End (E2E) Browser Verification** (Real user interaction via Playwright)

---

## 2. Testing Tiers & Coverage

```
┌────────────────────────────────────────────────────────┐
│                   E2E (PLAYWRIGHT)                     │
│    Real Browser Sessions • Interactive Replan Flow     │
│    Emergency Workflows • Timeline & State Audits       │
├────────────────────────────────────────────────────────┤
│                 INTEGRATION (PYTEST)                   │
│   Cascading Event Pipelines • Multi-Entity Mutations   │
│   Database Transactions • State Propagation Engine     │
├────────────────────────────────────────────────────────┤
│                    UNIT (PYTEST)                       │
│    Entity State Machines • Formula Derivations         │
│    Constraint Rules • Event Schema Validation          │
└────────────────────────────────────────────────────────┘
```

---

### Tier 1: Unit Tests (Python / pytest)
Target: Pure domain services, state machines, and mathematical derivations.

- **State Transition Rules**:
  - Valid transitions (e.g., `DRAFT` → `PLANNED` for Expedition).
  - Invalid transitions reject with structured errors (e.g., `COMPLETED` cannot move back to `PROPOSED`).
- **Operational Event Creation**:
  - Verification that state mutations produce strictly formatted `OperationalEvent` records with required metadata.
- **Inventory Derivations**:
  - Verify formula: $\text{Available} = \text{Physical} - (\text{Reserved} + \text{Quarantined} + \text{Consumed})$.
  - Verify negative available quantities are rejected or flagged.
- **Derived Readiness Logic**:
  - Mission readiness switches to `BLOCKED` when required asset enters `UNSERVICEABLE`.
  - Expedition readiness switches to `AT_RISK` when non-critical cargo is `DELAYED`.
- **Constraint Evaluations**:
  - Test threshold rules (e.g., fuel reserve < 45 days triggers `CRITICAL`).
- **Replan Trigger Engine**:
  - Ensure replanning is only initiated when hard constraints or infeasibilities are breached.
- **Approval Logic**:
  - Verify that approval transitions the recommended plan and logs the approver's ID and comments.

---

### Tier 2: Integration Tests (FastAPI TestClient / Database)
Target: Cross-entity pipelines and cascading updates across the modular monolith.

- **Pipeline 1: Cargo Delay Cascading**:
  1. Set up Expedition, Mission, Cargo Consignment, Transport Leg.
  2. Emit `TransportDelayed` event on transport leg.
  3. Verify `CargoConsignment` derived risk becomes `AT_RISK` or `LATE`.
  4. Verify `Mission` readiness transitions to `BLOCKED`.
  5. Verify an operational constraint violation is raised.
- **Pipeline 2: Inventory Shortage to Mission Impact**:
  1. Snowcat requires replacement hydraulic hose.
  2. Emergency stock reserved for station generator.
  3. Available inventory drops to 0.
  4. Asset availability transitions to `UNAVAILABLE`.
  5. Dependent field mission readiness transitions to `BLOCKED`.
- **Pipeline 3: Personnel Unavailability**:
  1. Team lead marked `UNAVAILABLE` due to medical hold.
  2. Team readiness transitions from `READY` to `FORMING`.
  3. Mission transitions to `BLOCKED`.
- **Pipeline 4: Incident Response Flow**:
  1. Declare severe blizzard incident at Maitri Station.
  2. All open field missions within 50km radius automatically flagged `BLOCKED`.
  3. Emergency response actions spawned and assigned.

---

### Tier 3: End-to-End (E2E) Browser Verification (Playwright)
Target: Complete interactive operator workflows executed in a live browser.

> **Rule**: Always use the native Playwright tool for browser verification. Do not build custom synthetic browser mock scripts.

#### The Primary E2E Test Flow: "Hero Cargo Delay & Replanning"
1. **Initialize**: Log in as Expedition Operations Officer.
2. **Setup**: View the 45th ISEA expedition dashboard. Verify active missions and scheduled transport legs.
3. **Trigger Event**: Introduce an operational delay to Flight Leg `FL-CPT-MTR-01` (48-hour weather delay).
4. **Observe Cascade**:
   - Inspect Cargo Consignment status badge shifting to `LATE`.
   - Inspect dependent Mission `Deep Ice Core Drilling` shifting to `BLOCKED`.
   - Verify active warning alert appears in the Control Tower.
5. **Replan Generation**:
   - Click "Review Impact & Options".
   - Verify Replan Engine generates 2 distinct mitigation recommendations.
6. **Approval**:
   - Operator selects "Option B: Reallocate Local Backup Sensors from Bharati Station".
   - Operator inputs sign-off note: *"Approved per scientific director radio conference"*.
   - Click "Approve & Execute Update".
7. **Verify State**:
   - Verify Mission readiness clears to `READY`.
   - Verify immutable event history displays the delay, constraint breach, recommendation, and approval record with timestamp and approver ID.

#### Secondary Flow: Emergency Blizzard Incident Declaration
- Declare station-level emergency incident.
- Verify lockdown propagation across outdoor transport legs.
- Verify emergency response checklist and audit logging.

---

## 4. Unified Verification Script & Developer Responsibilities

Both Person A and Person B must maintain and execute automated tests for their respective vertical tracks:

- **Person A**: Tests planning engine, constraint evaluations, human approval state machine, readiness calculations, event persistence, and control tower views.
- **Person B**: Tests cargo consignments, package validation, transport legs, inventory calculations, asset maintenance schedules, incident response, and offline sync.
- **Shared Verification Command**:
  ```powershell
  # Must pass before any PR is marked ready for review:
  .\scripts\verify.ps1
  ```
- **Playwright Execution**: Interactive user journeys must be verified using Playwright browser tooling. PRs altering UI components or workflows must document successful Playwright execution in the PR description.

