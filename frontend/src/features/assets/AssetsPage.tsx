import { useState, useMemo } from 'react';
import { Cpu, Search, Filter } from 'lucide-react';
import { PageHeader } from '../../components/shared/PageHeader';
import { EntityCode } from '../../components/shared/EntityCode';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { AssetDetailPanel } from './AssetDetailPanel';
import { useAssets } from './hooks/useAssets';
import type { Asset, AssetStatus, AssetCriticality } from '../../lib/types/api';

const STATUS_OPTIONS: Array<AssetStatus | 'ALL'> = [
  'ALL',
  'AVAILABLE',
  'RESERVED',
  'IN_USE',
  'MAINTENANCE',
  'QUARANTINED',
  'RETIRED',
];

const CRITICALITY_OPTIONS: Array<AssetCriticality | 'ALL'> = [
  'ALL',
  'STANDARD',
  'MISSION_CRITICAL',
  'LIFE_SUPPORT',
  'SAFETY',
];

export function AssetsPage() {
  const [statusFilter, setStatusFilter] = useState<AssetStatus | 'ALL'>('ALL');
  const [criticalityFilter, setCriticalityFilter] = useState<AssetCriticality | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);

  const filters = useMemo(() => {
    const f: { status?: AssetStatus; criticality?: AssetCriticality } = {};
    if (statusFilter !== 'ALL') f.status = statusFilter;
    if (criticalityFilter !== 'ALL') f.criticality = criticalityFilter;
    return f;
  }, [statusFilter, criticalityFilter]);

  const {
    data: assets = [],
    isLoading,
    error,
    refetch,
  } = useAssets(filters);

  const filteredAssets = useMemo(() => {
    if (!searchQuery.trim()) return assets;
    const q = searchQuery.toLowerCase();
    return assets.filter(
      (a: Asset) =>
        a.code.toLowerCase().includes(q) ||
        a.type.toLowerCase().includes(q) ||
        (a.serial_number && a.serial_number.toLowerCase().includes(q))
    );
  }, [assets, searchQuery]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Assets & Maintenance"
        subtitle="Polar expedition equipment registry, readiness lifecycle, relocation, and maintenance tracking"
        actions={
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-slate-500" aria-hidden="true" />
            <span className="text-slate-400 text-xs font-mono">{filteredAssets.length} assets</span>
          </div>
        }
      />

      {/* Control Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-slate-900/40 p-4 rounded-lg border border-slate-800">
        <div className="flex items-center gap-3 flex-1 flex-wrap">
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
            <input
              type="search"
              placeholder="Search by code, type, serial..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              aria-label="Search assets"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-500" aria-hidden="true" />
            <label htmlFor="asset-status-filter" className="sr-only">Filter by Status</label>
            <select
              id="asset-status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as AssetStatus | 'ALL')}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              {STATUS_OPTIONS.map((st) => (
                <option key={st} value={st}>
                  {st === 'ALL' ? 'All Statuses' : st}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="asset-criticality-filter" className="sr-only">Filter by Criticality</label>
            <select
              id="asset-criticality-filter"
              value={criticalityFilter}
              onChange={(e) => setCriticalityFilter(e.target.value as AssetCriticality | 'ALL')}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              {CRITICALITY_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {c === 'ALL' ? 'All Criticalities' : c}
                </option>
              ))}
            </select>
          </div>
        </div>

        <span className="text-xs font-mono text-slate-400 self-center">
          Showing {filteredAssets.length} asset{filteredAssets.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Main Content */}
      {isLoading && (
        <div className="p-6">
          <LoadingSkeleton lines={6} />
        </div>
      )}

      {error && (
        <div className="p-6">
          <ErrorDisplay error={error} title="Failed to load assets" />
        </div>
      )}

      {!isLoading && !error && filteredAssets.length === 0 && (
        <EmptyState
          icon={<Cpu className="w-12 h-12 text-slate-600" aria-hidden="true" />}
          title="No Assets Found"
          message={
            searchQuery || statusFilter !== 'ALL' || criticalityFilter !== 'ALL'
              ? 'Try modifying active filters or search terms.'
              : 'No operational equipment registered in the platform.'
          }
        />
      )}

      {!isLoading && !error && filteredAssets.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/20">
          <table className="w-full text-left text-sm" role="table" aria-label="Assets table">
            <thead className="bg-slate-900 font-mono text-xs text-slate-400 uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Asset Code</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Serial No</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Condition</th>
                <th className="px-4 py-3">Criticality</th>
                <th className="px-4 py-3">Location</th>
                <th className="px-4 py-3">Provenance</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {filteredAssets.map((asset: Asset) => (
                <tr
                  key={asset.id}
                  className="hover:bg-slate-800/40 transition-colors"
                >
                  <td className="px-4 py-3 font-semibold text-slate-200">
                    <EntityCode code={asset.code} />
                  </td>
                  <td className="px-4 py-3 font-sans font-medium text-slate-200">
                    {asset.type}
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {asset.serial_number ?? '-'}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={asset.status} />
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-1.5 py-0.5 rounded text-[11px] font-semibold ${
                        asset.condition === 'OPERATIONAL'
                          ? 'text-emerald-400'
                          : asset.condition === 'DEGRADED'
                          ? 'text-amber-400'
                          : 'text-rose-400'
                      }`}
                    >
                      {asset.condition}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {asset.criticality}
                  </td>
                  <td className="px-4 py-3 text-slate-400 truncate max-w-[120px]" title={asset.location_id}>
                    {asset.location_id.slice(0, 8)}...
                  </td>
                  <td className="px-4 py-3">
                    <ProvenanceTag provenance={asset.data_provenance} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => setSelectedAsset(asset)}
                      className="px-3 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white transition-colors"
                      aria-label={`Inspect ${asset.code}`}
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail Slide-over Panel */}
      {selectedAsset && (
        <AssetDetailPanel
          asset={selectedAsset}
          onClose={() => setSelectedAsset(null)}
          onRefreshAsset={refetch}
        />
      )}
    </div>
  );
}
