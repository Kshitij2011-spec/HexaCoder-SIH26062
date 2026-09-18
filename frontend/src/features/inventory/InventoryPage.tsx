import { useState, useMemo } from 'react';
import { Boxes, Search, Filter } from 'lucide-react';
import { PageHeader } from '../../components/shared/PageHeader';
import { EntityCode } from '../../components/shared/EntityCode';
import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { InventoryDetailPanel } from './InventoryDetailPanel';
import { useInventoryItems } from './hooks/useInventoryItems';
import type { InventoryItem, ItemCriticality } from '../../lib/types/api';

const CRITICALITY_OPTIONS: Array<ItemCriticality | 'ALL'> = [
  'ALL',
  'STANDARD',
  'MISSION_CRITICAL',
  'LIFE_SUPPORT',
  'SAFETY',
];

export function InventoryPage() {
  const [selectedCriticality, setSelectedCriticality] = useState<ItemCriticality | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null);

  const {
    data: items = [],
    isLoading,
    error,
  } = useInventoryItems(
    selectedCriticality !== 'ALL' ? { criticality: selectedCriticality } : undefined
  );

  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase();
    return items.filter(
      (item: InventoryItem) =>
        item.code.toLowerCase().includes(q) ||
        item.name.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q)
    );
  }, [items, searchQuery]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Inventory Operations"
        subtitle="Authoritative expedition inventory tracking, stock lot balances, and operational requisition workflows"
        actions={
          <div className="flex items-center gap-2">
            <Boxes className="w-4 h-4 text-slate-500" aria-hidden="true" />
            <span className="text-slate-400 text-xs font-mono">{filteredItems.length} items</span>
          </div>
        }
      />

      {/* Control Bar: Filters & Search */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-slate-900/40 p-4 rounded-lg border border-slate-800">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
            <input
              type="search"
              placeholder="Search by code, item name, or category..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              aria-label="Search inventory items"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-500" aria-hidden="true" />
            <label htmlFor="criticality-filter" className="sr-only">Filter by Criticality</label>
            <select
              id="criticality-filter"
              value={selectedCriticality}
              onChange={(e) => setSelectedCriticality(e.target.value as ItemCriticality | 'ALL')}
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
          Showing {filteredItems.length} item{filteredItems.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Main Content Area */}
      {isLoading && (
        <div className="p-6">
          <LoadingSkeleton lines={6} />
        </div>
      )}

      {error && (
        <div className="p-6">
          <ErrorDisplay error={error} title="Failed to load inventory items" />
        </div>
      )}

      {!isLoading && !error && filteredItems.length === 0 && (
        <EmptyState
          icon={<Boxes className="w-12 h-12 text-slate-600" aria-hidden="true" />}
          title="No Inventory Items Found"
          message={
            searchQuery || selectedCriticality !== 'ALL'
              ? 'Try clearing or modifying the search filters.'
              : 'No items currently cataloged in the inventory system.'
          }
        />
      )}

      {!isLoading && !error && filteredItems.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/20">
          <table className="w-full text-left text-sm" role="table" aria-label="Inventory catalog">
            <thead className="bg-slate-900 font-mono text-xs text-slate-400 uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Item Code</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Criticality</th>
                <th className="px-4 py-3">UOM</th>
                <th className="px-4 py-3">Storage Specs</th>
                <th className="px-4 py-3">Provenance</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {filteredItems.map((item: InventoryItem) => (
                <tr
                  key={item.id}
                  className="hover:bg-slate-800/40 transition-colors"
                >
                  <td className="px-4 py-3 font-semibold text-slate-200">
                    <EntityCode code={item.code} />
                  </td>
                  <td className="px-4 py-3 font-sans font-medium text-slate-100">
                    {item.name}
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {item.category}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium ${
                        item.criticality === 'LIFE_SUPPORT' || item.criticality === 'SAFETY'
                          ? 'bg-rose-900/40 text-rose-300 border border-rose-700/60'
                          : item.criticality === 'MISSION_CRITICAL'
                          ? 'bg-amber-900/40 text-amber-300 border border-amber-700/60'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {item.criticality}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {item.unit_of_measure}
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-[11px]">
                    {item.minimum_temperature_c && item.maximum_temperature_c
                      ? `${item.minimum_temperature_c}°C to ${item.maximum_temperature_c}°C`
                      : item.hazmat_class
                      ? `Hazmat: ${item.hazmat_class}`
                      : 'Standard'}
                  </td>
                  <td className="px-4 py-3">
                    <ProvenanceTag provenance={item.data_provenance} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => setSelectedItem(item)}
                      className="px-3 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white transition-colors"
                      aria-label={`Inspect ${item.name}`}
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

      {/* Slide-over Detail Panel */}
      {selectedItem && (
        <InventoryDetailPanel
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
        />
      )}
    </div>
  );
}
