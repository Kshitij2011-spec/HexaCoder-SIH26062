import { useQuery } from '@tanstack/react-query';
import { apiClient, buildQuery } from '../../../lib/api/client';
import type { Asset, AssetStatus, AssetCriticality } from '../../../lib/types/api';

export interface AssetFilters {
  type?: string;
  status?: AssetStatus;
  criticality?: AssetCriticality;
  location_id?: string;
}

export function useAssets(filters?: AssetFilters) {
  return useQuery({
    queryKey: ['assets', filters],
    queryFn: async () => {
      const query = buildQuery({
        type: filters?.type,
        status: filters?.status,
        criticality: filters?.criticality,
        location_id: filters?.location_id,
      });
      const data = await apiClient.get<Record<string, unknown>[]>(`/assets${query}`);
      return (data ?? []).map((raw) => ({
        ...raw,
        code: (raw.asset_code as string) ?? (raw.code as string) ?? '',
        location_id: (raw.location_id as string) ?? (raw.current_location_id as string) ?? '',
      })) as unknown as Asset[];
    },
  });
}
