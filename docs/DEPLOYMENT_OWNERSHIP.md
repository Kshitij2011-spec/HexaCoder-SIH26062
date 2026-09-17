# SIH26062 — Deployment Authority & Infrastructure Ownership

## 1. Ownership Principle: Separation of Authority vs Product Ownership

To prevent conflicting infrastructure changes, broken production releases, and security leaks, **Person A holds exclusive operational deployment authority**.

> **Crucial Distinction**:
> **Deployment Authority does NOT equal Product Ownership.**
> Person B owns massive vertical product segments (Cargo, Packages, Transport, Locations, Inventory, Assets, Maintenance, Incidents, Response Actions, Offline Sync). 
> Restricting deployment execution to Person A ensures operational stability while allowing Person B to innovate with maximum feature velocity.

---

## 2. Responsibility Breakdown

### Person A: Production Release Commander
- **Cloud Accounts**: Owns and manages the production Render web service, Vercel frontend project, and Supabase production instance.
- **Environment Vaults**: Holds exclusive access to production secrets, service role keys, and production database passwords.
- **Merge & Tag Authority**: Performs the final PR merge into `main` and creates release tags (`v0.1.0`, `v1.0.0-hackathon`).
- **Release Execution**: Triggers deployment from the verified `main` branch.
- **Post-Deploy Smoke Test**: Executes post-deployment smoke tests and holds rollback decision authority.

### Person B: Feature Architect & Contributor
- **Feature Velocity**: Ships fully tested, robust features across logistics, inventory, fleet management, and emergency response domains.
- **Local & PR Verification**: Verifies feature branches locally against unit, integration, and Playwright suites.
- **Deployment Notes**: Outlines deployment notes, new environment keys needed, or migration sequences in PR descriptions.
- **Staging Inspection**: Can inspect deployment health, logs, and staging previews.
- **Zero Production Admin Burden**: Person B is never distracted by production provisioning failures, DNS records, or certificate rotations.

---

## 3. Production Deployment Rules

1. **Deploy Exclusively from `main`**: Deployments to production environments are strictly prohibited from personal feature branches (`a/*`, `b/*`).
2. **Pre-Deploy Verification Gate**:
   - All backend pytest tests must pass (100% green).
   - Frontend production build must succeed (`npm run build`).
   - Playwright end-to-end smoke verification must confirm the hero workflow.
3. **Rollback Protocol**: If a production incident or critical regression occurs, Person A executes an immediate rollback to the previous stable release tag on Render and Vercel.
