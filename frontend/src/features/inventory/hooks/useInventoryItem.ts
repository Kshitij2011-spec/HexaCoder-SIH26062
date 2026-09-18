import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { InventoryItem } from '../../../lib/types/api';

export function useInventoryItem(itemId: string | null) {
  return useQuery({
    queryKey: ['inventory-item', itemId],
    queryFn: async () => {
      if (!itemId) return null;
      const raw = await apiClient.get<Record<string, unknown>>(`/inventory/items/${itemId}`);
      if (!raw) return null;
      return {
        ...raw,
        code: (raw.item_code as string) ?? (raw.code as string) ?? '',
        name: (raw.item_name as string) ?? (raw.name as string) ?? '',
        unit_of_measure: (raw.unit as string) ?? (raw.unit_of_measure as string) ?? 'UNIT',
      } as unknown as InventoryItem;
    },
    enabled: !!itemId,
  });
}
