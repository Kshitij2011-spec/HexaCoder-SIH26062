import { useState } from 'react';
import { X, Truck, AlertTriangle } from 'lucide-react';
import { useTransportLeg } from './hooks/useTransportLeg';
import { useUpdateTransportLeg } from './hooks/useUpdateTransportLeg';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { EntityCode } from '../../components/shared/EntityCode';
import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';
import { TransportLegCargo } from './TransportLegCargo';
import { DelayWorkflow } from './DelayWorkflow';
import { OperationalTimeline } from '../../components/shared/OperationalTimeline';
import type { TransportStatus } from '../../lib/types/api';

interface Props {
  legId: string | null;
  onClose: () => void;
  onSelectConsignment?: (consignmentId: string) => void;
}

const TRANSPORT_STATUSES: TransportStatus[] = [
  'PLANNED', 'BOOKED', 'READY', 'DEPARTED', 'IN_TRANSIT',
  'ARRIVED', 'CLOSED', 'DELAYED', 'DIVERTED', 'CANCELLED',
];

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-slate-800/60 last:border-0">
      <span className="text-slate-500 text-xs w-36 shrink-0 pt-0.5">{label}</span>
      <span className="text-slate-200 text-sm break-all">{value ?? <span className="text-slate-600 italic">—</span>}</span>
    </div>
  );
}

