import { useQuery } from '@tanstack/react-query';
import { apiClient, buildQuery } from '../../../lib/api/client';
import type { Incident, IncidentStatus, IncidentSeverity } from '../../../lib/types/api';

export interface IncidentFilters {
  severity?: IncidentSeverity;
  status?: IncidentStatus;
  incident_type?: string;
}

export function useIncidents(filters?: IncidentFilters) {
  return useQuery({
    queryKey: ['incidents', filters],
    queryFn: async () => {
      const query = buildQuery({
        severity: filters?.severity,
        status: filters?.status,
        incident_type: filters?.incident_type,
      });
      const data = await apiClient.get<Record<string, unknown>[]>(`/incidents${query}`);
      return (data ?? []).map((raw) => ({
        ...raw,
        code: (raw.incident_code as string) ?? (raw.code as string) ?? '',
        incident_type: (raw.type as string) ?? (raw.incident_type as string) ?? '',
      })) as unknown as Incident[];
    },
  });
}
