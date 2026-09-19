import {
  AlertOctagon,
  ArrowRight,
  Compass,
  Link2,
  ShieldAlert,
  Target,
  X,
} from 'lucide-react';
import { EntityCode } from '../../../components/shared/EntityCode';
import { StatusBadge } from '../../../components/shared/StatusBadge';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { useIncidentContext } from '../hooks/useControlTower';

export interface IncidentEscalationBannerProps {
  incidentId: string;
  replanId: string;
  onExploreOptions: (replanId: string) => void;
  onDismiss?: () => void;
}

export function IncidentEscalationBanner({
  incidentId,
  replanId,
  onExploreOptions,
  onDismiss,
}: IncidentEscalationBannerProps) {
  const { data: incidentContext, isLoading, error } = useIncidentContext(incidentId);

  if (isLoading) {
    return (
      <div
        aria-busy="true"
        className="p-4 rounded-lg bg-slate-900/80 border border-slate-800 animate-pulse flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <AlertOctagon className="w-5 h-5 text-rose-400" />
          <span className="text-sm font-mono text-slate-300">
            Resolving incident escalation & blast-radius context...
          </span>
        </div>
      </div>
    );
  }

  if (error || !incidentContext) {
    return (
      <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertOctagon className="w-5 h-5 text-amber-400" />
          <div>
            <p className="text-sm font-semibold text-slate-200">Incident Escalation Context Linked</p>
            <p className="text-xs font-mono text-slate-400">
              Incident ID: {incidentId.slice(0, 8)}... | Active Replan: {replanId.slice(0, 8)}...
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onExploreOptions(replanId)}
            className="px-3 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Compass className="w-4 h-4" />
            Explore Candidate Options
          </button>
          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              className="p-1 text-slate-400 hover:text-slate-200"
              aria-label="Dismiss escalation banner"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <section
      aria-label="Incident Escalation Context"
      className="rounded-lg bg-gradient-to-r from-rose-950/50 via-slate-900 to-slate-950 border border-rose-800/60 shadow-lg overflow-hidden"
    >
      {/* Banner Header */}
      <div className="p-4 border-b border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start sm:items-center gap-3">
          <div className="p-2 rounded-lg bg-rose-950/80 border border-rose-700/60 text-rose-400 mt-0.5 sm:mt-0">
            <AlertOctagon className="w-5 h-5" aria-hidden="true" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider">
                Incident Escalation Context
              </span>
              <EntityCode code={incidentContext.incident_code} />
              <StatusBadge status={incidentContext.severity} />
              <StatusBadge status={incidentContext.status} />
              <ProvenanceTag provenance="SYNTHETIC_DEMO" />
            </div>
            <h2 className="text-sm sm:text-base font-semibold text-slate-100 mt-1">
              {incidentContext.title}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center">
          <button
            type="button"
            onClick={() => onExploreOptions(replanId)}
            className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-rose-500"
          >
            <Compass className="w-4 h-4" aria-hidden="true" />
            Explore Candidate Options
            <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
              aria-label="Dismiss incident escalation context"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {/* Banner Operational Summary & Metadata */}
      <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
        {/* Column 1: Blast Radius & Location */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-slate-400 font-semibold text-[11px] uppercase tracking-wider">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" aria-hidden="true" />
            Propagation & Blast Radius
            <ProvenanceTag provenance="DERIVED" className="ml-auto" />
          </div>
          <p className="text-slate-300 leading-relaxed bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
            {incidentContext.propagation_summary}
          </p>
          <div className="text-[11px] text-slate-400 flex items-center gap-1">
            <span className="text-slate-500">Location:</span>
            <span className="text-slate-200 font-semibold">
              {incidentContext.location_name ?? incidentContext.location_id ?? 'Polar Operations Area'}
            </span>
          </div>
        </div>

        {/* Column 2: Impacted Missions */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-slate-400 font-semibold text-[11px] uppercase tracking-wider">
            <Target className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
            Impacted Missions ({incidentContext.affected_missions.length})
            <ProvenanceTag provenance="DERIVED" className="ml-auto" />
          </div>
          <div className="space-y-1.5 max-h-28 overflow-y-auto pr-1">
            {incidentContext.affected_missions.length === 0 ? (
              <p className="text-slate-500 italic bg-slate-950/40 p-2 rounded border border-slate-800/60">
                No active missions directly interrupted in initial blast radius.
              </p>
            ) : (
              incidentContext.affected_missions.map((m, idx) => (
                <div
                  key={idx}
                  className="p-2 rounded bg-slate-950/70 border border-slate-800 flex items-center justify-between"
                >
                  <span className="text-amber-300 font-bold">
                    {String(m.code ?? m.mission_code ?? 'MSN')}
                  </span>
                  <span className="text-slate-300 truncate max-w-[160px]" title={String(m.title ?? '')}>
                    {String(m.title ?? 'Operational Mission')}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Column 3: Impacted Constraints & Correlation */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-slate-400 font-semibold text-[11px] uppercase tracking-wider">
            <Link2 className="w-3.5 h-3.5 text-cyan-400" aria-hidden="true" />
            Threatened Constraints & Linkage
            <ProvenanceTag provenance="ADVISORY" className="ml-auto" />
          </div>
          <div className="space-y-1.5 max-h-28 overflow-y-auto pr-1">
            {incidentContext.affected_constraints.length === 0 ? (
              <p className="text-slate-500 italic bg-slate-950/40 p-2 rounded border border-slate-800/60">
                No active hard constraints in terminal breach.
              </p>
            ) : (
              incidentContext.affected_constraints.map((c, idx) => (
                <div
                  key={idx}
                  className="p-1.5 rounded bg-slate-950/70 border border-rose-900/40 flex items-center justify-between text-[11px]"
                >
                  <span className="text-rose-300 font-bold">{String(c.code ?? 'CST')}</span>
                  <span className="text-slate-400 truncate max-w-[140px]" title={String(c.name ?? c.reason ?? '')}>
                    {String(c.name ?? c.reason ?? 'Safety Invariant')}
                  </span>
                </div>
              ))
            )}
          </div>
          {incidentContext.correlation_id && (
            <div className="pt-1 text-[10px] text-slate-500 truncate" title={incidentContext.correlation_id}>
              Trace: <span className="text-slate-400">{incidentContext.correlation_id}</span>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
