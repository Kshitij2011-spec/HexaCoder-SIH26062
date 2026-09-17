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

## 3. Strict Security Rules

1. **`.env` is Git-Ignored**: Real `.env` files are never tracked or committed.
2. **Template Only in Git**: Only [.env.example](../.env.example) is committed to Git, containing empty or mock development defaults.
3. **No Secret Inlining**: Never write production credentials into source code, PR descriptions, test scripts, or markdown documentation.
4. **Production Key Isolation**: Production API keys, Supabase Service Role keys, and Render database passwords are known exclusively to Person A and injected via cloud provider environment vaults.
