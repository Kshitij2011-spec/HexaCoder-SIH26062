import { StatusBadge } from '../../components/shared/StatusBadge';
import type { MaintenanceRecord } from '../../lib/types/api';

interface Props {
  records: MaintenanceRecord[];
  selectedRecordId?: string | null;
  onSelectRecord: (record: MaintenanceRecord) => void;
  isLoading?: boolean;
}

export function MaintenanceTable({
  records,
  selectedRecordId,
  onSelectRecord,
  isLoading,
}: Props) {
  if (isLoading) {
    return (
      <div className="p-6 text-center text-slate-500 font-mono text-xs">
        Loading maintenance records...
      </div>
    );
  }

  if (records.length === 0) {
    return (
      <div className="p-6 text-center text-slate-500 font-mono text-xs border border-slate-800 rounded bg-slate-900/30">
        No maintenance records found for this asset.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded border border-slate-800">
      <table className="w-full text-left text-xs" role="table" aria-label="Maintenance records table">
        <thead className="bg-slate-900 font-mono text-slate-400 uppercase tracking-wider border-b border-slate-800">
          <tr>
            <th className="px-3 py-2">Type</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2 text-center">Priority</th>
            <th className="px-3 py-2">Scheduled</th>
            <th className="px-3 py-2">Technician</th>
            <th className="px-3 py-2">Description</th>
            <th className="px-3 py-2 text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60 font-mono">
          {records.map((rec) => {
            const isSelected = selectedRecordId === rec.id;
            return (
              <tr
                key={rec.id}
                className={`transition-colors hover:bg-slate-800/40 ${
                  isSelected ? 'bg-cyan-950/30' : ''
                }`}
              >
                <td className="px-3 py-2 font-semibold text-slate-200">
                  {rec.maintenance_type}
                </td>
                <td className="px-3 py-2">
                  <StatusBadge status={rec.status} />
                </td>
                <td className="px-3 py-2 text-center">
                  <span
                    className={`inline-block px-1.5 py-0.5 rounded text-[11px] font-bold ${
                      rec.priority === 1
                        ? 'bg-rose-900/60 text-rose-200'
                        : rec.priority === 2
                        ? 'bg-amber-900/50 text-amber-300'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    P{rec.priority}
                  </span>
                </td>
                <td className="px-3 py-2 text-slate-400 whitespace-nowrap">
                  {new Date(rec.scheduled_start_at).toLocaleDateString()}
                </td>
                <td className="px-3 py-2 text-slate-300">
                  {rec.technician_name ?? '-'}
                </td>
                <td className="px-3 py-2 text-slate-400 max-w-[180px] truncate" title={rec.description}>
                  {rec.description}
                </td>
                <td className="px-3 py-2 text-right">
                  <button
                    type="button"
                    onClick={() => onSelectRecord(rec)}
                    className={`px-2 py-1 rounded text-xs transition-colors ${
                      isSelected
                        ? 'bg-cyan-700 text-cyan-100'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                    }`}
                  >
                    {isSelected ? 'Selected' : 'Action'}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
