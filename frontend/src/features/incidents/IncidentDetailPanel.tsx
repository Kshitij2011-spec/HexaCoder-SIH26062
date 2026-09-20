import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  AlertOctagon,
  Clock,
  Link2,
  ShieldAlert,
  Compass,
  ArrowRight,
  Loader2,
} from 'lucide-react';
import { EntityCode } from '../../components/shared/EntityCode';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { IncidentSeverityBadge } from './IncidentSeverityBadge';
import { IncidentStatusActions } from './IncidentStatusActions';
import { IncidentReferences } from './IncidentReferences';
import { IncidentTimeline } from './IncidentTimeline';
import { OperationalTimeline } from '../../components/shared/OperationalTimeline';
import { useIncidentTimeline } from './hooks/useIncidentTimeline';
import { useIncidentReferences } from './hooks/useIncidentReferences';
import { useEscalateIncidentToReplan } from './hooks/useIncidentMutations';
import { useIncidentContext } from '../control-tower/hooks/useControlTower';
import { useOfflineSync } from '../../lib/sync';
import type { Incident } from '../../lib/types/api';

interface Props {
  incident: Incident | null;
  onClose: () => void;
  onRefreshIncident?: () => void;
}

export function IncidentDetailPanel({ incident, onClose, onRefreshIncident }: Props) {
  const navigate = useNavigate();
  const [escalateError, setEscalateError] = useState<string | null>(null);

  const {
    data: timelineData,
    isLoading: isTimelineLoading,
    refetch: refetchTimeline,
  } = useIncidentTimeline(incident?.id ?? null);

  const {
    data: references = [],
    isLoading: isRefsLoading,
    refetch: refetchReferences,
  } = useIncidentReferences(incident?.id ?? null);

  const { data: incidentContext } = useIncidentContext(incident?.id ?? null);
  const escalateMutation = useEscalateIncidentToReplan(incident?.id ?? '');

  const { operations } = useOfflineSync();
  const queuedOp = operations.find(
    (op) => op.entity_type === 'INCIDENT' && op.entity_id === incident?.id && op.local_status === 'LOCAL_QUEUED'
  );
  const isLocalQueued = Boolean((incident as { _is_local_queued?: boolean } | null)?._is_local_queued || queuedOp);

  if (!incident) return null;

  const isEligibleStatus = ['OPEN', 'ACKNOWLEDGED', 'MITIGATING'].includes(incident.status);
  const hasPropagatedImpact =
    (incidentContext?.affected_entities && incidentContext.affected_entities.length > 0) ||
    references.length > 0 ||
    Boolean(incident.location_id) ||
    Boolean(incident.asset_id);
  const canEscalate = isEligibleStatus && hasPropagatedImpact;

  const handleEscalateToReplan = async () => {
    setEscalateError(null);
    try {
      const result = await escalateMutation.mutateAsync({
        requested_by: 'Expedition Operator',
        reason: `Operational escalation for incident ${incident.code}: ${incident.title}`,
      });
      onClose();
      navigate(`/control-tower?incidentId=${result.incident_id}&replanId=${result.replan_id}`);
    } catch (err) {
      setEscalateError(err instanceof Error ? err.message : 'Failed to escalate incident to replanning');
    }
  };

  const handleRefresh = () => {
    refetchTimeline();
    refetchReferences();
    onRefreshIncident?.();
  };

  return (
    <div
      className="fixed inset-y-0 right-0 w-full max-w-2xl bg-slate-950 border-l border-slate-800 shadow-2xl z-50 flex flex-col overflow-hidden"
      role="dialog"
      aria-modal="true"
      aria-label={`Incident details for ${incident.code}`}
    >
      {/* Drawer Header */}
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
        <div className="flex items-center gap-3">
          <AlertOctagon className="w-5 h-5 text-rose-500" aria-hidden="true" />
          <div>
            <div className="flex items-center gap-2">
              <EntityCode code={incident.code} />
              <IncidentSeverityBadge severity={incident.severity} />
              <StatusBadge status={incident.status} />
              {isLocalQueued && (
                <span
                  data-testid="detail-local-queued-badge"
                  className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950/90 border border-amber-500 text-amber-300 shadow-sm animate-pulse"
                >
                  LOCAL_QUEUED [SYNTHETIC/DEMO]
                </span>
              )}
              <ProvenanceTag provenance={incident.data_provenance} />
            </div>
            <h2 className="text-base font-semibold text-slate-100 mt-0.5">
              {incident.title}
            </h2>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          aria-label="Close detail panel"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Drawer Body */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        {/* Incident Summary / Specs */}
        <section className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 text-xs font-mono">
          <h3 className="text-slate-400 uppercase tracking-wider text-[11px] mb-3 font-semibold">
            Operational Incident Specifications
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <span className="text-slate-500">Incident Type:</span>
              <p className="text-slate-200 font-semibold">{incident.incident_type}</p>
            </div>
            <div>
              <span className="text-slate-500">Priority:</span>
              <p className="text-rose-400 font-bold">P{incident.priority}</p>
            </div>
            <div>
              <span className="text-slate-500">Detected:</span>
              <p className="text-slate-300">
                {new Date(incident.detected_at).toLocaleString()}
              </p>
            </div>
            {incident.acknowledged_at && (
              <div>
                <span className="text-slate-500">Acknowledged:</span>
                <p className="text-amber-300">
                  {new Date(incident.acknowledged_at).toLocaleString()}
                </p>
              </div>
            )}
            {incident.resolved_at && (
              <div>
                <span className="text-slate-500">Resolved:</span>
                <p className="text-emerald-400 font-semibold">
                  {new Date(incident.resolved_at).toLocaleString()}
                </p>
              </div>
            )}
            {incident.closed_at && (
              <div>
                <span className="text-slate-500">Closed:</span>
                <p className="text-slate-400">
                  {new Date(incident.closed_at).toLocaleString()}
                </p>
              </div>
            )}
            {incident.location_id && (
              <div>
                <span className="text-slate-500">Location ID:</span>
                <p className="text-slate-300 truncate" title={incident.location_id}>
                  {incident.location_id.slice(0, 8)}...
                </p>
              </div>
            )}
            {incident.asset_id && (
              <div>
                <span className="text-slate-500">Asset ID:</span>
                <p className="text-slate-300 truncate" title={incident.asset_id}>
                  {incident.asset_id.slice(0, 8)}...
                </p>
              </div>
            )}
          </div>
          <div className="mt-3 pt-2 border-t border-slate-800/80">
            <span className="text-slate-500 block mb-1">Impact & Description:</span>
            <p className="text-slate-300 whitespace-pre-wrap">{incident.description}</p>
          </div>
        </section>

        {/* Lifecycle Transitions Section */}
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-400" aria-hidden="true" />
            Lifecycle Operations
          </h3>
          <IncidentStatusActions incident={incident} onSuccess={handleRefresh} />
        </section>

        {/* Operational Escalation to Control Tower (A7) */}
        {canEscalate && (
          <section
            aria-label="Escalate to Replan"
            className="p-4 rounded-lg bg-gradient-to-r from-rose-950/40 via-slate-900/95 to-slate-950 border border-rose-800/70 space-y-3 font-mono text-xs shadow-md"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-rose-200 flex items-center gap-2">
                <Compass className="w-4 h-4 text-rose-400" aria-hidden="true" />
                Operational Escalation & Replanning
              </h3>
              <ProvenanceTag provenance="DERIVED" />
            </div>

            <p className="text-slate-300 leading-relaxed">
              Escalate this active operational incident to the Control Tower replanning engine.
              The blast radius will propagate across logistics dependencies to generate candidate mitigation options.
            </p>

            {/* Context Summary for Operator */}
            <div className="p-3 rounded bg-slate-950/80 border border-slate-800/90 space-y-2 text-[11px]">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-slate-500">Classification:</span>{' '}
                  <span className="text-slate-200 font-semibold">{incident.incident_type}</span>
                </div>
                <div>
                  <span className="text-slate-500">Severity:</span>{' '}
                  <span className="text-rose-400 font-semibold">{incident.severity}</span>
                </div>
                <div>
                  <span className="text-slate-500">Location:</span>{' '}
                  <span className="text-slate-300 font-semibold">
                    {incidentContext?.location_name ?? incident.location_id?.slice(0, 8) ?? 'Polar Field Area'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Propagated Entities:</span>{' '}
                  <span className="text-cyan-400 font-semibold">
                    {incidentContext?.affected_entities?.length ?? references.length} resources
                  </span>
                </div>
              </div>
              <div className="pt-1.5 border-t border-slate-800/80">
                <span className="text-slate-500 block mb-0.5">Propagation Summary:</span>
                <p className="text-slate-300">
                  {incidentContext?.propagation_summary ??
                    'Blast radius evaluated across active polar dependencies and mission constraints.'}
                </p>
              </div>
              {incidentContext?.affected_missions && incidentContext.affected_missions.length > 0 && (
                <div className="pt-1.5 border-t border-slate-800/80">
                  <span className="text-slate-500 block mb-1">
                    Impacted Missions ({incidentContext.affected_missions.length}):
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {incidentContext.affected_missions.map((m, idx) => (
                      <span
                        key={idx}
                        className="px-1.5 py-0.5 rounded bg-amber-950/60 border border-amber-800/50 text-amber-300 text-[10px]"
                      >
                        {String(m.code ?? m.mission_code ?? 'MSN')}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {escalateError && (
              <ErrorDisplay error={new Error(escalateError)} title="Incident Escalation Failed" />
            )}

            <button
              type="button"
              onClick={handleEscalateToReplan}
              disabled={escalateMutation.isPending}
              className="w-full py-2 px-4 rounded-lg bg-rose-600 hover:bg-rose-500 active:bg-rose-700 disabled:opacity-50 text-white font-semibold flex items-center justify-center gap-2 shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-rose-500"
            >
              {escalateMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>Escalating to Replan Engine...</span>
                </>
              ) : (
                <>
                  <Compass className="w-4 h-4" aria-hidden="true" />
                  <span>Escalate to Replan</span>
                  <ArrowRight className="w-4 h-4 ml-auto" aria-hidden="true" />
                </>
              )}
            </button>
          </section>
        )}

        {/* References Section */}
        <section className="space-y-3 pt-4 border-t border-slate-800">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Link2 className="w-4 h-4 text-cyan-400" aria-hidden="true" />
            Affected Polar Domain Resources
          </h3>
          <IncidentReferences
            incidentId={incident.id}
            references={references}
            isLoading={isRefsLoading}
          />
        </section>

        {/* Operational Timeline Section */}
        <section className="space-y-4 pt-4 border-t border-slate-800">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Clock className="w-4 h-4 text-rose-400" aria-hidden="true" />
            Incident Journal & Event History
          </h3>
          <IncidentTimeline
            entries={timelineData?.history ?? []}
            isLoading={isTimelineLoading}
          />
          <OperationalTimeline
            entityType="INCIDENT"
            entityId={incident.id}
            title="Cross-Domain Incident Propagation & Event History"
            defaultIncludeRelated={true}
          />
        </section>
      </div>
    </div>
  );
}
