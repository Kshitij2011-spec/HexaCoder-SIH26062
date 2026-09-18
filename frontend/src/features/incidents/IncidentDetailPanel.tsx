import { X, AlertOctagon, Clock, Link2, ShieldAlert } from 'lucide-react';
import { EntityCode } from '../../components/shared/EntityCode';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import { IncidentSeverityBadge } from './IncidentSeverityBadge';
import { IncidentStatusActions } from './IncidentStatusActions';
import { IncidentReferences } from './IncidentReferences';
import { IncidentTimeline } from './IncidentTimeline';
import { OperationalTimeline } from '../../components/shared/OperationalTimeline';
import { useIncidentTimeline } from './hooks/useIncidentTimeline';
import { useIncidentReferences } from './hooks/useIncidentReferences';
import type { Incident } from '../../lib/types/api';

interface Props {
  incident: Incident | null;
  onClose: () => void;
  onRefreshIncident?: () => void;
}

export function IncidentDetailPanel({ incident, onClose, onRefreshIncident }: Props) {
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

  if (!incident) return null;

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
