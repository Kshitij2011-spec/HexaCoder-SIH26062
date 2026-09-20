import { useState } from 'react';
import { CheckCircle2, Shield, Play, Ban } from 'lucide-react';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import {
  useAcknowledgeIncident,
  useMitigateIncident,
  useResolveIncident,
  useCloseIncident,
} from './hooks/useIncidentMutations';
import { useOfflineSync } from '../../lib/sync';
import type { Incident } from '../../lib/types/api';

interface Props {
  incident: Incident;
  onSuccess?: () => void;
}

export function IncidentStatusActions({ incident, onSuccess }: Props) {
  const { operations } = useOfflineSync();
  const queuedOp = operations.find(
    (op) => op.entity_type === 'INCIDENT' && op.entity_id === incident.id && op.local_status === 'LOCAL_QUEUED'
  );
  const isLocalQueued = Boolean((incident as { _is_local_queued?: boolean })._is_local_queued || queuedOp);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<(() => Promise<unknown>) | null>(null);
  const [dialogTitle, setDialogTitle] = useState('');
  const [dialogMessage, setDialogMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const ackMutation = useAcknowledgeIncident(incident.id);
  const mitMutation = useMitigateIncident(incident.id);
  const resMutation = useResolveIncident(incident.id);
  const closeMutation = useCloseIncident(incident.id);

  const isSubmitting =
    ackMutation.isPending ||
    mitMutation.isPending ||
    resMutation.isPending ||
    closeMutation.isPending;

  const handleAcknowledge = () => {
    setErrorMessage(null);
    setDialogTitle('Acknowledge Incident');
    setDialogMessage(`Acknowledge operational incident ${incident.code}?`);
    setPendingAction(() => () => ackMutation.mutateAsync());
    setConfirmOpen(true);
  };

  const handleMitigate = () => {
    setErrorMessage(null);
    setDialogTitle('Start Mitigation');
    setDialogMessage(`Transition incident ${incident.code} to MITIGATING status?`);
    setPendingAction(() => () => mitMutation.mutateAsync());
    setConfirmOpen(true);
  };

  const handleResolve = () => {
    setErrorMessage(null);
    setDialogTitle('Resolve Incident');
    setDialogMessage(`Mark incident ${incident.code} as RESOLVED?`);
    setPendingAction(() => () => resMutation.mutateAsync());
    setConfirmOpen(true);
  };

  const handleClose = () => {
    setErrorMessage(null);
    setDialogTitle('Close Incident');
    setDialogMessage(`Close incident ${incident.code}? This will transition the incident to terminal CLOSED status.`);
    setPendingAction(() => () => closeMutation.mutateAsync());
    setConfirmOpen(true);
  };

  const executeConfirmed = async () => {
    if (!pendingAction) return;
    try {
      await pendingAction();
      setConfirmOpen(false);
      setPendingAction(null);
      onSuccess?.();
    } catch (err) {
      setConfirmOpen(false);
      setErrorMessage(err instanceof Error ? err.message : 'Operation failed.');
    }
  };

  if (incident.status === 'CLOSED') {
    return (
      <div className="p-4 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-400 font-mono text-xs">
        Incident is in terminal state <span className="font-bold text-zinc-200">CLOSED</span>. No further lifecycle actions or transitions are permitted.
      </div>
    );
  }

  return (
    <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-3 font-mono text-xs">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <span className="text-slate-400 uppercase tracking-wider text-[11px]">
          Lifecycle Transitions
        </span>
        <span className="text-cyan-400 font-semibold">Current: {incident.status}</span>
      </div>

      {isLocalQueued && (
        <div
          data-testid="local-queued-status-banner"
          className="p-2.5 rounded bg-amber-950/70 border border-amber-500/80 text-amber-300 font-mono text-xs flex items-center justify-between gap-2"
        >
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <span className="font-semibold">LOCAL_QUEUED — FIELD BUFFERED [SYNTHETIC/DEMO]</span>
          </div>
          {queuedOp && (
            <span className="text-[10px] text-amber-400/80 font-mono">
              OP: {queuedOp.client_operation_id.slice(0, 8)}...
            </span>
          )}
        </div>
      )}

      {errorMessage && (
        <ErrorDisplay error={new Error(errorMessage)} title="Lifecycle Action Failed" />
      )}

      <div className="flex flex-wrap gap-2 pt-1">
        {incident.status === 'OPEN' && (
          <button
            type="button"
            onClick={handleAcknowledge}
            disabled={isSubmitting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-amber-700 hover:bg-amber-600 disabled:opacity-50 text-white font-medium transition-colors"
          >
            <Shield className="w-3.5 h-3.5" aria-hidden="true" />
            Acknowledge
          </button>
        )}

        {incident.status === 'ACKNOWLEDGED' && (
          <button
            type="button"
            onClick={handleMitigate}
            disabled={isSubmitting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white font-medium transition-colors"
          >
            <Play className="w-3.5 h-3.5" aria-hidden="true" />
            Start Mitigation
          </button>
        )}

        {(incident.status === 'OPEN' || incident.status === 'ACKNOWLEDGED' || incident.status === 'MITIGATING') && (
          <button
            type="button"
            onClick={handleResolve}
            disabled={isSubmitting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-white font-medium transition-colors"
          >
            <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
            Resolve Incident
          </button>
        )}

        {(incident.status === 'OPEN' || incident.status === 'ACKNOWLEDGED' || incident.status === 'RESOLVED') && (
          <button
            type="button"
            onClick={handleClose}
            disabled={isSubmitting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 disabled:opacity-50 text-slate-200 transition-colors"
          >
            <Ban className="w-3.5 h-3.5" aria-hidden="true" />
            Close Incident
          </button>
        )}
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title={dialogTitle}
        message={dialogMessage}
        confirmLabel="Confirm"
        onConfirm={executeConfirmed}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
