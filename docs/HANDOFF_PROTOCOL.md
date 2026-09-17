# Handoff & PR Completion Protocol

This protocol defines the exact steps required for a feature branch to be considered complete, reviewed, merged into `main`, and subsequently synchronized back to working branches.

---

## 1. Feature Completion Definition of Done (DoD)

A branch (`a/<feature-name>` or `b/<feature-name>`) is **READY FOR REVIEW** if and only if all of the following conditions are met:

1. **Implementation Complete**:
   - Scope is self-contained and fulfills the target task or user story.
   - Code adheres to the Modular Monolith layering rules in [docs/ARCHITECTURE.md](file:///c:/Users/Kshitij%20Parkhe/OneDrive/Desktop/HexaCoder-SIH26062/docs/ARCHITECTURE.md).
2. **Automated Tests Included**:
   - New or modified logic is backed by deterministic automated tests (`pytest` for backend, unit/component tests for frontend).
   - All tests pass locally (`python -m pytest -p no:cacheprovider`).
3. **Database Integrity**:
   - Any schema changes are in a new, sequential migration file under `supabase/migrations/`.
   - Existing migration files are untouched.
   - `supabase/seed.sql` is updated if new mandatory entities or reference codes were introduced.
4. **Contract & Documentation Alignment**:
   - If public API endpoints, event types, or dependency relations were added/changed, relevant docs ([docs/API_CONTRACT_POLICY.md](file:///c:/Users/Kshitij%20Parkhe/OneDrive/Desktop/HexaCoder-SIH26062/docs/API_CONTRACT_POLICY.md), [docs/EVENT_CONTRACT.md](file:///c:/Users/Kshitij%20Parkhe/OneDrive/Desktop/HexaCoder-SIH26062/docs/EVENT_CONTRACT.md), [docs/DEPENDENCY_CONTRACT.md](file:///c:/Users/Kshitij%20Parkhe/OneDrive/Desktop/HexaCoder-SIH26062/docs/DEPENDENCY_CONTRACT.md)) are updated in the same PR.
5. **E2E & UI Verification**:
   - If frontend UI components or pages were added/modified, interactive behavior is verified via Playwright.
6. **Clean Working Tree**:
   - No untracked scratch files, temp artifacts, or stray logs.
   - `git status` shows a clean working tree.
7. **No Hardcoded Secrets**:
   - Zero API keys, passwords, or service role keys present in any committed file or git diff.
8. **PR Template Completed**:
   - PR is opened against `main` using `.github/PULL_REQUEST_TEMPLATE.md` with all checklist items checked.

---

## 2. Pre-PR Synchronization Policy: Rebase onto Main

To prevent messy merge commits and ensure that all tests run against the latest integrated state, the project enforces a **Rebase onto Main** policy before PR submission.

### Workflow:
```powershell
# 1. Fetch latest changes from remote
git fetch origin

# 2. Rebase local feature branch onto latest origin/main
git checkout b/cargo-rebalancing
git rebase origin/main

# 3. Resolve any conflicts locally and run verification
.\scripts\verify.ps1

# 4. Push branch to remote
git push origin b/cargo-rebalancing
```

> [!WARNING]
> Only rebase your own unmerged feature branch (`a/*` or `b/*`). Never rebase `main` or a `shared/*` branch that another developer is concurrently working on.

---

## 3. Pull Request Review & Merge Protocol

### Review Responsibilities:
- **Track B PRs (Person B)**: Reviewed by Person A. Person A verifies architectural alignment, database migrations, shared contract stability, and runs automated checks.
- **Track A PRs (Person A)**: Person A opens PRs for substantial features. Person B reviews and tests contract consumers.
- **Shared Platform PRs**: Must be reviewed by both developers.

### Merge Strategy: Squash and Merge
- **Method**: Every PR must be merged via **Squash and Merge** on GitHub.
- **Merge Authority**: **Person A has exclusive final merge authority.** Person B does not self-merge PRs.
- **Commit Message Convention**: The squash commit title on `main` must follow Conventional Commits:
  - `feat(cargo): implement package weight and volume validation (#12)`
  - `fix(missions): correct weather window temporal boundary evaluation (#14)`
  - `chore(deps): update fast-api and pydantic dependencies (#15)`

---

## 4. Post-Merge Developer Synchronization

Immediately after Person A merges a PR into `main`:

### For the Developer whose PR was merged:
```powershell
# Switch to main and pull latest squashed commit
git checkout main
git pull origin main

# Delete local feature branch
git branch -d b/cargo-rebalancing
```

### For the Parallel Developer working on an active branch:
```powershell
# Fetch updated main
git fetch origin

# Rebase active feature branch onto newly updated main
git checkout b/active-feature
git rebase origin/main

# Verify tests still pass against newly integrated state
.\scripts\verify.ps1
```

This guarantees continuous micro-integration and eliminates large, painful end-of-phase merge conflicts.
