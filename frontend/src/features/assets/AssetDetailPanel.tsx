import { useState } from 'react';
import { X, Wrench, Clock, ShieldAlert, Cpu } from 'lucide-react';
import { EntityCode } from '../../components/shared/EntityCode';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import { AssetStatusActions } from './AssetStatusActions';
import { MaintenanceTable } from './MaintenanceTable';
import { MaintenanceWorkflow } from './MaintenanceWorkflow';
import { AssetTimeline } from './AssetTimeline';
import { OperationalTimeline } from '../../components/shared/OperationalTimeline';
import { useAssetTimeline } from './hooks/useAssetTimeline';
import { useMaintenanceRecords } from './hooks/useMaintenanceRecords';
import type { Asset, MaintenanceRecord } from '../../lib/types/api';

interface Props {
  asset: Asset | null;
  onClose: () => void;
  onRefreshAsset?: () => void;
}

export function AssetDetailPanel({ asset, onClose, onRefreshAsset }: Props) {
  const [selectedRecord, setSelectedRecord] = useState<MaintenanceRecord | null>(null);

  const {
    data: timelineData,
    isLoading: isTimelineLoading,
    refetch: refetchTimeline,
  } = useAssetTimeline(asset?.id ?? null);

  const {
    data: maintenanceRecords = [],
    isLoading: isMaintLoading,
    refetch: refetchMaintenance,
  } = useMaintenanceRecords(asset?.id ?? null);

  if (!asset) return null;

  const handleRefresh = () => {
    refetchTimeline();
    refetchMaintenance();
    onRefreshAsset?.();
  };

  return (
    <div
      className="fixed inset-y-0 right-0 w-full max-w-2xl bg-slate-950 border-l border-slate-800 shadow-2xl z-50 flex flex-col overflow-hidden"
      role="dialog"
      aria-modal="true"
      aria-label={`Asset details for ${asset.code}`}
    >
      {/* Drawer Header */}
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
        <div className="flex items-center gap-3">
          <Cpu className="w-5 h-5 text-cyan-400" aria-hidden="true" />
          <div>
            <div className="flex items-center gap-2">
              <EntityCode code={asset.code} />
              <StatusBadge status={asset.status} />
              <ProvenanceTag provenance={asset.data_provenance} />
            </div>
            <h2 className="text-base font-semibold text-slate-100 mt-0.5">
              {asset.type} {asset.serial_number ? `· SN: ${asset.serial_number}` : ''}
            </h2>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          aria-label="Close detail panel"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Drawer Body */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        {/* Asset Specifications */}
        <section className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 text-xs font-mono">
          <h3 className="text-slate-400 uppercase tracking-wider text-[11px] mb-3 font-semibold">
            Equipment Registry Details
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <span className="text-slate-500">Condition:</span>
              <p className="text-slate-200 font-semibold">{asset.condition}</p>
            </div>
            <div>
              <span className="text-slate-500">Criticality:</span>
              <p className="text-amber-400 font-semibold">{asset.criticality}</p>
            </div>
            <div>
              <span className="text-slate-500">Current Location:</span>
              <p className="text-slate-200 font-semibold truncate" title={asset.location_id}>
                {asset.location_id.slice(0, 8)}...
              </p>
            </div>
            {asset.commissioned_at && (
              <div>
                <span className="text-slate-500">Commissioned:</span>
                <p className="text-slate-300">
                  {new Date(asset.commissioned_at).toLocaleDateString()}
                </p>
              </div>
            )}
            {asset.retired_at && (
              <div>
                <span className="text-slate-500">Retired:</span>
                <p className="text-rose-400 font-semibold">
                  {new Date(asset.retired_at).toLocaleDateString()}
                </p>
              </div>
            )}
          </div>
          {asset.description && (
            <p className="mt-3 pt-2 border-t border-slate-800/80 text-slate-400">
              {asset.description}
            </p>
          )}
        </section>

        {/* State Machine & Relocation Workflows */}
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-cyan-400" aria-hidden="true" />
            Operational State & Relocation
          </h3>
          <AssetStatusActions asset={asset} onSuccess={handleRefresh} />
        </section>

        {/* Maintenance Management Section */}
        <section className="space-y-4 pt-4 border-t border-slate-800">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Wrench className="w-4 h-4 text-cyan-400" aria-hidden="true" />
              Maintenance Orders ({maintenanceRecords.length})
            </h3>
            <span className="text-xs text-slate-500 font-mono">
              Schedule or execute work orders
            </span>
          </div>

          <MaintenanceWorkflow
            assetId={asset.id}
            selectedRecord={selectedRecord}
            onClearSelected={() => setSelectedRecord(null)}
            onSuccess={handleRefresh}
          />

          <MaintenanceTable
            records={maintenanceRecords}
            selectedRecordId={selectedRecord?.id}
            onSelectRecord={(rec) => setSelectedRecord(rec)}
            isLoading={isMaintLoading}
          />
        </section>

        {/* Operational Timeline Section */}
        <section className="space-y-4 pt-4 border-t border-slate-800">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" aria-hidden="true" />
            Operational Event History
          </h3>
          <AssetTimeline
            entries={timelineData?.history ?? []}
            isLoading={isTimelineLoading}
          />
          <OperationalTimeline
            entityType="ASSET"
            entityId={asset.id}
            title="Cross-Domain Operational History & Audit Log"
            defaultIncludeRelated={true}
          />
        </section>
      </div>
    </div>
  );
}
