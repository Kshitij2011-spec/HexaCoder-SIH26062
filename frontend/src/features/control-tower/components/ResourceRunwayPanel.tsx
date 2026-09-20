import React, { useState } from 'react';
import {
  Fuel,
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Clock,
  MinusCircle,
  Package,
  RotateCcw,
  TrendingDown,
  Calendar,
  Layers,
  Info,
} from 'lucide-react';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { EntityCode } from '../../../components/shared/EntityCode';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../../components/shared/ErrorDisplay';
import { useResourceRunways } from '../hooks/useResourceRunways';
import type { ResourceRunwayItem, RunwayState } from '../../../lib/types/api';

export interface ResourceRunwayPanelProps {
  expeditionId: string;
  onInitiateReplan?: (item: ResourceRunwayItem) => void;
}

const formatDate = (dateStr?: string | null): string => {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toISOString().replace('T', ' ').slice(0, 16) + ' UTC';
  } catch {
    return dateStr;
  }
};

const formatNumber = (val: string | number | null | undefined, decimals: number = 1): string => {
  if (val === null || val === undefined) return '—';
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return '—';
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

interface RunwayStateConfig {
  label: string;
  badgeClass: string;
  cardBorderClass: string;
  icon: React.ComponentType<{ className?: string }>;
}

const RUNWAY_STATE_CONFIGS: Record<RunwayState, RunwayStateConfig> = {
  RESUPPLY_GAP: {
    label: 'RESUPPLY GAP',
    badgeClass: 'bg-rose-950/80 text-rose-300 border-rose-600/80',
    cardBorderClass: 'border-rose-700/60 bg-gradient-to-br from-rose-950/20 to-slate-900/60',
    icon: AlertOctagon,
  },
  NO_INBOUND_SCHEDULED: {
    label: 'NO INBOUND SCHEDULED',
    badgeClass: 'bg-amber-950/80 text-amber-300 border-amber-600/80',
    cardBorderClass: 'border-amber-700/60 bg-gradient-to-br from-amber-950/20 to-slate-900/60',
    icon: Clock,
  },
  AT_RISK: {
    label: 'AT RISK',
    badgeClass: 'bg-yellow-950/80 text-yellow-300 border-yellow-600/80',
    cardBorderClass: 'border-yellow-700/60 bg-gradient-to-br from-yellow-950/20 to-slate-900/60',
    icon: AlertTriangle,
  },
  COVERED: {
    label: 'COVERED',
    badgeClass: 'bg-emerald-950/80 text-emerald-300 border-emerald-600/80',
    cardBorderClass: 'border-emerald-800/50 bg-gradient-to-br from-emerald-950/15 to-slate-900/60',
    icon: CheckCircle2,
  },
  NO_CONSUMPTION_OBSERVED: {
    label: 'NO CONSUMPTION',
    badgeClass: 'bg-slate-800 text-slate-400 border-slate-700',
    cardBorderClass: 'border-slate-800 bg-slate-900/40',
    icon: MinusCircle,
  },
};

const getBurnRateSourceLabel = (source: string): string => {
  switch (source) {
    case 'OBSERVED_TRANSACTIONS_14D':
      return '14-Day Issues';
    case 'CATALOG_BASELINE':
      return 'Catalog Baseline';
    case 'NO_CONSUMPTION_OBSERVED':
      return 'Zero Consumption';
    default:
      return source;
  }
};

export function ResourceRunwayPanel({ expeditionId, onInitiateReplan }: ResourceRunwayPanelProps) {
  const { data: summary, isLoading, error } = useResourceRunways(expeditionId);
  const [filterState, setFilterState] = useState<string>('ALL');

  if (isLoading) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Fuel className="h-5 w-5 text-indigo-400" />
            <span className="font-semibold text-slate-200">Polar Consumables & Utility Runway</span>
          </div>
        </div>
        <LoadingSkeleton lines={4} />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorDisplay
        error={error}
        title="Failed to evaluate polar resource runway projections"
      />
    );
  }

  const runways = summary?.runways ?? [];
  const filteredRunways = runways.filter((r) => {
    if (filterState === 'ALL') return true;
    if (filterState === 'GAPS') return r.runway_state === 'RESUPPLY_GAP';
    if (filterState === 'AT_RISK') return r.runway_state === 'AT_RISK' || r.runway_state === 'NO_INBOUND_SCHEDULED';
    if (filterState === 'COVERED') return r.runway_state === 'COVERED';
    return true;
  });

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-5">
      {/* ─── Header & Compact Provenance Note ─── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <Fuel className="h-5 w-5 text-indigo-400" />
            <h3 className="text-base font-semibold text-slate-100">
              Polar Consumables & Utility Runway
            </h3>
            <ProvenanceTag provenance={summary?.data_provenance ?? 'DERIVED'} />
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
            <Info className="h-3.5 w-3.5 text-slate-500 shrink-0" />
            Runway is projected from recorded inventory issues and scheduled inbound stock.
          </p>
        </div>

        {/* ─── Filter Pills ─── */}
        <div className="flex items-center gap-1.5 bg-slate-950/60 p-1 rounded-lg border border-slate-800 self-start sm:self-auto text-xs">
          <button
            type="button"
            onClick={() => setFilterState('ALL')}
            className={`px-2.5 py-1 rounded-md transition-colors ${
              filterState === 'ALL'
                ? 'bg-slate-800 text-slate-100 font-medium'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All ({runways.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterState('GAPS')}
            className={`px-2.5 py-1 rounded-md transition-colors ${
              filterState === 'GAPS'
                ? 'bg-rose-950/80 text-rose-300 font-medium'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Resupply Gaps ({summary?.items_with_resupply_gap ?? 0})
          </button>
          <button
            type="button"
            onClick={() => setFilterState('AT_RISK')}
            className={`px-2.5 py-1 rounded-md transition-colors ${
              filterState === 'AT_RISK'
                ? 'bg-yellow-950/80 text-yellow-300 font-medium'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            At Risk ({summary?.items_at_risk ?? 0})
          </button>
          <button
            type="button"
            onClick={() => setFilterState('COVERED')}
            className={`px-2.5 py-1 rounded-md transition-colors ${
              filterState === 'COVERED'
                ? 'bg-emerald-950/80 text-emerald-300 font-medium'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Covered
          </button>
        </div>
      </div>

      {/* ─── Campaign Summary Metrics ─── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">Monitored Lots</span>
            <Package className="h-4 w-4 text-slate-500" />
          </div>
          <div className="text-xl font-bold text-slate-200 mt-1">
            {summary?.total_candidates ?? 0}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Consumable stocks</div>
        </div>

        <div
          className={`border rounded-lg p-3 ${
            (summary?.items_with_resupply_gap ?? 0) > 0
              ? 'bg-rose-950/30 border-rose-800/60'
              : 'bg-slate-950/50 border-slate-800/80'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">Resupply Gaps</span>
            <AlertOctagon
              className={`h-4 w-4 ${
                (summary?.items_with_resupply_gap ?? 0) > 0
                  ? 'text-rose-400 animate-pulse'
                  : 'text-slate-500'
              }`}
            />
          </div>
          <div
            className={`text-xl font-bold mt-1 ${
              (summary?.items_with_resupply_gap ?? 0) > 0 ? 'text-rose-300' : 'text-slate-200'
            }`}
          >
            {summary?.items_with_resupply_gap ?? 0}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Exhaustion &lt; Inbound</div>
        </div>

        <div
          className={`border rounded-lg p-3 ${
            (summary?.items_at_risk ?? 0) > 0
              ? 'bg-yellow-950/30 border-yellow-800/60'
              : 'bg-slate-950/50 border-slate-800/80'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">At Risk / No Inbound</span>
            <AlertTriangle
              className={`h-4 w-4 ${
                (summary?.items_at_risk ?? 0) > 0 ? 'text-yellow-400' : 'text-slate-500'
              }`}
            />
          </div>
          <div
            className={`text-xl font-bold mt-1 ${
              (summary?.items_at_risk ?? 0) > 0 ? 'text-yellow-300' : 'text-slate-200'
            }`}
          >
            {summary?.items_at_risk ?? 0}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Lead-time or buffer breach</div>
        </div>

        <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">Minimum Runway</span>
            <TrendingDown className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="text-xl font-bold text-slate-200 mt-1">
            {summary?.minimum_runway_days != null
              ? `${summary.minimum_runway_days.toFixed(1)} d`
              : '—'}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Earliest depletion horizon</div>
        </div>
      </div>

      {/* ─── Resource Cards Grid ─── */}
      {filteredRunways.length === 0 ? (
        <div className="text-center py-8 border border-dashed border-slate-800 rounded-lg">
          <p className="text-sm text-slate-400">
            {filterState === 'ALL'
              ? 'No consumable inventory items tracked for this expedition.'
              : `No consumable items matching the filter "${filterState}".`}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredRunways.map((item) => {
            const stateConfig =
              RUNWAY_STATE_CONFIGS[item.runway_state] ??
              RUNWAY_STATE_CONFIGS.NO_CONSUMPTION_OBSERVED;
            const StateIcon = stateConfig.icon;
            const isActionable =
              item.runway_state === 'RESUPPLY_GAP' ||
              item.runway_state === 'AT_RISK' ||
              item.runway_state === 'NO_INBOUND_SCHEDULED';

            return (
              <div
                key={item.stock_lot_id}
                className={`border rounded-xl p-4 flex flex-col justify-between transition-all ${stateConfig.cardBorderClass}`}
                data-testid={`runway-card-${item.item_code}`}
              >
                <div>
                  {/* Top line: Name, Code, Badges */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-slate-100 text-sm">
                          {item.item_name}
                        </span>
                        <EntityCode code={item.item_code} />
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                          {item.category}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/80 border border-slate-700/60 text-slate-400">
                          {item.criticality}
                        </span>
                      </div>
                      <div className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                        <span>Loc: {item.location_name || item.location_id}</span>
                        {item.lot_code && <span>• Lot: {item.lot_code}</span>}
                      </div>
                    </div>

                    {/* State Badge */}
                    <div
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border shrink-0 ${stateConfig.badgeClass}`}
                    >
                      <StateIcon className="h-3 w-3" />
                      <span>{stateConfig.label}</span>
                    </div>
                  </div>

                  {/* Operational Metrics Grid */}
                  <div className="grid grid-cols-3 gap-2 mt-4 bg-slate-950/60 rounded-lg p-2.5 border border-slate-800/70 text-xs">
                    <div>
                      <div className="text-[10px] text-slate-400 flex items-center justify-between">
                        <span>Available</span>
                        <ProvenanceTag provenance="MEASURED" className="text-[9px] px-1" />
                      </div>
                      <div className="font-mono font-bold text-slate-100 text-sm mt-0.5">
                        {formatNumber(item.available_quantity)} {item.unit}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        OH: {formatNumber(item.on_hand_quantity, 0)} | Res: {formatNumber(item.reserved_quantity, 0)}
                      </div>
                    </div>

                    <div>
                      <div className="text-[10px] text-slate-400 flex items-center justify-between">
                        <span>Burn Rate</span>
                        <ProvenanceTag provenance="DERIVED" className="text-[9px] px-1" />
                      </div>
                      <div className="font-mono font-bold text-slate-100 text-sm mt-0.5">
                        {formatNumber(item.daily_burn_rate)} {item.unit}/d
                      </div>
                      <div className="text-[10px] text-slate-500 truncate" title={item.burn_rate_source}>
                        {getBurnRateSourceLabel(item.burn_rate_source)}
                      </div>
                    </div>

                    <div>
                      <div className="text-[10px] text-slate-400 flex items-center justify-between">
                        <span>Runway</span>
                        <ProvenanceTag provenance="FORECAST" className="text-[9px] px-1" />
                      </div>
                      <div
                        className={`font-mono font-bold text-sm mt-0.5 ${
                          item.runway_days == null
                            ? 'text-slate-400'
                            : item.runway_days < 7
                            ? 'text-rose-400'
                            : item.runway_days < 14
                            ? 'text-yellow-400'
                            : 'text-emerald-400'
                        }`}
                      >
                        {item.runway_days !== null && item.runway_days !== undefined
                          ? `${item.runway_days.toFixed(1)} days`
                          : 'Indefinite'}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        {item.reorder_buffer_days != null
                          ? `Buf: ${item.reorder_buffer_days.toFixed(1)}d`
                          : 'No buffer'}
                      </div>
                    </div>
                  </div>

                  {/* Horizon Timeline Details */}
                  <div className="mt-3 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between text-slate-300">
                      <span className="text-slate-400 flex items-center gap-1">
                        <TrendingDown className="h-3 w-3 text-slate-500" />
                        Projected Exhaustion:
                      </span>
                      <div className="flex items-center gap-1.5 font-mono">
                        <span>{formatDate(item.exhaustion_at)}</span>
                        {item.exhaustion_at && (
                          <ProvenanceTag provenance="FORECAST" className="text-[8px] px-1" />
                        )}
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-slate-300">
                      <span className="text-slate-400 flex items-center gap-1">
                        <Calendar className="h-3 w-3 text-slate-500" />
                        Next Resupply Inbound:
                      </span>
                      <div className="flex items-center gap-1.5 font-mono">
                        <span className={item.next_inbound_at ? 'text-slate-200' : 'text-slate-500'}>
                          {formatDate(item.next_inbound_at)}
                        </span>
                        {item.next_inbound_at && (
                          <ProvenanceTag provenance="MEASURED" className="text-[8px] px-1" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Resupply Gap Critical Notice */}
                  {item.resupply_gap_days > 0 && (
                    <div className="mt-3 bg-rose-950/70 border border-rose-700/80 rounded-lg p-2.5 flex items-start gap-2">
                      <AlertOctagon className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                      <div className="text-xs">
                        <span className="font-semibold text-rose-200">
                          Resupply Gap Deficit: {item.resupply_gap_days.toFixed(1)} days
                        </span>
                        <p className="text-[11px] text-rose-300/90 mt-0.5">
                          Stockout is projected {item.resupply_gap_days.toFixed(1)} days before the next replenishment arrival.
                        </p>
                      </div>
                    </div>
                  )}

                  {item.runway_state === 'NO_INBOUND_SCHEDULED' && (
                    <div className="mt-3 bg-amber-950/60 border border-amber-700/60 rounded-lg p-2 flex items-start gap-2 text-xs text-amber-200">
                      <Clock className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                      <span>Stock breaching reorder/lead buffer with no inbound shipment scheduled.</span>
                    </div>
                  )}
                </div>

                {/* Card Action Footer */}
                {isActionable && onInitiateReplan && (
                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-[11px] text-slate-400 flex items-center gap-1">
                      <Layers className="h-3 w-3 text-slate-500" />
                      Actionable operational deficit
                    </span>
                    <button
                      type="button"
                      onClick={() => onInitiateReplan(item)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-950/90 hover:bg-rose-900 border border-rose-700/80 text-rose-200 transition-colors shadow-sm focus:outline-none focus:ring-1 focus:ring-rose-500"
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                      <span>Initiate Replan</span>
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
export default ResourceRunwayPanel;
