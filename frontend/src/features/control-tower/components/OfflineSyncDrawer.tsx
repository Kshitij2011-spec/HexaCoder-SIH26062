/**
 * Offline Synchronization & Outbox Drawer (A8).
 *
 * Operational slide-over panel displaying locally buffered operations,
 * connectivity posture, client operation UUIDs, reconciliation statuses,
 * and manual replay controls.
 * Provenance: SYNTHETIC/DEMO.
 */

import {
  X,
  RefreshCw,
  Trash2,
  Wifi,
  WifiOff,
  Radio,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Layers,
  ChevronRight,
} from 'lucide-react';
import { useOfflineSync } from '../../../lib/sync';
import type { LocalSyncStatus, OutboxOperation } from '../../../lib/sync/types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

function getStatusBadge(status: LocalSyncStatus) {
  switch (status) {
    case 'LOCAL_QUEUED':
      return {
        label: 'LOCAL QUEUED',
        color: 'bg-amber-950/70 border-amber-500/80 text-amber-300',
        dot: 'bg-amber-400 animate-pulse',
      };
    case 'SYNCING':
      return {
        label: 'SYNCING',
        color: 'bg-cyan-950/70 border-cyan-500/80 text-cyan-300',
        dot: 'bg-cyan-400 animate-spin',
      };
    case 'APPLIED':
      return {
        label: 'APPLIED',
        color: 'bg-emerald-950/70 border-emerald-500/80 text-emerald-300',
        dot: 'bg-emerald-400',
      };
    case 'FAILED':
      return {
        label: 'FAILED',
        color: 'bg-rose-950/70 border-rose-500/80 text-rose-300',
        dot: 'bg-rose-400',
      };
    case 'CONFLICT':
      return {
        label: 'CONFLICT',
        color: 'bg-purple-950/70 border-purple-500/80 text-purple-300',
        dot: 'bg-purple-400',
      };
  }
}

