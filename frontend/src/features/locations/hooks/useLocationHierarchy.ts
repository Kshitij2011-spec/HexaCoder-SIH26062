import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { LocationHierarchy } from '../../../lib/types/api';

export function useLocationHierarchy(id: string | null) {
  return useQuery<LocationHierarchy>({
    queryKey: ['location-hierarchy', id],
    queryFn: ({ signal }) => apiClient.get<LocationHierarchy>(`/locations/${id}/hierarchy`, signal),
    enabled: !!id,
  });
}
