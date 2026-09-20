/**
 * Domain types for client-side disruption resilience and store-and-forward sync (A8).
 * Provenance: SYNTHETIC_DEMO.
 */

export type LocalSyncStatus =
  | 'LOCAL_QUEUED'
  | 'SYNCING'
  | 'APPLIED'
  | 'FAILED'
  | 'CONFLICT';

export type OfflineOperationType =
  | 'CREATE'
  | 'UPDATE'
  | 'STATE_TRANSITION'
  | 'DELETE';

export interface OutboxOperation {
  /** Client-supplied idempotency key (UUID v4) */
  client_operation_id: string;
  /** Target entity domain type (e.g. INCIDENT, INVENTORY_ITEM, ASSET) */
  entity_type: string;
  /** Identifier of the target entity */
  entity_id: string;
  /** Operation classification */
  operation_type: OfflineOperationType;
  /** JSON-serializable operational payload */
  payload: Record<string, any>;
  /** Client ISO timestamp when buffered */
  queued_at: string;
  /** Client-side lifecycle status */
  local_status: LocalSyncStatus;
  /** Number of replay attempts */
  retry_count: number;
  /** Human-readable failure/conflict message if any */
  last_error?: string | null;
  /** Provenance tag (always SYNTHETIC_DEMO for demo/field operations) */
  data_provenance: string;
  /** Expedition context if available */
  expedition_id?: string | null;
  /** Server-side internal UUID once reconciled */
  server_record_id?: string | null;
  /** Timestamp when backend reconciled to APPLIED */
  applied_at?: string | null;
}

export interface SyncBatchItemPayload {
  operation_id: string;
  entity_type: string;
  operation_type: string;
  payload: Record<string, any>;
  queued_at?: string;
  actor_id?: string | null;
}

export interface SyncBatchResultItem {
  operation_id: string;
  outcome: 'ENQUEUED' | 'DUPLICATE' | 'ERROR';
  message?: string;
}

export interface SyncBatchResultData {
  enqueued: number;
  skipped_duplicate: number;
  failed: number;
  results: SyncBatchResultItem[];
}

export interface SyncQueueSummaryData {
  pending: number;
  applied: number;
  failed: number;
  rejected: number;
  total: number;
  data_provenance: string;
}

export interface SyncManagerSnapshot {
  /** Real browser connectivity (navigator.onLine) */
  isOnline: boolean;
  /** Controlled demo Antarctic blackout simulation */
  isSimulatedBlackout: boolean;
  /** Effective operational connectivity (isOnline && !isSimulatedBlackout) */
  effectiveOnline: boolean;
  /** True while batch replay and server reconciliation are active */
  isSyncing: boolean;
  /** Count of operations currently buffered locally (LOCAL_QUEUED) */
  queuedCount: number;
  /** Count of operations whose replay failed (FAILED) */
  failedCount: number;
  /** Count of operations reconciled to server (APPLIED) */
  appliedCount: number;
  /** ISO timestamp of the last successful sync reconciliation */
  lastSyncAt: string | null;
  /** Last error message encountered during replay */
  lastError: string | null;
}
