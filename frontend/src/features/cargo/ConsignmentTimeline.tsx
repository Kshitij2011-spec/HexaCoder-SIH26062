import { Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useConsignmentTimeline } from './hooks/useConsignmentTimeline';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { RiskBadge } from './RiskBadge';

interface Props {
  consignmentId: string;
}

export function ConsignmentTimeline({ consignmentId }: Props) {
  const { data: timeline, isLoading, error } = useConsignmentTimeline(consignmentId);

  if (isLoading) {
    return <LoadingSkeleton lines={4} />;
  }

  if (error) {
    return <ErrorDisplay error={error} title="Failed to load timeline" />;
  }

  if (!timeline) {
    return null;
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short',
      });
    } catch {
      return dateStr;
    }
  };

  const bufferHours = timeline.buffer_hours;
  const isNegativeBuffer = bufferHours !== null && bufferHours < 0;

  return (
    <div className="space-y-4">
      {/* Alert Banner if delayed */}
      {timeline.is_delayed && (
        <div
          role="alert"
          className="flex items-start gap-3 p-3.5 rounded-lg border border-rose-800/70 bg-rose-950/40 text-rose-200 text-xs"
        >
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" aria-hidden="true" />
          <div className="space-y-1">
            <p className="font-semibold text-rose-300">Operational Delay Detected</p>
            {timeline.exception_reason ? (
              <p className="text-rose-300/90">{timeline.exception_reason}</p>
            ) : (
              <p className="text-rose-300/80">Estimated arrival exceeds deadline.</p>
            )}
          </div>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/50">
          <p className="text-[10px] font-mono uppercase text-slate-500">Risk Assessment</p>
          <div className="mt-1.5">
            <RiskBadge level={timeline.risk_level} />
          </div>
        </div>

        <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/50">
          <p className="text-[10px] font-mono uppercase text-slate-500">Buffer Remaining</p>
          <p
            className={`text-sm font-mono font-medium mt-1 ${
              isNegativeBuffer
                ? 'text-rose-400'
                : bufferHours !== null && bufferHours <= 24
                ? 'text-amber-400'
                : 'text-emerald-400'
            }`}
          >
            {bufferHours !== null ? `${bufferHours > 0 ? '+' : ''}${bufferHours.toFixed(1)} hrs` : 'N/A'}
          </p>
        </div>
      </div>

      {/* Timeline Milestones */}
      <div className="p-3.5 rounded-lg border border-slate-800 bg-slate-900/30 space-y-3">
        <p className="text-xs font-semibold text-slate-300 flex items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-cyan-400" aria-hidden="true" />
          Schedule Milestones
        </p>

        <div className="space-y-2.5 text-xs">
          <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
            <span className="text-slate-400">Required By (Deadline)</span>
            <span className="font-mono text-slate-200">{formatDate(timeline.required_by_at)}</span>
          </div>

          <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
            <span className="text-slate-400">Planned Arrival</span>
            <span className="font-mono text-slate-300">{formatDate(timeline.planned_arrival_at)}</span>
          </div>

          <div className="flex justify-between items-center py-1">
            <span className="text-slate-400">Estimated Arrival</span>
            <span
              className={`font-mono ${
                timeline.is_delayed ? 'text-rose-400 font-semibold' : 'text-slate-200'
              }`}
            >
              {formatDate(timeline.estimated_arrival_at)}
            </span>
          </div>
        </div>
      </div>

      {!timeline.is_delayed && bufferHours !== null && bufferHours >= 0 && (
        <div className="flex items-center gap-2 text-xs text-emerald-400/90 px-1">
          <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
          <span>Consignment is on schedule within operational buffer.</span>
        </div>
      )}
    </div>
  );
}
