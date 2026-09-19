import { useState } from 'react';
import {
  ShieldAlert,
  GitPullRequest,
  Clock,
  ArrowUpRight,
  Sparkles,
} from 'lucide-react';
import { useDecisionQueue } from '../hooks/useControlTower';
import { StatusBadge } from '../../../components/shared/StatusBadge';
import { EntityCode } from '../../../components/shared/EntityCode';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../../components/shared/ErrorDisplay';
import { EmptyState } from '../../../components/shared/EmptyState';
import { ApprovalModal } from './ApprovalModal';
import type {
  DecisionApprovalItem,
  DecisionRecommendationItem,
  DecisionReplanItem,
} from '../../../lib/types/api';

export interface DecisionQueuePanelProps {
  expeditionId: string;
  onSelectRecommendation?: (recommendationId: string) => void;
}

type TabKey = 'approvals' | 'recommendations' | 'replans';

export function DecisionQueuePanel({
  expeditionId,
  onSelectRecommendation,
}: DecisionQueuePanelProps) {
  const [activeTab, setActiveTab] = useState<TabKey>('approvals');
  const [selectedRecommendationId, setSelectedRecommendationId] = useState<string | null>(null);

  const { data, isLoading, error } = useDecisionQueue(expeditionId);

  const handleOpenReview = (recommendationId: string) => {
    setSelectedRecommendationId(recommendationId);
    onSelectRecommendation?.(recommendationId);
  };

  const handleCloseReview = () => {
    setSelectedRecommendationId(null);
  };

  const pendingApprovals = data?.pending_approvals ?? [];
  const pendingRecommendations = data?.pending_recommendations ?? [];
  const pendingReplans = data?.pending_replans ?? [];

  return (
    <section
      aria-labelledby="decision-queue-heading"
      className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm"
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-950/40">
        <div className="flex items-center gap-2.5">
          <ShieldAlert className="w-5 h-5 text-amber-400" aria-hidden="true" />
          <div>
            <h2
              id="decision-queue-heading"
              className="text-base font-bold text-slate-100 tracking-wide flex items-center gap-2"
            >
              <span>Decision Queue & Human Governance</span>
              <span className="text-xs font-mono text-slate-400 font-normal">
                (Awaiting Operator Decision)
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Operational replans, candidate recommendations, and human approval gates
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <ProvenanceTag provenance={data?.data_provenance ?? 'DERIVED'} />
        </div>
      </div>

      {/* Tabs */}
      <div className="px-4 border-b border-slate-800 bg-slate-950/20">
        <div role="tablist" aria-label="Decision queue views" className="flex gap-2">
          <button
            type="button"
            role="tab"
            id="tab-approvals"
            aria-selected={activeTab === 'approvals'}
            aria-controls="tabpanel-approvals"
            data-testid="tab-approvals"
            onClick={() => setActiveTab('approvals')}
            className={`py-2.5 px-3 text-xs font-mono font-medium border-b-2 transition-colors flex items-center gap-2 focus:outline-none focus:ring-1 focus:ring-cyan-500 ${
              activeTab === 'approvals'
                ? 'border-cyan-500 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <span>Pending Approvals</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[11px] ${
                pendingApprovals.length > 0
                  ? 'bg-amber-900/60 text-amber-300 font-bold'
                  : 'bg-slate-800 text-slate-400'
              }`}
            >
              {pendingApprovals.length}
            </span>
          </button>

          <button
            type="button"
            role="tab"
            id="tab-recommendations"
            aria-selected={activeTab === 'recommendations'}
            aria-controls="tabpanel-recommendations"
            data-testid="tab-recommendations"
            onClick={() => setActiveTab('recommendations')}
            className={`py-2.5 px-3 text-xs font-mono font-medium border-b-2 transition-colors flex items-center gap-2 focus:outline-none focus:ring-1 focus:ring-cyan-500 ${
              activeTab === 'recommendations'
                ? 'border-cyan-500 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <span>Recommendations</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[11px] ${
                pendingRecommendations.length > 0
                  ? 'bg-sky-900/60 text-sky-300 font-bold'
                  : 'bg-slate-800 text-slate-400'
              }`}
            >
              {pendingRecommendations.length}
            </span>
          </button>

          <button
            type="button"
            role="tab"
            id="tab-replans"
            aria-selected={activeTab === 'replans'}
            aria-controls="tabpanel-replans"
            data-testid="tab-replans"
            onClick={() => setActiveTab('replans')}
            className={`py-2.5 px-3 text-xs font-mono font-medium border-b-2 transition-colors flex items-center gap-2 focus:outline-none focus:ring-1 focus:ring-cyan-500 ${
              activeTab === 'replans'
                ? 'border-cyan-500 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <span>Replans</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[11px] ${
                pendingReplans.length > 0
                  ? 'bg-slate-700 text-slate-200 font-bold'
                  : 'bg-slate-800 text-slate-400'
              }`}
            >
              {pendingReplans.length}
            </span>
          </button>
        </div>
      </div>

      {/* Panel Content */}
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
            title="Failed to load operational decision queue"
          />
        )}

        {/* Loaded State */}
        {!isLoading && !error && (
          <div>
            {/* 1. Approvals Tab */}
            {activeTab === 'approvals' && (
              <div
                role="tabpanel"
                id="tabpanel-approvals"
                aria-labelledby="tab-approvals"
                className="space-y-3"
              >
                {pendingApprovals.length === 0 ? (
                  <EmptyState
                    title="No pending approvals"
                    message="There are no human approval gates currently pending operator review for this expedition."
                  />
                ) : (
                  pendingApprovals.map((item: DecisionApprovalItem) => (
                    <div
                      key={item.approval_id}
                      className="p-4 bg-slate-950/40 border border-slate-800 rounded-lg hover:border-slate-700 transition-colors space-y-3"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-cyan-400 font-semibold">
                              APPROVAL
                            </span>
                            <h3 className="text-sm font-semibold text-slate-100">
                              {item.recommendation_title}
                            </h3>
                          </div>
                          <div className="flex items-center gap-2 text-xs font-mono text-slate-400 mt-1">
                            <span>Role Required: {item.required_approver_role}</span>
                            <span>•</span>
                            <span>Options: {item.available_options_count}</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <StatusBadge status={item.status} />
                          <button
                            type="button"
                            onClick={() => handleOpenReview(item.recommendation_id)}
                            className="px-3 py-1 text-xs font-medium text-cyan-300 bg-cyan-950/60 border border-cyan-800 hover:bg-cyan-900/60 rounded flex items-center gap-1 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                          >
                            <span>Review & Decide</span>
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs font-mono bg-slate-900/60 p-2.5 rounded border border-slate-800/80">
                        <div>
                          <span className="text-slate-400">What Changed: </span>
                          <span className="text-slate-200">{item.what_changed}</span>
                        </div>
                        <div>
                          <span className="text-slate-400">Why It Matters: </span>
                          <span className="text-slate-200">{item.why_it_matters}</span>
                        </div>
                        <div className="md:col-span-2">
                          <span className="text-amber-400">Constraint Involved: </span>
                          <span className="text-slate-300">{item.what_constraint_is_involved}</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
                        <span>Approval ID: {item.approval_id}</span>
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          <span>{new Date(item.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* 2. Recommendations Tab */}
            {activeTab === 'recommendations' && (
              <div
                role="tabpanel"
                id="tabpanel-recommendations"
                aria-labelledby="tab-recommendations"
                className="space-y-3"
              >
                {pendingRecommendations.length === 0 ? (
                  <EmptyState
                    title="No pending recommendations"
                    message="There are no candidate operational recommendations requiring evaluation."
                  />
                ) : (
                  pendingRecommendations.map((item: DecisionRecommendationItem) => (
                    <div
                      key={item.recommendation_id}
                      className="p-4 bg-slate-950/40 border border-slate-800 rounded-lg hover:border-slate-700 transition-colors space-y-3"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-sky-400" />
                            <h3 className="text-sm font-semibold text-slate-100">
                              {item.title}
                            </h3>
                          </div>
                          {item.summary && (
                            <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
                              {item.summary}
                            </p>
                          )}
                        </div>

                        <div className="flex items-center gap-2">
                          <StatusBadge status={item.status} />
                          <StatusBadge status={item.approval_state} />
                          <button
                            type="button"
                            onClick={() => handleOpenReview(item.recommendation_id)}
                            className="px-3 py-1 text-xs font-medium text-sky-300 bg-sky-950/60 border border-sky-800 hover:bg-sky-900/60 rounded flex items-center gap-1 focus:outline-none focus:ring-1 focus:ring-sky-500"
                          >
                            <span>Review Recommendation</span>
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      {item.rationale && item.rationale.length > 0 && (
                        <div className="text-xs text-slate-300 bg-slate-900/60 p-2 rounded border border-slate-800/80">
                          <span className="text-slate-400 font-mono block mb-1">Rationale:</span>
                          <ul className="list-disc list-inside space-y-0.5">
                            {item.rationale.map((r, idx) => (
                              <li key={idx}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-400 pt-1 border-t border-slate-800/60">
                        <span>Affected entities: {item.what_is_affected.length}</span>
                        <span>Proposed changes: {item.proposed_changes.length}</span>
                        <div className="flex items-center gap-1 text-slate-500">
                          <Clock className="w-3 h-3" />
                          <span>{new Date(item.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* 3. Replans Tab */}
            {activeTab === 'replans' && (
              <div
                role="tabpanel"
                id="tabpanel-replans"
                aria-labelledby="tab-replans"
                className="space-y-3"
              >
                {pendingReplans.length === 0 ? (
                  <EmptyState
                    title="No pending replans"
                    message="No active replanning workflows are currently processing or awaiting approval."
                  />
                ) : (
                  pendingReplans.map((item: DecisionReplanItem) => (
                    <div
                      key={item.replan_id}
                      className="p-4 bg-slate-950/40 border border-slate-800 rounded-lg hover:border-slate-700 transition-colors space-y-3"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <GitPullRequest className="w-4 h-4 text-purple-400" />
                          <EntityCode code={item.replan_code} />
                          <span className="text-xs font-mono text-slate-400">
                            Mode: {item.trigger_mode}
                          </span>
                        </div>
                        <StatusBadge status={item.status} />
                      </div>

                      <div className="text-xs text-slate-300 bg-slate-900/60 p-2.5 rounded border border-slate-800/80 space-y-1">
                        <div>
                          <span className="text-slate-400 font-mono">What Changed: </span>
                          <span>{item.what_changed}</span>
                        </div>
                        {item.trigger_reason && (
                          <div>
                            <span className="text-slate-400 font-mono">Trigger: </span>
                            <span>{item.trigger_reason}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-400 pt-1 border-t border-slate-800/60">
                        <span>Affected entities: {item.affected_entities_count}</span>
                        <span className={item.violated_constraints_count > 0 ? 'text-amber-400' : ''}>
                          Violated constraints: {item.violated_constraints_count}
                        </span>
                        <div className="flex items-center gap-1 text-slate-500">
                          <Clock className="w-3 h-3" />
                          <span>{new Date(item.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Review Modal */}
      {selectedRecommendationId && (
        <ApprovalModal
          recommendationId={selectedRecommendationId}
          onClose={handleCloseReview}
          expeditionId={expeditionId}
        />
      )}
    </section>
  );
}
