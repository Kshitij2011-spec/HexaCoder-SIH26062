-- ============================================================
-- SIH26062 — HexaCoders Polar Expedition Operations Platform
-- Migration: 20260918000006_track_b_offline_sync.sql
-- Description: Offline operation queue and sync foundation for Track B
-- ============================================================

-- 1. Offline Operations Queue Table
-- Stores operations queued while connectivity was unavailable.
-- operation_id is the client-supplied idempotency key (UUID).
CREATE TABLE IF NOT EXISTS public.offline_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation_id UUID NOT NULL UNIQUE,          -- client idempotency key
    entity_type VARCHAR(100) NOT NULL,          -- e.g. INVENTORY_ITEM, ASSET, INCIDENT
    operation_type VARCHAR(100) NOT NULL,       -- e.g. CREATE, UPDATE, STATE_TRANSITION
    payload JSONB NOT NULL DEFAULT '{}',        -- operation payload snapshot (SYNTHETIC_DEMO)
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',  -- PENDING, APPLIED, FAILED, REJECTED
    queued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    applied_at TIMESTAMPTZ,
    failure_reason TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    actor_id UUID,                              -- person/user who queued this operation
    correlation_id UUID,
    data_provenance VARCHAR(50) NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_offline_op_status CHECK (
        status IN ('PENDING', 'APPLIED', 'FAILED', 'REJECTED')
    ),
    CONSTRAINT chk_offline_op_retry CHECK (retry_count >= 0)
);

-- 2. Performance indexes
CREATE INDEX IF NOT EXISTS idx_offline_ops_operation_id ON public.offline_operations(operation_id);
CREATE INDEX IF NOT EXISTS idx_offline_ops_status ON public.offline_operations(status);
CREATE INDEX IF NOT EXISTS idx_offline_ops_entity ON public.offline_operations(entity_type, operation_type);
CREATE INDEX IF NOT EXISTS idx_offline_ops_queued_at ON public.offline_operations(queued_at);
CREATE INDEX IF NOT EXISTS idx_offline_ops_actor_id ON public.offline_operations(actor_id);

-- 3. Row Level Security
ALTER TABLE IF EXISTS public.offline_operations ENABLE ROW LEVEL SECURITY;
