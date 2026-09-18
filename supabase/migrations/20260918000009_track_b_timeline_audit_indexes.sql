-- Track B Milestone B9: Operational Timeline Query Performance Indexes
-- Additive indexes on public.audit_log for entity timeline lookups, occurred_at ordering, and correlation joins.

CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON public.audit_log (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_occurred_at ON public.audit_log (occurred_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_correlation_id ON public.audit_log (correlation_id);
