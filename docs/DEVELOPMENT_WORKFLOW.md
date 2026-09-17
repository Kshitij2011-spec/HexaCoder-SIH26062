# SIH26062 — Development & Engineering Workflow

## 1. The Mandatory Development Loop

Every engineering agent and developer contributing to the HexaCoders codebase must adhere strictly to the following 8-step cycle:

```
[1. INSPECT] ──▶ [2. PLAN] ──▶ [3. IMPLEMENT] ──▶ [4. TARGETED TEST]
                                                        │
[8. CHECKPOINT] ◀── [7. REGRESSION] ◀── [6. PLAYWRIGHT] ◀── [5. BUILD]
```

### Step 1: INSPECT
- Examine current codebase, active Git branch, existing models, and shared services.
- Never write code based on assumptions about what exists. Run directory listings, search functions, and check current database schema migrations.
- If investigating complex architectural interactions, use the `graphify` skill or codebase search tools.

### Step 2: PLAN
- Outline the minimal, coherent modification required.
- Identify the exact entities, events, schemas, and UI components that will be touched.
- Ensure the planned changes comply with `AGENTS.md` and `ENGINEERING_RULES.md`.

### Step 3: IMPLEMENT
- Write clean, modular, typed code.
- Follow established patterns in the repository (e.g. Pydantic v2 validation, SQLAlchemy async models, TanStack Query hooks, shadcn/ui components).
- Preserve existing comments and docstrings.

### Step 4: TARGETED TEST
- Execute fast unit and integration tests specifically targeting the modified service or component:
  ```bash
  pytest backend/tests/unit/test_<target>.py
  ```
- Resolve any logic errors, boundary exceptions, or schema mismatches immediately.

### Step 5: BUILD & TYPE-CHECK
- Verify that TypeScript compiles cleanly without errors or ignored type safety:
  ```bash
  npm run build --prefix frontend
  ```
- Verify backend linting and syntax:
  ```bash
  python -m py_compile backend/app/main.py
  ```

### Step 6: PLAYWRIGHT BROWSER CHECK
- For any user-facing feature or updated workflow, perform a real browser interaction session using the Playwright tool.
- Verify that elements render correctly, reactive states update upon mutation, and error states display clearly.

### Step 7: REGRESSION CHECK & GIT DIFF AUDIT
- Run the broader test suite to ensure no collateral damage to existing services.
- Inspect the exact git diff before committing:
  ```bash
  git diff
  ```
- Confirm that no unintended files, debug print statements, or secrets are staged.

### Step 8: GIT CHECKPOINT & PR WORKFLOW
- Stage only relevant files and create a clean, descriptive Git commit representing that coherent milestone.
- **NEVER** commit feature work directly to `main`.
- Work on dedicated developer branches (`a/<feature>` for Person A, `b/<feature>` for Person B).
- Rebase onto latest `origin/main` before opening PR.
- Submit Pull Request using `.github/PULL_REQUEST_TEMPLATE.md`.
- Person A merges approved PRs into `main` using **Squash and Merge**.

---

## 2. Two-Person Parallel Development Loop

```
Person A (Track A: Planning / Decisions / Controls)
    └── Branch: a/<feature> ──▶ Rebase origin/main ──▶ PR ──▶ Squash Merge ──┐
                                                                              │
                                                                         MAIN TRUNK
                                                                              │
Person B (Track B: Logistics / Resources / Incidents)                         │
    └── Branch: b/<feature> ──▶ Rebase origin/main ──▶ PR ──▶ Squash Merge ──┘
```

1. **Branch Naming**:
   - Person A: `a/<feature-name>` (e.g. `a/expedition-service`, `a/replan-engine`)
   - Person B: `b/<feature-name>` (e.g. `b/cargo-manifests`, `b/incident-triage`)
   - Shared Contract: `shared/<contract-name>` (e.g. `shared/api-envelope`)
2. **Strict Domain Non-Intrusion**:
   - Developers coordinate through explicit public contracts and shared services.
   - See [docs/CROSS_DOMAIN_PROTOCOL.md](CROSS_DOMAIN_PROTOCOL.md) and [docs/HANDOFF_PROTOCOL.md](HANDOFF_PROTOCOL.md).
3. **Automated Pre-PR Verification**:
   - Run `./scripts/verify.ps1` to ensure tests, builds, and sanity checks pass prior to opening PR.

---

## 3. Rules for Modifying Existing Subsystems

1. **Smallest Coherent Change**: Do not refactor an entire module to fix or add a single behavior.
2. **Preserve Tested Contracts**: Avoid changing public schema signatures or database column names unless an approved migration plan is documented.
3. **No Blind Rewrites**: Never delete working code to replace it with a newly generated implementation from scratch without verifying that the existing logic was truly defective.
4. **Additive Migrations Only**: Existing applied migrations under `supabase/migrations/` must never be modified. Create new sequential migration files.

