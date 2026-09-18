import { AlertOctagon, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import type { IncidentSeverity } from '../../lib/types/api';

interface Props {
  severity: IncidentSeverity;
  className?: string;
}

export function IncidentSeverityBadge({ severity, className = '' }: Props) {
  let icon = <Info className="w-3.5 h-3.5" aria-hidden="true" />;
  let style = 'bg-slate-800 text-slate-300 border-slate-700';

  switch (severity) {
    case 'CRITICAL':
      icon = <AlertOctagon className="w-3.5 h-3.5 text-rose-400" aria-hidden="true" />;
      style = 'bg-rose-950/80 text-rose-200 border-rose-600 font-bold';
      break;
    case 'HIGH':
      icon = <AlertTriangle className="w-3.5 h-3.5 text-orange-400" aria-hidden="true" />;
      style = 'bg-orange-950/70 text-orange-200 border-orange-600 font-semibold';
      break;
    case 'MEDIUM':
      icon = <AlertCircle className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />;
      style = 'bg-amber-950/60 text-amber-200 border-amber-600';
      break;
    case 'LOW':
      icon = <Info className="w-3.5 h-3.5 text-slate-400" aria-hidden="true" />;
      style = 'bg-slate-800 text-slate-300 border-slate-700';
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono border ${style} ${className}`}
      role="status"
      aria-label={`Severity: ${severity}`}
    >
      {icon}
      <span>{severity}</span>
    </span>
  );
}
