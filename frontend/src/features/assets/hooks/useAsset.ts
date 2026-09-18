import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { Asset } from '../../../lib/types/api';

export function useAsset(assetId: string | null) {
  return useQuery({
    queryKey: ['asset', assetId],
    queryFn: async () => {
      if (!assetId) return null;
      const raw = await apiClient.get<Record<string, unknown>>(`/assets/${assetId}`);
      if (!raw) return null;
      return {
        ...raw,
        code: (raw.asset_code as string) ?? (raw.code as string) ?? '',
        location_id: (raw.location_id as string) ?? (raw.current_location_id as string) ?? '',
      } as unknown as Asset;
    },
    enabled: !!assetId,
  });
}
