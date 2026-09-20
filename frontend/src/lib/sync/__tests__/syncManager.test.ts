import { describe, it, expect, vi, beforeEach } from 'vitest';
import { syncManager } from '../syncManager';
import { apiClient } from '../../api/client';
import { getOperation } from '../outboxStore';
import type { OutboxOperation } from '../types';

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    readonly code: string;
    readonly status?: number;
    constructor(code: string, message: string, _field?: any, status?: number) {
      super(message);
      this.code = code;
      this.status = status;
    }
  },
}));

describe('SyncManager Service (A8)', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await syncManager.resetForTesting();
  });

  const mockOp: OutboxOperation = {
    client_operation_id: '12345678-1234-1234-1234-123456789abc',
    entity_type: 'INCIDENT',
    entity_id: '77777777-7777-7777-7777-777777777777',
    operation_type: 'STATE_TRANSITION',
    payload: { action: 'ACKNOWLEDGE', target_status: 'ACKNOWLEDGED' },
    queued_at: new Date().toISOString(),
    local_status: 'LOCAL_QUEUED',
    retry_count: 0,
    data_provenance: 'SYNTHETIC_DEMO',
  };

  it('correctly tracks simulated blackout posture', () => {
    expect(syncManager.isEffectiveOnline()).toBe(true);
    expect(syncManager.isSimulatedBlackout()).toBe(false);

    syncManager.setSimulatedBlackout(true);
    expect(syncManager.isSimulatedBlackout()).toBe(true);
    expect(syncManager.isEffectiveOnline()).toBe(false);

    syncManager.setSimulatedBlackout(false);
    expect(syncManager.isSimulatedBlackout()).toBe(false);
    expect(syncManager.isEffectiveOnline()).toBe(true);
  });

  it('enqueues operation and updates snapshot counts', async () => {
    await syncManager.enqueueOperation(mockOp);

    const snapshot = await syncManager.getSnapshot();
    expect(snapshot.queuedCount).toBe(1);
    expect(snapshot.failedCount).toBe(0);
    expect(snapshot.appliedCount).toBe(0);
  });

  it('replays batch, reconciles hero mutation, marks server record APPLIED, and transitions local state', async () => {
    await syncManager.enqueueOperation(mockOp);

    // Mock batch enqueue response
    vi.mocked(apiClient.post).mockImplementation(async (path: string) => {
      if (path === '/sync/batch') {
        return {
          enqueued: 1,
          skipped_duplicate: 0,
          failed: 0,
          results: [{ operation_id: mockOp.client_operation_id, outcome: 'ENQUEUED' }],
        };
      }
      if (path.includes('/acknowledge')) {
        return { id: mockOp.entity_id, status: 'ACKNOWLEDGED' };
      }
      throw new Error(`Unexpected post path: ${path}`);
    });

    // Mock lookup by client operation id
    vi.mocked(apiClient.get).mockImplementation(async (path: string) => {
      if (path.includes('/sync/by-operation-id/')) {
        return { id: 'server-record-uuid-1', status: 'PENDING' };
      }
      throw new Error(`Unexpected get path: ${path}`);
    });

    // Mock apply patch
    vi.mocked(apiClient.patch).mockImplementation(async (path: string) => {
      if (path === '/sync/server-record-uuid-1/apply') {
        return { id: 'server-record-uuid-1', status: 'APPLIED' };
      }
      throw new Error(`Unexpected patch path: ${path}`);
    });

    const result = await syncManager.replayQueuedBatch();
    expect(result).toBeDefined();
    expect(result?.enqueued).toBe(1);

    // Verify backend calls
    expect(apiClient.post).toHaveBeenCalledWith('/sync/batch', expect.any(Object));
    expect(apiClient.get).toHaveBeenCalledWith(`/sync/by-operation-id/${mockOp.client_operation_id}`);
    expect(apiClient.post).toHaveBeenCalledWith(`/incidents/${mockOp.entity_id}/acknowledge`, {});
    expect(apiClient.patch).toHaveBeenCalledWith('/sync/server-record-uuid-1/apply', { status: 'APPLIED' });

    // Verify local record transition
    const stored = await getOperation(mockOp.client_operation_id);
    expect(stored?.local_status).toBe('APPLIED');
    expect(stored?.server_record_id).toBe('server-record-uuid-1');
    expect(stored?.applied_at).toBeDefined();

    const snapshot = await syncManager.getSnapshot();
    expect(snapshot.queuedCount).toBe(0);
    expect(snapshot.appliedCount).toBe(1);
    expect(snapshot.lastSyncAt).toBeDefined();
  });

  it('handles server rejection / batch ERROR gracefully', async () => {
    await syncManager.enqueueOperation(mockOp);

    vi.mocked(apiClient.post).mockResolvedValueOnce({
      enqueued: 0,
      skipped_duplicate: 0,
      failed: 1,
      results: [
        {
          operation_id: mockOp.client_operation_id,
          outcome: 'ERROR',
          message: 'Invalid payload entity constraint',
        },
      ],
    });

    await syncManager.replayQueuedBatch();

    const stored = await getOperation(mockOp.client_operation_id);
    expect(stored?.local_status).toBe('FAILED');
    expect(stored?.last_error).toContain('Invalid payload entity constraint');
    expect(stored?.retry_count).toBe(1);

    const snapshot = await syncManager.getSnapshot();
    expect(snapshot.failedCount).toBe(1);
    expect(snapshot.queuedCount).toBe(0);
  });

  it('allows retry of failed operations', async () => {
    const failedOp = { ...mockOp, local_status: 'FAILED' as const, last_error: 'Timeout' };
    await syncManager.enqueueOperation(failedOp);

    await syncManager.retryOperation(failedOp.client_operation_id);

    const stored = await getOperation(failedOp.client_operation_id);
    expect(stored?.local_status).toBe('LOCAL_QUEUED');
    expect(stored?.last_error).toBeNull();
  });
});
