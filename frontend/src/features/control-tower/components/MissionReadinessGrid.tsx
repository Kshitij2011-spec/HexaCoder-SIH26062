import { useState } from 'react';
import {
  Search,
  AlertCircle,
  AlertTriangle,
  RotateCcw,
  Clock,
  X,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { EntityCode } from '../../../components/shared/EntityCode';
import { StatusBadge } from '../../../components/shared/StatusBadge';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { EmptyState } from '../../../components/shared/EmptyState';
import { ErrorDisplay } from '../../../components/shared/ErrorDisplay';
import { useMissionOperations } from '../hooks/useControlTower';
import type { ReadinessState, MissionOperationsItem } from '../../../lib/types/api';

export interface MissionReadinessGridProps {
  expeditionId: string;
  onInitiateReplan?: (mission: MissionOperationsItem) => void;
}

const READINESS_FILTER_OPTIONS: { label: string; value: string }[] = [
  { label: 'All Readiness', value: '' },
  { label: 'Ready', value: 'READY' },
  { label: 'At Risk', value: 'AT_RISK' },
  { label: 'Blocked', value: 'BLOCKED' },
  { label: 'Unknown', value: 'UNKNOWN' },
];

const STATUS_FILTER_OPTIONS: { label: string; value: string }[] = [
  { label: 'All Statuses', value: '' },
  { label: 'Proposed', value: 'PROPOSED' },
  { label: 'Approved', value: 'APPROVED' },
  { label: 'Ready', value: 'READY' },
  { label: 'Scheduled', value: 'SCHEDULED' },
  { label: 'In Progress', value: 'IN_PROGRESS' },
  { label: 'Completed', value: 'COMPLETED' },
  { label: 'Blocked', value: 'BLOCKED' },
  { label: 'Deferred', value: 'DEFERRED' },
  { label: 'Cancelled', value: 'CANCELLED' },
];

const READINESS_BADGE_STYLES: Record<ReadinessState | string, string> = {
  READY: 'bg-emerald-950/70 text-emerald-300 border-emerald-600',
  AT_RISK: 'bg-amber-950/70 text-amber-300 border-amber-600',
  BLOCKED: 'bg-rose-950/70 text-rose-200 border-rose-600',
  UNKNOWN: 'bg-slate-800 text-slate-400 border-slate-600',
};

export function MissionReadinessGrid({
  expeditionId,
  onInitiateReplan,
}: MissionReadinessGridProps) {
  const [readinessFilter, setReadinessFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [selectedMissionId, setSelectedMissionId] = useState<string | null>(null);

  const {
    data: missions,
    isLoading,
    error,
  } = useMissionOperations(expeditionId, {
    readiness: (readinessFilter as ReadinessState) || undefined,
    status: statusFilter || undefined,
    page,
    page_size: pageSize,
  });

  // Client-side search over currently loaded page of missions
  const filteredMissions = (missions ?? []).filter((m) => {
    if (!search.trim()) return true;
    const query = search.toLowerCase().trim();
    return (
      m.code.toLowerCase().includes(query) ||
      m.title.toLowerCase().includes(query) ||
      m.type.toLowerCase().includes(query)
    );
  });

  const selectedMission =
    filteredMissions.find((m) => m.mission_id === selectedMissionId) ??
    (missions ?? []).find((m) => m.mission_id === selectedMissionId);

  const handleReadinessChange = (value: string) => {
    setReadinessFilter(value);
    setPage(1);
  };

  const handleStatusChange = (value: string) => {
    setStatusFilter(value);
    setPage(1);
  };

  return (
    <section
      aria-label="Mission Operations & Readiness"
      className="rounded-lg bg-slate-900 border border-slate-800 shadow-sm"
    >
      {/* ─── Header & Filters Toolbar ─── */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <h2 className="text-base font-semibold text-slate-100">
              Mission Readiness & Operations
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Derived operational posture, constraint evaluations, and readiness blockers
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span>Showing {filteredMissions.length} missions</span>
          </div>
        </div>

        {/* Filters Row */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Readiness Pills */}
          <div
            role="group"
            aria-label="Filter by mission readiness"
            className="flex items-center rounded border border-slate-800 bg-slate-950 p-0.5"
          >
            {READINESS_FILTER_OPTIONS.map((opt) => {
              const active = readinessFilter === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => handleReadinessChange(opt.value)}
                  className={`px-2.5 py-1 text-xs font-mono rounded transition-colors ${
                    active
                      ? 'bg-sky-950 text-sky-200 font-semibold border border-sky-700'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  aria-pressed={active}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>

          {/* Status Dropdown */}
          <div className="flex items-center gap-2">
            <label
              htmlFor="mission-status-filter"
              className="text-xs font-mono text-slate-400 uppercase tracking-wider"
            >
              Status:
            </label>
            <select
              id="mission-status-filter"
              aria-label="Filter by lifecycle status"
              value={statusFilter}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="bg-slate-950 text-slate-100 text-xs font-mono rounded border border-slate-700 px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              {STATUS_FILTER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Client-side Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search
              className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500"
              aria-hidden="true"
            />
            <input
              type="search"
              placeholder="Search code, title, or type (current page)…"
              aria-label="Search current missions by code or title"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-950 text-slate-100 text-xs rounded border border-slate-700 pl-8 pr-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500 placeholder:text-slate-600 font-mono"
            />
          </div>
        </div>
      </div>

      {/* ─── Content Area: Loading / Error / Table & Inspector ─── */}
      <div className="p-4">
        {isLoading && (
          <div aria-busy="true" className="py-4">
            <LoadingSkeleton lines={6} />
          </div>
        )}

        {error && (
          <div className="py-4">
            <ErrorDisplay error={error} title="Failed to load mission operations" />
          </div>
        )}

        {!isLoading && !error && filteredMissions.length === 0 && (
          <EmptyState
            title="No missions found"
            message="No missions match the selected operational filters for this expedition."
          />
        )}

        {!isLoading && !error && filteredMissions.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Table Column */}
            <div className={selectedMission ? 'lg:col-span-7' : 'lg:col-span-12'}>
              <div className="overflow-x-auto rounded border border-slate-800">
                <table className="w-full text-sm text-left font-sans" role="table">
                  <thead className="bg-slate-950 text-[11px] font-mono text-slate-400 uppercase tracking-wider border-b border-slate-800">
                    <tr>
                      <th scope="col" className="px-3 py-2.5">Code</th>
                      <th scope="col" className="px-3 py-2.5">Title</th>
                      <th scope="col" className="px-3 py-2.5">Readiness</th>
                      <th scope="col" className="px-3 py-2.5">Status</th>
                      <th scope="col" className="px-3 py-2.5">Priority</th>
                      <th scope="col" className="px-3 py-2.5">Blockers / Constraints</th>
                      <th scope="col" className="px-3 py-2.5">Latest Event</th>
                      <th scope="col" className="px-3 py-2.5 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                    {filteredMissions.map((m) => {
                      const isSelected = m.mission_id === selectedMissionId;
                      const rStyle =
                        READINESS_BADGE_STYLES[m.readiness_state] ??
                        READINESS_BADGE_STYLES.UNKNOWN;
                      const hasBlockers = (m.readiness_blockers?.length ?? 0) > 0;
                      const hasViolations = (m.violated_constraints?.length ?? 0) > 0;
                      const hasReplans = (m.pending_replans?.length ?? 0) > 0;

                      return (
                        <tr
                          key={m.mission_id}
                          onClick={() =>
                            setSelectedMissionId(isSelected ? null : m.mission_id)
                          }
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-sky-950/40 border-l-2 border-l-sky-400'
                              : 'hover:bg-slate-800/50'
                          }`}
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              setSelectedMissionId(isSelected ? null : m.mission_id);
                            }
                          }}
                          role="button"
                          aria-pressed={isSelected}
                          aria-label={`Select mission ${m.code}`}
                        >
                          {/* Code */}
                          <td className="px-3 py-2.5 whitespace-nowrap">
                            <EntityCode code={m.code} />
                          </td>

                          {/* Title & Type */}
                          <td className="px-3 py-2.5 font-sans">
                            <div className="font-medium text-slate-200 max-w-[220px] truncate">
                              {m.title}
                            </div>
                            <span className="text-[11px] font-mono text-slate-400">
                              {m.type}
                            </span>
                          </td>

                          {/* Readiness State */}
                          <td className="px-3 py-2.5 whitespace-nowrap">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${rStyle}`}
                              role="status"
                              aria-label={`Readiness: ${m.readiness_state}`}
                            >
                              {m.readiness_state === 'AT_RISK' ? 'AT RISK' : m.readiness_state}
                            </span>
                          </td>

                          {/* Lifecycle Status */}
                          <td className="px-3 py-2.5 whitespace-nowrap">
                            <StatusBadge status={m.status} />
                          </td>

                          {/* Priority */}
                          <td className="px-3 py-2.5 whitespace-nowrap">
                            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                              P{m.priority}
                            </span>
                          </td>

                          {/* Blockers / Constraints / Replans */}
                          <td className="px-3 py-2.5 whitespace-nowrap">
                            <div className="flex items-center gap-2">
                              {hasBlockers && (
                                <span
                                  className="inline-flex items-center gap-1 text-rose-400"
                                  title={`${m.readiness_blockers.length} readiness blockers`}
                                >
                                  <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />
                                  <span>{m.readiness_blockers.length}</span>
                                </span>
                              )}
                              {hasViolations && (
                                <span
                                  className="inline-flex items-center gap-1 text-amber-400"
                                  title={`${m.violated_constraints.length} violated constraints`}
                                >
                                  <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
                                  <span>{m.violated_constraints.length}</span>
                                </span>
                              )}
                              {hasReplans && (
                                <span
                                  className="inline-flex items-center gap-1 text-sky-400"
                                  title={`${m.pending_replans.length} pending replans`}
                                >
                                  <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
                                  <span>{m.pending_replans.length}</span>
                                </span>
                              )}
                              {!hasBlockers && !hasViolations && !hasReplans && (
                                <span className="text-slate-600">—</span>
                              )}
                            </div>
                          </td>

                          {/* Latest Event */}
                          <td className="px-3 py-2.5 whitespace-nowrap text-slate-400">
                            {m.latest_event ? (
                              <span
                                title={new Date(m.latest_event.occurred_at).toLocaleString()}
                                className="truncate max-w-[140px] block"
                              >
                                {m.latest_event.event_type}
                              </span>
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
                          </td>

                          {/* Action */}
                          <td className="px-3 py-2.5 whitespace-nowrap text-right">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedMissionId(isSelected ? null : m.mission_id);
                              }}
                              className="text-xs text-sky-400 hover:text-sky-300 underline font-mono"
                              aria-label={`${isSelected ? 'Close details for' : 'Inspect details for'} ${m.code}`}
                            >
                              {isSelected ? 'Close' : 'Inspect'}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination Controls */}
              <div className="flex items-center justify-between mt-3 text-xs font-mono text-slate-400">
                <span>Page {page}</span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="flex items-center gap-1 px-2.5 py-1 rounded border border-slate-700 bg-slate-950 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:border-slate-600"
                    aria-label="Previous page"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Prev</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPage((p) => p + 1)}
                    disabled={(missions ?? []).length < pageSize}
                    className="flex items-center gap-1 px-2.5 py-1 rounded border border-slate-700 bg-slate-950 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:border-slate-600"
                    aria-label="Next page"
                  >
                    <span>Next</span>
                    <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
                  </button>
                </div>
              </div>
            </div>

            {/* ─── Mission Detail Inspector Column ─── */}
            {selectedMission && (
              <div
                className="lg:col-span-5 p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-4"
                aria-label={`Mission inspection panel for ${selectedMission.code}`}
              >
                {/* Inspector Header */}
                <div className="flex items-start justify-between pb-3 border-b border-slate-800">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <EntityCode code={selectedMission.code} />
                      <span className="text-xs font-mono text-slate-400 px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">
                        {selectedMission.type}
                      </span>
                      <span className="text-xs font-mono text-slate-400 px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">
                        P{selectedMission.priority}
                      </span>
                    </div>
                    <h3 className="font-semibold text-slate-100 text-sm">
                      {selectedMission.title}
                    </h3>
                  </div>

                  <button
                    type="button"
                    onClick={() => setSelectedMissionId(null)}
                    className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                    aria-label="Close mission inspection panel"
                  >
                    <X className="w-4 h-4" aria-hidden="true" />
                  </button>
                </div>

                {/* State & Provenance */}
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-mono">Status:</span>
                    <StatusBadge status={selectedMission.status} />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-mono">Readiness:</span>
                    <span
                      className={`px-2 py-0.5 rounded font-mono text-[11px] font-semibold border ${
                        READINESS_BADGE_STYLES[selectedMission.readiness_state] ??
                        READINESS_BADGE_STYLES.UNKNOWN
                      }`}
                    >
                      {selectedMission.readiness_state}
                    </span>
                  </div>
                  <ProvenanceTag provenance={selectedMission.data_provenance} />
                </div>

                {/* Section 1: Readiness Blockers */}
                <div>
                  <h4 className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 text-rose-400" aria-hidden="true" />
                    <span>Readiness Blockers ({(selectedMission.readiness_blockers ?? []).length})</span>
                  </h4>
                  {(selectedMission.readiness_blockers ?? []).length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No active readiness blockers.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {selectedMission.readiness_blockers.map((b, idx) => (
                        <div
                          key={idx}
                          className="p-2 rounded bg-rose-950/20 border border-rose-900/50 text-xs text-rose-300 font-mono"
                        >
                          <div className="font-semibold text-[11px] text-rose-200">
                            {String(b.blocker_type ?? b.code ?? 'BLOCKER')}
                          </div>
                          <div className="mt-0.5 text-rose-300 font-sans">
                            {String(b.reason ?? b.message ?? JSON.stringify(b))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Section 2: Violated Constraints */}
                <div>
                  <h4 className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
                    <span>Violated Constraints ({(selectedMission.violated_constraints ?? []).length})</span>
                  </h4>
                  {(selectedMission.violated_constraints ?? []).length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No active constraints violated.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {selectedMission.violated_constraints.map((c, idx) => (
                        <div
                          key={idx}
                          className="p-2 rounded bg-amber-950/20 border border-amber-900/50 text-xs text-amber-300 font-mono"
                        >
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="font-semibold text-amber-200">
                              {String(c.code ?? c.rule_code ?? 'CONSTRAINT')}
                            </span>
                            <span className="text-[10px] text-amber-400">
                              {String(c.hard_or_soft ?? 'HARD')}
                            </span>
                          </div>
                          <div className="mt-0.5 text-amber-300 font-sans">
                            {String(c.reason ?? c.message ?? JSON.stringify(c))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Section 3: Pending Replans */}
                <div>
                  <h4 className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <RotateCcw className="w-3.5 h-3.5 text-sky-400" aria-hidden="true" />
                    <span>Pending Replans ({(selectedMission.pending_replans ?? []).length})</span>
                  </h4>
                  {(selectedMission.pending_replans ?? []).length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No active replan cycles.</p>
                  ) : (
                    <div className="space-y-1">
                      {selectedMission.pending_replans.map((r, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 rounded bg-sky-950/20 border border-sky-900/40 text-xs font-mono text-sky-300"
                        >
                          <span>{String(r.replan_code ?? r.replan_id)}</span>
                          <span className="text-[11px] px-1.5 py-0.5 rounded bg-sky-900/50 text-sky-200">
                            {String(r.status)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Section 4: Latest Operational Event */}
                <div>
                  <h4 className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-400" aria-hidden="true" />
                    <span>Latest Operational Event</span>
                  </h4>
                  {selectedMission.latest_event ? (
                    <div className="p-2.5 rounded bg-slate-900 border border-slate-800 text-xs font-mono space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-200">
                          {selectedMission.latest_event.event_type}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {new Date(selectedMission.latest_event.occurred_at).toLocaleString()}
                        </span>
                      </div>
                      {selectedMission.latest_event.previous_state && selectedMission.latest_event.new_state && (
                        <div className="text-slate-400 text-[11px]">
                          {selectedMission.latest_event.previous_state} →{' '}
                          <span className="text-slate-200">
                            {selectedMission.latest_event.new_state}
                          </span>
                        </div>
                      )}
                      <div className="text-[10px] text-slate-500">
                        source: {selectedMission.latest_event.source}
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic">No operational events recorded.</p>
                  )}
                </div>

                {/* Section 5: Operator Actions */}
                {onInitiateReplan && (
                  <div className="pt-2 border-t border-slate-800">
                    <button
                      type="button"
                      data-testid={`initiate-replan-mission-${selectedMission.code.toLowerCase()}`}
                      onClick={() => onInitiateReplan(selectedMission)}
                      className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-amber-600 hover:bg-amber-500 text-slate-950 font-semibold text-xs tracking-wide transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                    >
                      <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
                      <span>Initiate Operational Replan</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
