import { describe, it, expect, beforeEach } from 'vitest';
import {
  saveOperation,
  getOperation,
  getAllOperations,
  getQueuedOperations,
  updateOperationStatus,
  deleteOperation,
  clearAppliedOperations,
  resetStoreForTesting,
} from '../outboxStore';
import type { OutboxOperation } from '../types';

describe('IndexedDB / Memory OutboxStore (A8)', () => {
  beforeEach(async () => {
    await resetStoreForTesting();
  });

  const mockOp: OutboxOperation = {
    client_operation_id: '11111111-1111-1111-1111-111111111111',
    entity_type: 'INCIDENT',
    entity_id: '77777777-7777-7777-7777-777777777777',
    operation_type: 'STATE_TRANSITION',
    payload: { action: 'ACKNOWLEDGE', target_status: 'ACKNOWLEDGED' },
    queued_at: new Date('2026-09-19T10:00:00Z').toISOString(),
    local_status: 'LOCAL_QUEUED',
    retry_count: 0,
    data_provenance: 'SYNTHETIC_DEMO',
  };

  it('saves and retrieves an operation by client_operation_id', async () => {
    await saveOperation(mockOp);
    const retrieved = await getOperation(mockOp.client_operation_id);
    expect(retrieved).toBeDefined();
    expect(retrieved?.client_operation_id).toBe(mockOp.client_operation_id);
    expect(retrieved?.entity_type).toBe('INCIDENT');
    expect(retrieved?.local_status).toBe('LOCAL_QUEUED');
  });

  it('lists all operations in deterministic descending order', async () => {
    const op1 = { ...mockOp, client_operation_id: 'op-1', queued_at: '2026-09-19T10:00:00Z' };
    const op2 = { ...mockOp, client_operation_id: 'op-2', queued_at: '2026-09-19T10:05:00Z' };
    await saveOperation(op1);
    await saveOperation(op2);

    const all = await getAllOperations();
    expect(all).toHaveLength(2);
    expect(all[0].client_operation_id).toBe('op-2');
    expect(all[1].client_operation_id).toBe('op-1');
  });

  it('filters queued operations awaiting replay (FIFO)', async () => {
    const op1 = { ...mockOp, client_operation_id: 'op-1', local_status: 'LOCAL_QUEUED' as const, queued_at: '2026-09-19T10:00:00Z' };
    const op2 = { ...mockOp, client_operation_id: 'op-2', local_status: 'APPLIED' as const, queued_at: '2026-09-19T10:05:00Z' };
    const op3 = { ...mockOp, client_operation_id: 'op-3', local_status: 'FAILED' as const, queued_at: '2026-09-19T10:10:00Z' };
    await saveOperation(op1);
    await saveOperation(op2);
    await saveOperation(op3);

    const queued = await getQueuedOperations();
    expect(queued).toHaveLength(2);
    expect(queued[0].client_operation_id).toBe('op-1');
    expect(queued[1].client_operation_id).toBe('op-3');
  });

  it('updates operation status and retains metadata', async () => {
    await saveOperation(mockOp);
    await updateOperationStatus(mockOp.client_operation_id, {
      local_status: 'APPLIED',
      server_record_id: 'srv-1234',
      applied_at: '2026-09-19T10:15:00Z',
    });

    const updated = await getOperation(mockOp.client_operation_id);
    expect(updated?.local_status).toBe('APPLIED');
    expect(updated?.server_record_id).toBe('srv-1234');
    expect(updated?.applied_at).toBe('2026-09-19T10:15:00Z');
  });

  it('clears applied operations while preserving queued or failed ones', async () => {
    const op1 = { ...mockOp, client_operation_id: 'op-1', local_status: 'APPLIED' as const };
    const op2 = { ...mockOp, client_operation_id: 'op-2', local_status: 'FAILED' as const };
    await saveOperation(op1);
    await saveOperation(op2);

    await clearAppliedOperations();

    const all = await getAllOperations();
    expect(all).toHaveLength(1);
    expect(all[0].client_operation_id).toBe('op-2');
  });

  it('deletes an operation by client_operation_id', async () => {
    await saveOperation(mockOp);
    await deleteOperation(mockOp.client_operation_id);

    const retrieved = await getOperation(mockOp.client_operation_id);
    expect(retrieved).toBeUndefined();
  });
});
