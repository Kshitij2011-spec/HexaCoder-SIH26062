import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { Location } from '../../../lib/types/api';

export function useLocation(id: string | null) {
  return useQuery<Location>({
    queryKey: ['location', id],
    queryFn: ({ signal }) => apiClient.get<Location>(`/locations/${id}`, signal),
    enabled: !!id,
  });
}
