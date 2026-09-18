import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type {
  Asset,
  MaintenanceRecord,
  AssetMoveRequest,
  AssetStatusTransitionRequest,
  MaintenanceScheduleRequest,
  MaintenanceStartRequest,
  MaintenanceCompleteRequest,
  MaintenanceCancelRequest,
} from '../../../lib/types/api';

export function useMoveAsset(assetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AssetMoveRequest) => {
      return await apiClient.post<Asset>(`/assets/${assetId}/move`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['asset', assetId] });
      queryClient.invalidateQueries({ queryKey: ['asset-timeline', assetId] });
    },
  });
}

export function useTransitionAsset(assetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AssetStatusTransitionRequest) => {
      return await apiClient.post<Asset>(`/assets/${assetId}/transition`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['asset', assetId] });
      queryClient.invalidateQueries({ queryKey: ['asset-timeline', assetId] });
    },
  });
}

export function useScheduleMaintenance(assetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: MaintenanceScheduleRequest) => {
      return await apiClient.post<MaintenanceRecord>(`/assets/${assetId}/maintenance`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-maintenance', assetId] });
      queryClient.invalidateQueries({ queryKey: ['asset-timeline', assetId] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}

export function useStartMaintenance(assetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ maintenanceId, payload }: { maintenanceId: string; payload: MaintenanceStartRequest }) => {
      return await apiClient.post<MaintenanceRecord>(`/assets/maintenance/${maintenanceId}/start`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-maintenance', assetId] });
      queryClient.invalidateQueries({ queryKey: ['asset-timeline', assetId] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['asset', assetId] });
    },
  });
}

export function useCompleteMaintenance(assetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ maintenanceId, payload }: { maintenanceId: string; payload: MaintenanceCompleteRequest }) => {
      return await apiClient.post<MaintenanceRecord>(`/assets/maintenance/${maintenanceId}/complete`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-maintenance', assetId] });
      queryClient.invalidateQueries({ queryKey: ['asset-timeline', assetId] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['asset', assetId] });
    },
  });
}

export function useCancelMaintenance(assetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ maintenanceId, payload }: { maintenanceId: string; payload: MaintenanceCancelRequest }) => {
      return await apiClient.post<MaintenanceRecord>(`/assets/maintenance/${maintenanceId}/cancel`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-maintenance', assetId] });
      queryClient.invalidateQueries({ queryKey: ['asset-timeline', assetId] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}
