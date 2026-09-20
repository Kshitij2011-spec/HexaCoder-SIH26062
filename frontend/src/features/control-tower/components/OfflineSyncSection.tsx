/**
 * Offline Synchronization & Disruption Posture Section (A8).
 *
 * Operational card integrated into the Control Tower dashboard,
 * communicating connectivity posture, outbox queue metrics,
 * and quick field action during communications blackouts.
 * Provenance: SYNTHETIC/DEMO.
 */

import { Wifi, WifiOff, Radio, Layers, Shield } from 'lucide-react';
import { useOfflineSync } from '../../../lib/sync';
import { useIncidents } from '../../incidents/hooks/useIncidents';
import { useAcknowledgeIncident } from '../../incidents/hooks/useIncidentMutations';

interface Props {
  expeditionId: string;
  onOpenDrawer: () => void;
}

export function OfflineSyncSection({ onOpenDrawer }: Props) {
  const { snapshot, toggleSimulatedBlackout, operations } = useOfflineSync();
  const { effectiveOnline, isSimulatedBlackout, queuedCount, failedCount, appliedCount, lastSyncAt } = snapshot;

  // Retrieve open field incidents for hero action execution
  const { data: openIncidents = [], isLoading: isLoadingIncidents } = useIncidents({ status: 'OPEN' });
  const activeIncident = openIncidents.length > 0 ? openIncidents[0] : null;

  const ackMutation = useAcknowledgeIncident(activeIncident?.id ?? '');

  const isIncidentQueued = activeIncident
    ? operations.some(
        (op) => op.entity_type === 'INCIDENT' && op.entity_id === activeIncident.id && op.local_status === 'LOCAL_QUEUED'
      )
    : false;

  const handleQuickAcknowledge = async () => {
    if (!activeIncident) return;
    try {
      await ackMutation.mutateAsync();
    } catch (err) {
      console.error('Failed to acknowledge incident:', err);
    }
  };

  return (
    <section
      data-testid="offline-sync-section"
      aria-label="Offline Synchronization & Disruption Resilience"
      className="p-5 rounded-lg bg-slate-900/60 border border-slate-800 space-y-4 font-mono text-xs shadow-sm"
    >
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <Layers className="w-5 h-5 text-cyan-400" aria-hidden="true" />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
                Store-and-Forward Disruption Resilience
              </h3>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400">
                [SYNTHETIC/DEMO]
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Polar field communications posture & client-side outbox queue
            </p>
          </div>
        </div>

        {/* Connectivity Posture Badge & Blackout Toggle */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div
            data-testid="section-connectivity-badge"
            className={`flex items-center gap-1.5 px-3 py-1 rounded border text-xs font-semibold ${
              effectiveOnline
                ? 'bg-emerald-950/50 border-emerald-800 text-emerald-300'
                : 'bg-amber-950/70 border-amber-500 text-amber-300'
            }`}
          >
            {effectiveOnline ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <Wifi className="w-3.5 h-3.5" />
                <span>ONLINE</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                <WifiOff className="w-3.5 h-3.5" />
                <span>OFFLINE — FIELD BUFFERING ACTIVE</span>
              </>
            )}
          </div>

          <button
            type="button"
            onClick={toggleSimulatedBlackout}
            data-testid="section-blackout-toggle-btn"
            className={`flex items-center gap-1.5 px-3 py-1 rounded border text-xs transition-colors ${
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
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 rounded-md bg-slate-950/60 border border-slate-800">
          <span className="text-slate-500 block text-[10px] uppercase">Queued Operations</span>
          <span
            data-testid="metric-queued-count"
            className={`text-base font-bold ${queuedCount > 0 ? 'text-amber-400' : 'text-slate-200'}`}
          >
            {queuedCount}
          </span>
        </div>
        <div className="p-3 rounded-md bg-slate-950/60 border border-slate-800">
          <span className="text-slate-500 block text-[10px] uppercase">Replay Failures</span>
          <span
            data-testid="metric-failed-count"
            className={`text-base font-bold ${failedCount > 0 ? 'text-rose-400' : 'text-slate-200'}`}
          >
            {failedCount}
          </span>
        </div>
        <div className="p-3 rounded-md bg-slate-950/60 border border-slate-800">
          <span className="text-slate-500 block text-[10px] uppercase">Reconciled (Applied)</span>
          <span
            data-testid="metric-applied-count"
            className={`text-base font-bold ${appliedCount > 0 ? 'text-emerald-400' : 'text-slate-200'}`}
          >
            {appliedCount}
          </span>
        </div>
        <div className="p-3 rounded-md bg-slate-950/60 border border-slate-800">
          <span className="text-slate-500 block text-[10px] uppercase">Last Reconciliation</span>
          <span className="text-xs text-slate-300 block truncate mt-1">
            {lastSyncAt ? new Date(lastSyncAt).toLocaleTimeString() : 'None'}
          </span>
        </div>
      </div>

      {/* Hero Operational Action Box: Incident Acknowledgement */}
      <div className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800/90 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-semibold uppercase text-[11px]">
              Field Hero Mutation:
            </span>
            <span className="text-cyan-400 font-bold">Incident Acknowledgement</span>
          </div>
          {activeIncident ? (
            <p className="text-slate-300 text-[11px] mt-0.5">
              Target: <strong className="text-slate-100">{activeIncident.code}</strong> — {activeIncident.title} ({activeIncident.status})
            </p>
          ) : (
            <p className="text-slate-500 text-[11px] mt-0.5">
              {isLoadingIncidents ? 'Checking field incidents...' : 'No OPEN incidents currently pending acknowledgement.'}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {activeIncident && activeIncident.status === 'OPEN' && (
            <button
              type="button"
              onClick={() => void handleQuickAcknowledge()}
              disabled={ackMutation.isPending || isIncidentQueued}
              data-testid="quick-acknowledge-incident-btn"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-amber-700 hover:bg-amber-600 disabled:opacity-50 text-white font-medium transition-colors"
            >
              <Shield className="w-3.5 h-3.5" />
              <span>{isIncidentQueued ? 'LOCAL_QUEUED' : 'Acknowledge Incident'}</span>
            </button>
          )}

          {isIncidentQueued && (
            <span
              data-testid="hero-action-queued-badge"
              className="px-2.5 py-1 rounded bg-amber-950/80 border border-amber-500/80 text-amber-300 text-xs font-semibold flex items-center gap-1.5"
            >
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              <span>LOCAL_QUEUED — FIELD BUFFERED</span>
            </span>
          )}

          <button
            type="button"
            onClick={onOpenDrawer}
            data-testid="open-outbox-drawer-btn"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 transition-colors"
          >
            <span>Inspect Outbox ({queuedCount})</span>
          </button>
        </div>
      </div>
    </section>
  );
}