export function TransportLegDetailPanel({ legId, onClose, onSelectConsignment }: Props) {
  const { data: leg, isLoading, error } = useTransportLeg(legId);
  const updateMutation = useUpdateTransportLeg();

  const [activeTab, setActiveTab] = useState<'overview' | 'cargo' | 'operations'>('overview');
  const [showDelayModal, setShowDelayModal] = useState(false);
  const [newStatus, setNewStatus] = useState<TransportStatus | ''>('');
  const [confirmPending, setConfirmPending] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  const handleUpdateStatus = async () => {
    if (!leg || !newStatus) return;
    setActionError(null);

    try {
      await updateMutation.mutateAsync({
        id: leg.id,
        data: {
          status: newStatus,
        },
      });
      setConfirmPending(false);
      setActiveTab('overview');
    } catch (err) {
      setConfirmPending(false);
      setActionError((err as Error).message || 'Failed to update transport status.');
    }
  };

  return (
    <div
      className="fixed inset-y-0 right-0 z-40 w-full max-w-xl flex flex-col bg-slate-900 border-l border-slate-700 shadow-2xl"
      role="dialog"
      aria-modal="true"
      aria-label="Transport leg details"
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm">
        <Truck className="w-5 h-5 text-cyan-400" aria-hidden="true" />
        <div className="flex-1 min-w-0">
          <h2 className="text-slate-100 font-semibold text-sm truncate">
            {isLoading ? 'Loading…' : (leg?.code ?? 'Transport Leg')}
          </h2>
        </div>
        {leg && <ProvenanceTag provenance={leg.data_provenance} />}
        <button
          type="button"
          onClick={onClose}
          className="text-slate-500 hover:text-slate-200 transition-colors ml-2"
          aria-label="Close panel"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Tabs */}
      {leg && (
        <div className="flex border-b border-slate-800 bg-slate-950/40 px-6 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className={`py-2.5 px-3 font-medium border-b-2 transition-colors ${
              activeTab === 'overview'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Overview
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('cargo')}
            className={`py-2.5 px-3 font-medium border-b-2 transition-colors ${
              activeTab === 'cargo'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Cargo Manifest
          </button>
          <button
            type="button"
            onClick={() => {
              setNewStatus(leg.status);
              setActiveTab('operations');
            }}
            className={`py-2.5 px-3 font-medium border-b-2 transition-colors ${
              activeTab === 'operations'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Operations
          </button>
        </div>
      )}

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        {isLoading && <LoadingSkeleton lines={8} />}
        {error && <ErrorDisplay error={error} title="Failed to load transport leg" />}

        {leg && (
          <>
            {/* Overview Tab */}
            {activeTab === 'overview' && (
              <div className="space-y-5">
                <div className="flex flex-wrap items-center gap-2.5">
                  <EntityCode code={leg.code} />
                  <StatusBadge status={leg.status} />
                  <span className="px-2 py-0.5 rounded text-xs font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-800/80">
                    {leg.mode}
                  </span>
                </div>

                {leg.delay_reason && (
                  <div className="p-3 rounded-lg border border-amber-800/60 bg-amber-950/40 text-amber-200 text-xs flex items-start gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-amber-300">Operational Delay Logged</p>
                      <p className="mt-0.5 text-amber-200/90">{leg.delay_reason}</p>
                    </div>
                  </div>
                )}

                <div className="divide-y divide-slate-800/60">
                  <DetailRow label="Leg ID" value={<span className="font-mono text-xs">{leg.id}</span>} />
                  <DetailRow label="Expedition" value={<span className="font-mono text-xs">{leg.expedition_id}</span>} />
                  <DetailRow label="Origin Location" value={<span className="font-mono text-xs">{leg.origin_location_id}</span>} />
                  <DetailRow label="Destination" value={<span className="font-mono text-xs">{leg.destination_location_id}</span>} />
                  <DetailRow
                    label="Capacity"
                    value={
                      leg.capacity
                        ? `${leg.capacity} ${leg.capacity_unit ?? 'units'}`
                        : null
                    }
                  />
                  <DetailRow label="Planned Departure" value={formatDate(leg.planned_departure_at)} />
                  <DetailRow label="Planned Arrival" value={formatDate(leg.planned_arrival_at)} />
                  <DetailRow label="Estimated Departure" value={formatDate(leg.estimated_departure_at)} />
                  <DetailRow
                    label="Estimated Arrival"
                    value={
                      <span className={leg.status === 'DELAYED' ? 'text-amber-400 font-medium' : ''}>
                        {formatDate(leg.estimated_arrival_at)}
                      </span>
                    }
                  />
                  <DetailRow label="Actual Departure" value={formatDate(leg.actual_departure_at)} />
                  <DetailRow label="Actual Arrival" value={formatDate(leg.actual_arrival_at)} />
                  <DetailRow label="Created" value={formatDate(leg.created_at)} />
                  <DetailRow label="Last Updated" value={formatDate(leg.updated_at)} />
                </div>
              </div>
            )}

            {/* Cargo Manifest Tab */}
            {activeTab === 'cargo' && (
              <TransportLegCargo
                legId={leg.id}
                onSelectConsignment={onSelectConsignment}
              />
            )}

            {/* Operations Tab */}
            {activeTab === 'operations' && (
              <div className="space-y-6">
                {/* Quick Delay Workflow */}
                {showDelayModal ? (
                  <DelayWorkflow
                    leg={leg}
                    onSuccess={() => setShowDelayModal(false)}
                    onCancel={() => setShowDelayModal(false)}
                  />
                ) : (
                  <div className="p-4 rounded-xl border border-amber-800/50 bg-amber-950/20 flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-semibold text-amber-300 flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Operational Delay Propagation
                      </h4>
                      <p className="text-[11px] text-slate-400 mt-1">
                        Record weather/logistics delays and recalculate cargo arrival timelines.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowDelayModal(true)}
                      className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium shrink-0 ml-3 transition-colors"
                    >
                      Record Delay
                    </button>
                  </div>
                )}

                {/* Status Transition Form */}
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/50 space-y-4">
                  <h4 className="text-xs font-semibold text-slate-200">
                    Leg Lifecycle State Transition
                  </h4>

                  {actionError && (
                    <div className="text-xs text-rose-400 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span>{actionError}</span>
                    </div>
                  )}

                  <div className="space-y-3 text-xs">
                    <div>
                      <label className="block text-[10px] font-mono uppercase text-slate-400 mb-1">
                        Target Status
                      </label>
                      <select
                        value={newStatus}
                        onChange={(e) => setNewStatus(e.target.value as TransportStatus)}
                        className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-xs font-mono focus:outline-none focus:border-cyan-600"
                      >
                        {TRANSPORT_STATUSES.map((st) => (
                          <option key={st} value={st}>
                            {st}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      type="button"
                      onClick={() => setConfirmPending(true)}
                      disabled={updateMutation.isPending || newStatus === leg.status}
                      className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium transition-colors disabled:opacity-50"
                    >
                      {updateMutation.isPending ? 'Updating…' : 'Execute State Transition'}
                    </button>
                  </div>
                </div>

                {/* Operational History & Event Journal */}
                <OperationalTimeline
                  entityType="TRANSPORT_LEG"
                  entityId={leg.id}
                  title="Transport Leg Operational History"
                  defaultIncludeRelated={true}
                />

                <ConfirmDialog
                  isOpen={confirmPending}
                  title="Confirm Transport State Transition"
                  message={`Are you sure you want to transition transport leg ${leg.code} to ${newStatus}? This will be recorded as an immutable operational event.`}
                  confirmLabel="Confirm Transition"
                  isDestructive={newStatus === 'CANCELLED' || newStatus === 'DIVERTED'}
                  onConfirm={handleUpdateStatus}
                  onCancel={() => setConfirmPending(false)}
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
