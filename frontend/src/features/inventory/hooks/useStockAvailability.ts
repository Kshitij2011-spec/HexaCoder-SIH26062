import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { StockAvailability } from '../../../lib/types/api';

export function useStockAvailability(stockLotId: string | null) {
  return useQuery({
    queryKey: ['stock-availability', stockLotId],
    queryFn: async () => {
      if (!stockLotId) return null;
      const raw = await apiClient.get<Record<string, unknown>>(`/inventory/stock-lots/${stockLotId}/availability`);
      if (!raw) return null;
      return {
        ...raw,
        on_hand_quantity: String(raw.on_hand_quantity ?? '0'),
        reserved_quantity: String(raw.reserved_quantity ?? '0'),
        quarantined_quantity: String(raw.quarantined_quantity ?? '0'),
        damaged_quantity: String(raw.damaged_quantity ?? '0'),
        available_quantity: String(raw.available_quantity ?? '0'),
        reorder_point: raw.reorder_point != null ? String(raw.reorder_point) : null,
      } as unknown as StockAvailability;
    },
    enabled: !!stockLotId,
  });
}
