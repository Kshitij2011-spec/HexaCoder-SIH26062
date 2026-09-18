import { useQuery } from '@tanstack/react-query';
import { apiClient, buildQuery } from '../../../lib/api/client';
import type { InventoryStockLot, InventoryStatus } from '../../../lib/types/api';

export interface StockLotFilters {
  inventory_item_id?: string;
  location_id?: string;
  status?: InventoryStatus;
}

export function useStockLots(filters?: StockLotFilters) {
  return useQuery({
    queryKey: ['stock-lots', filters],
    queryFn: async () => {
      const query = buildQuery({
        inventory_item_id: filters?.inventory_item_id,
        location_id: filters?.location_id,
        status: filters?.status,
      });
      const data = await apiClient.get<Record<string, unknown>[]>(`/inventory/stock-lots${query}`);
      return (data ?? []).map((raw) => ({
        ...raw,
        lot_number: (raw.lot_code as string) ?? (raw.lot_number as string) ?? 'LOT-DEFAULT',
        on_hand_quantity: String(raw.on_hand_quantity ?? '0'),
        reserved_quantity: String(raw.reserved_quantity ?? '0'),
        quarantined_quantity: String(raw.quarantined_quantity ?? '0'),
        damaged_quantity: String(raw.damaged_quantity ?? '0'),
        available_quantity: String(raw.available_quantity ?? '0'),
        reorder_point: raw.reorder_point != null ? String(raw.reorder_point) : null,
      })) as unknown as InventoryStockLot[];
    },
  });
}
