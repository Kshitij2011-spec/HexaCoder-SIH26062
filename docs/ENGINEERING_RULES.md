# SIH26062 — Engineering Rules & Prohibitions

This document outlines the strict engineering rules, architectural boundaries, and explicit prohibitions for the **HexaCoders — SIH26062** project. Every developer and autonomous coding agent must strictly adhere to these rules.

---

## 1. Explicit Prohibitions

### Data & External Claims
- **DO NOT** invent or pretend to integrate with private NCPOR (National Centre for Polar and Ocean Research) internal APIs.
- **DO NOT** invent government, ministry, or defense integrations.
- **DO NOT** claim live GPS or satellite tracking feeds.
- **DO NOT** claim live vessel Automatic Identification System (AIS) feeds.
- **DO NOT** claim live station personnel biometrics or RFID feeds.
- **DO NOT** invent proprietary polar communications protocols.
- **DO NOT** label synthetic or simulated scenario data as "Live".
- **DO NOT** claim any system capability or workflow is complete without actual automated and browser verification.

### Domain & Logic Integrity
- **DO NOT** generate arbitrary or unexplainable fake KPIs (e.g., "Operational efficiency: 89.4%"). All scores must be mathematically derived from explicit criteria.
- **DO NOT** implement autonomous execution of high-consequence operational decisions (e.g., auto-cancelling a mission, auto-jettisoning cargo).
- **DO NOT** hide or obscure dependency reasoning. When a mission is marked `BLOCKED`, the system must explicitly disclose the upstream root cause.
- **DO NOT** omit approval records. Any modification to a plan, roster, or reserve threshold must preserve the approver identity and reasoning.
- **DO NOT** build isolated CRUD screens disconnected from the shared operational state. Every module must participate in the event and dependency graph.
- **DO NOT** make barcode/QR scanning the "core value" of the product. Barcodes are merely package identifiers, not operational intelligence.
- **DO NOT** make mapping or GIS visualization the "core value". Maps are a contextual view, not the operational decision engine.
- **DO NOT** make a generic conversational chatbot the primary product interface.
- **DO NOT** make vague "AI/GenAI" claims without a deterministic, verifiable algorithm or explicit model backing.
- **DO NOT** build fake SCADA, station boiler telemetry, or generator monitoring interfaces.

### Architectural & Infrastructure Boundaries
- **DO NOT** introduce Apache Kafka or complex event streaming platforms. The modular monolith uses transactional database event tables and asynchronous worker queues.
- **DO NOT** introduce Kubernetes or microservice orchestration.
- **DO NOT** implement blockchain, distributed ledgers, or smart contracts.
- **DO NOT** build heavy 3D visualizations, three.js globes, or digital twin game scenes unless specifically requested by future explicit requirements.
- **DO NOT** commit secrets, service keys, database passwords, or JWT secrets into Git or documentation.
- **DO NOT** silently deploy to Render, Vercel, or cloud infrastructure without explicit authorization.
- **DO NOT** silently push commits to remote Git repositories.

---

## 2. Feature Justification Test

Every proposed feature, endpoint, UI element, or data structure must pass the **Feature Justification Test**.

Before implementing any code, ensure the feature maps directly to at least one of the following:
1. **A Domain Object**: Directly models an expedition entity (`Expedition`, `Mission`, `Person`, `Asset`, `Cargo`, `Inventory`, etc.).
2. **An Operational Event**: Emits or handles an auditable state transition (`CargoDelayed`, `AssetDamaged`, etc.).
3. **A Dependency Relationship**: Expresses how entities constrain or support each other (`REQUIRES`, `SUPPORTS`, `LOCATED_AT`).
4. **An Operational Constraint**: Evaluates safety floors, weather windows, or compliance rules.
5. **A Planning / Replanning Workflow**: Surfaces alternatives, computes trade-offs, or presents human-approval interfaces.
6. **An Explicit Supporting Requirement**: Authentication, offline sync, audit log, or testing harness.

> **Flag and Halt Rule**: If a proposed feature does not clearly map to the criteria above, flag it for clarification instead of silently introducing it into the codebase.
