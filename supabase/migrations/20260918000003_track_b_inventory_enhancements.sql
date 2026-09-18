-- ============================================================
-- SIH26062 — HexaCoders Polar Expedition Operations Platform
-- Migration: 20260918000003_track_b_inventory_enhancements.sql
-- Description: Additive operational fields and indexes for Track B Inventory Domain
-- ============================================================

-- 1. Operational Metadata Enhancements for Inventory Entities
ALTER TABLE IF EXISTS public.inventory_items
    ADD COLUMN IF NOT EXISTS operational_metadata JSONB NOT NULL DEFAULT '{}';

ALTER TABLE IF EXISTS public.inventory_stock_lots
    ADD COLUMN IF NOT EXISTS operational_metadata JSONB NOT NULL DEFAULT '{}';

ALTER TABLE IF EXISTS public.inventory_transactions
    ADD COLUMN IF NOT EXISTS operational_metadata JSONB NOT NULL DEFAULT '{}';

-- 2. Inventory Query & Ledger Performance Indexes
CREATE INDEX IF NOT EXISTS idx_stock_lots_item_location ON public.inventory_stock_lots(inventory_item_id, location_id);
CREATE INDEX IF NOT EXISTS idx_stock_transactions_lot_occurred ON public.inventory_transactions(stock_lot_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_stock_transactions_reference ON public.inventory_transactions(reference_type, reference_id);
