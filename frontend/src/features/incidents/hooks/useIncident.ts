import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { Incident } from '../../../lib/types/api';

export function useIncident(incidentId: string | null) {
  return useQuery({
    queryKey: ['incident', incidentId],
    queryFn: async () => {
      if (!incidentId) return null;
      const raw = await apiClient.get<Record<string, unknown>>(`/incidents/${incidentId}`);
      if (!raw) return null;
      return {
        ...raw,
        code: (raw.incident_code as string) ?? (raw.code as string) ?? '',
        incident_type: (raw.type as string) ?? (raw.incident_type as string) ?? '',
      } as unknown as Incident;
    },
    enabled: !!incidentId,
  });
}
