import { useQuery } from '@tanstack/react-query';
import { apiClient, buildQuery } from '../../../lib/api/client';
import type { TimelineResponse } from '../../../lib/types/api';

export interface UseOperationalTimelineOptions {
  includeRelated?: boolean;
  order?: 'desc' | 'asc';
  page?: number;
  pageSize?: number;
  entryType?: string;
  occurredFrom?: string;
  occurredTo?: string;
}

export function useOperationalTimeline(
  entityType: string | null,
  entityId: string | null,
  options: UseOperationalTimelineOptions = {},
) {
  const {
    includeRelated = false,
    order = 'desc',
    page = 1,
    pageSize = 50,
    entryType,
    occurredFrom,
    occurredTo,
  } = options;

  return useQuery({
    queryKey: [
      'operational-timeline',
      entityType,
      entityId,
      includeRelated,
      order,
      page,
      pageSize,
      entryType,
      occurredFrom,
      occurredTo,
    ],
    queryFn: async () => {
      if (!entityType || !entityId) return null;
      const query = buildQuery({
        include_related: includeRelated ? 'true' : undefined,
        order,
        page,
        page_size: pageSize,
        entry_type: entryType || undefined,
        occurred_from: occurredFrom || undefined,
        occurred_to: occurredTo || undefined,
      });
      return await apiClient.get<TimelineResponse>(
        `/operations/timeline/${entityType}/${entityId}${query}`,
      );
    },
    enabled: !!entityType && !!entityId,
  });
}
