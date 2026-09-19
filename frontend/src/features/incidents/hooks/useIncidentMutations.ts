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
      return await apiClient.post<Incident>(`/incidents/${incidentId}/acknowledge`, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incident-timeline', incidentId] });
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
