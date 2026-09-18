import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { StockAvailability } from '../../lib/types/api';

interface Props {
  availability: StockAvailability | null | undefined;
  className?: string;
}

export function AvailabilityIndicator({ availability, className = '' }: Props) {
  if (!availability) {
    return (
      <div className={`p-4 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 text-sm ${className}`}>
        No availability metrics recorded.
      </div>
    );
  }

  const {
    on_hand_quantity,
    reserved_quantity,
    quarantined_quantity,
    damaged_quantity,
    available_quantity,
    reorder_point,
    is_deficit,
  } = availability;

  const availableNum = parseFloat(available_quantity) || 0;
  const isZero = availableNum <= 0;

  return (
    <div className={`p-4 rounded-lg bg-slate-900/80 border ${is_deficit ? 'border-rose-700/60 bg-rose-950/20' : 'border-slate-800'} ${className}`}>
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Authoritative Availability
          </span>
          {is_deficit ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-rose-900/60 text-rose-200 border border-rose-600">
              <AlertTriangle className="w-3 h-3" aria-hidden="true" />
              DEFICIT
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-emerald-900/40 text-emerald-300 border border-emerald-700">
              <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
              STOCKED
            </span>
          )}
        </div>

        <div className="text-right">
          <span className="text-xs font-mono text-slate-400 mr-2">Available:</span>
          <span className={`text-xl font-bold font-mono ${isZero ? 'text-rose-400' : 'text-emerald-400'}`}>
            {available_quantity}
          </span>
        </div>
      </div>

      {/* Grid of stock components */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        <div className="p-2 rounded bg-slate-950/60 border border-slate-800/80">
          <div className="text-slate-400 text-[11px]">On-Hand</div>
          <div className="text-slate-100 font-semibold text-sm mt-0.5">{on_hand_quantity}</div>
        </div>
        <div className="p-2 rounded bg-slate-950/60 border border-slate-800/80">
          <div className="text-slate-400 text-[11px]">Reserved</div>
          <div className="text-amber-300 font-semibold text-sm mt-0.5">{reserved_quantity}</div>
        </div>
        <div className="p-2 rounded bg-slate-950/60 border border-slate-800/80">
          <div className="text-slate-400 text-[11px]">Quarantined</div>
          <div className="text-orange-400 font-semibold text-sm mt-0.5">{quarantined_quantity}</div>
        </div>
        <div className="p-2 rounded bg-slate-950/60 border border-slate-800/80">
          <div className="text-slate-400 text-[11px]">Damaged</div>
          <div className="text-rose-400 font-semibold text-sm mt-0.5">{damaged_quantity}</div>
        </div>
      </div>

      {reorder_point && (
        <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400 font-mono">
          <span>Reorder Threshold:</span>
          <span className="font-semibold text-slate-300">{reorder_point}</span>
        </div>
      )}

      <p className="mt-2 text-[10px] text-slate-500 font-mono">
        Backend formula: available = on_hand - reserved - quarantined - damaged
      </p>
    </div>
  );
}