export function OfflineSyncDrawer({ isOpen, onClose }: Props) {
  const {
    snapshot,
    operations,
    toggleSimulatedBlackout,
    triggerSync,
    retryOperation,
    clearApplied,
  } = useOfflineSync();

  if (!isOpen) return null;

  const { effectiveOnline, isSimulatedBlackout, isSyncing, queuedCount, failedCount, appliedCount, lastSyncAt, lastError } =
    snapshot;

  const handleSyncNow = async () => {
    await triggerSync();
  };

  return (
    <div
      data-testid="offline-sync-drawer"
      className="fixed inset-y-0 right-0 w-full max-w-2xl bg-slate-950 border-l border-slate-800 shadow-2xl z-50 flex flex-col overflow-hidden"
      role="dialog"
      aria-modal="true"
      aria-label="Offline Synchronization Outbox"
    >
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
        <div className="flex items-center gap-3">
          <Layers className="w-5 h-5 text-cyan-400" aria-hidden="true" />
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-100">
                Field Synchronization Outbox
              </h2>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400">
                [SYNTHETIC/DEMO]
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Client-side store-and-forward queue for polar communications resilience
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          data-testid="close-sync-drawer-btn"
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          aria-label="Close sync drawer"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Connectivity Banner & Demo Controls */}
      <div className="px-6 py-4 bg-slate-900/40 border-b border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {effectiveOnline ? (
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs font-mono">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <Wifi className="w-3.5 h-3.5" />
                <span>ONLINE — REAL-TIME REPLAY READY</span>
              </span>
            ) : (
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-950/70 border border-amber-500 text-amber-300 text-xs font-mono">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                <WifiOff className="w-3.5 h-3.5" />
                <span>OFFLINE — FIELD BUFFERING ACTIVE [SYNTHETIC/DEMO]</span>
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={toggleSimulatedBlackout}
            data-testid="drawer-blackout-toggle-btn"
            className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-mono border transition-colors ${
              isSimulatedBlackout
                ? 'bg-rose-950/70 border-rose-600 text-rose-200 hover:bg-rose-900'
                : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            <span>
              {isSimulatedBlackout
                ? 'Restore Connectivity [SYNTHETIC/DEMO]'
                : 'Simulate Antarctic Blackout [SYNTHETIC/DEMO]'}
            </span>
          </button>
        </div>

        {/* Sync Summary Counters */}
        <div className="grid grid-cols-4 gap-2 text-center text-xs font-mono pt-1">
          <div className="p-2 rounded bg-slate-950/70 border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase">Queued</span>
            <span className="text-amber-400 text-sm font-bold">{queuedCount}</span>
          </div>
          <div className="p-2 rounded bg-slate-950/70 border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase">Failed</span>
            <span className="text-rose-400 text-sm font-bold">{failedCount}</span>
          </div>
          <div className="p-2 rounded bg-slate-950/70 border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase">Applied</span>
            <span className="text-emerald-400 text-sm font-bold">{appliedCount}</span>
          </div>
          <div className="p-2 rounded bg-slate-950/70 border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase">Total Buffered</span>
            <span className="text-slate-200 text-sm font-bold">{operations.length}</span>
          </div>
        </div>

        {/* Global Error Banner if any */}
        {lastError && (
          <div className="p-2.5 rounded bg-rose-950/50 border border-rose-800 text-rose-300 text-xs font-mono flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>Replay Error: {lastError}</span>
          </div>
        )}
      </div>

      {/* Outbox Operations List */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
        <div className="flex items-center justify-between pb-1 border-b border-slate-800/80">
          <h3 className="text-xs font-semibold font-mono uppercase tracking-wider text-slate-400">
            Local Queue Records ({operations.length})
          </h3>
          <div className="flex items-center gap-2">
            {appliedCount > 0 && (
              <button
                type="button"
                onClick={() => void clearApplied()}
                data-testid="clear-applied-btn"
                className="flex items-center gap-1 text-[11px] font-mono text-slate-400 hover:text-slate-200 transition-colors"
                title="Clear reconciled operations from local queue"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear Applied</span>
              </button>
            )}
          </div>
        </div>

        {operations.length === 0 ? (
          <div className="py-12 text-center text-slate-500 font-mono text-xs">
            <CheckCircle2 className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p>Outbox is clean. No locally queued or pending operations.</p>
            <p className="text-[11px] text-slate-600 mt-1">
              Field mutations during communication blackouts will buffer here automatically.
            </p>
          </div>
        ) : (
          <div className="space-y-2.5" data-testid="outbox-operations-list">
            {operations.map((op: OutboxOperation) => {
              const badge = getStatusBadge(op.local_status);
              return (
                <div
                  key={op.client_operation_id}
                  data-testid={`outbox-item-${op.client_operation_id}`}
                  className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors space-y-2.5 font-mono text-xs"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-semibold ${badge.color}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`} />
                        <span>{badge.label}</span>
                      </span>
                      <span className="text-slate-200 font-bold">
                        {op.entity_type} · {op.operation_type}
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(op.queued_at).toLocaleTimeString()}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-slate-800/60">
                    <div>
                      <span className="text-slate-500">Client Op ID:</span>
                      <p className="text-cyan-300 font-mono truncate" title={op.client_operation_id}>
                        {op.client_operation_id}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-500">Target ID:</span>
                      <p className="text-slate-300 font-mono truncate" title={op.entity_id}>
                        {op.entity_id}
                      </p>
                    </div>
                    {op.server_record_id && (
                      <div className="col-span-2">
                        <span className="text-slate-500">Server Sync Record:</span>
                        <p className="text-emerald-400 font-mono truncate" title={op.server_record_id}>
                          {op.server_record_id}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Failure message and retry button */}
                  {op.last_error && (
                    <div className="p-2 rounded bg-rose-950/40 border border-rose-800/60 text-rose-300 text-[11px] flex items-center justify-between">
                      <span className="truncate" title={op.last_error}>
                        Error: {op.last_error}
                      </span>
                      <button
                        type="button"
                        onClick={() => void retryOperation(op.client_operation_id)}
                        className="ml-2 text-rose-200 underline hover:text-white"
                      >
                        Retry
                      </button>
                    </div>
                  )}

                  {/* Payload Details Preview */}
                  <details className="text-[11px] text-slate-400 group">
                    <summary className="cursor-pointer hover:text-slate-200 flex items-center gap-1">
                      <ChevronRight className="w-3 h-3 group-open:rotate-90 transition-transform" />
                      <span>View Payload Snapshot</span>
                    </summary>
                    <pre className="mt-1.5 p-2 rounded bg-slate-950 border border-slate-800/80 text-[10px] text-slate-300 overflow-x-auto">
                      {JSON.stringify(op.payload, null, 2)}
                    </pre>
                  </details>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Drawer Footer Actions */}
      <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between">
        <div className="text-xs font-mono text-slate-500">
          Last Reconciliation: {lastSyncAt ? new Date(lastSyncAt).toLocaleString() : 'None'}
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800 text-xs font-mono transition-colors"
          >
            Close
          </button>
          <button
            type="button"
            onClick={() => void handleSyncNow()}
            disabled={isSyncing || !effectiveOnline || queuedCount === 0}
            data-testid="sync-now-btn"
            className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-mono font-medium shadow-sm transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            <span>{isSyncing ? 'Replaying...' : 'Sync Now'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
