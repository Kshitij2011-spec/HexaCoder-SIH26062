import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { MaintenanceRecord } from '../../../lib/types/api';

export function useMaintenanceRecords(assetId: string | null) {
  return useQuery({
    queryKey: ['asset-maintenance', assetId],
    queryFn: async () => {
      if (!assetId) return [];
      const data = await apiClient.get<MaintenanceRecord[]>(`/assets/${assetId}/maintenance`);
      return data ?? [];
    },
    enabled: !!assetId,
  });
}
