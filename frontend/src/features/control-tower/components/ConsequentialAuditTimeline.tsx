import { useState } from 'react';
import {
  FileCheck2,
  Clock,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  UserCheck,
  Sparkles,
} from 'lucide-react';
import { useConsequentialAudit } from '../hooks/useControlTower';
import { StatusBadge } from '../../../components/shared/StatusBadge';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../../components/shared/ErrorDisplay';
import { EmptyState } from '../../../components/shared/EmptyState';
import type { ConsequentialActionItem } from '../../../lib/types/api';

export interface ConsequentialAuditTimelineProps {
  expeditionId: string;
}

export function ConsequentialAuditTimeline({
  expeditionId,
}: ConsequentialAuditTimelineProps) {
  const [page, setPage] = useState(1);
  const [expandedEntries, setExpandedEntries] = useState<Record<string, boolean>>({});

  const { data, isLoading, error } = useConsequentialAudit(expeditionId, page);

  const items: ConsequentialActionItem[] = Array.isArray(data) ? data : [];

  const toggleExpand = (id: string) => {
    setExpandedEntries((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return '—';
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
    <section
      aria-labelledby="consequential-audit-heading"
      className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm"
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-950/40">
        <div className="flex items-center gap-2.5">
          <FileCheck2 className="w-5 h-5 text-emerald-400" aria-hidden="true" />
          <div>
            <h2
              id="consequential-audit-heading"
              className="text-base font-bold text-slate-100 tracking-wide flex items-center gap-2"
            >
              <span>Consequential Audit Timeline</span>
              {items.length > 0 && (
                <span className="text-xs font-mono font-normal px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                  {items.length} {items.length === 1 ? 'record' : 'records'}
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-400">
              Permanent auditable ledger of human approvals and executed operational adaptations
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <ProvenanceTag
            provenance={items[0]?.data_provenance ?? 'DERIVED'}
          />
        </div>
      </div>

      {/* Content Area */}
      <div className="p-4">
        {/* Loading State */}
        {isLoading && (
          <div aria-busy="true" className="space-y-3">
            <LoadingSkeleton lines={3} />
            <LoadingSkeleton lines={4} />
          </div>
        )}

        {/* Error State */}
        {error && (
          <ErrorDisplay
            error={error}
            title="Failed to load consequential audit trail"
          />
        )}

        {/* Empty State */}
        {!isLoading && !error && items.length === 0 && (
          <EmptyState
            title="No consequential audit records"
            message="No approved decisions or operational changes have been executed for this expedition yet."
          />
        )}

        {/* Loaded Timeline */}
        {!isLoading && !error && items.length > 0 && (
          <div className="space-y-4">
            <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
              {items.map((item: ConsequentialActionItem) => {
                const key = item.approval_id;
                const isExpanded = !!expandedEntries[key];
                const hasAppliedChanges =
                  item.applied_changes && item.applied_changes.length > 0;
                const isApproved = item.decision === 'APPROVED';

                return (
                  <div key={key} className="relative group">
                    {/* Timeline Dot */}
                    <div
                      className={`absolute -left-6 top-2 w-4 h-4 rounded-full bg-slate-950 border-2 ${
                        isApproved
                          ? 'border-emerald-500 text-emerald-400'
                          : 'border-rose-500 text-rose-400'
                      } flex items-center justify-center`}
                    >
                      <div className="w-1.5 h-1.5 rounded-full bg-current opacity-90" />
                    </div>

                    {/* Timeline Card */}
                    <div className="p-4 rounded-lg bg-slate-950/40 border border-slate-800 hover:border-slate-700 transition-colors space-y-3">
                      {/* Row 1: Decision, Action Summary, Timestamp */}
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <StatusBadge status={item.decision ?? 'APPROVED'} />
                          <h3 className="text-sm font-semibold text-slate-100">
                            {item.action_summary}
                          </h3>
                        </div>

                        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                          <Clock className="w-3.5 h-3.5 text-slate-500" />
                          <span>{formatDate(item.decided_at ?? item.created_at)}</span>
                        </div>
                      </div>

                      {/* Row 2: Human Governance Metadata */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 p-2.5 rounded bg-slate-900/60 border border-slate-800/80 text-xs font-mono text-slate-300">
                        <div className="flex items-center gap-1.5">
                          <UserCheck className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                          <span className="text-slate-400">Operator:</span>
                          <span className="text-slate-100 font-semibold truncate">
                            {item.approver_person_id}
                          </span>
                        </div>

                        {item.approver_role && (
                          <div>
                            <span className="text-slate-400">Role: </span>
                            <span className="text-slate-200">{item.approver_role}</span>
                          </div>
                        )}

                        {item.resulting_event_id && (
                          <div className="flex items-center gap-1.5">
                            <Sparkles className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                            <span className="text-slate-400">Event ID: </span>
                            <span className="text-amber-300 font-semibold truncate">
                              {item.resulting_event_id}
                            </span>
                          </div>
                        )}

                        <div className="text-[11px] text-slate-400 truncate">
                          <span>Rec: </span>
                          <span className="text-slate-300">{item.recommendation_id}</span>
                        </div>

                        {item.replan_id && (
                          <div className="text-[11px] text-slate-400 truncate">
                            <span>Replan: </span>
                            <span className="text-slate-300">{item.replan_id}</span>
                          </div>
                        )}

                        {item.correlation_id && (
                          <div className="text-[11px] text-slate-400 truncate">
                            <span>Correlation: </span>
                            <span className="text-slate-300">{item.correlation_id}</span>
                          </div>
                        )}
                      </div>

                      {/* Row 3: Human Operator Comment / Justification */}
                      {item.comment && (
                        <div className="text-xs text-slate-300 bg-slate-900/40 p-2.5 rounded border border-slate-800 italic">
                          <span className="not-italic text-slate-400 font-mono block text-[11px] mb-0.5">
                            Operator Justification:
                          </span>
                          "{item.comment}"
                        </div>
                      )}

                      {/* Row 4: Expandable Applied Operational Changes */}
                      {hasAppliedChanges && (
                        <div>
                          <button
                            type="button"
                            onClick={() => toggleExpand(key)}
                            aria-expanded={isExpanded}
                            className="text-xs font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1 focus:outline-none focus:underline"
                          >
                            <span>
                              {isExpanded
                                ? 'Hide Executed Operational Changes'
                                : `Show Executed Operational Changes (${item.applied_changes.length})`}
                            </span>
                            {isExpanded ? (
                              <ChevronUp className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5" />
                            )}
                          </button>

                          {isExpanded && (
                            <div className="mt-2 space-y-1.5 pl-2 border-l-2 border-cyan-800">
                              {item.applied_changes.map((ch, chIdx) => (
                                <div
                                  key={chIdx}
                                  className="p-2 rounded bg-slate-900/80 border border-slate-800 text-xs font-mono space-y-0.5"
                                >
                                  {typeof ch === 'object' && ch !== null ? (
                                    Object.entries(ch as Record<string, unknown>).map(
                                      ([k, v]) => (
                                        <div key={k} className="flex gap-2">
                                          <span className="text-cyan-400">{k}:</span>
                                          <span className="text-slate-200">{String(v)}</span>
                                        </div>
                                      ),
                                    )
                                  ) : (
                                    <span>{String(ch)}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs font-mono text-slate-400">
              <span>Page {page}</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={items.length < 20}
                  className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
