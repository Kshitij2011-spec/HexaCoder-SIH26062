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
