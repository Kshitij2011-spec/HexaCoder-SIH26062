/**
 * Offline Sync Indicator (A8).
 *
 * Communicates real/simulated polar connectivity posture, field buffering state,
 * and queued operation counts.
 * Provenance: SYNTHETIC/DEMO when blackout simulation is active.
 */

import { Wifi, WifiOff, RefreshCw, Radio } from 'lucide-react';
import { useOfflineSync } from '../../../lib/sync';

interface Props {
  onOpenDrawer?: () => void;
  showToggle?: boolean;
}

export function OfflineSyncIndicator({ onOpenDrawer, showToggle = true }: Props) {
  const { snapshot, toggleSimulatedBlackout } = useOfflineSync();
  const { effectiveOnline, isSimulatedBlackout, isSyncing, queuedCount, failedCount, lastSyncAt } = snapshot;

  const formattedLastSync = lastSyncAt
    ? new Date(lastSyncAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : 'Never';

  return (
    <div
      data-testid="offline-sync-indicator"
      className="flex items-center gap-2 text-xs font-mono"
    >
      {/* Connectivity Status Badge */}
      <div
        className={`flex items-center gap-2 px-2.5 py-1 rounded-md border shadow-sm transition-colors ${
          effectiveOnline
            ? 'bg-emerald-950/40 border-emerald-800/80 text-emerald-300'
            : 'bg-amber-950/70 border-amber-500/80 text-amber-300'
        }`}
      >
        {effectiveOnline ? (
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <Wifi className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
            <span className="font-semibold tracking-wide">ONLINE</span>
          </span>
        ) : (
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <WifiOff className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
            <span className="font-semibold tracking-wide">
              OFFLINE — FIELD BUFFERING ACTIVE
            </span>
            {isSimulatedBlackout && (
              <span className="text-[10px] px-1 py-0.2 bg-amber-900/60 border border-amber-600/60 rounded text-amber-200">
                [SYNTHETIC/DEMO]
              </span>
            )}
          </span>
        )}

        {/* Sync in progress indicator */}
        {isSyncing && (
          <span title="Syncing...">
            <RefreshCw className="w-3 h-3 text-cyan-400 animate-spin ml-1" />
          </span>
        )}
      </div>

      {/* Operation Counts & Last Sync */}
      <button
        type="button"
        onClick={onOpenDrawer}
        data-testid="sync-drawer-toggle-btn"
        className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-slate-800 bg-slate-900/80 hover:bg-slate-800 hover:border-slate-700 text-slate-300 transition-colors"
        title="Open Offline Synchronization Drawer"
      >
        <span className="text-slate-400">
          Queued: <strong className={queuedCount > 0 ? 'text-amber-400' : 'text-slate-200'}>{queuedCount}</strong>
        </span>
        <span className="text-slate-600">|</span>
        <span className="text-slate-400">
          Failed: <strong className={failedCount > 0 ? 'text-rose-400' : 'text-slate-200'}>{failedCount}</strong>
        </span>
        <span className="text-slate-600">|</span>
        <span className="text-slate-400">
          Last sync: <span className="text-slate-300">{formattedLastSync}</span>
        </span>
      </button>

      {/* Blackout Simulation Toggle Switch */}
      {showToggle && (
        <button
          type="button"
          onClick={toggleSimulatedBlackout}
          data-testid="blackout-toggle-btn"
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs transition-colors ${
            isSimulatedBlackout
              ? 'bg-rose-950/60 border-rose-600 text-rose-300 hover:bg-rose-900/70'
              : 'bg-slate-900 border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`}
          title="Simulate Antarctic Communications Blackout [SYNTHETIC/DEMO]"
        >
          <Radio className="w-3.5 h-3.5 text-current" aria-hidden="true" />
          <span>
            {isSimulatedBlackout
              ? 'Restore Connectivity [SYNTHETIC/DEMO]'
              : 'Simulate Antarctic Blackout [SYNTHETIC/DEMO]'}
          </span>
        </button>
      )}
    </div>
  );
}
