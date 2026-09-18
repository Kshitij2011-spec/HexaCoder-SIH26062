import { useQuery } from '@tanstack/react-query';
import { apiClient, buildQuery } from '../../../lib/api/client';
import type { CargoConsignment } from '../../../lib/types/api';

export interface ConsignmentFilters {
  status?: string;
  risk_level?: string;
  page?: number;
  page_size?: number;
}

export function useConsignments(filters: ConsignmentFilters = {}) {
  const query = buildQuery({ ...filters, page: filters.page ?? 1, page_size: filters.page_size ?? 50 });
  return useQuery<CargoConsignment[]>({
    queryKey: ['cargo-consignments', filters],
    queryFn: ({ signal }) => apiClient.get<CargoConsignment[]>(`/cargo/consignments${query}`, signal),
  });
}
