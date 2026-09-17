# SIH26062 — Semantic Dependency Graph Contract

## 1. Overview & Adjacency Model

The core intelligence of HexaCoders relies on a **Semantic Directed Adjacency Graph** persisted in the `dependencies` table. 

Every edge connects a Source Entity to a Target Entity via a typed, domain-validated semantic verb.

Untyped relationships, generic "linked" foreign keys, or undocumented ad-hoc edges are strictly prohibited.

---

## 2. Authoritative 15-Verb Semantic Vocabulary

All dependency relationships must use one of the following 15 enum values:

| Semantic Verb | Intended Meaning | Example in System |
| :--- | :--- | :--- |
| `REQUIRES` | Hard operational necessity. Source entity cannot execute/operate without Target. | `Mission M-08 REQUIRES Asset I-42` |
| `SUPPORTS` | Operational facilitation or resource provision without absolute exclusivity. | `Cargo C-117 SUPPORTS Mission M-08` |
| `ASSIGNED_TO` | Formal organizational or mission deployment assignment. | `Team R-04 ASSIGNED_TO Mission M-08` |
| `LOCATED_AT` | Current physical placement or operational node. | `Asset PB-01 LOCATED_AT Location Maitri-Station` |
| `MOVES_VIA` | Physical transit manifestation on a transport leg. | `Cargo C-117 MOVES_VIA Transport-Leg T-08` |
| `CONTAINS` | Parent-to-child physical containment or organizational hierarchy. | `Cargo Package PKG-117-01 CONTAINS Asset I-42` |
| `DELIVERED_TO` | Designated logistical drop-off or warehouse destination. | `Cargo C-117 DELIVERED_TO Location Maitri-Warehouse` |
| `RESERVED_FOR` | Resource or stock lock dedicated to a specific mission or safety floor. | `Stock SKU-HYD-HOSE-08 RESERVED_FOR Asset GEN-01` |
| `REPLENISHED_BY` | Inventory or asset resupply dependency chain. | `Stock Lot LOT-01 REPLENISHED_BY Cargo C-115` |
| `AFFECTS` | State propagation link showing direct operational impact. | `Incident INC-01 AFFECTS Location Field-Camp-A` |
| `DEPENDS_ON` | Upstream functional prerequisite. | `Asset DRILL-01 DEPENDS_ON Item SKU-DRILL-CARB` |
| `CONSTRAINED_BY` | Boundary limitation governed by time windows or safety rules. | `Mission M-08 CONSTRAINED_BY Time-Window TW-M08-SURVEY` |
| `OPERATED_BY` | Person or crew certified to operate heavy machinery or aircraft. | `Asset PB-01 OPERATED_BY Person Vikramaditya-Rao` |
| `OCCURS_AT` | Event, traverse, or leg staging location. | `Transport-Leg T-08 OCCURS_AT Location Cape-Town` |
| `BELONGS_TO` | Relational ownership within campaign boundary. | `Mission M-08 BELONGS_TO Expedition EXP-26-A` |

---

## 3. Polymorphic Validation in Backend Services

Because the `dependencies` table links heterogeneous entities (`source_entity_type`, `source_entity_id`, `target_entity_type`, `target_entity_id`), referential integrity cannot be resolved entirely by standard database foreign keys.

Therefore, the shared backend **`dependency_service`** bears explicit responsibility for:
1. **Entity Verification**: Validating that both `source_entity_id` and `target_entity_id` exist in their respective tables.
2. **Cycle Prevention**: Ensuring non-cyclical graphs where cyclical dependencies would produce infinite replanning loops.
3. **Traversal Performance**: Using recursive Common Table Expressions (CTEs) to trace upstream and downstream impact trees within a single SQL transaction.
