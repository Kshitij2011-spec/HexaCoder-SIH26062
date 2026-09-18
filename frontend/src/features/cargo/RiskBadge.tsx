import type { CargoRiskLevel } from '../../lib/types/api';

interface Props {
  level: CargoRiskLevel;
  className?: string;
}

const RISK_STYLES: Record<CargoRiskLevel, { bg: string; text: string; border: string; dot: string }> = {
  NOMINAL:  { bg: 'bg-emerald-950/50', border: 'border-emerald-800/60', text: 'text-emerald-300', dot: 'bg-emerald-400' },
  MODERATE: { bg: 'bg-amber-950/50',   border: 'border-amber-800/60',   text: 'text-amber-300',   dot: 'bg-amber-400'   },
  ELEVATED: { bg: 'bg-orange-950/50',  border: 'border-orange-800/60',  text: 'text-orange-300',  dot: 'bg-orange-400'  },
  CRITICAL: { bg: 'bg-rose-950/50',    border: 'border-rose-800/60',    text: 'text-rose-300',    dot: 'bg-rose-400'    },
};

export function RiskBadge({ level, className = '' }: Props) {
  const style = RISK_STYLES[level] ?? {
    bg: 'bg-slate-900/50',
    border: 'border-slate-700',
    text: 'text-slate-400',
    dot: 'bg-slate-400',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono font-medium border ${style.bg} ${style.border} ${style.text} ${className}`}
      aria-label={`Risk level: ${level}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} aria-hidden="true" />
      {level}
    </span>
  );
}
