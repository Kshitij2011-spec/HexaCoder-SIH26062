# Frontend Architecture & Directory Scaffolding

This directory contains the React + TypeScript + Vite frontend application for the SIH26062 Antarctic & Polar Expedition Operational Logistics Platform.

---

## 1. Directory Structure

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
```

---

## 2. Core Architectural Rules

1. **Shared API Client**: Features **MUST NOT** define their own `fetch` clients or hardcode endpoints. All data queries must route through `lib/api/` using TanStack Query.
2. **Shared Design System**: Features must use components from `components/ui/` and `components/shared/`. Do not create one-off styling frameworks or uncoordinated color schemes.
3. **Domain Separation**: Feature modules in `features/` must encapsulate their own view components and hooks. Cross-feature integration occurs via standard URL routing or shared services, never by deep-linking into another feature's private helper methods.
4. **Data Provenance**: Any data item displayed must show its provenance tag (`[MEASURED]`, `[DERIVED]`, `[FORECAST]`, `[SCENARIO]`, `[SYNTHETIC/DEMO]`, `[ADVISORY]`).
