import { useState } from 'react';
import { Plus, Check, Play, Ban } from 'lucide-react';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import {
  useScheduleMaintenance,
  useStartMaintenance,
  useCompleteMaintenance,
  useCancelMaintenance,
} from './hooks/useAssetMutations';
import type { MaintenanceRecord, AssetStatus } from '../../lib/types/api';

interface Props {
  assetId: string;
  selectedRecord?: MaintenanceRecord | null;
  onClearSelected?: () => void;
  onSuccess?: () => void;
}

export function MaintenanceWorkflow({
  assetId,
  selectedRecord,
  onClearSelected,
  onSuccess,
}: Props) {
  const [userMode, setUserMode] = useState<'SCHEDULE' | 'ACTION' | null>(null);
  const mode = userMode ?? (selectedRecord ? 'ACTION' : 'SCHEDULE');

  // Schedule fields
  const [maintenanceType, setMaintenanceType] = useState('PREVENTIVE');
  const [priority, setPriority] = useState(2);
  const [description, setDescription] = useState('');
  const [scheduledStart, setScheduledStart] = useState('');
  const [durationHours, setDurationHours] = useState(4);
  const [technicianName, setTechnicianName] = useState('');

  // Lifecycle action fields
  const [findings, setFindings] = useState('');
  const [correctiveAction, setCorrectiveAction] = useState('');
  const [targetAssetStatus, setTargetAssetStatus] = useState<AssetStatus | ''>('AVAILABLE');
  const [cancelReason, setCancelReason] = useState('');
  const [startNotes, setStartNotes] = useState('');

  // Dialog & errors
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingFn, setPendingFn] = useState<(() => Promise<unknown>) | null>(null);
  const [dialogTitle, setDialogTitle] = useState('');
  const [dialogMessage, setDialogMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const scheduleMutation = useScheduleMaintenance(assetId);
  const startMutation = useStartMaintenance(assetId);
  const completeMutation = useCompleteMaintenance(assetId);
  const cancelMutation = useCancelMaintenance(assetId);

  const isSubmitting =
    scheduleMutation.isPending ||
    startMutation.isPending ||
    completeMutation.isPending ||
    cancelMutation.isPending;

  const handleScheduleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    if (!description.trim()) {
      setErrorMessage('Description is required.');
      return;
    }
    if (!scheduledStart) {
      setErrorMessage('Scheduled start date/time is required.');
      return;
    }

    setDialogTitle('Schedule Maintenance');
    setDialogMessage(`Schedule ${maintenanceType} maintenance for this asset?`);
    setPendingFn(() => () =>
      scheduleMutation.mutateAsync({
        maintenance_type: maintenanceType,
        priority: Number(priority),
        description: description.trim(),
        scheduled_start_at: new Date(scheduledStart).toISOString(),
        estimated_duration_hours: Number(durationHours),
        technician_name: technicianName.trim() || undefined,
      })
    );
    setConfirmOpen(true);
  };

  const handleStart = (record: MaintenanceRecord) => {
    setErrorMessage(null);
    setDialogTitle('Start Maintenance Order');
    setDialogMessage(`Mark maintenance record ${record.id.slice(0, 8)} as IN_PROGRESS?`);
    setPendingFn(() => () =>
      startMutation.mutateAsync({
        maintenanceId: record.id,
        payload: {
          notes: startNotes.trim() || undefined,
        },
      })
    );
    setConfirmOpen(true);
  };

  const handleComplete = (record: MaintenanceRecord) => {
    setErrorMessage(null);
    if (!findings.trim() || !correctiveAction.trim()) {
      setErrorMessage('Findings and Corrective Action are both required upon completion.');
      return;
    }

    setDialogTitle('Complete Maintenance Order');
    setDialogMessage(
      `Complete maintenance order ${record.id.slice(0, 8)}? Asset status will be set to ${targetAssetStatus || 'AVAILABLE'}.`
    );
    setPendingFn(() => () =>
      completeMutation.mutateAsync({
        maintenanceId: record.id,
        payload: {
          findings: findings.trim(),
          corrective_action: correctiveAction.trim(),
          target_asset_status: targetAssetStatus ? (targetAssetStatus as AssetStatus) : undefined,
        },
      })
    );
    setConfirmOpen(true);
  };

  const handleCancel = (record: MaintenanceRecord) => {
    setErrorMessage(null);
    if (!cancelReason.trim()) {
      setErrorMessage('Cancellation reason is required.');
      return;
    }

    setDialogTitle('Cancel Maintenance Order');
    setDialogMessage(`Cancel maintenance order ${record.id.slice(0, 8)}?`);
    setPendingFn(() => () =>
      cancelMutation.mutateAsync({
        maintenanceId: record.id,
        payload: {
          cancel_reason: cancelReason.trim(),
        },
      })
    );
    setConfirmOpen(true);
  };

  const executeConfirmed = async () => {
    if (!pendingFn) return;
    try {
      await pendingFn();
      setConfirmOpen(false);
      setPendingFn(null);
      setDescription('');
      setScheduledStart('');
      setTechnicianName('');
      setFindings('');
      setCorrectiveAction('');
      setCancelReason('');
      setStartNotes('');
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
              setUserMode('SCHEDULE');
              onClearSelected?.();
              setErrorMessage(null);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-colors ${
              mode === 'SCHEDULE' && !selectedRecord
                ? 'bg-cyan-900/60 text-cyan-200 border border-cyan-700'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <Plus className="w-3.5 h-3.5" aria-hidden="true" />
            Schedule Order
          </button>
          {selectedRecord && (
            <button
              type="button"
              onClick={() => {
                setUserMode('ACTION');
                setErrorMessage(null);
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-colors ${
                mode === 'ACTION'
                  ? 'bg-cyan-900/60 text-cyan-200 border border-cyan-700'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              Order {selectedRecord.id.slice(0, 8)} ({selectedRecord.status})
            </button>
          )}
        </div>
        {selectedRecord && (
          <button
            type="button"
            onClick={onClearSelected}
            className="text-slate-500 hover:text-slate-300"
          >
            Clear Selected
          </button>
        )}
      </div>

      {errorMessage && (
        <div className="mb-3">
          <ErrorDisplay error={new Error(errorMessage)} title="Maintenance Action Failed" />
        </div>
      )}

      {selectedRecord && mode === 'ACTION' ? (
        <div className="space-y-4">
          <div className="p-3 rounded bg-slate-950 border border-slate-800">
            <div className="flex justify-between items-center mb-1">
              <span className="font-semibold text-slate-200">{selectedRecord.maintenance_type}</span>
              <span className="text-cyan-400 font-bold">{selectedRecord.status}</span>
            </div>
            <p className="text-slate-400">{selectedRecord.description}</p>
          </div>

          {selectedRecord.status === 'SCHEDULED' || selectedRecord.status === 'OVERDUE' ? (
            <div className="space-y-3">
              <div>
                <label htmlFor="start-notes" className="block text-slate-400 mb-1">
                  Start Notes
                </label>
                <input
                  id="start-notes"
                  type="text"
                  value={startNotes}
                  onChange={(e) => setStartNotes(e.target.value)}
                  placeholder="Technician check-in notes"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleStart(selectedRecord)}
                  disabled={isSubmitting}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 text-white font-medium"
                >
                  <Play className="w-3.5 h-3.5" aria-hidden="true" />
                  Start Work (IN_PROGRESS)
                </button>
                <button
                  type="button"
                  onClick={() => handleCancel(selectedRecord)}
                  disabled={isSubmitting}
                  className="py-2 px-3 rounded bg-rose-900/60 hover:bg-rose-800 border border-rose-700 text-rose-200 font-medium"
                >
                  <Ban className="w-3.5 h-3.5" aria-hidden="true" />
                  Cancel Order
                </button>
              </div>
            </div>
          ) : selectedRecord.status === 'IN_PROGRESS' ? (
            <div className="space-y-3">
              <div>
                <label htmlFor="findings-input" className="block text-slate-400 mb-1">
                  Inspection Findings <span className="text-rose-400">*</span>
                </label>
                <input
                  id="findings-input"
                  type="text"
                  value={findings}
                  onChange={(e) => setFindings(e.target.value)}
                  placeholder="Observed wear, diagnostic outputs, or test results"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  required
                />
              </div>

              <div>
                <label htmlFor="corrective-action-input" className="block text-slate-400 mb-1">
                  Corrective Action Taken <span className="text-rose-400">*</span>
                </label>
                <input
                  id="corrective-action-input"
                  type="text"
                  value={correctiveAction}
                  onChange={(e) => setCorrectiveAction(e.target.value)}
                  placeholder="Repairs made, parts replaced, calibration performed"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  required
                />
              </div>

              <div>
                <label htmlFor="target-asset-status-input" className="block text-slate-400 mb-1">
                  Resulting Asset Status
                </label>
                <select
                  id="target-asset-status-input"
                  value={targetAssetStatus}
                  onChange={(e) => setTargetAssetStatus(e.target.value as AssetStatus)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="AVAILABLE">AVAILABLE (Operational)</option>
                  <option value="QUARANTINED">QUARANTINED (Hold for review)</option>
                  <option value="RETIRED">RETIRED (End of service)</option>
                </select>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => handleComplete(selectedRecord)}
                  disabled={isSubmitting}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-white font-medium"
                >
                  <Check className="w-3.5 h-3.5" aria-hidden="true" />
                  Complete Maintenance
                </button>
                <button
                  type="button"
                  onClick={() => handleCancel(selectedRecord)}
                  disabled={isSubmitting}
                  className="py-2 px-3 rounded bg-rose-900/60 hover:bg-rose-800 border border-rose-700 text-rose-200 font-medium"
                >
                  <Ban className="w-3.5 h-3.5" aria-hidden="true" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="p-3 rounded bg-slate-950 text-slate-400 text-center">
              Order is in terminal state ({selectedRecord.status}). No further actions available.
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={handleScheduleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="maint-type" className="block text-slate-400 mb-1">
                Maintenance Type
              </label>
              <select
                id="maint-type"
                value={maintenanceType}
                onChange={(e) => setMaintenanceType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="PREVENTIVE">PREVENTIVE</option>
                <option value="CORRECTIVE">CORRECTIVE</option>
                <option value="CONDITION_BASED">CONDITION_BASED</option>
                <option value="INSPECTION">INSPECTION</option>
                <option value="EMERGENCY">EMERGENCY</option>
              </select>
            </div>

            <div>
              <label htmlFor="maint-priority" className="block text-slate-400 mb-1">
                Priority (1 = Highest)
              </label>
              <input
                id="maint-priority"
                type="number"
                min="1"
                max="5"
                value={priority}
                onChange={(e) => setPriority(parseInt(e.target.value, 10))}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div>
            <label htmlFor="maint-desc" className="block text-slate-400 mb-1">
              Description / Work Scope <span className="text-rose-400">*</span>
            </label>
            <input
              id="maint-desc"
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. 500-hour hydraulic pump check and fluid analysis"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="maint-start" className="block text-slate-400 mb-1">
                Scheduled Start <span className="text-rose-400">*</span>
              </label>
              <input
                id="maint-start"
                type="datetime-local"
                value={scheduledStart}
                onChange={(e) => setScheduledStart(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                required
              />
            </div>

            <div>
              <label htmlFor="maint-duration" className="block text-slate-400 mb-1">
                Est. Duration (hrs)
              </label>
              <input
                id="maint-duration"
                type="number"
                min="0.5"
                step="0.5"
                value={durationHours}
                onChange={(e) => setDurationHours(parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div>
            <label htmlFor="maint-tech" className="block text-slate-400 mb-1">
              Technician Name / ID
            </label>
            <input
              id="maint-tech"
              type="text"
              value={technicianName}
              onChange={(e) => setTechnicianName(e.target.value)}
              placeholder="e.g. Tech Specialist Sharma"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2 px-4 rounded bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 text-white font-medium transition-colors"
          >
            {isSubmitting ? 'Scheduling...' : 'Schedule Maintenance Order'}
          </button>
        </form>
      )}

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
