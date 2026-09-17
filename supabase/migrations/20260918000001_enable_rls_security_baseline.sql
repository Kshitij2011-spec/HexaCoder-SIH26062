-- ============================================================
-- SIH26062 — HexaCoders Polar Expedition Operations Platform
-- Migration: 20260918000001_enable_rls_security_baseline.sql
-- Description: Enable Row Level Security (RLS) across all 35 operational tables.
--              No permissive public policies defined yet (Phase 2 RBAC baseline).
--              Protects unauthenticated PostgREST / Supabase REST endpoint from
--              direct anonymous data leakage while preserving FastAPI private direct access.
-- ============================================================

-- 1. Core Expedition & Personnel Tables
ALTER TABLE IF EXISTS public.expeditions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.missions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.people ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.assignments ENABLE ROW LEVEL SECURITY;

-- 2. Cargo & Transport Legs Tables
ALTER TABLE IF EXISTS public.cargo_consignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.transport_legs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.cargo_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.transport_cargo_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.transport_person_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.transport_asset_assignments ENABLE ROW LEVEL SECURITY;

-- 3. Inventory & Assets Tables
ALTER TABLE IF EXISTS public.inventory_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.inventory_stock_lots ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.inventory_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.maintenance_records ENABLE ROW LEVEL SECURITY;

-- 4. Governance, Windows, Dependencies & Events
ALTER TABLE IF EXISTS public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.time_windows ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.constraints ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.operational_events ENABLE ROW LEVEL SECURITY;

-- 5. Emergency Incidents & Actions Tables
ALTER TABLE IF EXISTS public.incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.incident_people ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.incident_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.incident_missions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.incident_cargo ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.response_actions ENABLE ROW LEVEL SECURITY;

-- 6. Replanning, Recommendations & Approvals Tables
ALTER TABLE IF EXISTS public.replans ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.recommendation_alternatives ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.approvals ENABLE ROW LEVEL SECURITY;

-- 7. Audit & Offline Synchronization Tables
ALTER TABLE IF EXISTS public.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.sync_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.sync_conflicts ENABLE ROW LEVEL SECURITY;
