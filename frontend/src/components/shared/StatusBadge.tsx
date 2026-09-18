import type { LocationStatus } from '../../lib/types/api';
import type { CargoStatus, CargoRiskLevel, CargoPackageStatus, TransportStatus } from '../../lib/types/api';

type AnyStatus = LocationStatus | CargoStatus | CargoRiskLevel | CargoPackageStatus | TransportStatus | string;

const STATUS_STYLES: Record<string, string> = {
  // Location
  AVAILABLE:    'bg-emerald-900/50 text-emerald-300 border border-emerald-700',
  RESTRICTED:   'bg-amber-900/50 text-amber-300 border border-amber-700',
  INACCESSIBLE: 'bg-rose-900/50 text-rose-300 border border-rose-700',
  CLOSED:       'bg-slate-700/50 text-slate-400 border border-slate-600',
  // Transport
  PLANNED:      'bg-sky-900/50 text-sky-300 border border-sky-700',
  BOOKED:       'bg-blue-900/50 text-blue-300 border border-blue-700',
  READY:        'bg-emerald-900/50 text-emerald-300 border border-emerald-700',
  DEPARTED:     'bg-cyan-900/50 text-cyan-300 border border-cyan-700',
  IN_TRANSIT:   'bg-cyan-900/50 text-cyan-300 border border-cyan-700',
  ARRIVED:      'bg-emerald-900/50 text-emerald-300 border border-emerald-700',
  DELAYED:      'bg-amber-900/50 text-amber-300 border border-amber-700',
  DIVERTED:     'bg-orange-900/50 text-orange-300 border border-orange-700',
  CANCELLED:    'bg-slate-700/50 text-slate-400 border border-slate-600',
  // Cargo
  REQUESTED:    'bg-sky-900/50 text-sky-300 border border-sky-700',
  DECLARED:     'bg-blue-900/50 text-blue-300 border border-blue-700',
  APPROVED:     'bg-emerald-900/50 text-emerald-300 border border-emerald-700',
  PACKED:       'bg-teal-900/50 text-teal-300 border border-teal-700',
  DISPATCHED:   'bg-cyan-900/50 text-cyan-300 border border-cyan-700',
  RECEIVED:     'bg-emerald-900/50 text-emerald-300 border border-emerald-700',
  HELD:         'bg-amber-900/50 text-amber-300 border border-amber-700',
  DAMAGED:      'bg-rose-900/50 text-rose-300 border border-rose-700',
  LOST:         'bg-rose-900/60 text-rose-200 border border-rose-600',
  REJECTED:     'bg-slate-700/50 text-slate-400 border border-slate-600',
  // Risk & Severity
  NOMINAL:      'bg-emerald-900/50 text-emerald-300 border border-emerald-700',
  MODERATE:     'bg-amber-900/50 text-amber-300 border border-amber-700',
  ELEVATED:     'bg-orange-900/50 text-orange-300 border border-orange-700',
  LOW:          'bg-slate-700/50 text-slate-300 border border-slate-600',
  MEDIUM:       'bg-amber-900/50 text-amber-300 border border-amber-700',
  HIGH:         'bg-orange-900/50 text-orange-300 border border-orange-700',
  CRITICAL:     'bg-rose-900/60 text-rose-200 border border-rose-600',
  // Package
  LOADED:       'bg-cyan-900/50 text-cyan-300 border border-cyan-700',
  ISSUED:       'bg-teal-900/50 text-teal-300 border border-teal-700',
  RETURNED:     'bg-slate-700/50 text-slate-400 border border-slate-600',
  QUARANTINED:  'bg-amber-900/50 text-amber-300 border border-amber-700',
  // Inventory
  ON_ORDER:     'bg-blue-900/50 text-blue-300 border border-blue-700',
  INBOUND:      'bg-cyan-900/50 text-cyan-300 border border-cyan-700',
  RESERVED:     'bg-indigo-900/50 text-indigo-300 border border-indigo-700',
  CONSUMED:     'bg-purple-900/50 text-purple-300 border border-purple-700',
  TRANSFERRED:  'bg-violet-900/50 text-violet-300 border border-violet-700',
  DISPOSED:     'bg-zinc-800 text-zinc-400 border border-zinc-600',
  // Asset
  IN_USE:       'bg-blue-900/50 text-blue-300 border border-blue-700',
  MAINTENANCE:  'bg-amber-900/50 text-amber-300 border border-amber-700',
  RETIRED:      'bg-zinc-800 text-zinc-400 border border-zinc-600',
  OPERATIONAL:  'bg-emerald-900/50 text-emerald-300 border border-emerald-700',
  DEGRADED:     'bg-amber-900/50 text-amber-300 border border-amber-700',
  INOPERABLE:   'bg-rose-900/60 text-rose-200 border border-rose-600',
  // Maintenance Record
  SCHEDULED:    'bg-sky-900/50 text-sky-300 border border-sky-700',
  IN_PROGRESS:  'bg-amber-900/50 text-amber-300 border border-amber-700',
  OVERDUE:      'bg-rose-900/60 text-rose-200 border border-rose-600',
  COMPLETED:    'bg-emerald-900/50 text-emerald-300 border border-emerald-700',
  // Incident Lifecycle
  OPEN:         'bg-rose-900/50 text-rose-300 border border-rose-700',
  ACKNOWLEDGED: 'bg-amber-900/50 text-amber-300 border border-amber-700',
  MITIGATING:   'bg-indigo-900/50 text-indigo-300 border border-indigo-700',
};

interface Props {
  status: AnyStatus;
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label, className = '' }: Props) {
  const style = STATUS_STYLES[status] ?? 'bg-slate-700/50 text-slate-300 border border-slate-600';
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium tracking-wide ${style} ${className}`}
      role="status"
      aria-label={`Status: ${label ?? status}`}
    >
      {label ?? status}
    </span>
  );
}
