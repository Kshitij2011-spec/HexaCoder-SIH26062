import { useQuery } from '@tanstack/react-query';
import { apiClient, buildQuery } from '../../../lib/api/client';
import type { InventoryItem, ItemCriticality } from '../../../lib/types/api';

export interface InventoryItemFilters {
  category?: string;
  criticality?: ItemCriticality;
}

export function useInventoryItems(filters?: InventoryItemFilters) {
  return useQuery({
    queryKey: ['inventory-items', filters],
    queryFn: async () => {
      const query = buildQuery({
        category: filters?.category,
        criticality: filters?.criticality,
      });
      const data = await apiClient.get<Record<string, unknown>[]>(`/inventory/items${query}`);
      return (data ?? []).map((raw) => ({
        ...raw,
        code: (raw.item_code as string) ?? (raw.code as string) ?? '',
        name: (raw.item_name as string) ?? (raw.name as string) ?? '',
        unit_of_measure: (raw.unit as string) ?? (raw.unit_of_measure as string) ?? 'UNIT',
      })) as unknown as InventoryItem[];
    },
  });
}
