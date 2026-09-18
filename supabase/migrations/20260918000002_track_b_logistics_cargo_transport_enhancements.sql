-- ============================================================
-- SIH26062 — HexaCoders Polar Expedition Operations Platform
-- Migration: 20260918000002_track_b_logistics_cargo_transport_enhancements.sql
-- Description: Additive operational fields and indexes for Track B Logistics (Transport & Cargo)
-- ============================================================

-- 1. Transport Legs Enhancements
ALTER TABLE IF EXISTS public.transport_legs
    ADD COLUMN IF NOT EXISTS actual_departure_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS actual_arrival_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS operational_metadata JSONB NOT NULL DEFAULT '{}';

-- 2. Cargo Consignments Enhancements
ALTER TABLE IF EXISTS public.cargo_consignments
    ADD COLUMN IF NOT EXISTS planned_arrival_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS risk_level VARCHAR(50) NOT NULL DEFAULT 'NOMINAL';

-- 3. Logistics Performance Indexes
CREATE INDEX IF NOT EXISTS idx_locations_parent ON public.locations(parent_location_id);
CREATE INDEX IF NOT EXISTS idx_locations_status ON public.locations(status);
CREATE INDEX IF NOT EXISTS idx_transport_legs_status ON public.transport_legs(status);
CREATE INDEX IF NOT EXISTS idx_transport_legs_origin ON public.transport_legs(origin_location_id);
CREATE INDEX IF NOT EXISTS idx_transport_legs_destination ON public.transport_legs(destination_location_id);
CREATE INDEX IF NOT EXISTS idx_cargo_consignments_status ON public.cargo_consignments(status);
CREATE INDEX IF NOT EXISTS idx_cargo_consignments_risk ON public.cargo_consignments(risk_level);
CREATE INDEX IF NOT EXISTS idx_cargo_packages_consignment ON public.cargo_packages(consignment_id);
