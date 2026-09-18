import { useState } from 'react';
import { MapPin, Search } from 'lucide-react';
import { useLocations } from './hooks/useLocations';
import { LocationDetailPanel } from './LocationDetailPanel';
import { LocationStatusBadge } from './LocationStatusBadge';
import { EntityCode } from '../../components/shared/EntityCode';
import { OperationalTable } from '../../components/shared/OperationalTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { PageHeader } from '../../components/shared/PageHeader';
import type { Location, LocationStatus } from '../../lib/types/api';

const STATUS_FILTERS: { label: string; value: string }[] = [
  { label: 'All', value: '' },
  { label: 'Available', value: 'AVAILABLE' },
  { label: 'Restricted', value: 'RESTRICTED' },
  { label: 'Inaccessible', value: 'INACCESSIBLE' },
  { label: 'Closed', value: 'CLOSED' },
];

export function LocationsPage() {
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading, error } = useLocations({ status: statusFilter || undefined });

  // Client-side name search (API doesn't support search param)
  const filtered = (data ?? []).filter((loc) =>
    search
      ? loc.name.toLowerCase().includes(search.toLowerCase()) ||
        loc.code.toLowerCase().includes(search.toLowerCase())
      : true,
  );

  const columns = [
    {
      key: 'code',
      header: 'Code',
      render: (loc: Location) => (
        <EntityCode code={loc.code} onClick={() => setSelectedId(loc.id)} />
      ),
    },
    {
      key: 'name',
      header: 'Name',
      render: (loc: Location) => (
        <span className="font-medium text-slate-200">{loc.name}</span>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (loc: Location) => (
        <span className="text-slate-400 text-xs font-mono">{loc.type}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (loc: Location) => <LocationStatusBadge status={loc.status as LocationStatus} />,
    },
    {
      key: 'hierarchy',
      header: 'Parent',
      render: (loc: Location) =>
        loc.parent_location_id ? (
          <span className="text-slate-500 text-xs font-mono truncate">…</span>
        ) : (
          <span className="text-slate-600 text-xs italic">root</span>
        ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Locations"
        subtitle="Operational facilities, field depots, and logistics nodes"
        actions={
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-slate-500" aria-hidden="true" />
            <span className="text-slate-400 text-xs">{filtered.length} locations</span>
          </div>
        }
      />

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        {/* Search */}
        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500"
            aria-hidden="true"
          />
          <input
            type="search"
            placeholder="Search name or code…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search locations"
            className="pl-9 pr-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:border-cyan-600 w-60"
          />
        </div>

        {/* Status filter pills */}
        <div className="flex items-center gap-1" role="group" aria-label="Filter by status">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => setStatusFilter(f.value)}
              aria-pressed={statusFilter === f.value}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                statusFilter === f.value
                  ? 'bg-cyan-900/60 border-cyan-700 text-cyan-300'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
        {isLoading && <div className="p-6"><LoadingSkeleton lines={8} /></div>}
        {error && <div className="p-6"><ErrorDisplay error={error} title="Failed to load locations" /></div>}
        {!isLoading && !error && filtered.length === 0 && (
          <EmptyState
            title="No locations found"
            message="No locations match the current filters. Try adjusting the status filter or search."
            icon={<MapPin className="w-12 h-12" />}
          />
        )}
        {!isLoading && !error && filtered.length > 0 && (
          <OperationalTable
            columns={columns}
            data={filtered}
            getRowKey={(loc) => loc.id}
            onRowClick={(loc) => setSelectedId(loc.id)}
          />
        )}
      </div>

      {/* Detail panel */}
      {selectedId && (
        <>
          <div
            className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm"
            onClick={() => setSelectedId(null)}
            aria-hidden="true"
          />
          <LocationDetailPanel
            locationId={selectedId}
            onClose={() => setSelectedId(null)}
            onNavigate={(loc) => setSelectedId(loc.id)}
          />
        </>
      )}
    </div>
  );
}
