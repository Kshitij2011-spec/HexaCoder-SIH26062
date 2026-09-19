import { useState } from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  Filter,
} from 'lucide-react';
import { EntityCode } from '../../../components/shared/EntityCode';
import { StatusBadge } from '../../../components/shared/StatusBadge';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { EmptyState } from '../../../components/shared/EmptyState';
import { ErrorDisplay } from '../../../components/shared/ErrorDisplay';
import { useControlTowerConstraints } from '../hooks/useControlTower';
import type { ControlTowerConstraintItem, ConstraintState } from '../../../lib/types/api';

export interface ActiveConstraintsFeedProps {
  expeditionId: string;
}

const STATE_FILTER_OPTIONS: { label: string; value: string }[] = [
  { label: 'All States', value: '' },
  { label: 'Violated', value: 'VIOLATED' },
  { label: 'Not Evaluable', value: 'NOT_EVALUABLE' },
  { label: 'Satisfied', value: 'SATISFIED' },
];

const RIGIDITY_FILTER_OPTIONS: { label: string; value: string }[] = [
  { label: 'All Rigidity', value: '' },
  { label: 'Hard Only', value: 'HARD' },
  { label: 'Soft Only', value: 'SOFT' },
];

const STATE_BADGE_CONFIG: Record<
  ConstraintState | string,
  { label: string; badgeClass: string; icon: React.ComponentType<{ className?: string }> }
> = {
  VIOLATED: {
    label: 'VIOLATED',
    badgeClass: 'bg-rose-950/80 text-rose-200 border-rose-600',
    icon: ShieldAlert,
  },
  NOT_EVALUABLE: {
    label: 'NOT EVALUABLE',
    badgeClass: 'bg-amber-950/80 text-amber-300 border-amber-600',
    icon: AlertTriangle,
  },
  SATISFIED: {
    label: 'SATISFIED',
    badgeClass: 'bg-emerald-950/80 text-emerald-300 border-emerald-600',
    icon: CheckCircle2,
  },
};

