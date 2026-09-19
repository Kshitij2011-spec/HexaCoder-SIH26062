import { useState } from 'react';
import {
  AlertOctagon,
  Plane,
  Zap,
  ThermometerSnowflake,
  RotateCcw,
  CheckCircle2,
  X,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { EntityCode } from '../../../components/shared/EntityCode';
import { useInjectScenario } from '../hooks/useControlTower';
import type { BenchmarkScenarioKey, ScenarioInjectResult } from '../../../lib/types/api';

export interface ScenarioCockpitBannerProps {
  expeditionId: string;
}

interface ScenarioButtonConfig {
  key: BenchmarkScenarioKey;
  label: string;
  sublabel: string;
  icon: React.ComponentType<{ className?: string }>;
  colorClasses: string;
  hoverClasses: string;
  ringClass: string;
}

const SCENARIOS: ScenarioButtonConfig[] = [
  {
    key: 'FLIGHT_GROUNDING',
    label: 'Flight Grounding',
    sublabel: 'Air transport delay (+5d blizzard grounding)',
    icon: Plane,
    colorClasses: 'bg-indigo-950/70 border-indigo-700/60 text-indigo-200',
    hoverClasses: 'hover:bg-indigo-900/80 hover:border-indigo-500',
    ringClass: 'focus:ring-indigo-500',
  },
  {
    key: 'GENERATOR_FAILURE',
    label: 'Generator Failure',
    sublabel: 'Life-support generator engine seizure (DAMAGED)',
    icon: Zap,
    colorClasses: 'bg-amber-950/70 border-amber-700/60 text-amber-200',
    hoverClasses: 'hover:bg-amber-900/80 hover:border-amber-500',
    ringClass: 'focus:ring-amber-500',
  },
  {
    key: 'COLD_CHAIN_EXCURSION',
    label: 'Cold-Chain Excursion',
    sublabel: 'Thermal breach (+8.2°C) → quarantine hold',
    icon: ThermometerSnowflake,
    colorClasses: 'bg-cyan-950/70 border-cyan-700/60 text-cyan-200',
    hoverClasses: 'hover:bg-cyan-900/80 hover:border-cyan-500',
    ringClass: 'focus:ring-cyan-500',
  },
];

export function ScenarioCockpitBanner({ expeditionId }: ScenarioCockpitBannerProps) {
  const [lastResult, setLastResult] = useState<ScenarioInjectResult | null>(null);
  const [activeScenarioKey, setActiveScenarioKey] = useState<BenchmarkScenarioKey | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const injectMutation = useInjectScenario(expeditionId);

  const handleInject = (scenarioKey: BenchmarkScenarioKey) => {
    setActiveScenarioKey(scenarioKey);
    setErrorMessage(null);

    injectMutation.mutate(
      {
        scenario_key: scenarioKey,
        expedition_id: expeditionId,
      },
      {
        onSuccess: (result) => {
          setLastResult(result);
          setActiveScenarioKey(null);
        },
        onError: (err) => {
          setErrorMessage(err instanceof Error ? err.message : 'Scenario injection failed');
          setActiveScenarioKey(null);
        },
      },
    );
  };

  return (
    <section
      aria-label="Polar Disruption Scenario Cockpit"
      className="rounded-lg bg-gradient-to-r from-slate-900 via-slate-900/95 to-slate-950 border border-slate-800 shadow-md overflow-hidden"
    >
      <div className="p-4 sm:p-5 border-b border-slate-800/80">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-rose-950/50 border border-rose-800/60 text-rose-400">
              <AlertOctagon className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider font-mono">
                  Polar Disruption Simulation Cockpit
                </h2>
                <ProvenanceTag provenance="SYNTHETIC_DEMO" />
              </div>
              <p className="text-xs text-slate-400 mt-0.5 font-sans">
                Inject deterministic operational shocks to test dependency propagation, constraint
                solver, and human governance loop.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400 bg-slate-950/60 px-3 py-1.5 rounded border border-slate-800 self-start sm:self-auto">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span>Autonomous Replanning Prohibited (Rule 4)</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
          {SCENARIOS.map((sc) => {
            const Icon = sc.icon;
            const isInjecting = injectMutation.isPending && activeScenarioKey === sc.key;
            return (
              <button
                key={sc.key}
                type="button"
                data-testid={`scenario-btn-${sc.key.toLowerCase()}`}
                disabled={injectMutation.isPending}
                onClick={() => handleInject(sc.key)}
                className={`flex items-start gap-3 p-3 rounded-lg border text-left transition-all focus:outline-none focus:ring-2 ${sc.ringClass} ${sc.colorClasses} ${sc.hoverClasses} disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <div className="mt-0.5 p-1.5 rounded bg-black/20">
                  {isInjecting ? (
                    <RotateCcw className="w-4 h-4 animate-spin text-slate-300" />
                  ) : (
                    <Icon className="w-4 h-4" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold tracking-wide flex items-center justify-between">
                    <span>{sc.label}</span>
                    {isInjecting && (
                      <span className="text-[10px] uppercase font-mono text-cyan-400">
                        Injecting...
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-400 truncate mt-0.5 font-sans">
                    {sc.sublabel}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Result Notification Banner */}
      {lastResult && (
        <div
          data-testid="scenario-result-banner"
          className="p-3.5 bg-cyan-950/30 border-t border-cyan-900/60 flex items-start justify-between gap-3 text-xs text-cyan-200 animate-in fade-in duration-200"
        >
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold flex items-center gap-2">
                <span>Disruption Injected: {lastResult.scenario_key}</span>
                <span className="text-[11px] font-mono text-slate-400">
                  Affected: {lastResult.affected_entity_type} (<EntityCode code={lastResult.affected_entity_code} />)
                </span>
              </div>
              <p className="mt-0.5 text-cyan-300/90 font-sans">{lastResult.summary}</p>
              <div className="mt-1 text-[11px] font-mono text-slate-400 flex items-center gap-3">
                {lastResult.trigger_event_id && (
                  <span>Event ID: {lastResult.trigger_event_id.slice(0, 8)}...</span>
                )}
                <span>Notice: Impact calculated; operator must initiate replan if required.</span>
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setLastResult(null)}
            className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800 transition-colors"
            aria-label="Dismiss banner"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Error Message Banner */}
      {errorMessage && (
        <div
          data-testid="scenario-error-banner"
          className="p-3.5 bg-rose-950/30 border-t border-rose-900/60 flex items-start justify-between gap-3 text-xs text-rose-200"
        >
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Scenario Injection Warning: </span>
              <span className="font-sans">{errorMessage}</span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800 transition-colors"
            aria-label="Dismiss error"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </section>
  );
}
