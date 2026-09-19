import { useState, useEffect } from 'react';
import { X, CheckCircle, AlertTriangle, XCircle, ShieldCheck, ArrowRight } from 'lucide-react';
import { useRecommendation, useApprovalMutations } from '../hooks/useControlTower';
import { StatusBadge } from '../../../components/shared/StatusBadge';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../../components/shared/ErrorDisplay';
import type { ReplanApplyResult } from '../../../lib/types/api';

export interface ApprovalModalProps {
  recommendationId: string | null;
  onClose: () => void;
  expeditionId?: string;
}

export function ApprovalModal({
  recommendationId,
  onClose,
  expeditionId,
}: ApprovalModalProps) {
  const [operatorId, setOperatorId] = useState('');
  const [approverRole, setApproverRole] = useState('EXPEDITION_OPERATOR');
  const [comment, setComment] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [localApproved, setLocalApproved] = useState(false);
  const [localRejected, setLocalRejected] = useState(false);
  const [applyResult, setApplyResult] = useState<ReplanApplyResult | null>(null);

  const {
    data: recommendation,
    isLoading,
    error,
  } = useRecommendation(recommendationId);

  const { approveMutation, rejectMutation, applyMutation } =
    useApprovalMutations(expeditionId);

  // Reset local state on recommendation change
  useEffect(() => {
    setOperatorId('');
    setApproverRole('EXPEDITION_OPERATOR');
    setComment('');
    setValidationError(null);
    setLocalApproved(false);
    setLocalRejected(false);
    setApplyResult(null);
  }, [recommendationId]);

  // Keyboard accessibility: Escape to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!recommendationId) return null;

  const isApproved =
    localApproved ||
    recommendation?.approval_state === 'APPROVED';

  const isRejected =
    localRejected ||
    recommendation?.approval_state === 'REJECTED';

  const isApplied =
    Boolean(applyResult) ||
    recommendation?.status === 'APPLIED';

  const handleApprove = async () => {
    if (!operatorId.trim()) {
      setValidationError('Operator / Approver Person ID is required to approve this recommendation.');
      return;
    }
    setValidationError(null);

    try {
      await approveMutation.mutateAsync({
        recommendationId,
        payload: {
          approver_person_id: operatorId.trim(),
          approver_role: approverRole.trim() || undefined,
          decision: 'APPROVED',
          comment: comment.trim() || undefined,
        },
        expeditionId,
      });
      setLocalApproved(true);
    } catch {
      // Error captured by mutation state
    }
  };

  const handleReject = async () => {
    if (!operatorId.trim()) {
      setValidationError('Operator / Approver Person ID is required to reject this recommendation.');
      return;
    }
    setValidationError(null);

    try {
      await rejectMutation.mutateAsync({
        recommendationId,
        payload: {
          approver_person_id: operatorId.trim(),
          approver_role: approverRole.trim() || undefined,
          decision: 'REJECTED',
          comment: comment.trim() || undefined,
        },
        expeditionId,
      });
      setLocalRejected(true);
    } catch {
      // Error captured by mutation state
    }
  };

  const handleApply = async () => {
    if (!operatorId.trim()) {
      setValidationError('Actor Person ID is required to apply the approved recommendation.');
      return;
    }
    setValidationError(null);

    try {
      const result = await applyMutation.mutateAsync({
        recommendationId,
        payload: {
          actor_person_id: operatorId.trim(),
          comment: comment.trim() || undefined,
        },
        expeditionId,
      });
      setApplyResult(result);
    } catch {
      // Error captured by mutation state
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="approval-modal-title"
    >
      <div className="relative w-full max-w-3xl my-8 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <ShieldCheck className="w-5 h-5 text-cyan-400" aria-hidden="true" />
            <h2
              id="approval-modal-title"
              className="text-lg font-semibold text-slate-100 tracking-wide"
            >
              Operational Decision Review
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close review modal"
            className="p-1 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-500"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-300">
          {/* Loading */}
          {isLoading && (
            <div aria-busy="true" className="space-y-4">
              <LoadingSkeleton lines={4} />
              <LoadingSkeleton lines={6} />
            </div>
          )}

          {/* Error */}
          {error && (
            <ErrorDisplay
              error={error}
              title="Failed to load recommendation details"
            />
          )}

          {/* Content */}
          {!isLoading && !error && recommendation && (
            <>
              {/* Title & Metadata Header */}
              <div className="space-y-2 border-b border-slate-800 pb-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-xl font-bold text-slate-100">
                    {recommendation.title}
                  </h3>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={recommendation.status} />
                    <StatusBadge status={recommendation.approval_state} />
                    <ProvenanceTag provenance={recommendation.data_provenance} />
                  </div>
                </div>
                {recommendation.summary && (
                  <p className="text-sm text-slate-300 leading-relaxed">
                    {recommendation.summary}
                  </p>
                )}
                <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400 pt-1">
                  <span>REC ID: {recommendation.id}</span>
                  <span>REPLAN: {recommendation.replan_id}</span>
                  <span>
                    Generated: {new Date(recommendation.generated_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Operational Rationale */}
              {recommendation.rationale && recommendation.rationale.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
                    Operational Rationale
                  </h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-slate-200 bg-slate-950/40 p-3 rounded border border-slate-800">
                    {recommendation.rationale.map((point, idx) => (
                      <li key={idx} className="leading-relaxed">
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Proposed Changes */}
              {recommendation.proposed_changes && recommendation.proposed_changes.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
                    Proposed Domain Changes ({recommendation.proposed_changes.length})
                  </h4>
                  <div className="space-y-2">
                    {recommendation.proposed_changes.map((change, idx) => (
                      <div
                        key={idx}
                        className="bg-slate-950/40 border border-slate-800 rounded p-3 text-xs font-mono text-slate-300 space-y-1"
                      >
                        {typeof change === 'object' && change !== null ? (
                          Object.entries(change as Record<string, unknown>).map(
                            ([k, v]) => (
                              <div key={k} className="flex gap-2">
                                <span className="text-cyan-400 font-semibold">{k}:</span>
                                <span className="text-slate-200">{String(v)}</span>
                              </div>
                            ),
                          )
                        ) : (
                          <span>{String(change)}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Expected Operational Impact */}
              {recommendation.expected_impact &&
                Object.keys(recommendation.expected_impact).length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
                      Expected Impact
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-slate-950/40 border border-slate-800 rounded p-3 text-xs font-mono">
                      {Object.entries(recommendation.expected_impact).map(([k, v]) => (
                        <div key={k} className="space-y-0.5">
                          <span className="text-slate-400 font-medium capitalize">
                            {k.replace(/_/g, ' ')}:
                          </span>{' '}
                          <span className="text-slate-200 font-semibold">
                            {String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* Violated Constraints Addressed */}
              {recommendation.violated_constraints &&
                recommendation.violated_constraints.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-amber-400">
                      Addressed Constraint Violations (
                      {recommendation.violated_constraints.length})
                    </h4>
                    <div className="space-y-1.5">
                      {recommendation.violated_constraints.map((c, idx) => (
                        <div
                          key={idx}
                          className="bg-amber-950/20 border border-amber-900/50 rounded p-2.5 text-xs text-amber-200 flex items-start gap-2"
                        >
                          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                          <div>
                            {typeof c === 'object' && c !== null ? (
                              <span>
                                {String(
                                  (c as Record<string, unknown>).name ??
                                    (c as Record<string, unknown>).code ??
                                    JSON.stringify(c),
                                )}
                              </span>
                            ) : (
                              <span>{String(c)}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* ─── Governance State & Action Lifecycle ─── */}
              <div className="pt-4 border-t border-slate-800 space-y-4">
                {/* 1. Terminal State: APPLIED */}
                {isApplied && (
                  <div className="bg-emerald-950/40 border border-emerald-700/60 rounded-lg p-4 space-y-2">
                    <div className="flex items-center gap-2 text-emerald-300 font-semibold">
                      <CheckCircle className="w-5 h-5 text-emerald-400" />
                      <span>RECOMMENDATION APPLIED</span>
                    </div>
                    <p className="text-xs text-slate-300">
                      {applyResult?.message ??
                        'Operational changes have been successfully enacted across the expedition domain.'}
                    </p>
                    {applyResult?.applied_changes && (
                      <p className="text-xs font-mono text-emerald-400">
                        Mutations executed: {applyResult.applied_changes.length} change(s).
                      </p>
                    )}
                  </div>
                )}

                {/* 2. Terminal State: REJECTED */}
                {!isApplied && isRejected && (
                  <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-4 space-y-2">
                    <div className="flex items-center gap-2 text-slate-300 font-semibold">
                      <XCircle className="w-5 h-5 text-rose-400" />
                      <span>RECOMMENDATION REJECTED</span>
                    </div>
                    <p className="text-xs text-slate-400">
                      This operational recommendation was rejected by the operator and will not be applied.
                    </p>
                  </div>
                )}

                {/* 3. Intermediate State: APPROVED — READY TO APPLY */}
                {!isApplied && !isRejected && isApproved && (
                  <div className="space-y-4">
                    <div className="bg-emerald-950/30 border border-emerald-600/50 rounded-lg p-4 space-y-2">
                      <div className="flex items-center gap-2 text-emerald-300 font-bold text-sm">
                        <ShieldCheck className="w-5 h-5 text-emerald-400" />
                        <span>APPROVED — READY TO APPLY</span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        The recommendation has been formally approved by the human operator.
                        Operational domain state will remain unchanged until you explicitly enact the changes.
                      </p>
                    </div>

                    {/* Operator Identification for Application */}
                    <div className="space-y-3 bg-slate-950/50 p-4 rounded-lg border border-slate-800">
                      <div>
                        <label
                          htmlFor="apply-actor-person-id"
                          className="block text-xs font-mono text-slate-300 mb-1"
                        >
                          Executing Actor Person ID *
                        </label>
                        <input
                          id="apply-actor-person-id"
                          data-testid="apply-actor-person-id-input"
                          type="text"
                          value={operatorId}
                          onChange={(e) => setOperatorId(e.target.value)}
                          placeholder="e.g. PER-OPS-001 or Operator UUID"
                          className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                        />
                      </div>

                      {validationError && (
                        <p className="text-xs text-rose-400 font-medium">
                          {validationError}
                        </p>
                      )}

                      {applyMutation.error && (
                        <div className="bg-rose-950/40 border border-rose-800 rounded p-2.5 text-xs text-rose-300">
                          Application Failed: {applyMutation.error.message}.
                          <span className="block text-slate-400 mt-1">
                            The recommendation remains APPROVED. Execution can be retried once resolved.
                          </span>
                        </div>
                      )}

                      <div className="flex items-center justify-end gap-3 pt-2">
                        <button
                          type="button"
                          onClick={onClose}
                          className="px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded focus:outline-none focus:ring-2 focus:ring-slate-500"
                        >
                          Close Review
                        </button>
                        <button
                          type="button"
                          data-testid="apply-recommendation-btn"
                          onClick={handleApply}
                          disabled={applyMutation.isPending || !operatorId.trim()}
                          className="px-4 py-2 text-xs font-bold text-white bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed rounded shadow flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-cyan-400"
                        >
                          <span>
                            {applyMutation.isPending
                              ? 'Applying Operational Changes...'
                              : 'APPLY RECOMMENDATION'}
                          </span>
                          <ArrowRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* 4. Initial Phase: REVIEW / PENDING GOVERNANCE BOUNDARY */}
                {!isApplied && !isRejected && !isApproved && (
                  <div className="space-y-4 bg-slate-950/60 p-4 rounded-lg border border-slate-800">
                    <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-cyan-400" />
                      Human Operator Governance Boundary
                    </h4>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Operational decisions require explicit human approval. Approval will not automatically execute domain updates.
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label
                          htmlFor="approver-person-id"
                          className="block text-xs font-mono text-slate-300 mb-1"
                        >
                          Operator / Approver Person ID *
                        </label>
                        <input
                          id="approver-person-id"
                          data-testid="approver-person-id-input"
                          type="text"
                          value={operatorId}
                          onChange={(e) => setOperatorId(e.target.value)}
                          placeholder="e.g. PER-OPS-001 or Operator UUID"
                          className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                        />
                      </div>
                      <div>
                        <label
                          htmlFor="approver-role"
                          className="block text-xs font-mono text-slate-300 mb-1"
                        >
                          Approver Operational Role
                        </label>
                        <input
                          id="approver-role"
                          data-testid="approver-role-input"
                          type="text"
                          value={approverRole}
                          onChange={(e) => setApproverRole(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs font-mono text-slate-100 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label
                        htmlFor="approval-comment"
                        className="block text-xs font-mono text-slate-300 mb-1"
                      >
                        Operational Justification / Justification Comment
                      </label>
                      <textarea
                        id="approval-comment"
                        data-testid="approval-comment-input"
                        rows={2}
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        placeholder="State reason for decision or operational constraints noted..."
                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                      />
                    </div>

                    {validationError && (
                      <p className="text-xs text-rose-400 font-medium">
                        {validationError}
                      </p>
                    )}

                    {approveMutation.error && (
                      <p className="text-xs text-rose-400 font-medium bg-rose-950/40 p-2 rounded border border-rose-900">
                        Approval Failed: {approveMutation.error.message}
                      </p>
                    )}

                    {rejectMutation.error && (
                      <p className="text-xs text-rose-400 font-medium bg-rose-950/40 p-2 rounded border border-rose-900">
                        Rejection Failed: {rejectMutation.error.message}
                      </p>
                    )}

                    {/* Review Actions */}
                    <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                      <button
                        type="button"
                        onClick={onClose}
                        className="px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded focus:outline-none focus:ring-2 focus:ring-slate-500"
                      >
                        Cancel
                      </button>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          data-testid="reject-recommendation-btn"
                          onClick={handleReject}
                          disabled={
                            rejectMutation.isPending ||
                            approveMutation.isPending ||
                            !operatorId.trim()
                          }
                          className="px-3 py-1.5 text-xs font-medium text-white bg-rose-800 hover:bg-rose-700 disabled:opacity-50 disabled:cursor-not-allowed rounded focus:outline-none focus:ring-2 focus:ring-rose-500"
                        >
                          {rejectMutation.isPending
                            ? 'Rejecting...'
                            : 'Reject Recommendation'}
                        </button>
                        <button
                          type="button"
                          data-testid="approve-recommendation-btn"
                          onClick={handleApprove}
                          disabled={
                            approveMutation.isPending ||
                            rejectMutation.isPending ||
                            !operatorId.trim()
                          }
                          className="px-4 py-1.5 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed rounded shadow focus:outline-none focus:ring-2 focus:ring-emerald-400"
                        >
                          {approveMutation.isPending
                            ? 'Approving...'
                            : 'Approve Recommendation'}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/50 flex items-center justify-between text-xs font-mono text-slate-500">
          <span>Human Governance Invariant: Approval ≠ Application</span>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
