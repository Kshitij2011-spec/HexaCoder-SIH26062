import { useState } from 'react';
import {
  Clock,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  Radio,
  FileText,
  Share2,
  WifiOff,
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useOperationalTimeline } from '../../features/operations/hooks/useOperationalTimeline';
import { LoadingSkeleton } from './LoadingSkeleton';
import { ErrorDisplay } from './ErrorDisplay';
import { ProvenanceTag } from './ProvenanceTag';
import type { TimelineEntry, TimelineEntryType } from '../../lib/types/api';

interface Props {
  entityType: string;
  entityId: string;
  title?: string;
  defaultIncludeRelated?: boolean;
  showIncludeRelatedToggle?: boolean;
}

function getEntryTypeBadge(type: TimelineEntryType) {
  switch (type) {
    case 'OPERATIONAL_EVENT':
      return {
        label: 'EVENT',
        icon: Radio,
        color: 'text-cyan-400 border-cyan-800 bg-cyan-950/60',
        dot: 'border-cyan-500 bg-cyan-400',
      };
    case 'AUDIT_RECORD':
      return {
        label: 'AUDIT',
        icon: FileText,
        color: 'text-amber-400 border-amber-800 bg-amber-950/60',
        dot: 'border-amber-500 bg-amber-400',
      };
    case 'PROPAGATION_RECORD':
      return {
        label: 'PROPAGATION',
        icon: Share2,
        color: 'text-purple-400 border-purple-800 bg-purple-950/60',
        dot: 'border-purple-500 bg-purple-400',
      };
    case 'OFFLINE_SYNC':
      return {
        label: 'SYNC',
        icon: WifiOff,
        color: 'text-emerald-400 border-emerald-800 bg-emerald-950/60',
        dot: 'border-emerald-500 bg-emerald-400',
      };
    default:
      return {
        label: 'RECORD',
        icon: Radio,
        color: 'text-slate-400 border-slate-700 bg-slate-900',
        dot: 'border-slate-600 bg-slate-400',
      };
  }
}

