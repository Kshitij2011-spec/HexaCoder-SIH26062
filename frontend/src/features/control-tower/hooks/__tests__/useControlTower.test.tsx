import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { createTestQueryClient } from '../../../../test-utils';
import {
  controlTowerKeys,
  useControlTowerFastOverview,
  useControlTowerOverview,
  useExpeditionSummary,
  useMissionOperations,
  useControlTowerConstraints,
  useDecisionQueue,
  useConsequentialAudit,
  useApprovalMutations,
} from '../useControlTower';
import { apiClient } from '../../../../lib/api/client';
import type {
  ControlTowerOverview,
  ExpeditionControlSummary,
  MissionOperationsItem,
  ControlTowerConstraintItem,
  DecisionQueueSummary,
  ConsequentialActionItem,
  ApprovalRead,
  ReplanApplyResult,
} from '../../../../lib/types/api';

vi.mock('../../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
  buildQuery: (params: Record<string, string | number | undefined | null>) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') {
        q.set(k, String(v));
      }
    }
    const str = q.toString();
    return str ? `?${str}` : '';
  },
}));

describe('Control Tower Query Keys', () => {
  it('generates consistent and stable hierarchical query keys', () => {
    expect(controlTowerKeys.all).toEqual(['control-tower']);
    expect(controlTowerKeys.overview()).toEqual(['control-tower', 'overview']);
    expect(controlTowerKeys.overview('exp-44')).toEqual([
      'control-tower',
      'overview',
      { expeditionId: 'exp-44' },
    ]);
    expect(controlTowerKeys.summary('exp-44')).toEqual([
      'control-tower',
      'expedition',
      'exp-44',
      'summary',
    ]);
    expect(controlTowerKeys.missions('exp-44', { readiness: 'READY', page: 2 })).toEqual([
      'control-tower',
      'expedition',
      'exp-44',
      'missions',
      { readiness: 'READY', page: 2 },
    ]);
    expect(controlTowerKeys.constraints('exp-44', { state: 'VIOLATED' })).toEqual([
      'control-tower',
      'expedition',
      'exp-44',
      'constraints',
      { state: 'VIOLATED' },
    ]);
    expect(controlTowerKeys.decisions('exp-44')).toEqual([
      'control-tower',
      'expedition',
      'exp-44',
      'decisions',
    ]);
    expect(controlTowerKeys.audit('exp-44', 3)).toEqual([
      'control-tower',
      'expedition',
      'exp-44',
      'audit',
      { page: 3 },
    ]);
  });
});

