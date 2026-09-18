import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { IncidentTimeline } from '../../../lib/types/api';

export function useIncidentTimeline(incidentId: string | null) {
  return useQuery({
    queryKey: ['incident-timeline', incidentId],
    queryFn: async () => {
      if (!incidentId) return null;
      return await apiClient.get<IncidentTimeline>(`/incidents/${incidentId}/timeline`);
    },
    enabled: !!incidentId,
  });
}
