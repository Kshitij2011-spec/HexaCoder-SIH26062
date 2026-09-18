import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { InventoryTransaction } from '../../../lib/types/api';

export function useInventoryTransactions(stockLotId: string | null) {
  return useQuery({
    queryKey: ['inventory-transactions', stockLotId],
    queryFn: async () => {
      if (!stockLotId) return [];
      const data = await apiClient.get<Record<string, unknown>[]>(`/inventory/stock-lots/${stockLotId}/transactions`);
      return (data ?? []).map((raw) => ({
        ...raw,
        quantity: String(raw.quantity ?? '0'),
        balance_after: String(raw.balance_after ?? raw.quantity ?? '0'),
        reference_id: raw.reference_id ? String(raw.reference_id) : null,
        created_at: (raw.occurred_at as string) ?? (raw.created_at as string) ?? new Date().toISOString(),
      })) as unknown as InventoryTransaction[];
    },
    enabled: !!stockLotId,
  });
}
