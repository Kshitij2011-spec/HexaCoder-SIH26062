import { useState, useMemo } from 'react';
import { AlertOctagon, Plus, Search, Filter } from 'lucide-react';
import { PageHeader } from '../../components/shared/PageHeader';
import { EntityCode } from '../../components/shared/EntityCode';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { IncidentSeverityBadge } from './IncidentSeverityBadge';
import { IncidentDetailPanel } from './IncidentDetailPanel';
import { CreateIncidentWorkflow } from './CreateIncidentWorkflow';
import { useIncidents } from './hooks/useIncidents';
import type { Incident, IncidentSeverity, IncidentStatus } from '../../lib/types/api';

const SEVERITY_OPTIONS: Array<IncidentSeverity | 'ALL'> = [
  'ALL',
  'CRITICAL',
  'HIGH',
  'MEDIUM',
  'LOW',
];

const STATUS_OPTIONS: Array<IncidentStatus | 'ALL'> = [
  'ALL',
  'OPEN',
  'ACKNOWLEDGED',
  'MITIGATING',
  'RESOLVED',
  'CLOSED',
];

export function IncidentsPage() {
  const [severityFilter, setSeverityFilter] = useState<IncidentSeverity | 'ALL'>('ALL');
  const [statusFilter, setStatusFilter] = useState<IncidentStatus | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  const filters = useMemo(() => {
    const f: { severity?: IncidentSeverity; status?: IncidentStatus } = {};
    if (severityFilter !== 'ALL') f.severity = severityFilter;
    if (statusFilter !== 'ALL') f.status = statusFilter;
    return f;
  }, [severityFilter, statusFilter]);

  const {
    data: incidents = [],
    isLoading,
    error,
    refetch,
  } = useIncidents(filters);

  const filteredIncidents = useMemo(() => {
    if (!searchQuery.trim()) return incidents;
    const q = searchQuery.toLowerCase();
    return incidents.filter(
      (inc: Incident) =>
        inc.code.toLowerCase().includes(q) ||
        inc.title.toLowerCase().includes(q) ||
        inc.incident_type.toLowerCase().includes(q) ||
        inc.description.toLowerCase().includes(q)
    );
  }, [incidents, searchQuery]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <PageHeader
          title="Incident Response"
          subtitle="Operational exception containment, resource impact isolation, and audit journal"
          actions={
            <div className="flex items-center gap-3">
              <span className="text-slate-400 text-xs font-mono">{filteredIncidents.length} incidents</span>
              <button
                type="button"
                onClick={() => setCreateModalOpen(true)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-700 hover:bg-rose-600 text-white text-xs font-mono font-medium shadow transition-colors"
              >
                <Plus className="w-4 h-4" aria-hidden="true" />
                Declare Incident
              </button>
            </div>
          }
        />
      </div>

      {/* Control Bar: Filters & Search */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-slate-900/40 p-4 rounded-lg border border-slate-800">
        <div className="flex items-center gap-3 flex-1 flex-wrap">
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
            <input
              type="search"
              placeholder="Search by code, title, type..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              aria-label="Search incidents"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-500" aria-hidden="true" />
            <label htmlFor="inc-severity-filter" className="sr-only">Filter by Severity</label>
            <select
              id="inc-severity-filter"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value as IncidentSeverity | 'ALL')}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              {SEVERITY_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s === 'ALL' ? 'All Severities' : s}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="inc-status-filter" className="sr-only">Filter by Status</label>
            <select
              id="inc-status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as IncidentStatus | 'ALL')}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              {STATUS_OPTIONS.map((st) => (
                <option key={st} value={st}>
                  {st === 'ALL' ? 'All Statuses' : st}
                </option>
              ))}
            </select>
          </div>
        </div>

        <span className="text-xs font-mono text-slate-400 self-center">
          Showing {filteredIncidents.length} incident{filteredIncidents.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Main Content Area */}
      {isLoading && (
        <div className="p-6">
          <LoadingSkeleton lines={6} />
        </div>
      )}

      {error && (
        <div className="p-6">
          <ErrorDisplay error={error} title="Failed to load incidents" />
        </div>
      )}

      {!isLoading && !error && filteredIncidents.length === 0 && (
        <EmptyState
          icon={<AlertOctagon className="w-12 h-12 text-rose-500" aria-hidden="true" />}
          title="No Incidents Found"
          message={
            searchQuery || severityFilter !== 'ALL' || statusFilter !== 'ALL'
              ? 'Try modifying active filters or search queries.'
              : 'No operational incidents are currently reported.'
          }
        />
      )}

      {!isLoading && !error && filteredIncidents.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/20">
          <table className="w-full text-left text-sm" role="table" aria-label="Incidents table">
            <thead className="bg-slate-900 font-mono text-xs text-slate-400 uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Incident Code</th>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Severity</th>
                <th className="px-4 py-3 text-center">Priority</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Detected</th>
                <th className="px-4 py-3">Provenance</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {filteredIncidents.map((inc: Incident) => (
                <tr
                  key={inc.id}
                  className="hover:bg-slate-800/40 transition-colors"
                >
                  <td className="px-4 py-3 font-semibold text-slate-200">
                    <EntityCode code={inc.code} />
                  </td>
                  <td className="px-4 py-3 font-sans font-medium text-slate-100 max-w-[220px] truncate" title={inc.title}>
                    {inc.title}
                  </td>
                  <td className="px-4 py-3">
                    <IncidentSeverityBadge severity={inc.severity} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`inline-block px-1.5 py-0.5 rounded text-[11px] font-bold ${
                        inc.priority === 1
                          ? 'bg-rose-900/60 text-rose-200'
                          : inc.priority === 2
                          ? 'bg-amber-900/50 text-amber-300'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      P{inc.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={inc.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {inc.incident_type}
                  </td>
                  <td className="px-4 py-3 text-slate-400 whitespace-nowrap">
                    {new Date(inc.detected_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <ProvenanceTag provenance={inc.data_provenance} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => setSelectedIncident(inc)}
                      className="px-3 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white transition-colors"
                      aria-label={`Inspect ${inc.code}`}
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Incident Detail Drawer */}
      {selectedIncident && (
        <IncidentDetailPanel
          incident={selectedIncident}
          onClose={() => setSelectedIncident(null)}
          onRefreshIncident={refetch}
        />
      )}

      {/* Create Incident Modal */}
      <CreateIncidentWorkflow
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onCreated={refetch}
      />
    </div>
  );
}
