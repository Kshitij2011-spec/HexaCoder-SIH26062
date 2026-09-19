import { useState } from 'react';
import {
  Activity,
  ArrowRight,
  Clock,
  User,
  Hash,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  Filter,
} from 'lucide-react';
import { EntityCode } from '../../../components/shared/EntityCode';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { EmptyState } from '../../../components/shared/EmptyState';
import { ErrorDisplay } from '../../../components/shared/ErrorDisplay';
import { useOperationalEventsFeed } from '../hooks/useControlTower';
import type { OperationalEventFeedItem } from '../../../lib/types/api';

export interface OperationalEventsFeedProps {
  expeditionId: string;
}

const ENTITY_TYPE_OPTIONS: { label: string; value: string }[] = [
  { label: 'All Entity Types', value: '' },
  { label: 'Mission', value: 'MISSION' },
  { label: 'Expedition', value: 'EXPEDITION' },
  { label: 'Transport Leg', value: 'TRANSPORT_LEG' },
  { label: 'Cargo Consignment', value: 'CARGO_CONSIGNMENT' },
  { label: 'Asset', value: 'ASSET' },
  { label: 'Incident', value: 'INCIDENT' },
  { label: 'Replan', value: 'REPLAN' },
];

export function OperationalEventsFeed({ expeditionId }: OperationalEventsFeedProps) {
  const [entityType, setEntityType] = useState<string>('');
  const [eventType, setEventType] = useState<string>('');
  const [fromTime, setFromTime] = useState<string>('');
  const [toTime, setToTime] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const pageSize = 20;
  const [expandedEvidenceIds, setExpandedEvidenceIds] = useState<Record<string, boolean>>({});

  const {
    data: events,
    isLoading,
    error,
  } = useOperationalEventsFeed(expeditionId, {
    entity_type: entityType || undefined,
    event_type: eventType.trim() || undefined,
    from_time: fromTime ? new Date(fromTime).toISOString() : undefined,
    to_time: toTime ? new Date(toTime).toISOString() : undefined,
    page,
    page_size: pageSize,
  });

  const toggleEvidence = (eventId: string) => {
    setExpandedEvidenceIds((prev) => ({
      ...prev,
      [eventId]: !prev[eventId],
    }));
  };

  const handleEntityTypeChange = (val: string) => {
    setEntityType(val);
    setPage(1);
  };

  const handleEventTypeChange = (val: string) => {
    setEventType(val);
    setPage(1);
  };

  const handleFromTimeChange = (val: string) => {
    setFromTime(val);
    setPage(1);
  };

  const handleToTimeChange = (val: string) => {
    setToTime(val);
    setPage(1);
  };

  const clearFilters = () => {
    setEntityType('');
    setEventType('');
    setFromTime('');
    setToTime('');
    setPage(1);
  };

  const items = events ?? [];
  const hasActiveFilters = Boolean(entityType || eventType || fromTime || toTime);

  return (
    <section
      aria-label="Operational Events Timeline"
      className="rounded-lg bg-slate-900 border border-slate-800 shadow-sm"
    >
      {/* ─── Header & Filters Toolbar ─── */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-sky-400 shrink-0" aria-hidden="true" />
              <h2 className="text-base font-semibold text-slate-100">
                Operational Events Feed
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Chronological ledger of operational state mutations, evidence, and actor provenance
            </p>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
            <span>Showing {items.length} events</span>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="text-xs text-sky-400 hover:text-sky-300 underline font-mono"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Entity Type Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-500" aria-hidden="true" />
            <label
              htmlFor="events-entity-filter"
              className="text-xs font-mono text-slate-400 uppercase tracking-wider"
            >
              Entity:
            </label>
            <select
              id="events-entity-filter"
              aria-label="Filter events by entity type"
              value={entityType}
              onChange={(e) => handleEntityTypeChange(e.target.value)}
              className="bg-slate-950 text-slate-100 text-xs font-mono rounded border border-slate-700 px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              {ENTITY_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Event Type Input */}
          <div className="flex items-center gap-2">
            <label
              htmlFor="events-type-filter"
              className="text-xs font-mono text-slate-400 uppercase tracking-wider"
            >
              Event:
            </label>
            <input
              id="events-type-filter"
              type="text"
              placeholder="e.g. MissionApproved…"
              aria-label="Filter events by event type"
              value={eventType}
              onChange={(e) => handleEventTypeChange(e.target.value)}
              className="bg-slate-950 text-slate-100 text-xs font-mono rounded border border-slate-700 px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500 placeholder:text-slate-600 w-44"
            />
          </div>

          {/* From Time */}
          <div className="flex items-center gap-2">
            <label
              htmlFor="events-from-time"
              className="text-xs font-mono text-slate-400 uppercase tracking-wider"
            >
              From:
            </label>
            <input
              id="events-from-time"
              type="date"
              aria-label="Filter events occurred on or after"
              value={fromTime}
              onChange={(e) => handleFromTimeChange(e.target.value)}
              className="bg-slate-950 text-slate-100 text-xs font-mono rounded border border-slate-700 px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>

          {/* To Time */}
          <div className="flex items-center gap-2">
            <label
              htmlFor="events-to-time"
              className="text-xs font-mono text-slate-400 uppercase tracking-wider"
            >
              To:
            </label>
            <input
              id="events-to-time"
              type="date"
              aria-label="Filter events occurred on or before"
              value={toTime}
              onChange={(e) => handleToTimeChange(e.target.value)}
              className="bg-slate-950 text-slate-100 text-xs font-mono rounded border border-slate-700 px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>
        </div>
      </div>

      {/* ─── Content Area: Loading / Error / Empty / Events Timeline ─── */}
      <div className="p-4">
        {isLoading && (
          <div aria-busy="true" className="py-4">
            <LoadingSkeleton lines={5} />
          </div>
        )}

        {error && (
          <div className="py-4">
            <ErrorDisplay error={error} title="Failed to load operational events" />
          </div>
        )}

        {!isLoading && !error && items.length === 0 && (
          <EmptyState
            title={hasActiveFilters ? 'No matching operational events' : 'No operational events recorded'}
            message={
              hasActiveFilters
                ? 'No events match the selected entity, event type, or date criteria.'
                : 'There are no recorded operational events for this expedition yet.'
            }
          />
        )}

        {!isLoading && !error && items.length > 0 && (
          <div className="relative pl-6 space-y-4 border-l-2 border-slate-800">
            {items.map((ev: OperationalEventFeedItem) => {
              const isExpanded = Boolean(expandedEvidenceIds[ev.event_id]);
              const hasEvidence = ev.evidence && Object.keys(ev.evidence).length > 0;
              const hasTransition = Boolean(ev.previous_state && ev.new_state);

              return (
                <article
                  key={ev.event_id}
                  className="relative p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition-colors"
                  aria-label={`Event ${ev.event_type} on ${ev.entity_type}`}
                >
                  {/* Timeline Node Icon */}
                  <span
                    className="absolute -left-[31px] top-4 w-3.5 h-3.5 rounded-full bg-sky-500 border-2 border-slate-900 shadow-sm"
                    aria-hidden="true"
                  />

                  {/* Header Row: Event Type, Entity Badge, Timestamp, Provenance */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800/60">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-sky-300 px-2 py-0.5 rounded bg-sky-950/80 border border-sky-800">
                        {ev.event_type}
                      </span>
                      <EntityCode code={`${ev.entity_type}:${ev.entity_id.slice(0, 8)}`} />
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="flex items-center gap-1 text-[11px] font-mono text-slate-400">
                        <Clock className="w-3 h-3 text-slate-500" aria-hidden="true" />
                        <time dateTime={ev.occurred_at}>
                          {new Date(ev.occurred_at).toLocaleString()}
                        </time>
                      </span>
                      <ProvenanceTag provenance={ev.data_provenance} />
                    </div>
                  </div>

                  {/* State Transition (if recorded) */}
                  {hasTransition && (
                    <div className="mt-2 flex items-center gap-2 text-xs font-mono">
                      <span className="text-slate-400">Transition:</span>
                      <span className="px-1.5 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                        {ev.previous_state}
                      </span>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-500" aria-hidden="true" />
                      <span className="px-1.5 py-0.5 rounded bg-slate-900 text-emerald-300 font-semibold border border-slate-800">
                        {ev.new_state}
                      </span>
                    </div>
                  )}

                  {/* Operational Context: Source, Actor, Correlation */}
                  <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-mono text-slate-400">
                    <div>
                      <span className="text-slate-500">Source: </span>
                      <span className="text-slate-300">{ev.source}</span>
                    </div>

                    {(ev.actor_type || ev.actor_id) && (
                      <div className="flex items-center gap-1">
                        <User className="w-3 h-3 text-slate-500" aria-hidden="true" />
                        <span className="text-slate-500">Actor: </span>
                        <span className="text-slate-300">
                          {ev.actor_type ?? 'OPERATOR'}
                          {ev.actor_id ? ` (${ev.actor_id.slice(0, 8)})` : ''}
                        </span>
                      </div>
                    )}

                    {ev.correlation_id && (
                      <div className="flex items-center gap-1">
                        <Hash className="w-3 h-3 text-slate-500" aria-hidden="true" />
                        <span className="text-slate-500">Correlation: </span>
                        <span className="text-slate-400 text-[11px]">
                          {ev.correlation_id.slice(0, 8)}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Expandable Evidence */}
                  {hasEvidence && (
                    <div className="mt-2.5 pt-2 border-t border-slate-800/60">
                      <button
                        type="button"
                        onClick={() => toggleEvidence(ev.event_id)}
                        className="flex items-center gap-1.5 text-xs font-mono text-sky-400 hover:text-sky-300 focus:outline-none focus:underline"
                        aria-expanded={isExpanded}
                        aria-controls={`event-evidence-${ev.event_id}`}
                      >
                        {isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
                        )}
                        <span>
                          {isExpanded ? 'Hide' : 'Show'} Evidence & Details (
                          {Object.keys(ev.evidence).length} items)
                        </span>
                      </button>

                      {isExpanded && (
                        <div
                          id={`event-evidence-${ev.event_id}`}
                          className="mt-2 p-2.5 rounded bg-slate-900 border border-slate-800 font-mono text-xs"
                        >
                          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5">
                            {Object.entries(ev.evidence).map(([k, v]) => (
                              <div key={k} className="flex items-baseline justify-between gap-2 border-b border-slate-800/80 pb-1">
                                <dt className="text-slate-400 text-[11px] truncate max-w-[150px]">
                                  {k}:
                                </dt>
                                <dd className="text-slate-200 text-[11px] font-semibold truncate max-w-[220px]">
                                  {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                </dd>
                              </div>
                            ))}
                          </dl>
                        </div>
                      )}
                    </div>
                  )}
                </article>
              );
            })}

            {/* Pagination Controls */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-800 text-xs font-mono text-slate-400">
              <span>Page {page}</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="flex items-center gap-1 px-2.5 py-1 rounded border border-slate-700 bg-slate-950 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:border-slate-600"
                  aria-label="Previous events page"
                >
                  <ChevronLeft className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Prev</span>
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={items.length < pageSize}
                  className="flex items-center gap-1 px-2.5 py-1 rounded border border-slate-700 bg-slate-950 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:border-slate-600"
                  aria-label="Next events page"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
