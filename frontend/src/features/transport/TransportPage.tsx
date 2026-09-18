import { useState } from 'react';
import { Truck, Search, AlertCircle, AlertTriangle } from 'lucide-react';
import { useTransportLegs } from './hooks/useTransportLegs';
import { TransportLegDetailPanel } from './TransportLegDetailPanel';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { EntityCode } from '../../components/shared/EntityCode';
import { OperationalTable } from '../../components/shared/OperationalTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { PageHeader } from '../../components/shared/PageHeader';
import type { TransportLeg } from '../../lib/types/api';

const MODE_OPTIONS = [
  { label: 'All Modes', value: '' },
  { label: 'Vessel', value: 'VESSEL' },
  { label: 'Air', value: 'AIR' },
  { label: 'Overland', value: 'OVERLAND' },
  { label: 'Helicopter', value: 'HELICOPTER' },
];

const STATUS_FILTERS: { label: string; value: string }[] = [
  { label: 'All', value: '' },
  { label: 'Planned', value: 'PLANNED' },
  { label: 'Departed', value: 'DEPARTED' },
  { label: 'In Transit', value: 'IN_TRANSIT' },
  { label: 'Arrived', value: 'ARRIVED' },
  { label: 'Delayed', value: 'DELAYED' },
  { label: 'Closed', value: 'CLOSED' },
];

export function TransportPage() {
  const [modeFilter, setModeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading, error } = useTransportLegs({
    mode: modeFilter || undefined,
    status: statusFilter || undefined,
  });

  const legs = data ?? [];

  const filtered = legs.filter((leg) => {
    if (!search) return true;
    const term = search.toLowerCase();
    return (
      leg.code.toLowerCase().includes(term) ||
      leg.mode.toLowerCase().includes(term) ||
      (leg.delay_reason && leg.delay_reason.toLowerCase().includes(term))
    );
  });

  const columns = [
    {
      key: 'code',
      header: 'Leg Code',
      render: (leg: TransportLeg) => (
        <div className="flex items-center gap-2">
          <EntityCode code={leg.code} onClick={() => setSelectedId(leg.id)} />
          {leg.delay_reason && (
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" aria-label="Delayed" />
          )}
        </div>
      ),
    },
    {
      key: 'mode',
      header: 'Mode',
      render: (leg: TransportLeg) => (
        <span className="font-mono text-xs text-cyan-300 font-medium px-2 py-0.5 rounded bg-cyan-950/50 border border-cyan-800/60">
          {leg.mode}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (leg: TransportLeg) => <StatusBadge status={leg.status} />,
    },
    {
      key: 'route',
      header: 'Origin → Destination',
      render: (leg: TransportLeg) => (
        <span className="font-mono text-xs text-slate-400">
          {leg.origin_location_id.slice(0, 8)}… → {leg.destination_location_id.slice(0, 8)}…
        </span>
      ),
    },
    {
      key: 'schedule',
      header: 'Est. Arrival',
      render: (leg: TransportLeg) => (
        <span
          className={`font-mono text-xs ${
            leg.status === 'DELAYED' ? 'text-amber-400 font-semibold' : 'text-slate-300'
          }`}
        >
          {leg.estimated_arrival_at
            ? new Date(leg.estimated_arrival_at).toLocaleString([], {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })
            : leg.planned_arrival_at
            ? new Date(leg.planned_arrival_at).toLocaleString([], {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })
            : '—'}
        </span>
      ),
    },
    {
      key: 'capacity',
      header: 'Capacity',
      render: (leg: TransportLeg) => (
        <span className="font-mono text-xs text-slate-400">
          {leg.capacity ? `${leg.capacity} ${leg.capacity_unit ?? ''}` : '—'}
        </span>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Transport Legs"
        subtitle="Multimodal transit corridors, fleet movement, and operational delay tracking"
        actions={
          <div className="flex items-center gap-2">
            <Truck className="w-4 h-4 text-cyan-400" aria-hidden="true" />
            <span className="text-slate-400 text-xs">{filtered.length} legs</span>
          </div>
        }
      />

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        {/* Search */}
        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500"
            aria-hidden="true"
          />
          <input
            type="search"
            placeholder="Search leg code, mode, or notes…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search transport legs"
            className="pl-9 pr-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:border-cyan-600 w-64"
          />
        </div>

        {/* Mode dropdown */}
        <div>
          <select
            value={modeFilter}
            onChange={(e) => setModeFilter(e.target.value)}
            aria-label="Filter by transport mode"
            className="px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-xs font-medium focus:outline-none focus:border-cyan-600"
          >
            {MODE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Status pills */}
        <div className="flex items-center gap-1" role="group" aria-label="Filter by leg status">
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

      {/* Table Container */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
        {isLoading && (
          <div className="p-6">
            <LoadingSkeleton lines={8} />
          </div>
        )}
        {error && (
          <div className="p-6">
            <ErrorDisplay error={error} title="Failed to load transport legs" />
          </div>
        )}
        {!isLoading && !error && filtered.length === 0 && (
          <EmptyState
            title="No transport legs found"
            message="No transport segments match the selected search or filter criteria."
            icon={<AlertCircle className="w-12 h-12 text-slate-500" />}
          />
        )}
        {!isLoading && !error && filtered.length > 0 && (
          <OperationalTable
            columns={columns}
            data={filtered}
            getRowKey={(leg) => leg.id}
            onRowClick={(leg) => setSelectedId(leg.id)}
          />
        )}
      </div>

      {/* Detail drawer */}
      {selectedId && (
        <>
          <div
            className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm"
            onClick={() => setSelectedId(null)}
            aria-hidden="true"
          />
          <TransportLegDetailPanel
            legId={selectedId}
            onClose={() => setSelectedId(null)}
          />
        </>
      )}
    </div>
  );
}
