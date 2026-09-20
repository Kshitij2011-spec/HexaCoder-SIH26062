import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { ResourceRunwaySummary } from '../../../lib/types/api';

export const runwayKeys = {
  all: ['control-tower', 'runways'] as const,
  expedition: (expeditionId?: string) =>
    ['control-tower', 'expeditions', expeditionId, 'runways'] as const,
};

export function useResourceRunways(expeditionId?: string) {
  return useQuery({
    queryKey: runwayKeys.expedition(expeditionId),
    queryFn: async () => {
      if (!expeditionId) return null;
      return await apiClient.get<ResourceRunwaySummary>(
        `/control-tower/expeditions/${expeditionId}/runways`
      );
    },
    enabled: Boolean(expeditionId),
    refetchInterval: 30_000,
    staleTime: 10_000,
  });
}
