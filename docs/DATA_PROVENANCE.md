# SIH26062 — Data Provenance & Classification Framework

## 1. Purpose
In high-stakes polar operational environments, decision-makers must know with 100% certainty the origin, reliability, and methodology behind any datum presented on screen. 

Presenting simulated or estimated values as "real-time verified facts" can lead to catastrophic mission failure or loss of life.

Therefore, the HexaCoders platform enforces strict **Data Provenance Tagging** at both the schema and UI levels.

---

## 2. Authoritative Data Classifications

Every metric, entity state, ETA, inventory figure, and weather alert carries one of the following provenance classifications:

| Classification | Definition | Example in System |
| :--- | :--- | :--- |
| `MEASURED` | Ground-truth empirical observation directly captured by verified hardware or confirmed human manual check. | Physical weighbridge scale reading of cargo pallet; manual dipstick measurement of station fuel tank. *(Reserved for future verified telemetry)* |
| `DERIVED` | Programmatically computed value generated from known system state via deterministic business logic. | `AvailableInventory = Physical - Reserved - Quarantined`; `MissionReadiness = BLOCKED` due to missing specialist. |
| `FORECAST` | Estimated or projected future value based on models, historical averages, or external forecasts. | Weather window closure projection; estimated sea ice thickness trend. |
| `SCENARIO` | What-if simulation parameters created temporarily to evaluate replanning alternatives without altering canonical state. | Projected fuel consumption if Snowcat traverse is detoured 60km north to avoid crevasse field. |
| `SYNTHETIC / DEMO` | Curated, realistic mock datasets used to demonstrate end-to-end system capabilities during testing and evaluation. | 45th ISEA expedition manifest, sample cargo consignments, simulated blizzard delays. |
| `PUBLIC SOURCE` | Grounded data extracted from publicly accessible polar databases, scientific portals, or open cartography. | General Antarctic station coordinates (Maitri: 70°45′57″S 11°44′09″E; Bharati: 69°24′28″S 76°11′14″E), open bathymetry/elevation models. |
| `ADVISORY` | A suggested operational recommendation produced by the constraint and replanning engine awaiting human review. | Replan Option B: "Reallocate Asset PB-02 to Mission Ice-Core-03". |

---

## 3. MVP Provenance Baseline

For the Smart India Hackathon MVP:
- **Primary Data Classes**: The platform operates almost entirely on `SYNTHETIC / DEMO`, `DERIVED`, `SCENARIO`, and `ADVISORY` data.
- **Visual Indicators**: The user interface must prominently display a provenance badge (e.g. `[DEMO DATA]`, `[DERIVED]`, `[ADVISORY]`) on all overview screens, manifests, and recommendation cards.

---

## 4. Production Boundary Statement

> **Boundary Disclaimer**:
> This software is an independent engineering prototype designed for the Smart India Hackathon. It does **not** have direct access to, or authorized communication links with, the confidential, proprietary, or operational internal networks of the National Centre for Polar and Ocean Research (NCPOR), the Ministry of Earth Sciences (MoES), Government of India, or international polar operators (COMNAP, SCAR). All expedition schedules, personnel rosters, and manifests in this prototype are synthetic representations built for demonstration and evaluation purposes.
