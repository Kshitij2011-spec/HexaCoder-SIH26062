-- ============================================================
-- SIH26062 — HexaCoders Polar Expedition Operations Platform
-- Migration: 20260918000005_track_b_incident_response.sql
-- Description: Additive operational fields, incident references, and indexes for Track B Incident Response Domain
-- ============================================================

-- 1. Extend incident_status enum with OPEN, ACKNOWLEDGED, MITIGATING if using PostgreSQL
DO $$ BEGIN
    ALTER TYPE incident_status ADD VALUE IF NOT EXISTS 'OPEN';
    ALTER TYPE incident_status ADD VALUE IF NOT EXISTS 'ACKNOWLEDGED';
    ALTER TYPE incident_status ADD VALUE IF NOT EXISTS 'MITIGATING';
EXCEPTION WHEN duplicate_object THEN null;
END $$;

-- 2. Incidents Table Operational Enhancements
ALTER TABLE IF EXISTS public.incidents
    ALTER COLUMN expedition_id DROP NOT NULL,
    ALTER COLUMN status SET DEFAULT 'OPEN',
    ADD COLUMN IF NOT EXISTS title VARCHAR(255) NOT NULL DEFAULT 'Operational Incident',
    ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 3,
    ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS asset_id UUID REFERENCES public.assets(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS operational_metadata JSONB NOT NULL DEFAULT '{}';

-- 3. Incident References Table (Cross-Domain Loose Coupling)
CREATE TABLE IF NOT EXISTS public.incident_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES public.incidents(id) ON DELETE CASCADE,
    reference_type VARCHAR(50) NOT NULL,
    reference_id UUID NOT NULL,
    notes TEXT,
    operational_metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_incident_reference_target UNIQUE (incident_id, reference_type, reference_id)
);

-- 4. Performance and Lookup Indexes
CREATE INDEX IF NOT EXISTS idx_incidents_code ON public.incidents(incident_code);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON public.incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON public.incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_priority ON public.incidents(priority);
CREATE INDEX IF NOT EXISTS idx_incidents_detected_at ON public.incidents(detected_at);
CREATE INDEX IF NOT EXISTS idx_incidents_location_id ON public.incidents(location_id);
CREATE INDEX IF NOT EXISTS idx_incidents_asset_id ON public.incidents(asset_id);
CREATE INDEX IF NOT EXISTS idx_incident_references_incident_id ON public.incident_references(incident_id);
CREATE INDEX IF NOT EXISTS idx_incident_references_target ON public.incident_references(reference_type, reference_id);

-- 5. Row Level Security for Incident References
ALTER TABLE IF EXISTS public.incident_references ENABLE ROW LEVEL SECURITY;
