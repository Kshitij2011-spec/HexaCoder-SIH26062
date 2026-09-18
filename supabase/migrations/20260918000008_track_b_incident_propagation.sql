-- ============================================================
-- SIH26062 — HexaCoders Polar Expedition Operations Platform
-- Migration: 20260918000008_track_b_incident_propagation.sql
-- Description: Additive incident propagation audit and idempotency table for Track B Milestone B8
-- ============================================================

-- 1. Incident Propagations Table
-- Stores auditable results of cross-domain operational impact propagation from active incidents.
CREATE TABLE IF NOT EXISTS public.incident_propagations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES public.incidents(id) ON DELETE CASCADE,
    reference_id UUID NOT NULL,
    reference_type VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    previous_state VARCHAR(100),
    resulting_state VARCHAR(100),
    reason TEXT,
    event_id UUID,
    audit_id UUID,
    operational_metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_incident_propagation_status CHECK (
        status IN ('APPLIED', 'SKIPPED', 'REJECTED', 'REQUIRES_OPERATOR_ACTION', 'NOT_SUPPORTED')
    ),
    CONSTRAINT uq_incident_propagation_action UNIQUE (incident_id, reference_type, reference_id, action)
);

-- 2. Lookup and Performance Indexes
CREATE INDEX IF NOT EXISTS idx_incident_propagations_incident_id ON public.incident_propagations(incident_id);
CREATE INDEX IF NOT EXISTS idx_incident_propagations_reference ON public.incident_propagations(reference_type, reference_id);
CREATE INDEX IF NOT EXISTS idx_incident_propagations_status ON public.incident_propagations(status);
CREATE INDEX IF NOT EXISTS idx_incident_propagations_created_at ON public.incident_propagations(created_at);

-- 3. Row Level Security
ALTER TABLE IF EXISTS public.incident_propagations ENABLE ROW LEVEL SECURITY;
