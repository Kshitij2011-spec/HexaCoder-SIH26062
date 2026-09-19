import { useState, useEffect } from 'react';
import { apiClient } from '../../../lib/api/client';
import {
  Sparkles,
  X,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Coins,
  ShieldCheck,
  ArrowUpRight,
  RotateCcw,
  GitPullRequest,
  ListChecks,
} from 'lucide-react';
import { EntityCode } from '../../../components/shared/EntityCode';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { useReplan, useGenerateOptions } from '../hooks/useControlTower';
import type {
  OptionFeasibility,
  ReplanOptionRead,
  RecommendationRead,
} from '../../../lib/types/api';

export interface MitigationOptionsExplorerProps {
  isOpen: boolean;
  onClose: () => void;
  replanId: string | null;
  expeditionId: string;
  onSelectRecommendation: (recommendationId: string) => void;
}

const FEASIBILITY_STYLES: Record<
  OptionFeasibility | string,
  { label: string; badgeClass: string; icon: React.ComponentType<{ className?: string }> }
> = {
  FEASIBLE: {
    label: 'FEASIBLE',
    badgeClass: 'bg-emerald-950/80 text-emerald-300 border-emerald-600',
    icon: CheckCircle2,
  },
  CONSTRAINED: {
    label: 'CONSTRAINED',
    badgeClass: 'bg-amber-950/80 text-amber-300 border-amber-600',
    icon: AlertTriangle,
  },
  NOT_EVALUABLE: {
    label: 'NOT EVALUABLE',
    badgeClass: 'bg-slate-800 text-slate-300 border-slate-600',
    icon: Clock,
  },
  INFEASIBLE: {
    label: 'INFEASIBLE',
    badgeClass: 'bg-rose-950/80 text-rose-300 border-rose-600',
    icon: AlertTriangle,
  },
};

