import { AlertTriangle } from 'lucide-react';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { EntityCode } from '../../components/shared/EntityCode';
import type { InventoryStockLot } from '../../lib/types/api';

interface Props {
  lots: InventoryStockLot[];
  selectedLotId?: string | null;
  onSelectLot: (lot: InventoryStockLot) => void;
}

export function StockLotsTable({ lots, selectedLotId, onSelectLot }: Props) {
  if (lots.length === 0) {
    return (
      <div className="p-8 text-center text-slate-500 font-mono text-sm border border-slate-800 rounded-lg bg-slate-900/30">
        No stock lots found for this item.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-left text-sm" role="table" aria-label="Stock lots table">
        <thead className="bg-slate-900 text-xs font-mono text-slate-400 uppercase tracking-wider border-b border-slate-800">
          <tr>
            <th className="px-4 py-3">Lot Number</th>
            <th className="px-4 py-3">Location</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3 text-right">On Hand</th>
            <th className="px-4 py-3 text-right">Available</th>
            <th className="px-4 py-3 text-right">Reserved</th>
            <th className="px-4 py-3 text-center">Deficit</th>
            <th className="px-4 py-3">Expiry</th>
            <th className="px-4 py-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
          {lots.map((lot) => {
            const isSelected = selectedLotId === lot.id;
            return (
              <tr
                key={lot.id}
                className={`transition-colors hover:bg-slate-800/40 ${
                  isSelected ? 'bg-cyan-950/30' : ''
                }`}
              >
                <td className="px-4 py-3 font-semibold text-slate-200">
                  <EntityCode code={lot.lot_number} />
                </td>
                <td className="px-4 py-3 text-slate-400 truncate max-w-[120px]" title={lot.location_id}>
                  {lot.location_id.slice(0, 8)}...
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={lot.status} />
                </td>
                <td className="px-4 py-3 text-right text-slate-300">
                  {lot.on_hand_quantity}
                </td>
                <td className="px-4 py-3 text-right font-semibold text-emerald-400">
                  {lot.available_quantity}
                </td>
                <td className="px-4 py-3 text-right text-amber-300">
                  {lot.reserved_quantity}
                </td>
                <td className="px-4 py-3 text-center">
                  {lot.is_deficit ? (
                    <span className="inline-flex items-center text-rose-400 font-bold" title="Deficit: Available below reorder threshold">
                      <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
                    </span>
                  ) : (
                    <span className="text-slate-600">-</span>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {lot.expiry_date ? new Date(lot.expiry_date).toLocaleDateString() : 'N/A'}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    onClick={() => onSelectLot(lot)}
                    className={`px-2.5 py-1 rounded text-xs transition-colors ${
                      isSelected
                        ? 'bg-cyan-700 text-cyan-100'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                    }`}
                    aria-label={`Select lot ${lot.lot_number}`}
                  >
                    {isSelected ? 'Active' : 'Manage'}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
