/**
 * Central Offline Sync Manager (A8).
 *
 * Responsibilities:
 * 1. Track browser connectivity (navigator.onLine) + simulated Antarctic blackout.
 * 2. Maintain reactive sync posture snapshot.
 * 3. Store-and-forward batch replay: sends queued local operations to /api/v1/sync/batch,
 *    reconciles target domain mutation, and marks server records as APPLIED.
 * 4. Automatic replay upon connectivity restoration.
 * 5. Deterministic provenance: all simulated states labeled [SYNTHETIC/DEMO].
 */

import { apiClient, ApiError } from '../api/client';
import {
  saveOperation,
  getQueuedOperations,
  getAllOperations,
  updateOperationStatus,
  clearAppliedOperations,
  resetStoreForTesting,
} from './outboxStore';
import type {
  OutboxOperation,
  SyncManagerSnapshot,
  SyncBatchResultData,
  SyncBatchItemPayload,
} from './types';
import type { QueryClient } from '@tanstack/react-query';

type SyncListener = () => void;

class SyncManager {
  private _isOnline: boolean = typeof navigator !== 'undefined' ? navigator.onLine : true;
  private _isSimulatedBlackout: boolean =
    typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined'
      ? window.sessionStorage.getItem('polarops_simulated_blackout') === 'true'
      : false;
  private _isSyncing: boolean = false;
  private _lastSyncAt: string | null = null;
  private _lastError: string | null = null;
  private _listeners: Set<SyncListener> = new Set();
  private _queryClient: QueryClient | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this.handleOnline);
      window.addEventListener('offline', this.handleOffline);
    }
  }

  private handleOnline = () => {
    this._isOnline = true;
    this.notify();
    if (!this._isSimulatedBlackout) {
      void this.replayQueuedBatch();
    }
  };

  private handleOffline = () => {
    this._isOnline = false;
    this.notify();
  };

  public setQueryClient(client: QueryClient) {
    this._queryClient = client;
  }

  public getQueryClient(): QueryClient | null {
    return this._queryClient;
  }

  public isOnline(): boolean {
    return this._isOnline;
  }

  public isSimulatedBlackout(): boolean {
    return this._isSimulatedBlackout;
  }

  public isEffectiveOnline(): boolean {
    return this._isOnline && !this._isSimulatedBlackout;
  }

  /**
   * Deterministic simulated blackout switch for SIH demonstration.
   * Label: [SYNTHETIC/DEMO].
   */
  public setSimulatedBlackout(enabled: boolean): void {
    const previous = this._isSimulatedBlackout;
    this._isSimulatedBlackout = enabled;
    if (typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined') {
      if (enabled) {
        window.sessionStorage.setItem('polarops_simulated_blackout', 'true');
      } else {
        window.sessionStorage.removeItem('polarops_simulated_blackout');
      }
    }
    this.notify();

    // If connectivity is restored from simulated blackout, trigger automatic replay
    if (previous && !enabled && this._isOnline) {
      void this.replayQueuedBatch();
    }
  }

  public toggleSimulatedBlackout(): void {
    this.setSimulatedBlackout(!this._isSimulatedBlackout);
  }

  public subscribe(listener: SyncListener): () => void {
    this._listeners.add(listener);
    return () => {
      this._listeners.delete(listener);
    };
  }

  private notify(): void {
    for (const listener of this._listeners) {
      try {
        listener();
      } catch (err) {
        console.error('Error in sync listener callback:', err);
      }
    }
  }

  public async getSnapshot(): Promise<SyncManagerSnapshot> {
    const all = await getAllOperations();
    const queuedCount = all.filter((op) => op.local_status === 'LOCAL_QUEUED').length;
    const failedCount = all.filter((op) => op.local_status === 'FAILED').length;
    const appliedCount = all.filter((op) => op.local_status === 'APPLIED').length;

    return {
      isOnline: this._isOnline,
      isSimulatedBlackout: this._isSimulatedBlackout,
      effectiveOnline: this.isEffectiveOnline(),
      isSyncing: this._isSyncing,
      queuedCount,
      failedCount,
      appliedCount,
      lastSyncAt: this._lastSyncAt,
      lastError: this._lastError,
    };
  }

  /**
   * Queues an operational action locally in IndexedDB.
   */
  public async enqueueOperation(op: OutboxOperation): Promise<void> {
    await saveOperation(op);
    this.notify();
  }

  /**
   * Replays all locally queued operations to the backend sync API.
   * Flow:
   * 1. Check connectivity
   * 2. Gather LOCAL_QUEUED and FAILED operations
   * 3. Submit batch to POST /api/v1/sync/batch
   * 4. For successful batch registrations:
   *    - Reconcile underlying domain mutation (e.g. Incident Acknowledge)
   *    - Call PATCH /api/v1/sync/{record_id}/apply with { status: "APPLIED" }
   *    - Update local outbox record to APPLIED
   * 5. Invalidate React Query caches and notify listeners
   */
  public async replayQueuedBatch(): Promise<SyncBatchResultData | null> {
    if (!this.isEffectiveOnline() || this._isSyncing) {
      return null;
    }

    const queued = await getQueuedOperations();
    if (queued.length === 0) {
      return null;
    }

    this._isSyncing = true;
    this._lastError = null;
    this.notify();

    // Transition local operations to SYNCING
    for (const op of queued) {
      await updateOperationStatus(op.client_operation_id, { local_status: 'SYNCING' });
    }
    this.notify();

    const batchPayload: SyncBatchItemPayload[] = queued.map((op) => ({
      operation_id: op.client_operation_id,
      entity_type: op.entity_type,
      operation_type: op.operation_type,
      payload: op.payload,
      queued_at: op.queued_at,
    }));

    try {
      // 1. Batch enqueue with existing backend contract
      const batchResult = await apiClient.post<SyncBatchResultData>('/sync/batch', {
        operations: batchPayload,
      });

      // 2. Reconcile per-operation results
      for (const res of batchResult.results) {
        const op = queued.find((item) => item.client_operation_id === res.operation_id);
        if (!op) continue;

        if (res.outcome === 'ENQUEUED' || res.outcome === 'DUPLICATE') {
          try {
            // Fetch the server-side sync record to obtain its internal UUID
            const serverRecord = await apiClient.get<{ id: string; status: string }>(
              `/sync/by-operation-id/${op.client_operation_id}`
            );

            // Reconcile Hero Action: Incident Acknowledgement
            if (op.entity_type === 'INCIDENT' && op.payload?.action === 'ACKNOWLEDGE') {
              try {
                await apiClient.post(`/incidents/${op.entity_id}/acknowledge`, {});
              } catch (domainErr) {
                // If incident is already acknowledged or transitioned, treat as reconciled
                if (!(domainErr instanceof ApiError && domainErr.status === 400)) {
                  console.warn('Incident acknowledgement reconciliation warning:', domainErr);
                }
              }
            }

            // Mark server sync record as APPLIED if not already terminal
            if (serverRecord.status !== 'APPLIED' && serverRecord.status !== 'REJECTED') {
              try {
                await apiClient.patch(`/sync/${serverRecord.id}/apply`, {
                  status: 'APPLIED',
                });
              } catch (applyErr) {
                console.warn('Sync apply transition warning:', applyErr);
              }
            }

            // Update local status to APPLIED
            await updateOperationStatus(op.client_operation_id, {
              local_status: 'APPLIED',
              applied_at: new Date().toISOString(),
              server_record_id: serverRecord.id,
              last_error: null,
            });
          } catch (reconcileErr) {
            const msg = reconcileErr instanceof Error ? reconcileErr.message : 'Reconciliation failed';
            await updateOperationStatus(op.client_operation_id, {
              local_status: 'FAILED',
              last_error: msg,
              retry_count: op.retry_count + 1,
            });
          }
        } else {
          // Batch result was ERROR
          await updateOperationStatus(op.client_operation_id, {
            local_status: 'FAILED',
            last_error: res.message || 'Batch registration rejected by server',
            retry_count: op.retry_count + 1,
          });
        }
      }

      this._lastSyncAt = new Date().toISOString();

      // Invalidate relevant React Query caches
      if (this._queryClient) {
        this._queryClient.invalidateQueries({ queryKey: ['incidents'] });
        this._queryClient.invalidateQueries({ queryKey: ['incident'] });
        this._queryClient.invalidateQueries({ queryKey: ['incident-timeline'] });
        this._queryClient.invalidateQueries({ queryKey: ['operational-timeline'] });
        this._queryClient.invalidateQueries({ queryKey: ['control-tower'] });
        this._queryClient.invalidateQueries({ queryKey: ['sync-summary'] });
      }

      // Dispatch global window event for timeline and UI reactivity
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('polarops:sync-completed', {
            detail: { timestamp: this._lastSyncAt, result: batchResult },
          })
        );
      }

      return batchResult;
    } catch (networkOrBatchErr) {
      const errMsg = networkOrBatchErr instanceof Error ? networkOrBatchErr.message : 'Network error during batch replay';
      this._lastError = errMsg;

      // Revert items from SYNCING back to FAILED/LOCAL_QUEUED
      for (const op of queued) {
        await updateOperationStatus(op.client_operation_id, {
          local_status: 'FAILED',
          last_error: errMsg,
          retry_count: op.retry_count + 1,
        });
      }

      return null;
    } finally {
      this._isSyncing = false;
      this.notify();
    }
  }

  public async retryOperation(client_operation_id: string): Promise<void> {
    await updateOperationStatus(client_operation_id, {
      local_status: 'LOCAL_QUEUED',
      last_error: null,
    });
    this.notify();
    if (this.isEffectiveOnline()) {
      void this.replayQueuedBatch();
    }
  }

  public async clearApplied(): Promise<void> {
    await clearAppliedOperations();
    this.notify();
  }

  public async resetForTesting(): Promise<void> {
    this._isOnline = true;
    this._isSimulatedBlackout = false;
    if (typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined') {
      window.sessionStorage.removeItem('polarops_simulated_blackout');
    }
    this._isSyncing = false;
    this._lastSyncAt = null;
    this._lastError = null;
    await resetStoreForTesting();
    this.notify();
  }
}

export const syncManager = new SyncManager();