export function ActiveConstraintsFeed({ expeditionId }: ActiveConstraintsFeedProps) {
  const [stateFilter, setStateFilter] = useState<string>('');
  const [hardOrSoftFilter, setHardOrSoftFilter] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const pageSize = 20;
  const [expandedEvidenceIds, setExpandedEvidenceIds] = useState<Record<string, boolean>>({});

  const {
    data: constraints,
    isLoading,
    error,
  } = useControlTowerConstraints(expeditionId, {
    state: (stateFilter as ConstraintState) || undefined,
    hard_or_soft: hardOrSoftFilter || undefined,
    page,
    page_size: pageSize,
  });

  const toggleEvidence = (constraintId: string) => {
    setExpandedEvidenceIds((prev) => ({
      ...prev,
      [constraintId]: !prev[constraintId],
    }));
  };

  const handleStateChange = (value: string) => {
    setStateFilter(value);
    setPage(1);
  };

  const handleRigidityChange = (value: string) => {
    setHardOrSoftFilter(value);
    setPage(1);
  };

  const items = constraints ?? [];
  const violatedCount = items.filter((c) => c.state === 'VIOLATED').length;
  const hasFiltersActive = Boolean(stateFilter || hardOrSoftFilter);

  return (
    <section
      aria-label="Active Constraints & Invariants"
      className="rounded-lg bg-slate-900 border border-slate-800 shadow-sm"
    >
      {/* ─── Header & Filters Toolbar ─── */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-sky-400 shrink-0" aria-hidden="true" />
              <h2 className="text-base font-semibold text-slate-100">
                Active Constraints & Invariants
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Deterministic rule evaluation, subject bindings, and violation evidence
            </p>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
            <span>Showing {items.length} constraints</span>
            {violatedCount > 0 && (
              <span className="px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-700 font-semibold">
                {violatedCount} VIOLATED
              </span>
            )}
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="flex flex-wrap items-center gap-3">
          {/* State Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-500" aria-hidden="true" />
            <label
              htmlFor="constraint-state-filter"
              className="text-xs font-mono text-slate-400 uppercase tracking-wider"
            >
              State:
            </label>
            <select
              id="constraint-state-filter"
              aria-label="Filter by constraint evaluation state"
              value={stateFilter}
              onChange={(e) => handleStateChange(e.target.value)}
              className="bg-slate-950 text-slate-100 text-xs font-mono rounded border border-slate-700 px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              {STATE_FILTER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Rigidity Filter (Hard / Soft) */}
          <div className="flex items-center gap-2">
            <label
              htmlFor="constraint-rigidity-filter"
              className="text-xs font-mono text-slate-400 uppercase tracking-wider"
            >
              Rigidity:
            </label>
            <select
              id="constraint-rigidity-filter"
              aria-label="Filter by constraint rigidity"
              value={hardOrSoftFilter}
              onChange={(e) => handleRigidityChange(e.target.value)}
              className="bg-slate-950 text-slate-100 text-xs font-mono rounded border border-slate-700 px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              {RIGIDITY_FILTER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ─── Content Area: Loading / Error / Empty / Constraints List ─── */}
      <div className="p-4">
        {isLoading && (
          <div aria-busy="true" className="py-4">
            <LoadingSkeleton lines={5} />
          </div>
        )}

        {error && (
          <div className="py-4">
            <ErrorDisplay error={error} title="Failed to load active constraints" />
          </div>
        )}

        {!isLoading && !error && items.length === 0 && (
          <EmptyState
            title={hasFiltersActive ? 'No matching constraints' : 'No active constraints found'}
            message={
              hasFiltersActive
                ? 'No constraints match the selected state and rigidity filters.'
                : 'There are no active constraints configured for this expedition.'
            }
          />
        )}

        {!isLoading && !error && items.length > 0 && (
          <div className="space-y-3">
            {items.map((c: ControlTowerConstraintItem) => {
              const stateConfig = STATE_BADGE_CONFIG[c.state] ?? STATE_BADGE_CONFIG.SATISFIED;
              const StateIcon = stateConfig.icon;
              const isViolated = c.state === 'VIOLATED';
              const isExpanded = Boolean(expandedEvidenceIds[c.constraint_id]);
              const hasEvidence = c.evidence && Object.keys(c.evidence).length > 0;

              return (
                <article
                  key={c.constraint_id}
                  className={`p-3.5 rounded-lg border transition-colors ${
                    isViolated
                      ? 'bg-rose-950/15 border-rose-900/60'
                      : c.state === 'NOT_EVALUABLE'
                      ? 'bg-amber-950/15 border-amber-900/60'
                      : 'bg-slate-950/60 border-slate-800/80'
                  }`}
                  aria-label={`Constraint ${c.code}: ${c.name}`}
                >
                  {/* Top Bar: Code, Name, Badges, Provenance */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800/60">
                    <div className="flex flex-wrap items-center gap-2">
                      <EntityCode code={c.code} />
                      <h3 className="font-semibold text-slate-100 text-sm">
                        {c.name}
                      </h3>
                      <span className="text-xs font-mono text-slate-400">
                        [{c.rule_code}]
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* State Badge */}
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded font-mono text-[11px] font-semibold border ${stateConfig.badgeClass}`}
                        role="status"
                        aria-label={`Constraint state: ${stateConfig.label}`}
                      >
                        <StateIcon className="w-3.5 h-3.5" aria-hidden="true" />
                        <span>{stateConfig.label}</span>
                      </span>

                      {/* Hard / Soft Pill */}
                      <span
                        className={`px-1.5 py-0.5 rounded font-mono text-[10px] font-bold uppercase border ${
                          c.hard_or_soft === 'HARD'
                            ? 'bg-rose-950 text-rose-300 border-rose-800'
                            : 'bg-slate-800 text-slate-300 border-slate-700'
                        }`}
                      >
                        {c.hard_or_soft}
                      </span>

                      {/* Severity */}
                      {c.severity && (
                        <StatusBadge
                          status={c.severity}
                          label={c.severity}
                          className="text-[10px] px-1.5 py-0.5"
                        />
                      )}

                      <ProvenanceTag provenance={c.data_provenance} />
                    </div>
                  </div>

                  {/* Body: Subject Binding and Operational Reason */}
                  <div className="pt-2 text-xs">
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-slate-400 mb-1.5">
                      <div>
                        <span className="text-slate-500">Subject: </span>
                        <span className="text-sky-300">
                          {c.subject_type}: {c.subject_code ?? c.subject_id}
                        </span>
                      </div>
                      {c.type && (
                        <div>
                          <span className="text-slate-500">Type: </span>
                          <span className="text-slate-300">{c.type}</span>
                        </div>
                      )}
                    </div>

                    <p className="text-slate-300 text-xs font-sans leading-relaxed">
                      {c.reason}
                    </p>
                  </div>

                  {/* Expandable Evidence Section */}
                  {hasEvidence && (
                    <div className="mt-2.5 pt-2 border-t border-slate-800/60">
                      <button
                        type="button"
                        onClick={() => toggleEvidence(c.constraint_id)}
                        className="flex items-center gap-1.5 text-xs font-mono text-sky-400 hover:text-sky-300 focus:outline-none focus:underline"
                        aria-expanded={isExpanded}
                        aria-controls={`evidence-${c.constraint_id}`}
                      >
                        {isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
                        )}
                        <span>
                          {isExpanded ? 'Hide' : 'Show'} Evidence & Diagnostics (
                          {Object.keys(c.evidence).length} entries)
                        </span>
                      </button>

                      {isExpanded && (
                        <div
                          id={`evidence-${c.constraint_id}`}
                          className="mt-2 p-2.5 rounded bg-slate-950 border border-slate-800 font-mono text-xs"
                        >
                          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5">
                            {Object.entries(c.evidence).map(([k, v]) => (
                              <div key={k} className="flex items-baseline justify-between gap-2 border-b border-slate-900 pb-1">
                                <dt className="text-slate-400 text-[11px] truncate max-w-[150px]">
                                  {k}:
                                </dt>
                                <dd className="text-slate-200 text-[11px] font-semibold truncate max-w-[200px]">
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
                  aria-label="Previous constraints page"
                >
                  <ChevronLeft className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Prev</span>
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={items.length < pageSize}
                  className="flex items-center gap-1 px-2.5 py-1 rounded border border-slate-700 bg-slate-950 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:border-slate-600"
                  aria-label="Next constraints page"
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
