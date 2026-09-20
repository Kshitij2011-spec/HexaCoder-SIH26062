/**
 * React hook for client-side disruption resilience and offline sync (A8).
 */

import { useState, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { syncManager } from './syncManager';
import { getAllOperations } from './outboxStore';
import type { OutboxOperation, SyncManagerSnapshot } from './types';

const INITIAL_SNAPSHOT: SyncManagerSnapshot = {
  isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
  isSimulatedBlackout: false,
  effectiveOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
  isSyncing: false,
  queuedCount: 0,
  failedCount: 0,
  appliedCount: 0,
  lastSyncAt: null,
  lastError: null,
};

export function useOfflineSync() {
  const queryClient = useQueryClient();
  const [snapshot, setSnapshot] = useState<SyncManagerSnapshot>(INITIAL_SNAPSHOT);
  const [operations, setOperations] = useState<OutboxOperation[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Link React Query client to syncManager for automatic cache invalidation
  useEffect(() => {
    syncManager.setQueryClient(queryClient);
  }, [queryClient]);

  const refreshState = useCallback(async () => {
    try {
      const [snap, ops] = await Promise.all([
        syncManager.getSnapshot(),
        getAllOperations(),
      ]);
      setSnapshot(snap);
      setOperations(ops);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshState();
    const unsubscribe = syncManager.subscribe(() => {
      void refreshState();
    });

    const handleSyncEvent = () => {
      void refreshState();
    };

    window.addEventListener('polarops:sync-completed', handleSyncEvent);

    return () => {
      unsubscribe();
      window.removeEventListener('polarops:sync-completed', handleSyncEvent);
    };
  }, [refreshState]);

  const toggleSimulatedBlackout = useCallback(() => {
    syncManager.toggleSimulatedBlackout();
  }, []);

  const setSimulatedBlackout = useCallback((enabled: boolean) => {
    syncManager.setSimulatedBlackout(enabled);
  }, []);

  const triggerSync = useCallback(async () => {
    return await syncManager.replayQueuedBatch();
  }, []);

  const retryOperation = useCallback(async (client_operation_id: string) => {
    await syncManager.retryOperation(client_operation_id);
  }, []);

  const clearApplied = useCallback(async () => {
    await syncManager.clearApplied();
  }, []);

  return {
    snapshot,
    operations,
    isLoading,
    toggleSimulatedBlackout,
    setSimulatedBlackout,
    triggerSync,
    retryOperation,
    clearApplied,
  };
}
