## Pull Request Summary

### Title
<!-- Format: feat(domain): description | fix(domain): description | refactor(domain): description -->

### Domain / Module
<!-- e.g., Cargo / Missions / Constraints / Inventory / Shared Platform -->

---

## 1. Description & Context

### What Changed?
<!-- Clear, bulleted summary of technical and domain changes -->

### Why Did It Change?
<!-- Operational justification, bug fix, or roadmap phase alignment -->

---

## 2. Impact Analysis

### Database Changes
<!-- None / New migration / Seed update / Schema adjustment -->

### API Changes
<!-- New endpoints, modified request/response schemas, versioned routes -->

### Frontend Changes
<!-- New UI component, workspace view, reactive state change -->

### Cross-Domain Contract Changes
<!-- Any impact on other person's domain interfaces, event schemas, or dependencies -->

### Breaking Changes
<!-- Does this require downstream rebase, seed reset, or client cache invalidation? -->

### Deployment Impact
<!-- Any environment variable additions, migrations to run, or deployment order notes -->

---

## 3. Verification & Quality

### Tests Added / Updated
<!-- List of unit, integration, or contract tests authored in this PR -->

### Tests Executed
<!-- Commands run and exact results, e.g., pytest tests/... -->

### Playwright Browser Verification
<!-- Did you run Playwright browser tests? What user journey was confirmed? -->

### Screenshots / Recordings (If UI Changed)
<!-- Embed screenshots or recordings of visual interface changes -->

### Migration & Seed Notes
<!-- Instructions for applying or verifying local schema changes -->

### Known Limitations
<!-- Open items, deferred optimizations, or phase boundaries -->

---

## 4. Pre-Merge Checklist

- [ ] I have read and adhered to [AGENTS.md](AGENTS.md) and [ENGINEERING_RULES.md](docs/ENGINEERING_RULES.md).
- [ ] Existing domain abstractions and shared services were reused (no duplicate services introduced).
- [ ] Automated tests were added or updated to cover all modified logic.
- [ ] Targeted tests passed locally before submitting this PR.
- [ ] Frontend build succeeds without TypeScript or bundling errors (`npm run build`).
- [ ] Real Playwright browser verification was conducted if user-facing UI was modified.
- [ ] No secrets, private API keys, or credentials are committed or exposed.
- [ ] No fake "live" integrations (NCPOR, live GPS, AIS) are claimed; data provenance tags are strictly preserved.
- [ ] Database migration and seed changes were tested for referential integrity.
- [ ] Operational events are emitted for state changes; event history remains immutable.
