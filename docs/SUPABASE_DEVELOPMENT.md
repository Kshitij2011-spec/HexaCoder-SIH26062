# Shared Supabase Development Environment

This document records the configuration, metadata, and connection architecture for the dedicated development database powering the SIH26062 Antarctic & Polar Expedition Operational Logistics Platform.

---

## 1. Project Metadata

| Attribute | Value | Description |
|---|---|---|
| **Project Name** | `HexaCoders SIH26062 DEV` | Dedicated development project |
| **Project ID / Ref** | `tywtsmvccifkugoecrmd` | Canonical Supabase project reference |
| **Organization Name** | `Kshitij2011-spec's Org` | Supabase organization |
| **Organization ID** | `arhopcokketfspyswhgh` | Organization identifier |
| **Region** | `ap-south-1` (Mumbai, India) | Lowest latency Indian development region |
| **Engine / Version** | PostgreSQL 17.6 / PostGIS | Supabase managed relational platform |
| **Database Host** | `db.tywtsmvccifkugoecrmd.supabase.co` | Remote PostgreSQL server host |
| **Project URL** | `https://tywtsmvccifkugoecrmd.supabase.co` | REST / API endpoint |
| **Environment Tier** | **DEVELOPMENT ONLY** | Strictly isolated from future production |

> [!IMPORTANT]
> **Old Project Isolation**: The inactive legacy project `krishi-sahayak` (`pmvyiptvbdrqvzbvogvr`) was completely untouched and remains isolated. It is never used for SIH26062.
>
> **Production Isolation**: Production will be provisioned by Person A in a separate Supabase project during final deployment phases. No development work or tests may target production.

---

## 2. Database Architecture & Access Contract

```
┌───────────────────────────────────────┐
│        Supabase DEV Project           │
│        (ID: tywtsmvccifkugoecrmd)      │
│                                       │
│    PostgreSQL 17.6 + PostGIS          │
│    Authoritative Persistence Layer     │
└───────────────────▲───────────────────┘
                    │ Private DB Connection
                    │ (DATABASE_URL / SUPABASE_DB_URL)
┌───────────────────┴───────────────────┐
│            FastAPI Backend            │
│       Authoritative Business API      │
└───────────────────▲───────────────────┘
                    │ HTTP / REST (/api/v1/)
                    │ JSON Envelopes
┌───────────────────┴───────────────────┐
│          React + Vite Frontend        │
│          Presentation Layer           │
└───────────────────────────────────────┘
```

1. **FastAPI is Authoritative**: React clients never query or mutate core operational tables directly. All requests pass through FastAPI domain services.
2. **Private Connection**: The database connection string (`DATABASE_URL` or `SUPABASE_DB_URL`) is confidential to the backend runtime.
3. **No Secrets in Frontend**: `SUPABASE_SERVICE_ROLE_KEY` must never be provided to or bundled with frontend applications.

---

## 3. Applied Migration & Seed Verification

- **Authoritative DDL Migration**: [20260917000000_expedition_operational_schema.sql](file:///c:/Users/Kshitij%20Parkhe/OneDrive/Desktop/HexaCoder-SIH26062/supabase/migrations/20260917000000_expedition_operational_schema.sql)
  - Successfully applied to `tywtsmvccifkugoecrmd`.
  - 35 operational tables created.
  - 14 controlled enum types instantiated.
  - Immutability trigger `trg_operational_events_immutable` deployed and validated.
- **Deterministic Baseline Seed**: [supabase/seed.sql](file:///c:/Users/Kshitij%20Parkhe/OneDrive/Desktop/HexaCoder-SIH26062/supabase/seed.sql)
  - Successfully seeded against `tywtsmvccifkugoecrmd`.
  - 1 Expedition (`EXP-26-A`), 3 Missions (`M-08`, `M-02`, `M-05`), 2 Teams (`R-04`, `R-02`), 6 Personnel, 10 Locations.
  - 3 Cargo Consignments (`C-117`, `C-102`, `C-115`), 8 Packages, 5 Transport Legs (`T-08`, `T-01`..`T-04`).
  - 10 Inventory Items, 11 Stock Lots, 6 Assets, 5 Maintenance Records, 8 Documents, 6 Time Windows.
  - 17 Semantic Dependencies, 6 Constraints, 10 Operational Events, 2 Historical Incidents, 2 Response Actions.
- **Hero Operational Chain Verified**:
  `EXP-26-A` ──▶ `M-08` ──▶ `I-42` ──▶ `C-117` ──▶ `PKG-117-01` ──▶ `T-08` (validated via live relational join).
- **Event Immutability Verified**: Live `UPDATE` and `DELETE` attempts against `operational_events` were rejected with code `P0001`.

---

## 4. Developer Connection Instructions

Both Person A and Person B can configure their local backend to point to this shared development database by setting in their local `.env`:

```ini
# Shared Development Database Connection (Supabase Session Pooler or Direct)
# Obtain the secure development password from Person A's password vault
DATABASE_URL=postgresql://postgres:[DEV_PASSWORD]@db.tywtsmvccifkugoecrmd.supabase.co:5432/postgres
SUPABASE_URL=https://tywtsmvccifkugoecrmd.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Backend Config
ENVIRONMENT=development
API_BASE_URL=http://localhost:8000/api/v1
```

> [!CAUTION]
> Never commit `.env` or hardcode connection strings into source code or pull requests.