export function OperationalTimeline({
  entityType,
  entityId,
  title = 'Operational History & Event Journal',
  defaultIncludeRelated = false,
  showIncludeRelatedToggle = true,
}: Props) {
  const [includeRelated, setIncludeRelated] = useState(defaultIncludeRelated);
  const [order, setOrder] = useState<'desc' | 'asc'>('desc');
  const [page, setPage] = useState(1);
  const [expandedEntries, setExpandedEntries] = useState<Record<string, boolean>>({});

  const { data, isLoading, error } = useOperationalTimeline(entityType, entityId, {
    includeRelated,
    order,
    page,
    pageSize: 20,
  });

  const entries: TimelineEntry[] = Array.isArray(data?.entries) ? data.entries : [];
  const totalEntries = data?.total_entries ?? entries.length;

  const toggleExpand = (id: string) => {
    setExpandedEntries((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Header with Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-400" />
          <h4 className="font-semibold text-slate-200 tracking-wide">{title}</h4>
          {data && (
            <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 text-[10px]">
              {totalEntries} {totalEntries === 1 ? 'entry' : 'entries'}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Include Related Toggle */}
          {showIncludeRelatedToggle && (
            <label className="flex items-center gap-1.5 cursor-pointer text-slate-400 hover:text-slate-200 select-none text-[11px]">
              <input
                type="checkbox"
                checked={includeRelated}
                onChange={(e) => {
                  setIncludeRelated(e.target.checked);
                  setPage(1);
                }}
                className="rounded border-slate-700 bg-slate-950 text-cyan-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
              />
              <span>Include Related</span>
            </label>
          )}

          {/* Sort Order Toggle */}
          <button
            type="button"
            onClick={() => setOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'))}
            className="flex items-center gap-1 px-2 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-[11px] transition-colors"
            title="Toggle chronological order"
          >
            <SlidersHorizontal className="w-3 h-3" />
            <span>{order === 'desc' ? 'Newest' : 'Oldest'}</span>
          </button>
        </div>
      </div>

      {/* Content Area */}
      {isLoading && <LoadingSkeleton lines={4} />}

      {error && <ErrorDisplay error={error} />}

      {!isLoading && !error && data && entries.length === 0 && (
        <div className="p-6 text-center text-slate-500 border border-slate-800/80 rounded-lg bg-slate-900/30">
          No operational history or events recorded for this entity.
        </div>
      )}

      {!isLoading && !error && data && entries.length > 0 && (
        <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
          {entries.map((entry: TimelineEntry) => {
            const typeInfo = getEntryTypeBadge(entry.entry_type);
            const Icon = typeInfo.icon;
            const isExpanded = !!expandedEntries[entry.id];
            const hasDetails = entry.details && Object.keys(entry.details).length > 0;

            return (
              <div key={entry.id} className="relative group">
                {/* Timeline Dot */}
                <div
                  className={`absolute -left-6 top-1.5 w-4 h-4 rounded-full bg-slate-950 border-2 ${typeInfo.dot} flex items-center justify-center`}
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
                </div>

                {/* Timeline Item Card */}
                <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800/90 hover:border-slate-700 space-y-2 transition-colors">
                  {/* Row 1: Header (Badge, Action Name, Timestamp) */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] font-bold ${typeInfo.color}`}
                      >
                        <Icon className="w-3 h-3" />
                        {typeInfo.label}
                      </span>
                      <span className="font-semibold text-slate-200">
                        {entry.event_or_action}
                      </span>
                      {entry.audit_action && entry.audit_action !== entry.event_or_action && (
                        <span className="px-1.5 py-0.5 rounded bg-amber-950/40 border border-amber-800/60 text-amber-300 text-[10px]">
                          Audit: {entry.audit_action}
                        </span>
                      )}
                      {entry.related_entity_type && (
                        <span className="px-1.5 py-0.5 rounded bg-indigo-950/60 border border-indigo-800/60 text-indigo-300 text-[10px]">
                          Related: {entry.related_entity_type}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5 text-slate-500 text-[11px]">
                      <Clock className="w-3 h-3" />
                      <span>{formatDate(entry.timestamp)}</span>
                    </div>
                  </div>

                  {/* Row 2: State Transitions / Description */}
                  {entry.previous_state && entry.new_state ? (
                    <div className="flex items-center gap-2 py-1 text-[11px]">
                      <span className="px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700">
                        {entry.previous_state}
                      </span>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                      <span className="px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800">
                        {entry.new_state}
                      </span>
                    </div>
                  ) : entry.description ? (
                    <p className="text-slate-300 text-[11px] leading-relaxed">
                      {entry.description}
                    </p>
                  ) : null}

                  {/* Row 3: Footer Metadata (Actor, CID, Provenance, Expand Toggle) */}
                  <div className="pt-2 flex flex-wrap items-center justify-between gap-2 text-[10px] text-slate-500 border-t border-slate-800/60">
                    <div className="flex items-center gap-3">
                      <span>
                        Actor:{' '}
                        <span className="text-slate-300">
                          {entry.actor_id ? entry.actor_id.slice(0, 8) : entry.actor_type ?? 'SYSTEM'}
                        </span>
                      </span>

                      {entry.correlation_id && (
                        <span title={`Correlation ID: ${entry.correlation_id}`}>
                          CID:{' '}
                          <span className="text-slate-300 font-mono">
                            {entry.correlation_id.slice(0, 8)}…
                          </span>
                        </span>
                      )}

                      <ProvenanceTag provenance={entry.data_provenance} />
                    </div>

                    {hasDetails && (
                      <button
                        type="button"
                        onClick={() => toggleExpand(entry.id)}
                        className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300 transition-colors"
                      >
                        <span>{isExpanded ? 'Hide Details' : 'View Details'}</span>
                        {isExpanded ? (
                          <ChevronUp className="w-3 h-3" />
                        ) : (
                          <ChevronDown className="w-3 h-3" />
                        )}
                      </button>
                    )}
                  </div>

                  {/* Expanded JSON Inspector */}
                  {isExpanded && hasDetails && (
                    <div className="mt-2 p-2.5 rounded bg-slate-950/90 border border-slate-800 text-[11px] text-slate-300 overflow-x-auto">
                      <pre className="font-mono whitespace-pre-wrap break-all">
                        {JSON.stringify(entry.details, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {!isLoading && data && data.total_pages > 1 && (
        <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-[11px] text-slate-400">
          <span>
            Page {data.page} of {data.total_pages}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300 transition-colors"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              type="button"
              disabled={page >= data.total_pages}
              onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300 transition-colors"
              aria-label="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
