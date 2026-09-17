# Split-Readiness Evaluation & Checklist

This document tracks the objective readiness of the repository to be handed off to two developers (Person A and Person B) working concurrently on separate feature branches without cross-blocking.

---

## 1. Split-Readiness Assessment Status

**CURRENT STATUS**: `READY WITH CONDITIONS`

### Justification:
The internal repository architecture, domain boundaries, database foundation, migration pipeline, deterministic seed, test harness, git workflow, and handoff protocols are 100% established and validated. The repository is structurally complete and split-ready. However, three external administrative conditions must be completed on GitHub and cloud provider platforms before parallel developer branches are cut:

1. **GitHub Username for Person B**: The GitHub username for Person B must be added to `.github/CODEOWNERS` (currently configured with `@Kshitij2011-spec` for Person A and marked placeholder `@person-b-github-username`).
2. **GitHub Branch Protection Rules**: Branch protection on `main` (requiring pull requests, squash-and-merge only, and status checks passing) must be toggled in the GitHub repository settings UI.
3. **Production Cloud Environments Provisioning**: Person A must provision production projects in Vercel, Render, and Supabase and record connection strings in secure vaults.

---

## 2. Objective Verification Checklist

### Repository Foundation
- [x] `main` exists as the sole integration trunk.
- [x] Git history is linear and clean (`1218878`, `2cd861f`).
- [x] Branching policy is documented (`a/<feature>`, `b/<feature>`, `shared/<feature>`).
- [x] PR workflow and `.github/PULL_REQUEST_TEMPLATE.md` established.
- [x] `.github/CODEOWNERS` configured.
- [x] `.env.example` provides complete template without committed secrets.

### Architectural Layering & Domain Boundaries
- [x] Module ownership defined in `docs/MODULE_OWNERSHIP.md`.
- [x] Track A (Planning & Decision) and Track B (Logistics, Resources & Response) balanced.
- [x] Shared Platform contracts documented.
- [x] Event schema and canonical event types documented in `docs/EVENT_CONTRACT.md`.
- [x] 15-verb semantic dependency graph documented in `docs/DEPENDENCY_CONTRACT.md`.
- [x] API contract envelope (`/api/v1/`, `{ data, meta, errors }`) defined in `docs/API_CONTRACT_POLICY.md`.
- [x] Database change policy and immutable applied migration rule defined in `docs/DATABASE_CHANGE_POLICY.md`.

### Developer Independence
- [x] Person A can start Track A without touching Track B internals.
- [x] Person B can start Track B without touching Track A internals.
- [x] Cross-domain collaboration protocol defined in `docs/CROSS_DOMAIN_PROTOCOL.md`.
- [x] Local development instructions reproducible in `docs/LOCAL_DEVELOPMENT.md`.
- [x] No developer depends on private or undocumented local machine configurations.

### Database & Seed Integrity (Static Baseline)
- [x] Comprehensive migration exists (`supabase/migrations/20260917000000_expedition_operational_schema.sql`).
- [x] Deterministic seed data exists (`supabase/seed.sql`).
- [x] Stable hero scenario entities (`EXP-26-A`, `M-08`, `R-04`, `I-42`, `C-117`, `T-08`) established with fixed UUIDs.
- [x] Data provenance rules enforced across all records.
- [x] 25/25 backend database, seed, and diagnostic health tests pass via pytest.

### Real Database Verification (Supabase DEV: `tywtsmvccifkugoecrmd`)
- [x] Dedicated SIH26062 DEV Supabase project exists (`tywtsmvccifkugoecrmd` in `ap-south-1`).
- [x] Old Krishi Sahayak project completely untouched and isolated.
- [x] Migration applied to real PostgreSQL database (35 operational tables confirmed).
- [x] Seed applied to real PostgreSQL database (all 20 seed sections executed).
- [x] Real database schema verified (all enums, check constraints, foreign keys active).
- [x] Hero chain verified in real DB (`EXP-26-A` ──▶ `M-08` ──▶ `I-42` ──▶ `C-117` ──▶ `PKG-117-01` ──▶ `T-08`).
- [x] Operational event immutability verified against real DB (`UPDATE` and `DELETE` rejected by trigger `P0001`).
- [x] Database connection verified (`check_db_connectivity` and `get_db_health` tested).
- [x] Both developers can independently configure DEV access via `.env.example`.
- [x] Production remains strictly separate (Person A only).


### Infrastructure & Deployment Authority
- [x] Exclusive production deployment authority assigned to Person A in `docs/DEPLOYMENT_OWNERSHIP.md`.
- [x] Vercel, Render, and Supabase production administration assigned to Person A.
- [x] Environment variable tiers documented in `docs/ENVIRONMENT_STRATEGY.md`.
- [x] Zero secrets present in git tracking.

### Quality & Verification
- [x] Standard verification script (`scripts/verify.ps1`) created and functional.
- [x] Pre-PR rebase and merge protocol defined in `docs/HANDOFF_PROTOCOL.md`.
- [x] Design system boundaries defined in `docs/DESIGN_SYSTEM_CONTRACT.md`.
- [x] Canonical polar domain glossary defined in `docs/DOMAIN_LANGUAGE.md`.

---

## 3. Immediate Action Items to Reach Full `SPLIT READY`

1. **Owner Action (Person A)**:
   - Invite Person B to the GitHub repository with write access.
   - Update `.github/CODEOWNERS` with Person B's actual GitHub handle.
   - In GitHub Settings > Branches, enable branch protection on `main`:
     - Require pull requests before merging.
     - Require squash merge.
     - Do not allow force pushes or deletions.
2. **Branch Kickoff**:
   - Person A cuts `a/platform-foundation` or `a/expedition-domain`.
   - Person B cuts `b/cargo-domain` or `b/inventory-domain`.
