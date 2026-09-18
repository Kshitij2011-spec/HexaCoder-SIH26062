import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type {
  InventoryStockLot,
  StockReceiptRequest,
  StockReservationRequest,
  StockReleaseRequest,
  StockIssueRequest,
  StockQuarantineRequest,
  StockStatusTransitionRequest,
} from '../../../lib/types/api';

export function useReceiveStock(stockLotId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: StockReceiptRequest) => {
      return await apiClient.post<InventoryStockLot>(
        `/inventory/stock-lots/${stockLotId}/receive`,
        payload
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stock-lots'] });
      queryClient.invalidateQueries({ queryKey: ['stock-availability', stockLotId] });
      queryClient.invalidateQueries({ queryKey: ['inventory-transactions', stockLotId] });
      queryClient.invalidateQueries({ queryKey: ['inventory-items'] });
    },
  });
}

export function useReserveStock(stockLotId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: StockReservationRequest) => {
      return await apiClient.post<InventoryStockLot>(
        `/inventory/stock-lots/${stockLotId}/reserve`,
        payload
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stock-lots'] });
      queryClient.invalidateQueries({ queryKey: ['stock-availability', stockLotId] });
      queryClient.invalidateQueries({ queryKey: ['inventory-transactions', stockLotId] });
    },
  });
}

export function useReleaseStock(stockLotId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: StockReleaseRequest) => {
      return await apiClient.post<InventoryStockLot>(
        `/inventory/stock-lots/${stockLotId}/release`,
        payload
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stock-lots'] });
      queryClient.invalidateQueries({ queryKey: ['stock-availability', stockLotId] });
      queryClient.invalidateQueries({ queryKey: ['inventory-transactions', stockLotId] });
    },
  });
}

export function useIssueStock(stockLotId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: StockIssueRequest) => {
      return await apiClient.post<InventoryStockLot>(
        `/inventory/stock-lots/${stockLotId}/issue`,
        payload
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stock-lots'] });
      queryClient.invalidateQueries({ queryKey: ['stock-availability', stockLotId] });
      queryClient.invalidateQueries({ queryKey: ['inventory-transactions', stockLotId] });
      queryClient.invalidateQueries({ queryKey: ['inventory-items'] });
    },
  });
}

export function useQuarantineStock(stockLotId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: StockQuarantineRequest) => {
      return await apiClient.post<InventoryStockLot>(
        `/inventory/stock-lots/${stockLotId}/quarantine`,
        payload
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stock-lots'] });
      queryClient.invalidateQueries({ queryKey: ['stock-availability', stockLotId] });
      queryClient.invalidateQueries({ queryKey: ['inventory-transactions', stockLotId] });
    },
  });
}

export function useTransitionStock(stockLotId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: StockStatusTransitionRequest) => {
      return await apiClient.post<InventoryStockLot>(
        `/inventory/stock-lots/${stockLotId}/transition`,
        payload
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stock-lots'] });
      queryClient.invalidateQueries({ queryKey: ['stock-availability', stockLotId] });
      queryClient.invalidateQueries({ queryKey: ['inventory-transactions', stockLotId] });
    },
  });
}