export function MitigationOptionsExplorer({
  isOpen,
  onClose,
  replanId,
  expeditionId,
  onSelectRecommendation,
}: MitigationOptionsExplorerProps) {
  const [generatedOptions, setGeneratedOptions] = useState<ReplanOptionRead[] | null>(null);
  const [generatedRecs, setGeneratedRecs] = useState<RecommendationRead[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: replan, isLoading } = useReplan(replanId);
  const generateMutation = useGenerateOptions(expeditionId);

  useEffect(() => {
    setGeneratedOptions(null);
    setGeneratedRecs(null);
    setError(null);
  }, [replanId]);

  useEffect(() => {
    if (isOpen && replanId && replan?.status === 'OPTIONS_READY' && generatedOptions === null) {
      Promise.all([
        apiClient.get<ReplanOptionRead[]>(`/replans/${replanId}/options`).catch(() => []),
        apiClient.get<RecommendationRead[]>(`/replans/${replanId}/recommendations`).catch(() => []),
      ]).then(([opts, recs]) => {
        if (opts && opts.length > 0) setGeneratedOptions(opts);
        if (recs && recs.length > 0) setGeneratedRecs(recs);
      });
    }
  }, [isOpen, replanId, replan?.status, generatedOptions]);

  if (!isOpen || !replanId) return null;

  const handleGenerate = () => {
    setError(null);
    generateMutation.mutate(
      { replanId, expeditionId },
      {
        onSuccess: (res) => {
          setGeneratedOptions(res.options);
          setGeneratedRecs(res.recommendations);
        },
        onError: (err) => {
          setError(err instanceof Error ? err.message : 'Option generation failed');
        },
      },
    );
  };

  const options = generatedOptions ?? [];
  const recommendations = generatedRecs ?? [];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="mitigation-options-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
    >
      <div className="w-full max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-800 rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-sky-950/50 border border-sky-800/60 text-sky-400">
              <Sparkles className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h3 id="mitigation-options-title" className="text-base font-bold text-slate-100 font-mono">
                  Candidate Mitigation Options Explorer
                </h3>
                <ProvenanceTag provenance="DERIVED" />
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic candidates evaluated against hard & soft polar constraints
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

        {/* Modal Scrollable Content */}
        <div className="p-5 overflow-y-auto space-y-5 flex-1">
          {/* Replan Summary Banner */}
          {isLoading && <LoadingSkeleton lines={3} />}
          {replan && (
            <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <GitPullRequest className="w-4 h-4 text-purple-400" />
                  <EntityCode code={replan.replan_code} />
                  <span className="font-mono text-slate-400 font-medium">
                    Status: <span className="text-slate-200">{replan.status}</span>
                  </span>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  {new Date(replan.created_at).toLocaleString()}
                </span>
              </div>
              {replan.trigger_reason && (
                <div className="text-slate-300 font-sans">
                  <span className="font-mono text-slate-400 font-semibold">Trigger Reason: </span>
                  {replan.trigger_reason}
                </div>
              )}
            </div>
          )}

          {/* Action to Generate Options if not already done */}
          <div className="flex items-center justify-between gap-3 p-3 bg-slate-950/40 border border-slate-800 rounded-lg">
            <div>
              <div className="text-xs font-semibold text-slate-200">
                Deterministic Constraint-Checked Options
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">
                Generates candidate operational options and synthesizes human-governed recommendations.
              </div>
            </div>
            <button
              type="button"
              data-testid="generate-options-btn"
              disabled={generateMutation.isPending}
              onClick={handleGenerate}
              className="px-3.5 py-1.5 text-xs font-semibold font-mono bg-sky-600 hover:bg-sky-500 text-slate-950 rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
            >
              {generateMutation.isPending ? (
                <>
                  <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                  <span>Evaluating...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{options.length > 0 ? 'Regenerate Options' : 'Generate Options'}</span>
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="p-3 rounded bg-rose-950/30 border border-rose-900/60 text-xs text-rose-300 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Options List */}
          {options.length > 0 && (
            <div className="space-y-4">
              <h4 className="text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <ListChecks className="w-4 h-4 text-sky-400" />
                <span>Evaluated Mitigation Options ({options.length})</span>
              </h4>

              <div className="grid grid-cols-1 gap-3.5">
                {options.map((opt) => {
                  const feasConfig = FEASIBILITY_STYLES[opt.feasibility] ?? FEASIBILITY_STYLES.NOT_EVALUABLE;
                  const FeasIcon = feasConfig.icon;

                  // Find recommendation matching this option
                  const matchingRec = recommendations.find(
                    (r) => r.option_id === opt.id || (!r.option_id && options[0]?.id === opt.id)
                  );

                  return (
                    <div
                      key={opt.id}
                      data-testid={`mitigation-option-card-${opt.option_code.toLowerCase()}`}
                      className="p-4 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-colors space-y-3"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2.5">
                          <EntityCode code={opt.option_code} />
                          <span className="text-xs font-semibold text-slate-100 font-sans">
                            {opt.title}
                          </span>
                        </div>
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${feasConfig.badgeClass}`}
                        >
                          <FeasIcon className="w-3 h-3" />
                          <span>{feasConfig.label}</span>
                        </span>
                      </div>

                      <p className="text-xs text-slate-300 font-sans leading-relaxed">
                        {opt.description}
                      </p>

                      {/* Tradeoffs & Metrics */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/80 text-[11px] font-mono">
                        <div className="p-2 rounded bg-slate-900 border border-slate-800">
                          <span className="text-slate-500 block">Delay Impact</span>
                          <span className="font-semibold text-slate-200 flex items-center gap-1 mt-0.5">
                            <Clock className="w-3 h-3 text-amber-400" />
                            {opt.estimated_delay_hours > 0 ? `+${opt.estimated_delay_hours} hrs` : '0 hrs'}
                          </span>
                        </div>
                        <div className="p-2 rounded bg-slate-900 border border-slate-800">
                          <span className="text-slate-500 block">Cost Delta</span>
                          <span className="font-semibold text-slate-200 flex items-center gap-1 mt-0.5">
                            <Coins className="w-3 h-3 text-cyan-400" />
                            {opt.estimated_cost_delta > 0 ? `+$${opt.estimated_cost_delta.toLocaleString()}` : '$0'}
                          </span>
                        </div>
                        <div className="p-2 rounded bg-slate-900 border border-slate-800">
                          <span className="text-slate-500 block">Action Type</span>
                          <span className="font-semibold text-slate-200 mt-0.5 block truncate">
                            {opt.action_type}
                          </span>
                        </div>
                        <div className="p-2 rounded bg-slate-900 border border-slate-800">
                          <span className="text-slate-500 block">Risk Score</span>
                          <span className="font-semibold text-slate-200 mt-0.5 block">
                            {opt.risk_score} / 100
                          </span>
                        </div>
                      </div>

                      {/* Assumptions */}
                      {opt.assumptions && opt.assumptions.length > 0 && (
                        <div className="text-[11px] text-slate-400 font-sans">
                          <span className="font-mono text-slate-500 font-semibold">Assumptions: </span>
                          {opt.assumptions.join('; ')}
                        </div>
                      )}

                      {/* Recommendation Action Button */}
                      {matchingRec && (
                        <div className="pt-2 flex items-center justify-between gap-3 border-t border-slate-800/80">
                          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                            <ShieldCheck className="w-4 h-4 text-cyan-400" />
                            <span>Synthesized Recommendation:</span>
                            <span className="text-slate-200 font-sans font-medium">
                              {matchingRec.title}
                            </span>
                          </div>
                          <button
                            type="button"
                            data-testid={`select-recommendation-${matchingRec.id}`}
                            onClick={() => {
                              onClose();
                              onSelectRecommendation(matchingRec.id);
                            }}
                            className="px-3 py-1.5 text-xs font-semibold font-mono bg-cyan-600 hover:bg-cyan-500 text-slate-950 rounded-lg transition-colors flex items-center gap-1.5 shrink-0 shadow-sm"
                          >
                            <span>Review & Decide</span>
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-end shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            Close Explorer
          </button>
        </div>
      </div>
    </div>
  );
}
