# SIH26062 — Database Change & Migration Policy

## 1. Migration Immutability Rule

> **CRITICAL RULE**:
> Once a migration SQL file in `supabase/migrations/` has been merged to `main`, it is **PERMANENT AND IMMUTABLE**.
> Developers must **NEVER** edit, reorder, or delete an existing migration file.

If a bug is discovered, a column needs renaming, or an index must be tuned, the developer must author a **NEW forward migration**:
```
supabase/migrations/<timestamp>_<descriptive_action>.sql
```

Editing applied migrations desynchronizes local developer databases, breaks CI test repeatability, and invalidates Supabase remote environments.

---

## 2. Migration Authoring Standards

1. **Additive Schema Design**: Prefer additive modifications (adding nullable columns, new tables, or new indexes) to avoid breaking concurrent feature branches.
2. **Deterministic & Safe Operations**:
   - Use `CREATE TABLE IF NOT EXISTS`.
   - Wrap enum modifications in safe conditional blocks (`DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN null; END $$;`).
   - Use `CREATE INDEX IF NOT EXISTS`.
3. **No Destructive Drops**: `DROP TABLE`, `DROP COLUMN`, or `TRUNCATE` are prohibited on operational history tables.
4. **Include Automated Test Updates**: Any change to constraints, enums, or foreign keys must be accompanied by an update to `tests/test_database_schema_and_seed.py`.

---

## 3. Seed Data Governance

The deterministic seed script `supabase/seed.sql` represents the single shared operational benchmark.

1. **Stable Hero Baseline**: The 6 hero operational entities must remain constant across all branches:
   - `EXP-26-A` (Expedition)
   - `M-08` (Mission)
   - `R-04` (Team)
   - `I-42` (Asset / Instrument)
   - `C-117` (Cargo Consignment)
   - `T-08` (Transport Leg)
2. **Adding Feature Seed Data**:
   - Developers may append domain-specific scenario records (e.g. additional skidoos, extra ration boxes) to the designated sections in `supabase/seed.sql`.
   - All added seed records must have fixed, deterministic UUIDs and carry `data_provenance = 'SYNTHETIC_DEMO'`.
3. **No Breaking Modifications to Existing Seed**: A developer must not delete or modify another developer's seeded records without explicit agreement.

---

## 4. Shared Development Database Safety Rules

1. **No Manual Remote Schema Edits**: Never manually edit remote schema using arbitrary SQL outside tracked migrations.
2. **Schema Changes Require Migration Files**: Every schema evolution must exist as an authored `.sql` file in `supabase/migrations/`.
3. **Applied Migrations Are Never Edited**: Forward migrations only.
4. **Feature Branch Migrations**: Developers may author new migrations on `a/<feature>` or `b/<feature>` branches.
5. **Pre-Merge Migration Rebase**: Before opening a PR or merging into `main`, the developer must:
   - Rebase against latest `origin/main`.
   - Verify migration sequence and timestamp ordering.
   - Confirm zero conflicting migration file names.
   - Run `./scripts/verify.ps1` to validate schema assertions.
6. **Coordinated Remote Operations**: Destructive development database operations (e.g. table resets, data purges) require explicit coordination between Person A and Person B.
7. **No Casual Database Drops**: No developer may casually drop or reset the shared development database (`tywtsmvccifkugoecrmd`).
8. **Seed Baseline is Canonical**: `supabase/seed.sql` is the authoritative source for demo data.
9. **Documented Seed Additions**: Domain-specific seed additions must be intentional, well-commented, and preserve data provenance (`SYNTHETIC_DEMO`).

