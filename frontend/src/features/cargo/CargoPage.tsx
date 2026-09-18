import { useState } from 'react';
import { Package, Search, AlertCircle } from 'lucide-react';
import { useConsignments } from './hooks/useConsignments';
import { ConsignmentDetailPanel } from './ConsignmentDetailPanel';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { RiskBadge } from './RiskBadge';
import { EntityCode } from '../../components/shared/EntityCode';
import { OperationalTable } from '../../components/shared/OperationalTable';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { PageHeader } from '../../components/shared/PageHeader';
import type { CargoConsignment, CargoRiskLevel } from '../../lib/types/api';

const STATUS_OPTIONS = [
  { label: 'All Statuses', value: '' },
  { label: 'Requested', value: 'REQUESTED' },
  { label: 'Declared', value: 'DECLARED' },
  { label: 'Approved', value: 'APPROVED' },
  { label: 'Ready', value: 'READY' },
  { label: 'In Transit', value: 'IN_TRANSIT' },
  { label: 'Arrived', value: 'ARRIVED' },
  { label: 'Received', value: 'RECEIVED' },
  { label: 'Held', value: 'HELD' },
  { label: 'Delayed', value: 'DELAYED' },
  { label: 'Damaged', value: 'DAMAGED' },
  { label: 'Lost', value: 'LOST' },
];

const RISK_FILTERS: { label: string; value: string }[] = [
  { label: 'All Risks', value: '' },
  { label: 'Nominal', value: 'NOMINAL' },
  { label: 'Moderate', value: 'MODERATE' },
  { label: 'Elevated', value: 'ELEVATED' },
  { label: 'Critical', value: 'CRITICAL' },
];

export function CargoPage() {
  const [statusFilter, setStatusFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading, error } = useConsignments({
    status: statusFilter || undefined,
    risk_level: riskFilter || undefined,
  });

  const consignments = data ?? [];

  // Client search filter on code or transport summary
  const filtered = consignments.filter((c) => {
    if (!search) return true;
    const term = search.toLowerCase();
    return (
      c.code.toLowerCase().includes(term) ||
      (c.transport_plan_summary && c.transport_plan_summary.toLowerCase().includes(term))
    );
  });

  const columns = [
    {
      key: 'code',
      header: 'Consignment Code',
      render: (c: CargoConsignment) => (
        <EntityCode code={c.code} onClick={() => setSelectedId(c.id)} />
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (c: CargoConsignment) => <StatusBadge status={c.status} />,
    },
    {
      key: 'risk_level',
      header: 'Risk Level',
      render: (c: CargoConsignment) => <RiskBadge level={c.risk_level as CargoRiskLevel} />,
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (c: CargoConsignment) => (
        <span className="font-mono text-xs text-slate-300">P{c.priority}</span>
      ),
    },
    {
      key: 'route',
      header: 'Origin → Destination',
      render: (c: CargoConsignment) => (
        <span className="font-mono text-xs text-slate-400">
          {c.origin_location_id.slice(0, 8)}… → {c.destination_location_id.slice(0, 8)}…
        </span>
      ),
    },
    {
      key: 'required_by_at',
      header: 'Required By',
      render: (c: CargoConsignment) => (
        <span className="font-mono text-xs text-slate-400">
          {new Date(c.required_by_at).toLocaleDateString()}
        </span>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Cargo Consignments"
        subtitle="Operational cargo manifests, transit tracking, and schedule risk"
        actions={
          <div className="flex items-center gap-2">
            <Package className="w-4 h-4 text-cyan-400" aria-hidden="true" />
            <span className="text-slate-400 text-xs">{filtered.length} consignments</span>
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
            placeholder="Search consignment code…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search consignments"
            className="pl-9 pr-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:border-cyan-600 w-64"
          />
        </div>

        {/* Status dropdown */}
        <div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by cargo status"
            className="px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-xs font-medium focus:outline-none focus:border-cyan-600"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Risk level filter pills */}
        <div className="flex items-center gap-1" role="group" aria-label="Filter by risk level">
          {RISK_FILTERS.map((r) => (
            <button
              key={r.value}
              type="button"
              onClick={() => setRiskFilter(r.value)}
              aria-pressed={riskFilter === r.value}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                riskFilter === r.value
                  ? 'bg-cyan-900/60 border-cyan-700 text-cyan-300'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              {r.label}
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
            <ErrorDisplay error={error} title="Failed to load cargo consignments" />
          </div>
        )}
        {!isLoading && !error && filtered.length === 0 && (
          <EmptyState
            title="No consignments found"
            message="No cargo consignments match the selected search or filter criteria."
            icon={<AlertCircle className="w-12 h-12 text-slate-500" />}
          />
        )}
        {!isLoading && !error && filtered.length > 0 && (
          <OperationalTable
            columns={columns}
            data={filtered}
            getRowKey={(c) => c.id}
            onRowClick={(c) => setSelectedId(c.id)}
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
          <ConsignmentDetailPanel
            consignmentId={selectedId}
            onClose={() => setSelectedId(null)}
          />
        </>
      )}
    </div>
  );
}
