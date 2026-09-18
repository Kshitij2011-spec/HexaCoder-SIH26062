import { useState } from 'react';
import { X, Box, Layers, History, ShieldAlert } from 'lucide-react';
import { EntityCode } from '../../components/shared/EntityCode';
import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { StockLotsTable } from './StockLotsTable';
import { AvailabilityIndicator } from './AvailabilityIndicator';
import { InventoryTransactionsTable } from './InventoryTransactionsTable';
import { InventoryActions } from './InventoryActions';
import { useStockLots } from './hooks/useStockLots';
import { useStockAvailability } from './hooks/useStockAvailability';
import { useInventoryTransactions } from './hooks/useInventoryTransactions';
import type { InventoryItem, InventoryStockLot } from '../../lib/types/api';

interface Props {
  item: InventoryItem | null;
  onClose: () => void;
}

export function InventoryDetailPanel({ item, onClose }: Props) {
  const [selectedLot, setSelectedLot] = useState<InventoryStockLot | null>(null);

  const {
    data: stockLots = [],
    isLoading: isLotsLoading,
    error: lotsError,
    refetch: refetchLots,
  } = useStockLots(item ? { inventory_item_id: item.id } : undefined);

  // Active lot availability & transactions
  const activeLotId = selectedLot?.id ?? stockLots[0]?.id ?? null;
  const activeLot = stockLots.find((l: InventoryStockLot) => l.id === activeLotId) ?? stockLots[0] ?? null;

  const {
    data: availability,
    isLoading: isAvailLoading,
    refetch: refetchAvail,
  } = useStockAvailability(activeLotId);

  const {
    data: transactions = [],
    isLoading: isTxLoading,
    refetch: refetchTx,
  } = useInventoryTransactions(activeLotId);

  if (!item) return null;

  const handleRefreshActiveLot = () => {
    refetchLots();
    if (activeLotId) {
      refetchAvail();
      refetchTx();
    }
  };

  return (
    <div
      className="fixed inset-y-0 right-0 w-full max-w-2xl bg-slate-950 border-l border-slate-800 shadow-2xl z-50 flex flex-col overflow-hidden"
      role="dialog"
      aria-modal="true"
      aria-label={`Inventory details for ${item.name}`}
    >
      {/* Drawer Header */}
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
        <div className="flex items-center gap-3">
          <Box className="w-5 h-5 text-cyan-400" aria-hidden="true" />
          <div>
            <div className="flex items-center gap-2">
              <EntityCode code={item.code} />
              <ProvenanceTag provenance={item.data_provenance} />
            </div>
            <h2 className="text-base font-semibold text-slate-100 mt-0.5">{item.name}</h2>
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
        {/* Item Metadata */}
        <section className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 text-xs font-mono">
          <h3 className="text-slate-400 uppercase tracking-wider text-[11px] mb-3 font-semibold">
            Item Specifications
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <span className="text-slate-500">Category:</span>
              <p className="text-slate-200 font-medium">{item.category}</p>
            </div>
            <div>
              <span className="text-slate-500">Criticality:</span>
              <p className="text-amber-400 font-medium">{item.criticality}</p>
            </div>
            <div>
              <span className="text-slate-500">Unit of Measure:</span>
              <p className="text-slate-200 font-medium">{item.unit_of_measure}</p>
            </div>
            {item.minimum_temperature_c && (
              <div>
                <span className="text-slate-500">Min Temp:</span>
                <p className="text-sky-300 font-medium">{item.minimum_temperature_c}°C</p>
              </div>
            )}
            {item.maximum_temperature_c && (
              <div>
                <span className="text-slate-500">Max Temp:</span>
                <p className="text-sky-300 font-medium">{item.maximum_temperature_c}°C</p>
              </div>
            )}
            {item.hazmat_class && (
              <div>
                <span className="text-slate-500">Hazmat:</span>
                <p className="text-rose-400 font-medium">{item.hazmat_class}</p>
              </div>
            )}
          </div>
          {item.description && (
            <p className="mt-3 pt-2 border-t border-slate-800/80 text-slate-400">
              {item.description}
            </p>
          )}
        </section>

        {/* Stock Lots Section */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" aria-hidden="true" />
              Stock Lots ({stockLots.length})
            </h3>
            <span className="text-xs text-slate-500 font-mono">Select a lot to inspect</span>
          </div>

          {isLotsLoading && <LoadingSkeleton lines={3} />}
          {lotsError && (
            <ErrorDisplay
              error={lotsError}
              title="Failed to load stock lots"
            />
          )}
          {!isLotsLoading && !lotsError && (
            <StockLotsTable
              lots={stockLots}
              selectedLotId={activeLot?.id}
              onSelectLot={(lot) => setSelectedLot(lot)}
            />
          )}
        </section>

        {/* Active Lot Management Section */}
        {activeLot && (
          <section className="space-y-4 pt-4 border-t border-slate-800">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-cyan-400" aria-hidden="true" />
                Active Lot: <span className="font-mono text-cyan-300">{activeLot.lot_number}</span>
              </h3>
              <span className="text-xs text-slate-400 font-mono">Location: {activeLot.location_id.slice(0, 8)}</span>
            </div>

            {/* Availability Indicator */}
            {isAvailLoading ? (
              <LoadingSkeleton lines={2} />
            ) : (
              <AvailabilityIndicator availability={availability} />
            )}

            {/* Operational Actions */}
            <div>
              <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">
                Lot Workflows & State Mutations
              </h4>
              <InventoryActions lot={activeLot} onActionComplete={handleRefreshActiveLot} />
            </div>

            {/* Transaction Ledger */}
            <div>
              <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                <History className="w-3.5 h-3.5 text-cyan-400" aria-hidden="true" />
                Immutable Transaction History
              </h4>
              <InventoryTransactionsTable transactions={transactions} isLoading={isTxLoading} />
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
