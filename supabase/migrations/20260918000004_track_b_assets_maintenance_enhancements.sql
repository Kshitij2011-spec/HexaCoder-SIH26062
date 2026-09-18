-- ============================================================
-- SIH26062 — HexaCoders Polar Expedition Operations Platform
-- Migration: 20260918000004_track_b_assets_maintenance_enhancements.sql
-- Description: Additive operational fields and indexes for Track B Assets & Maintenance Domain
-- ============================================================

-- 1. Extend asset_status enum with QUARANTINED if using PostgreSQL
DO $$ BEGIN
    ALTER TYPE asset_status ADD VALUE IF NOT EXISTS 'QUARANTINED';
EXCEPTION WHEN duplicate_object THEN null;
END $$;

-- 2. Assets Table Operational Enhancements
ALTER TABLE IF EXISTS public.assets
    ADD COLUMN IF NOT EXISTS serial_number VARCHAR(100),
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS criticality VARCHAR(50) NOT NULL DEFAULT 'STANDARD',
    ADD COLUMN IF NOT EXISTS operational_metadata JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS commissioned_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS retired_at TIMESTAMPTZ;

-- 3. Maintenance Records Operational Enhancements
ALTER TABLE IF EXISTS public.maintenance_records
    ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 3,
    ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS technician_reference VARCHAR(150),
    ADD COLUMN IF NOT EXISTS findings TEXT,
    ADD COLUMN IF NOT EXISTS corrective_action TEXT,
    ADD COLUMN IF NOT EXISTS operational_metadata JSONB NOT NULL DEFAULT '{}';

-- 4. Assets & Maintenance Performance Indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_assets_serial_number ON public.assets(serial_number) WHERE serial_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_assets_location ON public.assets(location_id);
CREATE INDEX IF NOT EXISTS idx_assets_status ON public.assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_type ON public.assets(type);
CREATE INDEX IF NOT EXISTS idx_maintenance_asset_status ON public.maintenance_records(asset_id, status);
CREATE INDEX IF NOT EXISTS idx_maintenance_scheduled_at ON public.maintenance_records(scheduled_at);
