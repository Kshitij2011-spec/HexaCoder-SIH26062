# Local Development Environment Contract

This document establishes the standardized local development environment configuration for both Person A and Person B on the HexaCoders engineering team for SIH26062.

---

## 1. Core Principle: Parity & Reproducibility

1. **Identical Baseline**: Person A and Person B must develop using identical toolchains, runtime versions, package managers, and configuration conventions.
2. **Zero Laptop Dependencies**: Person B must never depend on Person A's local machine, private files, or ad-hoc settings. Any developer cloning the repository must be able to boot the entire stack using:
   - Clean git clone of `main`
   - `.env.example` templates
   - Migration (`supabase/migrations/`) and Seed (`supabase/seed.sql`)
   - Standard package managers (`uv`/`pip` and `npm`)
   - Documentation in this file

---

## 2. Standardized Toolchain & Runtimes

| Component | Standardized Version | Purpose | Verification Command |
|---|---|---|---|
| **Python** | `3.13+` | Backend Runtime | `python --version` |
| **Node.js** | `v20.x` or `v22.x` LTS | Frontend Runtime & Tooling | `node --version` |
| **npm** | `10.x+` | Frontend Package Manager | `npm --version` |
| **PostgreSQL** | `15+` / `16+` (via Supabase) | Relational + PostGIS Engine | `psql --version` |
| **Git** | `2.40+` | Version Control | `git --version` |
| **PowerShell** | `7+` / Windows PowerShell 5.1 | Task Automation & Verification | `$PSVersionTable.PSVersion` |

---

## 3. Repository Structure & Workspace Layout

```
HexaCoder-SIH26062/
├── .github/                     # PR templates, CODEOWNERS, CI workflows
├── backend/                     # Python 3.13 FastAPI modular monolith
│   ├── app/                     # Core application, config, DB engine
│   ├── tests/                   # Backend pytest suite
│   └── requirements.txt         # Pinned backend dependencies
├── frontend/                    # React + TypeScript + Vite UI
│   ├── src/                     # Modular component & feature architecture
│   └── package.json             # Frontend dependencies & scripts
├── supabase/                    # Database foundation
│   ├── migrations/              # Authoritative, sequential SQL migrations
│   └── seed.sql                 # Deterministic baseline & hero scenario seed
├── docs/                        # Architecture, contracts, and governance
└── scripts/                     # Cross-platform verification harnesses
```

---

## 4. Environment Configuration Setup

Each developer maintains an untracked `.env` file at the repository root (or in `backend/` and `frontend/` as specified).

### Step 1: Copy Template
```bash
cp .env.example .env
```

### Step 2: Configure Local Connection Strings
```ini
# Backend Database Configuration (Direct connection or Supabase Pooler)
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=mock-local-anon-key
SUPABASE_SERVICE_ROLE_KEY=mock-local-service-role-key

# Backend Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=true

# Frontend Environment
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

> [!CAUTION]
> Never commit `.env` or paste real production secrets into any shared file or pull request.

---

## 5. Backend Setup & Local Execution

### Virtual Environment (Recommended: `venv` or `uv`)
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### Running Backend Tests
```powershell
# Run the complete test suite
python -m pytest -p no:cacheprovider
```

### Running the Backend Dev Server (Once Scaffolded)
```powershell
uvicorn backend.app.main:app --reload --port 8000
```

---

## 6. Frontend Setup & Local Execution

```bash
cd frontend
npm install
npm run dev
```

The frontend development server runs on `http://localhost:5173`.

---

## 7. Database & Supabase Local Setup

When developing locally with the Supabase CLI:
```bash
# Start local Supabase containers (requires Docker Desktop)
npx supabase start

# Apply authoritative migrations
npx supabase db reset

# Verify seed data is applied (seed.sql runs automatically on reset)
```

If connecting to an external development PostgreSQL database:
```bash
# Apply migrations manually via psql
psql "$DATABASE_URL" -f supabase/migrations/20260917000001_expedition_operational_schema.sql
psql "$DATABASE_URL" -f supabase/seed.sql
```

---

## 8. Unified Verification Command

Before opening any PR, both developers must run the unified verification script:

```powershell
# From repository root:
.\scripts\verify.ps1
```

This script enforces:
1. All Python tests pass.
2. Frontend builds without TypeScript or bundle errors (when scaffolded).
3. Playwright E2E smoke tests pass (when servers are running).

---

## 9. Developer Machine Parity Checklist

Before opening feature branches, confirm:
- [ ] Python 3.13+ installed and active in path
- [ ] Node.js LTS (v20+) and npm installed
- [ ] `.env` created from `.env.example`
- [ ] `python -m pytest -p no:cacheprovider` passes with 24/24 tests
- [ ] Git configured with user name and email (`git config user.name`, `git config user.email`)
- [ ] Local branch is updated with latest `origin/main`
