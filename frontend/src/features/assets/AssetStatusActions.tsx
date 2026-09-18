import { useState } from 'react';
import { Truck, RefreshCw } from 'lucide-react';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { useTransitionAsset, useMoveAsset } from './hooks/useAssetMutations';
import { ASSET_TRANSITIONS, type Asset, type AssetStatus } from '../../lib/types/api';

interface Props {
  asset: Asset;
  onSuccess?: () => void;
}

export function AssetStatusActions({ asset, onSuccess }: Props) {
  const [activeAction, setActiveAction] = useState<'TRANSITION' | 'RELOCATE'>('TRANSITION');
  const [targetStatus, setTargetStatus] = useState<AssetStatus | ''>('');
  const [transitionReason, setTransitionReason] = useState('');
  const [destinationLocationId, setDestinationLocationId] = useState('');
  const [moveReason, setMoveReason] = useState('');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<(() => Promise<unknown>) | null>(null);
  const [confirmTitle, setConfirmTitle] = useState('');
  const [confirmMessage, setConfirmMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const transitionMutation = useTransitionAsset(asset.id);
  const moveMutation = useMoveAsset(asset.id);

  const isSubmitting = transitionMutation.isPending || moveMutation.isPending;
  const isRetired = asset.status === 'RETIRED';
  const validTransitions = ASSET_TRANSITIONS[asset.status] || [];

  const handleTransitionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    if (!targetStatus) {
      setErrorMessage('Please select a target status.');
      return;
    }

    setConfirmTitle('Confirm Asset Status Transition');
    setConfirmMessage(
      `Transition asset ${asset.code} from ${asset.status} to ${targetStatus}?`
    );
    setPendingAction(() => () =>
      transitionMutation.mutateAsync({
        status: targetStatus as AssetStatus,
        reason: transitionReason.trim() || undefined,
      })
    );
    setConfirmOpen(true);
  };

  const handleMoveSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    if (!destinationLocationId.trim()) {
      setErrorMessage('Destination Location ID is required.');
      return;
    }

    setConfirmTitle('Confirm Asset Relocation');
    setConfirmMessage(
      `Relocate asset ${asset.code} to location ${destinationLocationId}?`
    );
    setPendingAction(() => () =>
      moveMutation.mutateAsync({
        destination_location_id: destinationLocationId.trim(),
        move_reason: moveReason.trim() || undefined,
      })
    );
    setConfirmOpen(true);
  };

  const executeConfirmed = async () => {
    if (!pendingAction) return;
    try {
      await pendingAction();
      setConfirmOpen(false);
      setPendingAction(null);
      setTargetStatus('');
      setTransitionReason('');
      setDestinationLocationId('');
      setMoveReason('');
      onSuccess?.();
    } catch (err) {
      setConfirmOpen(false);
      setErrorMessage(err instanceof Error ? err.message : 'Operation failed.');
    }
  };

  return (
    <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-4">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              setActiveAction('TRANSITION');
              setErrorMessage(null);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-colors ${
              activeAction === 'TRANSITION'
                ? 'bg-cyan-900/60 text-cyan-200 border border-cyan-700'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
            Status Transition
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveAction('RELOCATE');
              setErrorMessage(null);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-colors ${
              activeAction === 'RELOCATE'
                ? 'bg-cyan-900/60 text-cyan-200 border border-cyan-700'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <Truck className="w-3.5 h-3.5" aria-hidden="true" />
            Relocate Asset
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="mb-3">
          <ErrorDisplay error={new Error(errorMessage)} title="Asset Action Failed" />
        </div>
      )}

      {isRetired ? (
        <div className="p-3 rounded bg-zinc-900 border border-zinc-700 text-zinc-400">
          Status <span className="font-bold text-zinc-300">RETIRED</span> is terminal. No state transitions or movements are permitted.
        </div>
      ) : activeAction === 'TRANSITION' ? (
        <form onSubmit={handleTransitionSubmit} className="space-y-3">
          <div>
            <label htmlFor="asset-target-status" className="block text-slate-400 mb-1">
              Target Status <span className="text-rose-400">*</span>
            </label>
            <select
              id="asset-target-status"
              value={targetStatus}
              onChange={(e) => setTargetStatus(e.target.value as AssetStatus)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              required
            >
              <option value="">Select next status...</option>
              {validTransitions.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="transition-reason-input" className="block text-slate-400 mb-1">
              Operational Justification
            </label>
            <input
              id="transition-reason-input"
              type="text"
              value={transitionReason}
              onChange={(e) => setTransitionReason(e.target.value)}
              placeholder="e.g. Cleared after pre-season inspection"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting || validTransitions.length === 0}
            className="w-full py-2 px-4 rounded bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium transition-colors"
          >
            {isSubmitting ? 'Transitioning...' : 'Transition Status'}
          </button>
        </form>
      ) : (
        <form onSubmit={handleMoveSubmit} className="space-y-3">
          <div>
            <label htmlFor="dest-location" className="block text-slate-400 mb-1">
              Destination Location ID <span className="text-rose-400">*</span>
            </label>
            <input
              id="dest-location"
              type="text"
              value={destinationLocationId}
              onChange={(e) => setDestinationLocationId(e.target.value)}
              placeholder="UUID of destination facility / sector"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>

          <div>
            <label htmlFor="move-reason-input" className="block text-slate-400 mb-1">
              Movement Reason
            </label>
            <input
              id="move-reason-input"
              type="text"
              value={moveReason}
              onChange={(e) => setMoveReason(e.target.value)}
              placeholder="e.g. Staged at airfield hangar for summer sortie"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2 px-4 rounded bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium transition-colors"
          >
            {isSubmitting ? 'Relocating...' : 'Execute Relocation'}
          </button>
        </form>
      )}

      <ConfirmDialog
        open={confirmOpen}
        title={confirmTitle}
        message={confirmMessage}
        confirmLabel="Confirm"
        onConfirm={executeConfirmed}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
