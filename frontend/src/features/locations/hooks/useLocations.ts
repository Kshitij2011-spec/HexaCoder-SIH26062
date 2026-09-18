import { useQuery } from '@tanstack/react-query';
import { apiClient, buildQuery } from '../../../lib/api/client';
import type { Location } from '../../../lib/types/api';

export interface LocationFilters {
  type?: string;
  status?: string;
  parent_location_id?: string;
  page?: number;
  page_size?: number;
}

export function useLocations(filters: LocationFilters = {}) {
  const query = buildQuery({ ...filters, page: filters.page ?? 1, page_size: filters.page_size ?? 50 });
  return useQuery<Location[]>({
    queryKey: ['locations', filters],
    queryFn: ({ signal }) => apiClient.get<Location[]>(`/locations${query}`, signal),
  });
}
