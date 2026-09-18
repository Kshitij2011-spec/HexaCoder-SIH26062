import { Clock } from 'lucide-react';
import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import type { AssetTimelineEntry } from '../../lib/types/api';

interface Props {
  entries: AssetTimelineEntry[];
  isLoading?: boolean;
}

export function AssetTimeline({ entries, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="p-6 text-center text-slate-500 font-mono text-xs">
        Loading operational timeline...
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="p-6 text-center text-slate-500 font-mono text-xs border border-slate-800 rounded bg-slate-900/30">
        No operational timeline events recorded for this asset.
      </div>
    );
  }

  return (
    <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
      {entries.map((entry) => (
        <div key={entry.id} className="relative group text-xs font-mono">
          <div className="absolute -left-6 top-0.5 w-4 h-4 rounded-full bg-slate-950 border-2 border-cyan-500 flex items-center justify-center">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          </div>

          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-1">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-cyan-300">{entry.event_type}</span>
              <div className="flex items-center gap-1.5 text-slate-500 text-[11px]">
                <Clock className="w-3 h-3" />
                <span>{new Date(entry.timestamp).toLocaleString()}</span>
              </div>
            </div>

            <p className="text-slate-300">{entry.description}</p>

            <div className="pt-2 flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-800/60">
              <span>Actor: {entry.actor ?? 'SYSTEM'}</span>
              <ProvenanceTag provenance={entry.data_provenance} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
