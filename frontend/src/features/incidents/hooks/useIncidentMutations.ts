import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type {
  Incident,
  IncidentReference,
  IncidentCreateRequest,
  IncidentUpdateRequest,
  IncidentStatusTransitionRequest,
  IncidentReferenceCreateRequest,
  IncidentEscalationRequest,
  IncidentEscalationResult,
} from '../../../lib/types/api';
import { syncManager } from '../../../lib/sync/syncManager';
import type { OutboxOperation } from '../../../lib/sync/types';

export function useCreateIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: IncidentCreateRequest) => {
      return await apiClient.post<Incident>('/incidents', payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}

export function useUpdateIncident(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: IncidentUpdateRequest) => {
      return await apiClient.patch<Incident>(`/incidents/${incidentId}`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incident-timeline', incidentId] });
    },
  });
}

export function useAcknowledgeIncident(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      // If offline or simulated blackout is active, buffer in local outbox without network request
      if (!syncManager.isEffectiveOnline()) {
        const clientOpId =
          typeof crypto !== 'undefined' && crypto.randomUUID
            ? crypto.randomUUID()
            : `op-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

        const cachedIncident =
          queryClient.getQueryData<Incident>(['incident', incidentId]) ||
          queryClient.getQueryData<Incident[]>(['incidents'])?.find((i) => i.id === incidentId);

        const op: OutboxOperation = {
          client_operation_id: clientOpId,
          entity_type: 'INCIDENT',
          entity_id: incidentId,
          operation_type: 'STATE_TRANSITION',
          payload: {
            id: incidentId,
            entity_id: incidentId,
            action: 'ACKNOWLEDGE',
            target_status: 'ACKNOWLEDGED',
            incident_code: cachedIncident?.code,
          },
          queued_at: new Date().toISOString(),
          local_status: 'LOCAL_QUEUED',
          retry_count: 0,
          data_provenance: 'SYNTHETIC_DEMO',
        };

        await syncManager.enqueueOperation(op);

        // Optimistically update query cache with local queued indication
        if (cachedIncident) {
          queryClient.setQueryData(['incident', incidentId], {
            ...cachedIncident,
            status: 'ACKNOWLEDGED',
            acknowledged_at: new Date().toISOString(),
            _is_local_queued: true,
          });
        }

        queryClient.setQueriesData<Incident[]>({ queryKey: ['incidents'] }, (old) => {
          if (!old) return old;
          return old.map((inc) =>
            inc.id === incidentId
              ? { ...inc, status: 'ACKNOWLEDGED', acknowledged_at: new Date().toISOString(), _is_local_queued: true }
              : inc
          );
        });

        return {
          ...(cachedIncident || { id: incidentId, status: 'ACKNOWLEDGED' }),
          status: 'ACKNOWLEDGED',
          _is_local_queued: true,
          _client_operation_id: clientOpId,
        } as unknown as Incident;
      }

      // Online: normal API path
      return await apiClient.post<Incident>(`/incidents/${incidentId}/acknowledge`, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incident-timeline', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['operational-timeline'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
      queryClient.invalidateQueries({ queryKey: ['sync-summary'] });
    },
  });
}

export function useMitigateIncident(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      return await apiClient.post<Incident>(`/incidents/${incidentId}/mitigate`, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incident-timeline', incidentId] });
    },
  });
}

export function useResolveIncident(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      return await apiClient.post<Incident>(`/incidents/${incidentId}/resolve`, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incident-timeline', incidentId] });
    },
  });
}

export function useCloseIncident(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      return await apiClient.post<Incident>(`/incidents/${incidentId}/close`, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incident-timeline', incidentId] });
    },
  });
}

export function useTransitionIncident(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: IncidentStatusTransitionRequest) => {
      return await apiClient.post<Incident>(`/incidents/${incidentId}/transition`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incident-timeline', incidentId] });
    },
  });
}

export function useAddIncidentReference(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: IncidentReferenceCreateRequest) => {
      return await apiClient.post<IncidentReference>(`/incidents/${incidentId}/references`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident-references', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incident-timeline', incidentId] });
    },
  });
}

export function useEscalateIncidentToReplan(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: IncidentEscalationRequest = {}) => {
      return await apiClient.post<IncidentEscalationResult>(
        `/control-tower/incidents/${incidentId}/escalate`,
        payload
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['replans'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incident-context', incidentId] });
    },
  });
}
