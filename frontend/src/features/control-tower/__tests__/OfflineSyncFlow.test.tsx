import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import { ControlTowerPage } from '../ControlTowerPage';
import { apiClient } from '../../../lib/api/client';
import { syncManager } from '../../../lib/sync/syncManager';
import { getAllOperations } from '../../../lib/sync/outboxStore';
import type { ControlTowerOverview, Incident } from '../../../lib/types/api';

vi.mock('../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  buildQuery: () => '',
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

const mockOverview: ControlTowerOverview = {
  total_expeditions: 1,
  expeditions: [
    {
      expedition_id: 'exp-1',
      code: 'EXP-45',
      name: '45th Indian Antarctic Expedition',
      season: '2026-2027',
      lifecycle_status: 'ACTIVE',
      readiness_state: 'READY',
      total_missions: 1,
      ready_missions_count: 1,
      at_risk_missions_count: 0,
      blocked_missions_count: 0,
      active_incidents_count: 1,
      active_hard_constraint_violations_count: 0,
      pending_replans_count: 0,
      pending_approvals_count: 0,
      latest_events: [],
      blockers: [],
      warnings: [],
      unknown_requirements: [],
      data_provenance: 'DERIVED',
      generated_at: '2026-09-19T10:00:00Z',
    },
  ],
  total_missions: 1,
  missions_by_readiness: { READY: 1 },
  missions_by_status: { ACTIVE: 1 },
  active_incidents_count: 1,
  critical_constraints_violated_count: 0,
  pending_replans_count: 0,
  pending_recommendations_count: 0,
  pending_approvals_count: 0,
  offline_sync_summary: {
    pending: 0,
    applied: 0,
    failed: 0,
    rejected: 0,
    total: 0,
    data_provenance: 'SYNTHETIC_DEMO',
  },
  recent_operational_events: [],
  data_provenance: 'DERIVED',
  generated_at: '2026-09-19T10:00:00Z',
};

const mockOpenIncident: Incident = {
  id: '77777777-7777-7777-7777-777777777777',
  code: 'INC-2026-001',
  title: 'Crevasse Risk Detection on Traverse Route',
  incident_type: 'ENVIRONMENTAL',
  severity: 'HIGH',
  status: 'OPEN',
  priority: 1,
  description: 'Deep crevasse identified by ground-penetrating radar on route Alpha.',
  detected_at: '2026-09-19T08:00:00Z',
  data_provenance: 'SYNTHETIC_DEMO',
  created_at: '2026-09-19T08:00:00Z',
  updated_at: '2026-09-19T08:00:00Z',
};

describe('Offline Synchronization & Store-and-Forward Flow (A8)', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await syncManager.resetForTesting();

    vi.mocked(apiClient.get).mockImplementation(async (path: string) => {
      if (path.includes('/control-tower/overview')) {
        return mockOverview;
      }
      if (path.includes('/incidents')) {
        return [mockOpenIncident];
      }
      if (path.includes('/control-tower/decision-queue')) {
        return { replans: [], recommendations: [] };
      }
      if (path.includes('/sync/by-operation-id/')) {
        return { id: 'srv-sync-uuid-1', status: 'PENDING' };
      }
      if (path.includes('/operations/timeline/')) {
        return { entries: [], total_entries: 0 };
      }
      return [];
    });
  });

  it('1 & 2: Renders initial ONLINE state and toggles simulated blackout to OFFLINE', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ControlTowerPage />);

    await waitFor(() => {
      expect(screen.getByText('Control Tower')).toBeInTheDocument();
    });

    // Verify initial ONLINE posture
    expect(screen.getAllByText('ONLINE').length).toBeGreaterThan(0);

    // Toggle blackout simulation
    const blackoutButtons = screen.getAllByRole('button', {
      name: /simulate antarctic blackout/i,
    });
    expect(blackoutButtons.length).toBeGreaterThan(0);
    await user.click(blackoutButtons[0]);

    // Verify OFFLINE — FIELD BUFFERING ACTIVE posture
    await waitFor(() => {
      expect(
        screen.getAllByText(/OFFLINE — FIELD BUFFERING ACTIVE/i).length
      ).toBeGreaterThan(0);
      expect(screen.getAllByText(/\[SYNTHETIC\/DEMO\]/i).length).toBeGreaterThan(0);
    });
  });

  it('3, 4, 5, 6, 7 & 8: Buffers hero action locally without network requests and replays on reconnect', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ControlTowerPage />);

    await waitFor(() => {
      expect(screen.getByText('Control Tower')).toBeInTheDocument();
    });

    // 1. Enable Simulated Blackout
    const blackoutBtn = screen.getAllByRole('button', {
      name: /simulate antarctic blackout/i,
    })[0];
    await user.click(blackoutBtn);

    await waitFor(() => {
      expect(syncManager.isEffectiveOnline()).toBe(false);
    });

    // 2. Perform Hero Mutation: Acknowledge Incident
    const ackBtn = await screen.findByTestId('quick-acknowledge-incident-btn');
    expect(ackBtn).toBeInTheDocument();

    const postSpy = vi.mocked(apiClient.post);
    postSpy.mockClear();

    await user.click(ackBtn);

    // 3. Verify: NO network requests were made to /incidents/.../acknowledge
    expect(postSpy).not.toHaveBeenCalledWith(
      `/incidents/${mockOpenIncident.id}/acknowledge`,
      expect.anything()
    );

    // 4. Verify: Operation is stored in IndexedDB with a UUID and LOCAL_QUEUED status
    const ops = await getAllOperations();
    expect(ops).toHaveLength(1);
    const queuedOp = ops[0];
    expect(queuedOp.entity_type).toBe('INCIDENT');
    expect(queuedOp.entity_id).toBe(mockOpenIncident.id);
    expect(queuedOp.local_status).toBe('LOCAL_QUEUED');
    expect(queuedOp.client_operation_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$|op-/i
    );

    // 5. Verify: UI indicates LOCAL_QUEUED — FIELD BUFFERED
    await waitFor(() => {
      expect(
        screen.getByTestId('hero-action-queued-badge')
      ).toBeInTheDocument();
      expect(screen.getByText(/LOCAL_QUEUED — FIELD BUFFERED/i)).toBeInTheDocument();
    });

    // 6. Open Offline Sync Drawer and verify queued details
    const openDrawerBtn = screen.getByTestId('open-outbox-drawer-btn');
    await user.click(openDrawerBtn);

    const drawer = await screen.findByTestId('offline-sync-drawer');
    expect(drawer).toBeInTheDocument();
    expect(within(drawer).getByText(/LOCAL QUEUED/i)).toBeInTheDocument();
    expect(within(drawer).getByText(/INCIDENT · STATE_TRANSITION/i)).toBeInTheDocument();

    // 7. Mock server endpoints for batch replay & reconciliation
    postSpy.mockImplementation(async (path: string) => {
      if (path === '/sync/batch') {
        return {
          enqueued: 1,
          skipped_duplicate: 0,
          failed: 0,
          results: [{ operation_id: queuedOp.client_operation_id, outcome: 'ENQUEUED' }],
        };
      }
      if (path.includes('/acknowledge')) {
        return { ...mockOpenIncident, status: 'ACKNOWLEDGED' };
      }
      return {};
    });

    vi.mocked(apiClient.patch).mockResolvedValueOnce({
      id: 'srv-sync-uuid-1',
      status: 'APPLIED',
    });

    // 8. Restore connectivity / disable blackout
    const restoreBtn = within(drawer).getByTestId('drawer-blackout-toggle-btn');
    await user.click(restoreBtn);

    // 9. Verify: Automatic replay triggered
    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith('/sync/batch', {
        operations: [
          expect.objectContaining({
            operation_id: queuedOp.client_operation_id,
            entity_type: 'INCIDENT',
            operation_type: 'STATE_TRANSITION',
          }),
        ],
      });
    });

    // 10. Verify: Operation transitioned to APPLIED in local store
    await waitFor(async () => {
      const updatedOps = await getAllOperations();
      expect(updatedOps[0].local_status).toBe('APPLIED');
    });
  });

  it('9 & 10: Retains failed operations on server error and displays failure reason', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ControlTowerPage />);

    // Enable blackout
    const blackoutBtn = screen.getAllByRole('button', {
      name: /simulate antarctic blackout/i,
    })[0];
    await user.click(blackoutBtn);

    // Acknowledge incident
    const ackBtn = await screen.findByTestId('quick-acknowledge-incident-btn');
    await user.click(ackBtn);

    const ops = await getAllOperations();
    const queuedOp = ops[0];

    // Mock batch endpoint returning an ERROR outcome
    vi.mocked(apiClient.post).mockImplementation(async (path: string) => {
      if (path === '/sync/batch') {
        return {
          enqueued: 0,
          skipped_duplicate: 0,
          failed: 1,
          results: [
            {
              operation_id: queuedOp.client_operation_id,
              outcome: 'ERROR',
              message: 'State transition rejected by authoritative engine',
            },
          ],
        };
      }
      return {};
    });

    // Restore connectivity to trigger sync
    const restoreBtn = screen.getAllByRole('button', {
      name: /restore connectivity/i,
    })[0];
    await user.click(restoreBtn);

    // Verify operation retains error and transitions to FAILED
    await waitFor(async () => {
      const updatedOps = await getAllOperations();
      expect(updatedOps[0].local_status).toBe('FAILED');
      expect(updatedOps[0].last_error).toContain('State transition rejected');
    });
  });
});
