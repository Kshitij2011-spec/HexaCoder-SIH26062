import { Compass, AlertOctagon, AlertTriangle, RefreshCw, ShieldAlert } from 'lucide-react';
import { EntityCode } from '../../../components/shared/EntityCode';
import { StatusBadge } from '../../../components/shared/StatusBadge';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../../components/shared/ErrorDisplay';
import { useExpeditionSummary } from '../hooks/useControlTower';
import type { ExpeditionControlSummary, ReadinessState } from '../../../lib/types/api';

export interface ExpeditionContextBarProps {
  selectedExpeditionId: string;
  onSelectExpedition: (id: string) => void;
  expeditions: ExpeditionControlSummary[];
  isLoadingExpeditions?: boolean;
}

const READINESS_CONFIG: Record<
  ReadinessState | string,
  { label: string; badgeClass: string; dotClass: string }
> = {
  READY: {
    label: 'READY',
    badgeClass: 'bg-emerald-950/70 text-emerald-300 border-emerald-600',
    dotClass: 'bg-emerald-400',
  },
  AT_RISK: {
    label: 'AT RISK',
    badgeClass: 'bg-amber-950/70 text-amber-300 border-amber-600',
    dotClass: 'bg-amber-400',
  },
  BLOCKED: {
    label: 'BLOCKED',
    badgeClass: 'bg-rose-950/70 text-rose-200 border-rose-600',
    dotClass: 'bg-rose-400',
  },
  UNKNOWN: {
    label: 'UNKNOWN',
    badgeClass: 'bg-slate-800 text-slate-400 border-slate-600',
    dotClass: 'bg-slate-400',
  },
};

