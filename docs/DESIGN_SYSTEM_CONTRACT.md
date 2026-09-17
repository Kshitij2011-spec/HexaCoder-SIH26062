# Design System & UI Contract

This document defines the shared design system standards, component boundaries, and semantic visual language for the SIH26062 Antarctic & Polar Expedition Operational Logistics Platform.

Both Person A and Person B must adhere strictly to these conventions. **Neither developer may introduce competing component libraries, custom color systems, or ad-hoc style frameworks.**

---

## 1. Technology Foundations

- **Core Framework**: React 18+ with TypeScript.
- **Styling Engine**: Tailwind CSS (v3 or v4 as configured).
- **Component Primitives**: Radix UI / `shadcn/ui`.
- **Iconography**: `lucide-react` exclusively.
- **Design Aesthetic**: Rich dark-mode native polar operational console aesthetic (dark slate/obsidian canvas, high-contrast typography, crisp border delineation, purposeful micro-animations).

---

## 2. Semantic Color Palette & Meaning

All status badges, borders, state pills, charts, and node visualizations must use the exact semantic color mapping below:

| Semantic Meaning | Color Family | Tailwind Token | Polar Operational Usage |
|---|---|---|---|
| **Information / Normal** | Polar Blue | `sky` / `blue` | Neutral expedition data, ambient station info, default telemetry |
| **Transport & Sync** | Arctic Cyan | `cyan` / `teal` | Vessel/aircraft legs, manifests, satellite sync, movement |
| **Planning & Dependencies** | Aurora Violet | `violet` / `purple` | Planning engine, dependency graph nodes, constraint links |
| **Attention & Change** | Warning Amber | `amber` / `orange` | Pending state changes, replan proposals, stock low warnings |
| **Blocked & Critical** | Polar Alert Red | `rose` / `red` | Critical incidents, hard constraint violations, stockouts, blizzards |
| **Ready / Approved / Safe** | Ice Shelf Green | `emerald` / `green` | Human-approved actions, feasible missions, safe weather windows |

---

## 3. Typography & Display Scale

- **Primary Typeface**: Inter / System Sans (clean, legible, technical operational feel).
- **Monospace Typeface**: JetBrains Mono / Fira Code (used for all entity codes: `EXP-26-A`, `M-08`, `R-04`, `I-42`, `C-117`, `T-08`, and geographic coordinates).
- **Data Provenance Badges**: Always displayed in uppercase monospace (`[MEASURED]`, `[DERIVED]`, `[FORECAST]`, `[SCENARIO]`, `[SYNTHETIC/DEMO]`, `[ADVISORY]`) with subtle muted borders.

---

## 4. Shared UI Component Ownership

The following components belong to the **Shared Platform** layer (`frontend/src/components/shared/` and `frontend/src/components/ui/`):

1. **Button & Action Controls**: Primary, secondary, ghost, destructive, operational-action triggers.
2. **Form Inputs & Selectors**: Text inputs, dropdowns, datetime-pickers with UTC polar display, filters.
3. **Data Display**:
   - `OperationalTable`: Standard sortable, paginated, filterable grid.
   - `StatusBadge`: Semantic status indicator using the color palette above.
   - `ProvenanceTag`: Standard indicator showing data origin and freshness.
   - `EntityCode`: Standard monospaced clickable chip navigating to entity detail.
4. **Feedback & Overlays**:
   - Modal Dialogs, Slide-over Drawers, Toast notifications.
   - Confirmation Modals for Human Approvals (`OperatorApprovalModal`).
5. **Operational Visualizations**:
   - `TimelineView`: Horizontal Gantt-style operational leg / time-window renderer.
   - `DependencyGraphNode`: Visual node for displaying semantic relationship networks.

---

## 5. Feature UI Boundaries (Track A vs Track B)

| Feature Area | Assigned Track | Allowed Components |
|---|---|---|
| **Expeditions & Missions** | Track A (Person A) | Mission card, Expedition overview, Weather window gauge |
| **Planning & Approvals** | Track A (Person A) | Replan impact analyzer, Human approval console, Constraint matrix |
| **Control Tower** | Track A (Person A) | High-level situational summary, Alert banner, Global health |
| **Cargo & Consignments** | Track B (Person B) | Package manifest table, Hazmat indicator, Cargo volume breakdown |
| **Transport & Legs** | Track B (Person B) | Leg status tracker, Vessel/air route segment viewer, ETA card |
| **Inventory & Assets** | Track B (Person B) | Stock lot level gauge, Maintenance schedule card, Critical spare alert |
| **Incident Response** | Track B (Person B) | Incident triage list, Response action assignment card |
| **Offline Sync** | Track B (Person B) | Local sync queue drawer, Connectivity indicator, Sync conflict viewer |

---

## 6. Rules to Prevent UI Divergence

1. **No Ad-hoc Colors**: Do not use raw hex codes (e.g. `#123456`) in inline styles or arbitrary Tailwind classes. Use the theme tokens.
2. **Common Page Shell**: Every feature view must embed inside the shared `AppLayout` with the unified sidebar and top status bar.
3. **Shared API Client**: Features must never instantiate their own `fetch` or `axios` instances. All remote queries must use the shared TanStack Query hooks and API client in `frontend/src/lib/api/`.