describe('Control Tower Query Hooks', () => {
  let queryClient: ReturnType<typeof createTestQueryClient>;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('useControlTowerOverview fetches overview data', async () => {
    const mockOverview: Partial<ControlTowerOverview> = {
      total_expeditions: 2,
      total_missions: 5,
      active_incidents_count: 1,
      pending_approvals_count: 2,
    };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockOverview);

    const { result } = renderHook(() => useControlTowerOverview('exp-1'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith('/control-tower/overview?expedition_id=exp-1');
    expect(result.current.data).toEqual(mockOverview);
  });

  it('useControlTowerFastOverview fetches fast overview command posture data', async () => {
    const mockFastOverview: Partial<ControlTowerOverview> = {
      total_expeditions: 2,
      total_missions: 5,
      active_incidents_count: 1,
      pending_approvals_count: 2,
      data_provenance: 'DERIVED',
    };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockFastOverview);

    const { result } = renderHook(() => useControlTowerFastOverview('exp-1'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith('/control-tower/overview/fast?expedition_id=exp-1');
    expect(result.current.data).toEqual(mockFastOverview);
  });

  it('useExpeditionSummary fetches single expedition summary by ID', async () => {
    const mockSummary: Partial<ExpeditionControlSummary> = {
      expedition_id: 'exp-1',
      code: 'EXP-44',
      name: '44th Indian Antarctic Expedition',
      readiness_state: 'READY',
      total_missions: 3,
    };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockSummary);

    const { result } = renderHook(() => useExpeditionSummary('exp-1'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith('/control-tower/expeditions/exp-1');
    expect(result.current.data).toEqual(mockSummary);
  });

  it('useMissionOperations constructs filter query parameters accurately', async () => {
    const mockMissions: Partial<MissionOperationsItem>[] = [
      {
        mission_id: 'msn-1',
        code: 'MSN-SCI-01',
        readiness_state: 'BLOCKED',
        violated_constraints: [{ code: 'CST-01' }],
      },
    ];
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockMissions);

    const { result } = renderHook(
      () =>
        useMissionOperations('exp-1', {
          readiness: 'BLOCKED',
          status: 'ACTIVE',
          page: 1,
          page_size: 20,
        }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith(
      '/control-tower/expeditions/exp-1/missions?status=ACTIVE&readiness=BLOCKED&page=1&page_size=20',
    );
    expect(result.current.data).toEqual(mockMissions);
  });

  it('useControlTowerConstraints constructs constraint query parameters accurately', async () => {
    const mockConstraints: Partial<ControlTowerConstraintItem>[] = [
      {
        constraint_id: 'cst-1',
        code: 'CST-COLD-CHAIN',
        state: 'VIOLATED',
        hard_or_soft: 'HARD',
      },
    ];
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockConstraints);

    const { result } = renderHook(
      () =>
        useControlTowerConstraints('exp-1', {
          state: 'VIOLATED',
          hard_or_soft: 'HARD',
          page: 1,
          page_size: 50,
        }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith(
      '/control-tower/expeditions/exp-1/constraints?state=VIOLATED&hard_or_soft=HARD&page=1&page_size=50',
    );
    expect(result.current.data).toEqual(mockConstraints);
  });

  it('useDecisionQueue fetches decision queue summary', async () => {
    const mockDecisions: Partial<DecisionQueueSummary> = {
      expedition_id: 'exp-1',
      total_pending_replans: 1,
      total_pending_approvals: 1,
      pending_approvals: [],
    };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockDecisions);

    const { result } = renderHook(() => useDecisionQueue('exp-1'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith('/control-tower/expeditions/exp-1/decisions');
    expect(result.current.data).toEqual(mockDecisions);
  });

  it('useConsequentialAudit fetches audit actions with page parameter', async () => {
    const mockAudit: Partial<ConsequentialActionItem>[] = [
      {
        approval_id: 'appr-1',
        action_summary: 'Replan RPL-01 applied',
      },
    ];
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockAudit);

    const { result } = renderHook(() => useConsequentialAudit('exp-1', 2), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith(
      '/control-tower/expeditions/exp-1/audit?page=2&page_size=20',
    );
    expect(result.current.data).toEqual(mockAudit);
  });
});

describe('Approval & Apply Mutations', () => {
  let queryClient: ReturnType<typeof createTestQueryClient>;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('executes approve mutation with exact payload and invalidates decision queue and overview', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const mockApprovalResult: Partial<ApprovalRead> = {
      id: 'appr-1',
      recommendation_id: 'rec-1',
      status: 'APPROVED',
      decision: 'APPROVED',
    };
    vi.mocked(apiClient.post).mockResolvedValueOnce(mockApprovalResult);

    const { result } = renderHook(() => useApprovalMutations('exp-1'), { wrapper });

    await result.current.approveMutation.mutateAsync({
      recommendationId: 'rec-1',
      payload: {
        approver_person_id: 'per-01',
        approver_role: 'EXPEDITION_LEADER',
        decision: 'APPROVED',
        comment: 'Flight weather window cleared by meteorology team.',
      },
    });

    expect(apiClient.post).toHaveBeenCalledWith('/recommendations/rec-1/approve', {
      approver_person_id: 'per-01',
      approver_role: 'EXPEDITION_LEADER',
      decision: 'APPROVED',
      comment: 'Flight weather window cleared by meteorology team.',
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: controlTowerKeys.decisions('exp-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: controlTowerKeys.summary('exp-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['control-tower', 'overview'],
    });
  });

  it('executes reject mutation with exact payload and invalidates decision queue and overview', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const mockRejectResult: Partial<ApprovalRead> = {
      id: 'appr-1',
      recommendation_id: 'rec-1',
      status: 'REJECTED',
      decision: 'REJECTED',
    };
    vi.mocked(apiClient.post).mockResolvedValueOnce(mockRejectResult);

    const { result } = renderHook(() => useApprovalMutations('exp-1'), { wrapper });

    await result.current.rejectMutation.mutateAsync({
      recommendationId: 'rec-1',
      payload: {
        approver_person_id: 'per-01',
        decision: 'REJECTED',
        comment: 'Traverse route crevasse risk unacceptable.',
      },
    });

    expect(apiClient.post).toHaveBeenCalledWith('/recommendations/rec-1/reject', {
      approver_person_id: 'per-01',
      decision: 'REJECTED',
      comment: 'Traverse route crevasse risk unacceptable.',
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: controlTowerKeys.decisions('exp-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: controlTowerKeys.summary('exp-1'),
    });
  });

  it('executes apply mutation and invalidates all affected operational domains', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const mockApplyResult: Partial<ReplanApplyResult> = {
      recommendation_id: 'rec-1',
      status: 'APPLIED',
      message: 'Operational mutations executed successfully',
    };
    vi.mocked(apiClient.post).mockResolvedValueOnce(mockApplyResult);

    const { result } = renderHook(() => useApprovalMutations('exp-1'), { wrapper });

    await result.current.applyMutation.mutateAsync({
      recommendationId: 'rec-1',
      payload: {
        actor_person_id: 'per-01',
        comment: 'Applying approved transport diversion.',
      },
    });

    expect(apiClient.post).toHaveBeenCalledWith('/recommendations/rec-1/apply', {
      actor_person_id: 'per-01',
      comment: 'Applying approved transport diversion.',
    });

    // Invariant: Apply invalidates decisions, summary, missions, constraints, events, audit, overview
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: controlTowerKeys.decisions('exp-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: controlTowerKeys.summary('exp-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: controlTowerKeys.missionsRoot('exp-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: controlTowerKeys.constraintsRoot('exp-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: controlTowerKeys.eventsRoot('exp-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: controlTowerKeys.auditRoot('exp-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['control-tower', 'overview'],
    });
  });

  it('correctly uses variables.expeditionId when defaultExpeditionId is undefined', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const mockResult: Partial<ApprovalRead> = {
      id: 'appr-2',
      recommendation_id: 'rec-2',
      status: 'APPROVED',
    };
    vi.mocked(apiClient.post).mockResolvedValueOnce(mockResult);

    // Call hook without defaultExpeditionId
    const { result } = renderHook(() => useApprovalMutations(), { wrapper });

    await result.current.approveMutation.mutateAsync({
      recommendationId: 'rec-2',
      expeditionId: 'exp-99',
      payload: {
        approver_person_id: 'per-01',
        decision: 'APPROVED',
      },
    });

    // Invalidation should target exp-99
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: controlTowerKeys.decisions('exp-99'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: controlTowerKeys.summary('exp-99'),
    });
  });

  it('falls back to expedition predicate invalidation when no expeditionId is provided', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const mockResult: Partial<ReplanApplyResult> = {
      recommendation_id: 'rec-3',
      status: 'APPLIED',
      message: 'Applied',
    };
    vi.mocked(apiClient.post).mockResolvedValueOnce(mockResult);

    const { result } = renderHook(() => useApprovalMutations(), { wrapper });

    await result.current.applyMutation.mutateAsync({
      recommendationId: 'rec-3',
      payload: {
        actor_person_id: 'per-01',
      },
    });

    // Should call predicate invalidation for control-tower expedition queries
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        predicate: expect.any(Function),
      }),
    );
  });
});