export function ExpeditionContextBar({
  selectedExpeditionId,
  onSelectExpedition,
  expeditions,
  isLoadingExpeditions = false,
}: ExpeditionContextBarProps) {
  const {
    data: summary,
    isLoading: isLoadingSummary,
    error,
  } = useExpeditionSummary(selectedExpeditionId);

  if (isLoadingExpeditions) {
    return (
      <div className="p-4 rounded-lg bg-slate-900 border border-slate-800" aria-busy="true">
        <LoadingSkeleton lines={3} />
      </div>
    );
  }

  return (
    <section
      aria-label="Expedition Operational Context"
      className="p-4 rounded-lg bg-slate-900 border border-slate-800 shadow-sm"
    >
      {/* ─── Top Control Row ─── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        {/* Expedition Selector & Basic Identifiers */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Compass className="w-4 h-4 text-sky-400 shrink-0" aria-hidden="true" />
            <label
              htmlFor="expedition-select"
              className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider"
            >
              Expedition:
            </label>
            <select
              id="expedition-select"
              aria-label="Select Expedition Campaign"
              value={selectedExpeditionId}
              onChange={(e) => onSelectExpedition(e.target.value)}
              className="bg-slate-950 text-slate-100 text-sm font-mono rounded border border-slate-700 px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-sky-500"
            >
              {expeditions.map((exp) => (
                <option key={exp.expedition_id} value={exp.expedition_id}>
                  {exp.code} — {exp.name}
                </option>
              ))}
            </select>
          </div>

          {summary && (
            <>
              <EntityCode code={summary.code} />
              <span className="font-semibold text-slate-100 text-sm lg:text-base">
                {summary.name}
              </span>
              {summary.season && (
                <span className="text-xs font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-950 border border-slate-800">
                  {summary.season}
                </span>
              )}
              {summary.lifecycle_status && (
                <StatusBadge status={summary.lifecycle_status} />
              )}
            </>
          )}
        </div>

        {/* Operational Readiness Posture & Provenance */}
        {summary && (
          <div className="flex items-center gap-3 shrink-0">
            {(() => {
              const rConf = READINESS_CONFIG[summary.readiness_state] ?? READINESS_CONFIG.UNKNOWN;
              return (
                <div
                  className={`inline-flex items-center gap-2 px-3 py-1 rounded border font-mono text-xs font-semibold tracking-wider ${rConf.badgeClass}`}
                  role="status"
                  aria-label={`Overall expedition readiness state: ${rConf.label}`}
                >
                  <span className={`w-2 h-2 rounded-full ${rConf.dotClass} animate-pulse`} aria-hidden="true" />
                  <span>{rConf.label}</span>
                </div>
              );
            })()}

            <ProvenanceTag provenance={summary.data_provenance} />
          </div>
        )}
      </div>

      {/* ─── Body Details: Loading / Error / Metrics ─── */}
      {isLoadingSummary && (
        <div className="pt-4" aria-busy="true">
          <LoadingSkeleton lines={2} />
        </div>
      )}

      {error && (
        <div className="pt-4">
          <ErrorDisplay error={error} title="Failed to load expedition summary" />
        </div>
      )}

      {summary && !isLoadingSummary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-4">
          {/* Tile 1: Missions Breakdown */}
          <div className="p-3 rounded bg-slate-950/60 border border-slate-800/80">
            <span className="block text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1">
              Missions
            </span>
            <span className="text-xl font-mono font-bold text-slate-100">
              {summary.total_missions}
            </span>
            <div className="mt-1 flex flex-wrap gap-x-2 gap-y-0.5 text-[11px] font-mono">
              <span className="text-emerald-400">{summary.ready_missions_count} ready</span>
              <span className="text-amber-400">{summary.at_risk_missions_count} risk</span>
              <span className="text-rose-400">{summary.blocked_missions_count} blocked</span>
            </div>
          </div>

          {/* Tile 2: Active Incidents */}
          <div
            className={`p-3 rounded border transition-colors ${
              summary.active_incidents_count > 0
                ? 'bg-rose-950/20 border-rose-900/60'
                : 'bg-slate-950/60 border-slate-800/80'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1">
                Incidents
              </span>
              {summary.active_incidents_count > 0 && (
                <AlertOctagon className="w-3.5 h-3.5 text-rose-400" aria-hidden="true" />
              )}
            </div>
            <span
              className={`text-xl font-mono font-bold ${
                summary.active_incidents_count > 0 ? 'text-rose-400' : 'text-slate-100'
              }`}
            >
              {summary.active_incidents_count}
            </span>
            <span className="block mt-1 text-[11px] text-slate-400">active open</span>
          </div>

          {/* Tile 3: Hard Constraint Violations */}
          <div
            className={`p-3 rounded border transition-colors ${
              summary.active_hard_constraint_violations_count > 0
                ? 'bg-rose-950/20 border-rose-900/60'
                : 'bg-slate-950/60 border-slate-800/80'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1">
                Hard Violations
              </span>
              {summary.active_hard_constraint_violations_count > 0 && (
                <ShieldAlert className="w-3.5 h-3.5 text-rose-400" aria-hidden="true" />
              )}
            </div>
            <span
              className={`text-xl font-mono font-bold ${
                summary.active_hard_constraint_violations_count > 0
                  ? 'text-rose-400'
                  : 'text-slate-100'
              }`}
            >
              {summary.active_hard_constraint_violations_count}
            </span>
            <span className="block mt-1 text-[11px] text-slate-400">critical constraints</span>
          </div>

          {/* Tile 4: Pending Replans */}
          <div
            className={`p-3 rounded border transition-colors ${
              summary.pending_replans_count > 0
                ? 'bg-sky-950/20 border-sky-900/60'
                : 'bg-slate-950/60 border-slate-800/80'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1">
                Replans
              </span>
              {summary.pending_replans_count > 0 && (
                <RefreshCw className="w-3.5 h-3.5 text-sky-400" aria-hidden="true" />
              )}
            </div>
            <span
              className={`text-xl font-mono font-bold ${
                summary.pending_replans_count > 0 ? 'text-sky-400' : 'text-slate-100'
              }`}
            >
              {summary.pending_replans_count}
            </span>
            <span className="block mt-1 text-[11px] text-slate-400">cycles active</span>
          </div>

          {/* Tile 5: Pending Approvals */}
          <div
            className={`p-3 rounded border transition-colors ${
              summary.pending_approvals_count > 0
                ? 'bg-amber-950/20 border-amber-900/60'
                : 'bg-slate-950/60 border-slate-800/80'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1">
                Approvals
              </span>
              {summary.pending_approvals_count > 0 && (
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
              )}
            </div>
            <span
              className={`text-xl font-mono font-bold ${
                summary.pending_approvals_count > 0 ? 'text-amber-400' : 'text-slate-100'
              }`}
            >
              {summary.pending_approvals_count}
            </span>
            <span className="block mt-1 text-[11px] text-slate-400">awaiting operator</span>
          </div>

          {/* Tile 6: Blockers & Warnings */}
          <div className="p-3 rounded bg-slate-950/60 border border-slate-800/80">
            <span className="block text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1">
              Blockers / Warnings
            </span>
            <div className="flex items-baseline gap-2">
              <span
                className={`text-xl font-mono font-bold ${
                  (summary.blockers?.length ?? 0) > 0 ? 'text-rose-400' : 'text-slate-100'
                }`}
              >
                {summary.blockers?.length ?? 0}
              </span>
              <span className="text-slate-500 font-mono text-sm">/</span>
              <span
                className={`text-xl font-mono font-bold ${
                  (summary.warnings?.length ?? 0) > 0 ? 'text-amber-400' : 'text-slate-400'
                }`}
              >
                {summary.warnings?.length ?? 0}
              </span>
            </div>
            <span className="block mt-1 text-[11px] text-slate-400">
              {(summary.blockers?.length ?? 0) === 0 ? 'no blockers active' : 'readiness issues'}
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
