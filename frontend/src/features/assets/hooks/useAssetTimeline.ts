import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { AssetTimeline } from '../../../lib/types/api';

export function useAssetTimeline(assetId: string | null) {
  return useQuery({
    queryKey: ['asset-timeline', assetId],
    queryFn: async () => {
      if (!assetId) return null;
      return await apiClient.get<AssetTimeline>(`/assets/${assetId}/timeline`);
    },
    enabled: !!assetId,
  });
}
