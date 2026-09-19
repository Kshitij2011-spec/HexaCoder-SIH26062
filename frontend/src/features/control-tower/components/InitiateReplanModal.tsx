import { useState, useEffect } from 'react';
import { RotateCcw, X, AlertTriangle, GitPullRequest } from 'lucide-react';
import { EntityCode } from '../../../components/shared/EntityCode';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { useInitiateReplan } from '../hooks/useControlTower';

export interface InitiateReplanModalProps {
  isOpen: boolean;
  onClose: () => void;
  expeditionId: string;
  missionId?: string | null;
  missionCode?: string | null;
  missionTitle?: string | null;
  constraintCode?: string | null;
  initialReason?: string;
  onReplanCreated: (replanId: string) => void;
}

export function InitiateReplanModal({
  isOpen,
  onClose,
  expeditionId,
  missionId,
  missionCode,
  missionTitle,
  constraintCode,
  initialReason,
  onReplanCreated,
}: InitiateReplanModalProps) {
  const [reason, setReason] = useState(initialReason ?? '');
  const [error, setError] = useState<string | null>(null);

  const initiateMutation = useInitiateReplan(expeditionId);

  useEffect(() => {
    if (initialReason) {
      setReason(initialReason);
    } else if (missionCode) {
      setReason(`Operational disruption affecting mission ${missionCode}; replanning required.`);
    } else if (constraintCode) {
      setReason(`Hard constraint violation (${constraintCode}); operational replanning required.`);
    } else {
      setReason('Operational replanning initiated by station operator.');
    }
  }, [initialReason, missionCode, constraintCode, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError('A valid operational reason is required to initiate replanning.');
      return;
    }

    setError(null);
    initiateMutation.mutate(
      {
        trigger_mode: 'OPERATOR_REQUESTED',
        expedition_id: expeditionId,
        mission_id: missionId || undefined,
        reason: reason.trim(),
      },
      {
        onSuccess: (created) => {
          onClose();
          onReplanCreated(created.id);
        },
        onError: (err) => {
          setError(err instanceof Error ? err.message : 'Failed to initiate replan request');
        },
      },
    );
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="initiate-replan-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
    >
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-950/50 border border-amber-800/60 text-amber-400">
              <RotateCcw className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 id="initiate-replan-title" className="text-base font-bold text-slate-100">
                  Initiate Operational Replan
                </h3>
                <ProvenanceTag provenance="ADVISORY" />
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Explicit human request for deterministic mitigation option generation
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* Target Context */}
          {(missionCode || constraintCode) && (
            <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800 text-xs space-y-1">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">
                Target Disruption Context:
              </span>
              {missionCode && (
                <div className="flex items-center gap-2 text-slate-200">
                  <span className="text-slate-400">Mission:</span>
                  <EntityCode code={missionCode} />
                  {missionTitle && <span className="text-slate-300 font-sans truncate">— {missionTitle}</span>}
                </div>
              )}
              {constraintCode && (
                <div className="flex items-center gap-2 text-amber-300">
                  <span className="text-slate-400">Violated Constraint:</span>
                  <span className="font-mono font-semibold">{constraintCode}</span>
                </div>
              )}
            </div>
          )}

          {/* Reason Input */}
          <div>
            <label
              htmlFor="replan-reason-input"
              className="block text-xs font-mono font-medium text-slate-300 uppercase tracking-wider mb-1.5"
            >
              Operational Justification / Disruption Summary *
            </label>
            <textarea
              id="replan-reason-input"
              data-testid="replan-reason-input"
              rows={4}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Detail why operational replanning is requested and what disruption triggered this..."
              className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 font-sans"
              required
            />
          </div>

          {error && (
            <div
              data-testid="initiate-replan-error"
              className="p-3 rounded bg-rose-950/30 border border-rose-900/60 text-xs text-rose-300 flex items-start gap-2"
            >
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Modal Actions */}
          <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              data-testid="submit-initiate-replan"
              disabled={initiateMutation.isPending}
              className="px-4 py-2 text-xs font-mono font-semibold bg-amber-600 hover:bg-amber-500 text-slate-950 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
            >
              {initiateMutation.isPending ? (
                <>
                  <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                  <span>Initiating...</span>
                </>
              ) : (
                <>
                  <GitPullRequest className="w-3.5 h-3.5" />
                  <span>Create Replan Request</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
