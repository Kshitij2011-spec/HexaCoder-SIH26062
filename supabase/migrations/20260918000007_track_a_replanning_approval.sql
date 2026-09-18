-- ============================================================
-- SIH26062 — HexaCoders Polar Expedition Operations Platform
-- Migration: 20260918000007_track_a_replanning_approval.sql
-- Description: Additive enhancements for Track A Replanning, Recommendations,
--              Candidate Options, and Human Approval Decision Engine
-- ============================================================

-- 1. Replans Table Enhancements
ALTER TABLE IF EXISTS public.replans
    ADD COLUMN IF NOT EXISTS mission_id UUID REFERENCES public.missions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS trigger_entity_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS trigger_entity_id UUID,
    ADD COLUMN IF NOT EXISTS current_state_evidence JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS violated_constraints JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS affected_entities JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS requested_by UUID REFERENCES public.people(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS correlation_id UUID;

-- 2. Recommendation Alternatives (Replan Options) Enhancements
ALTER TABLE IF EXISTS public.recommendation_alternatives
    ALTER COLUMN recommendation_id DROP NOT NULL;

ALTER TABLE IF EXISTS public.recommendation_alternatives
    ADD COLUMN IF NOT EXISTS replan_id UUID REFERENCES public.replans(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS action_type VARCHAR(50) NOT NULL DEFAULT 'MODIFY_TRANSPORT',
    ADD COLUMN IF NOT EXISTS affected_entity_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS affected_entity_id UUID,
    ADD COLUMN IF NOT EXISTS proposed_state_change JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS prerequisite_conditions JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS constraints_checked JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS constraints_violated JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS unknown_requirements JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS feasibility_state VARCHAR(50) NOT NULL DEFAULT 'FEASIBLE',
    ADD COLUMN IF NOT EXISTS operational_rationale TEXT,
    ADD COLUMN IF NOT EXISTS evidence JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS data_provenance data_provenance NOT NULL DEFAULT 'ADVISORY';

-- 3. Recommendations Table Enhancements
ALTER TABLE IF EXISTS public.recommendations
    ADD COLUMN IF NOT EXISTS option_id UUID REFERENCES public.recommendation_alternatives(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS rationale JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS supporting_evidence JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS constraint_evaluation_summary JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'PROPOSED';

-- 4. Approvals Table Enhancements
ALTER TABLE IF EXISTS public.approvals
    ALTER COLUMN decision DROP NOT NULL;

ALTER TABLE IF EXISTS public.approvals
    ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    ADD COLUMN IF NOT EXISTS correlation_id UUID;

-- 5. Performance Indexes
CREATE INDEX IF NOT EXISTS idx_replans_expedition ON public.replans(expedition_id);
CREATE INDEX IF NOT EXISTS idx_replans_mission ON public.replans(mission_id);
CREATE INDEX IF NOT EXISTS idx_replans_status ON public.replans(status);
CREATE INDEX IF NOT EXISTS idx_replans_trigger_entity ON public.replans(trigger_entity_type, trigger_entity_id);
CREATE INDEX IF NOT EXISTS idx_replan_options_replan ON public.recommendation_alternatives(replan_id);
CREATE INDEX IF NOT EXISTS idx_replan_options_feasibility ON public.recommendation_alternatives(feasibility_state);
CREATE INDEX IF NOT EXISTS idx_recommendations_replan ON public.recommendations(replan_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_status ON public.recommendations(status);
CREATE INDEX IF NOT EXISTS idx_approvals_recommendation ON public.approvals(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON public.approvals(status);

-- 6. Row Level Security Policies (Authenticated Expedition Operators)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'replans' AND policyname = 'authenticated_replans_all'
    ) THEN
        CREATE POLICY authenticated_replans_all ON public.replans
            FOR ALL TO authenticated USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'recommendation_alternatives' AND policyname = 'authenticated_replan_options_all'
    ) THEN
        CREATE POLICY authenticated_replan_options_all ON public.recommendation_alternatives
            FOR ALL TO authenticated USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'recommendations' AND policyname = 'authenticated_recommendations_all'
    ) THEN
        CREATE POLICY authenticated_recommendations_all ON public.recommendations
            FOR ALL TO authenticated USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'approvals' AND policyname = 'authenticated_approvals_all'
    ) THEN
        CREATE POLICY authenticated_approvals_all ON public.approvals
            FOR ALL TO authenticated USING (true) WITH CHECK (true);
    END IF;
END $$;
