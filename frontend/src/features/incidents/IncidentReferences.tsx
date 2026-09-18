import { useState } from 'react';
import { Link2, Plus } from 'lucide-react';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { useAddIncidentReference } from './hooks/useIncidentMutations';
import type { IncidentReference, IncidentReferenceType } from '../../lib/types/api';

interface Props {
  incidentId: string;
  references: IncidentReference[];
  isLoading?: boolean;
}

const REF_TYPES: IncidentReferenceType[] = [
  'LOCATION',
  'ASSET',
  'INVENTORY_STOCK_LOT',
  'CARGO_CONSIGNMENT',
  'TRANSPORT_LEG',
];

export function IncidentReferences({ incidentId, references, isLoading }: Props) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [refType, setRefType] = useState<IncidentReferenceType>('ASSET');
  const [refId, setRefId] = useState('');
  const [notes, setNotes] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const addRefMutation = useAddIncidentReference(incidentId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    if (!refId.trim()) {
      setErrorMessage('Reference ID / UUID is required.');
      return;
    }

    try {
      await addRefMutation.mutateAsync({
        reference_type: refType,
        reference_id: refId.trim(),
        notes: notes.trim() || undefined,
      });
      setRefId('');
      setNotes('');
      setShowAddForm(false);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to attach reference.');
    }
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      <div className="flex items-center justify-between">
        <span className="text-slate-400 uppercase tracking-wider text-[11px] font-semibold flex items-center gap-1.5">
          <Link2 className="w-3.5 h-3.5 text-cyan-400" aria-hidden="true" />
          Attached Cross-Domain Resources ({references.length})
        </span>
        <button
          type="button"
          onClick={() => {
            setShowAddForm(!showAddForm);
            setErrorMessage(null);
          }}
          className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs transition-colors"
        >
          <Plus className="w-3.5 h-3.5" aria-hidden="true" />
          {showAddForm ? 'Cancel' : 'Attach Reference'}
        </button>
      </div>

      {errorMessage && (
        <ErrorDisplay error={new Error(errorMessage)} title="Reference Attachment Failed" />
      )}

      {showAddForm && (
        <form onSubmit={handleSubmit} className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="ref-type" className="block text-slate-400 mb-1">
                Domain Reference Type
              </label>
              <select
                id="ref-type"
                value={refType}
                onChange={(e) => setRefType(e.target.value as IncidentReferenceType)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {REF_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="ref-id" className="block text-slate-400 mb-1">
                Resource Entity ID / UUID <span className="text-rose-400">*</span>
              </label>
              <input
                id="ref-id"
                type="text"
                value={refId}
                onChange={(e) => setRefId(e.target.value)}
                placeholder="Target entity UUID"
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                required
              />
            </div>
          </div>

          <div>
            <label htmlFor="ref-notes" className="block text-slate-400 mb-1">
              Operational Notes
            </label>
            <input
              id="ref-notes"
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Primary generator failed; power routed to backup"
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <button
            type="submit"
            disabled={addRefMutation.isPending}
            className="w-full py-1.5 rounded bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 text-white font-medium transition-colors"
          >
            {addRefMutation.isPending ? 'Attaching...' : 'Save Reference'}
          </button>
        </form>
      )}

      {isLoading ? (
        <div className="p-4 text-center text-slate-500">Loading references...</div>
      ) : references.length === 0 ? (
        <div className="p-4 text-center text-slate-500 border border-slate-800 rounded bg-slate-900/30">
          No related resources currently linked to this incident.
        </div>
      ) : (
        <div className="overflow-x-auto rounded border border-slate-800">
          <table className="w-full text-left text-xs" role="table" aria-label="Incident references table">
            <thead className="bg-slate-900 font-mono text-slate-400 uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Reference ID</th>
                <th className="px-3 py-2">Notes</th>
                <th className="px-3 py-2">Linked At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {references.map((ref) => (
                <tr key={ref.id} className="hover:bg-slate-800/30">
                  <td className="px-3 py-2 text-cyan-300 font-semibold">{ref.reference_type}</td>
                  <td className="px-3 py-2 text-slate-300 truncate max-w-[150px]" title={ref.reference_id}>
                    {ref.reference_id.slice(0, 8)}...
                  </td>
                  <td className="px-3 py-2 text-slate-400">{ref.notes ?? '-'}</td>
                  <td className="px-3 py-2 text-slate-500">
                    {new Date(ref.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
