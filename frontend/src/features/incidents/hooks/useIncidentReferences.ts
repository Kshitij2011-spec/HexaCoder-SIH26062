import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { IncidentReference } from '../../../lib/types/api';

export function useIncidentReferences(incidentId: string | null) {
  return useQuery({
    queryKey: ['incident-references', incidentId],
    queryFn: async () => {
      if (!incidentId) return [];
      const data = await apiClient.get<IncidentReference[]>(`/incidents/${incidentId}/references`);
      return data ?? [];
    },
    enabled: !!incidentId,
  });
}
