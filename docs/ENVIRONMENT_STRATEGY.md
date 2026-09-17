# SIH26062 — Environment & Configuration Strategy

## 1. Environment Tiers

The project establishes three distinct runtime environment tiers:

```
┌────────────────────────┐     ┌────────────────────────┐     ┌────────────────────────┐
│   LOCAL DEVELOPMENT    │     │   SHARED STAGING / DEV │     │       PRODUCTION       │
│  Developer Local .env  │     │  Remote Supabase Dev   │     │  Vercel + Render Prod  │
│  Person A & B Isolated │ ──▶ │  Shared Test Database  │ ──▶ │  Managed Exclusively   │
│  Fast Iteration Loop   │     │  Integration Validation│     │  by Person A (Head)    │
└────────────────────────┘     └────────────────────────┘     └────────────────────────┘
```

---

## 2. Configuration Parameters & Tiers

| Configuration Key | Purpose | Local Dev | Shared Staging | Production (Person A Only) |
| :--- | :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | Execution mode | `development` | `staging` | `production` |
| `LOG_LEVEL` | Python logging verbosity | `DEBUG` / `INFO` | `INFO` | `WARNING` |
| `POSTGRES_SERVER` | Database host | `localhost` | Remote Dev Host | Supabase Cloud Pooler |
| `POSTGRES_PORT` | Database port | `5432` | `5432` / `6543` | `6543` (Transaction pooler) |
| `DATABASE_URL` | SQLAlchemy connection string | Local connection | Staging connection | Secure secret injection |
| `SUPABASE_URL` | Supabase API endpoint | *Optional / Local* | Staging project URL | Production project URL |
| `SUPABASE_ANON_KEY` | Public client API key | *Optional / Local* | Staging Anon Key | Production Anon Key |
| `SUPABASE_SERVICE_ROLE_KEY`| Administrative backend key | *Never in frontend*| Backend secret vault | Backend Render secret vault |
| `SECRET_KEY` | JWT signing secret | Local dev dummy key | Staging secret | High-entropy production key |
| `VITE_API_BASE_URL` | Frontend API client target | `http://localhost:8000/api/v1` | Staging API URL | Production API URL |

---

## 3. Dedicated Development Project (SIH26062 DEV)

The development environment operates on a dedicated Supabase PostgreSQL project:

- **Project ID**: `tywtsmvccifkugoecrmd`
- **Project Name**: `HexaCoders SIH26062 DEV`
- **Region**: `ap-south-1` (Mumbai, India — selected for lowest latency development access in India)
- **Status**: Active development database shared by Person A and Person B.
- **Legacy Project Isolation**: The old `krishi-sahayak` (`pmvyiptvbdrqvzbvogvr`) project is completely unassociated and untouched.
- **Production Isolation**: Production will run on a completely separate Supabase project provisioned exclusively by Person A. Production data must never be copied to or used in development.

---

## 4. Strict Security Rules

1. **`.env` is Git-Ignored**: Real `.env` files are never tracked or committed.
2. **Template Only in Git**: Only [.env.example](../.env.example) is committed to Git, containing empty or mock development defaults.
3. **No Secret Inlining**: Never write production credentials into source code, PR descriptions, test scripts, or markdown documentation.
4. **Backend-Only Service Role Key**: `SUPABASE_SERVICE_ROLE_KEY` is strictly for backend administrative routines and must never be exposed to the frontend.
5. **Production Key Isolation**: Production API keys, Supabase Service Role keys, and Render database passwords are known exclusively to Person A and injected via cloud provider environment vaults.

---

## 5. Shared DEV Credential Policy

Both Person A and Person B require independent access to the shared development database (`tywtsmvccifkugoecrmd`).

### Distribution Protocol:
1. **Out-of-Band Sharing Only**: The shared development database password is communicated strictly through secure out-of-band channels (team password manager, e.g. Bitwarden / 1Password, or encrypted direct communication).
2. **Never in Public/Shared Artifacts**: Storing or printing the database password in Git commits, GitHub issues, pull request descriptions, documentation, markdown files, test files, screenshots, or chat logs is **strictly prohibited**.
3. **Local Developer Storage**: Each developer places the connection string into their local `.env` file (which is git-ignored).
4. **Automated Safety Check**: Run `./scripts/check-env.ps1` to verify required variable names are present without exposing values or credentials.

---

## 6. Database Connection & Role Safety

1. **Direct Backend Connection**: The FastAPI backend connects directly to PostgreSQL via SQLAlchemy / asyncpg / psycopg using server-side configuration (`DATABASE_URL` or `SUPABASE_DB_URL`).
2. **Administrative Development Connection**: In the development tier, the backend uses the standard server-side connection string. Because this connection is private to the backend server and never exposed to browsers, this provides a pragmatic, secure foundation for the MVP.
3. **No Direct Client Database Access**: The React frontend has zero direct connection strings, service role keys, or database passwords. All operational data access is mediated through FastAPI domain endpoints (`/api/v1/`).


