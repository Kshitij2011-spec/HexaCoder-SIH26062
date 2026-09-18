import { useState } from 'react';
import { PackagePlus, AlertCircle, Check } from 'lucide-react';
import { useAssignCargo } from './hooks/useAssignCargo';
import { useConsignments } from '../cargo/hooks/useConsignments';

interface Props {
  legId: string;
  alreadyAssignedIds?: string[];
  onSuccess?: () => void;
  onCancel: () => void;
}

export function AssignCargoWorkflow({
  legId,
  alreadyAssignedIds = [],
  onSuccess,
  onCancel,
}: Props) {
  const assignMutation = useAssignCargo();
  const { data: consignments, isLoading: loadingConsignments } = useConsignments();

  const [selectedConsignmentId, setSelectedConsignmentId] = useState('');
  const [manualId, setManualId] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Available consignments that are not already assigned
  const availableConsignments = (consignments ?? []).filter(
    (c) => !alreadyAssignedIds.includes(c.id),
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const targetId = selectedConsignmentId || manualId.trim();
    if (!targetId) {
      setErrorMsg('Please select or enter a cargo consignment ID.');
      return;
    }

    try {
      await assignMutation.mutateAsync({
        legId,
        data: {
          cargo_consignment_id: targetId,
          status: 'ACTIVE',
        },
      });
      if (onSuccess) onSuccess();
    } catch (err) {
      setErrorMsg((err as Error).message || 'Failed to assign cargo to transport leg.');
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-4 rounded-xl border border-slate-800 bg-slate-900/80 space-y-3.5 text-xs"
    >
      <div className="flex items-center gap-2">
        <PackagePlus className="w-4 h-4 text-cyan-400" aria-hidden="true" />
        <h4 className="font-semibold text-slate-200">Manifest Cargo Consignment</h4>
      </div>

      <p className="text-slate-400">
        Assign a cargo consignment to this transport leg. The consignment will move via this leg schedule.
      </p>

      {errorMsg && (
        <div className="text-rose-400 p-2.5 rounded bg-rose-950/40 border border-rose-800/60 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Select from available consignments */}
      <div>
        <label className="block text-[10px] font-mono uppercase text-slate-400 mb-1">
          Select Available Consignment
        </label>
        {loadingConsignments ? (
          <p className="text-slate-500 italic">Loading consignments…</p>
        ) : availableConsignments.length > 0 ? (
          <select
            value={selectedConsignmentId}
            onChange={(e) => {
              setSelectedConsignmentId(e.target.value);
              setManualId('');
            }}
            className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 font-mono text-xs focus:outline-none focus:border-cyan-600"
          >
            <option value="">-- Choose Consignment --</option>
            {availableConsignments.map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} [{c.status}] - Priority {c.priority}
              </option>
            ))}
          </select>
        ) : (
          <p className="text-slate-500 text-[11px]">No unassigned consignments loaded in cache.</p>
        )}
      </div>

      {/* Or manual UUID input */}
      <div>
        <label className="block text-[10px] font-mono uppercase text-slate-400 mb-1">
          Or Enter Consignment UUID Directly
        </label>
        <input
          type="text"
          value={manualId}
          onChange={(e) => {
            setManualId(e.target.value);
            setSelectedConsignmentId('');
          }}
          placeholder="00000000-0000-0000-0000-000000000000"
          className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 font-mono text-xs focus:outline-none focus:border-cyan-600"
        />
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 rounded-lg text-slate-400 hover:text-slate-200 text-xs"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={assignMutation.isPending}
          className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs transition-colors disabled:opacity-50"
        >
          <Check className="w-3.5 h-3.5" />
          <span>{assignMutation.isPending ? 'Assigning…' : 'Add to Manifest'}</span>
        </button>
      </div>
    </form>
  );
}
