# SIH26062 — Git Branching, Integration & Merge Workflow

## 1. Branch Topology

The repository uses a streamlined **Trunk-Based Integration Model** centered on a single long-lived branch: `main`.

There is **NO** permanent `develop` branch. `main` is the continuous integration branch and the sole source for production deployments.

```
                   ┌────────────────────────────────────────┐
                   │                 MAIN                   │
                   │      (Protected Integration Trunk)     │
                   └────┬──────────────────────────────▲────┘
                        │                              │
             git checkout -b                    Squash Merge via PR
                        │                              │
       ┌────────────────┴───────────────┐              │
       │                                │              │
┌──────▼───────────────────┐    ┌───────▼──────────────┴───┐
│ Person A Feature Branch  │    │ Person B Feature Branch  │
│ e.g. a/mission-readiness │    │ e.g. b/cargo-tracking    │
└──────────────────────────┘    └──────────────────────────┘
```

---

## 2. Branch Naming Conventions

All work is conducted on short-lived feature branches following strict prefixes:

### Person A Branches (`a/*`)
Used for Person A's domains (Expeditions, Missions, Planning, Constraints, Approvals, Control Tower):
- `a/expedition-lifecycle`
- `a/mission-readiness-engine`
- `a/constraint-solver`
- `a/replan-recommendations`
- `a/control-tower-overview`

### Person B Branches (`b/*`)
Used for Person B's domains (Cargo, Transport, Inventory, Assets, Maintenance, Incidents, Sync):
- `b/cargo-manifesting`
- `b/transport-tracking`
- `b/inventory-reservations`
- `b/fleet-maintenance`
- `b/incident-emergency-command`
- `b/offline-sync-queue`

### Shared Branches (`shared/*`)
Used **only** when both developers explicitly collaborate on a cross-cutting platform change:
- `shared/api-contract-v1`
- `shared/design-system-tokens`
- `shared/test-harness-update`

---

## 3. Rules for the `main` Branch

1. **Production-Ready Baseline**: `main` must always build, pass all automated unit/integration tests, and be clean of broken features.
2. **No Routine Direct Commits**: Neither Person A nor Person B should commit feature code directly to `main`. All feature additions arrive via Pull Requests.
3. **No Force-Pushing**: Force-pushing (`git push --force`) to `main` is strictly prohibited.
4. **No History Rewriting**: Rebasing or amending commits that have already been pushed to `main` is forbidden.
5. **Sole Source for Deployments**: Deployments to Vercel (frontend) and Render (backend) occur exclusively from `main`.

---

## 4. End-to-End Developer Workflow

### Step 1: Branch Creation
Always branch from an up-to-date `main`:
```bash
git checkout main
git pull origin main
git checkout -b b/cargo-manifesting
```

### Step 2: Implementation & Local Testing
Write modular code, author tests, and execute targeted verification:
```bash
python -m pytest tests/test_database_schema_and_seed.py -v -p no:cacheprovider
```

### Step 3: Local Commit
Group changes logically with descriptive commit messages conforming to Conventional Commits:
```bash
git add .
git commit -m "feat(cargo): implement consignment manifest validation schema"
```

### Step 4: Rebase onto Current `main`
Before pushing, ensure your branch integrates cleanly with the latest changes merged to `main`:
```bash
git fetch origin main
git rebase origin/main
```
*(If merge conflicts occur, resolve them in your domain files, verify tests, and run `git rebase --continue`)*.

### Step 5: Push Branch & Open Pull Request
Push your branch to GitHub:
```bash
git push -u origin b/cargo-manifesting
```
Open a Pull Request targeting `main` using the standard [.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md).

### Step 6: Review & Merge
1. The peer developer reviews the PR, inspecting cross-domain contracts, tests, and documentation.
2. The GitHub Actions CI pipeline (`CI / Backend Unit & Schema Tests`) must pass green.
3. Person A performs the **Squash and Merge** into `main`.
4. The remote feature branch is deleted.
5. Person B checks out `main` and pulls the latest integrated state:
```bash
git checkout main
git pull origin main
```

---

## 5. Continuous Integration (CI) Pipeline

Automated checks are executed on every push and pull request targeting `main` via [.github/workflows/ci.yml](../.github/workflows/ci.yml).

### CI Gates Enforced:
1. **Repository & Artifact Integrity**: Verifies presence of authoritative migrations, seed files, constitution (`AGENTS.md`), and environment templates.
2. **Backend Unit & Schema Test Suite**: Executes `python -m pytest tests/ -v` on Python 3.13.
3. **No Database Secrets Required**: Baseline CI executes self-contained schema and unit checks without requiring remote Supabase credentials or production access.

Every Pull Request must achieve a passing CI run before merge.

---

## 6. GitHub Branch Protection Policy (`main`)

To preserve the integrity of the integration trunk, the following protection rules must be configured for the `main` branch in the GitHub repository settings:

1. **Require a pull request before merging**: Disallow direct routine commits to `main`.
2. **Require status checks to pass before merging**:
   - Required status check: `CI / Backend Unit & Schema Tests`
3. **Do not allow force pushes**: Block `git push --force`.
4. **Do not allow deletions**: Prevent accidental deletion of `main`.
5. **Merge Authority**: Person A (Project Head) retains exclusive final squash-and-merge authority. Approvals from specific named users are not hard-locked to prevent blocking parallel development before Person B's GitHub handle is confirmed.

> [!NOTE]
> **Enforcement Status**: Branch protection is fully documented here and in CODEOWNERS. Because GitHub remote branch protection rules require repository administrator configuration in GitHub Web Settings (or GitHub CLI with admin scope), the status is:
> **Branch protection documented but not remotely enforced**.
> Person A should toggle these settings in the GitHub repository Settings -> Branches UI upon the first remote push.

