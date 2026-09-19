import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApprovalModal } from '../ApprovalModal';
import { renderWithProviders } from '../../../../test-utils';
import { apiClient } from '../../../../lib/api/client';
import type { RecommendationRead, ApprovalRead, ReplanApplyResult } from '../../../../lib/types/api';

vi.mock('../../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  buildQuery: vi.fn((params) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') q.set(k, String(v));
    }
    const str = q.toString();
    return str ? `?${str}` : '';
  }),
}));

const mockRecommendationDetail: RecommendationRead = {
  id: 'rec-001',
  replan_id: 'rep-001',
  title: 'Divert Cargo Flight to Maitri Airfield',
  summary: 'Re-routes flight FL-902 directly to Maitri airstrip due to local blizzard.',
  rationale: [
    'Novolazarevskaya strip closed due to katabatic storm',
    'Maitri clear weather window open for 6 hours',
  ],
  supporting_evidence: { wind_speed_knots: 55, runway_ice_depth_cm: 12 },
  constraint_evaluation_summary: { evaluated: 3, violated: 1 },
  affected_entities: [{ type: 'TRANSPORT_LEG', id: 'leg-401' }],
  violated_constraints: [{ code: 'CST-COLD-CHAIN-INTEGRITY', name: 'Cold Chain Storage Integrity' }],
  proposed_changes: [{ action: 'DIVERT', destination: 'Maitri' }],
  expected_impact: { delay_hours: 3.5, fuel_delta_percent: 8 },
  assumptions: ['Maitri fuel pump operational'],
  status: 'PROPOSED',
  approval_state: 'PENDING',
  data_provenance: 'DERIVED',
  generated_at: '2026-09-18T14:20:00Z',
  created_at: '2026-09-18T14:20:00Z',
};

const mockApprovalResponse: ApprovalRead = {
  id: 'appr-999',
  recommendation_id: 'rec-001',
  approver_person_id: 'PER-OPS-CHIEF',
  approver_role: 'EXPEDITION_LEADER',
  decision: 'APPROVED',
  comment: 'Approved for mission safety.',
  status: 'APPROVED',
  decided_at: '2026-09-18T14:40:00Z',
  created_at: '2026-09-18T14:40:00Z',
};

const mockApplyResult: ReplanApplyResult = {
  recommendation_id: 'rec-001',
  status: 'APPLIED',
  applied_changes: [{ action: 'DIVERT', target: 'Maitri' }],
  resulting_event_id: 'evt-consequential-001',
  applied_at: '2026-09-18T14:45:00Z',
  message: 'Recommendation successfully enacted across transport domain.',
};

describe('ApprovalModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders recommendation details, rationale, and proposed changes', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockRecommendationDetail);
    renderWithProviders(
      <ApprovalModal recommendationId="rec-001" onClose={vi.fn()} expeditionId="exp-1" />,
    );

    expect(
      await screen.findByText('Divert Cargo Flight to Maitri Airfield'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Novolazarevskaya strip closed due to katabatic storm/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Proposed Domain Changes \(1\)/i),
    ).toBeInTheDocument();
    expect(screen.getByText('Cold Chain Storage Integrity')).toBeInTheDocument();
  });

  it('proves governance invariant: Apply button is NOT available before approval', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockRecommendationDetail);
    renderWithProviders(
      <ApprovalModal recommendationId="rec-001" onClose={vi.fn()} expeditionId="exp-1" />,
    );

    await screen.findByText('Divert Cargo Flight to Maitri Airfield');

    // In review phase, Apply must NOT be available
    expect(
      screen.queryByRole('button', { name: /apply recommendation/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /approve recommendation/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reject recommendation/i })).toBeInTheDocument();
  });

  it('submits approval and transitions to APPROVED — READY TO APPLY without automatically applying', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValue(mockRecommendationDetail);
    vi.mocked(apiClient.post).mockResolvedValue(mockApprovalResponse);

    renderWithProviders(
      <ApprovalModal recommendationId="rec-001" onClose={vi.fn()} expeditionId="exp-1" />,
    );

    await screen.findByText('Divert Cargo Flight to Maitri Airfield');

    const personInput = screen.getByTestId('approver-person-id-input');
    const roleInput = screen.getByTestId('approver-role-input');
    const commentInput = screen.getByTestId('approval-comment-input');

    await user.type(personInput, 'PER-OPS-CHIEF');
    await user.clear(roleInput);
    await user.type(roleInput, 'EXPEDITION_LEADER');
    await user.type(commentInput, 'Approved for mission safety.');

    const approveBtn = screen.getByRole('button', { name: /approve recommendation/i });
    await user.click(approveBtn);

    // Verify correct approval POST payload
    expect(apiClient.post).toHaveBeenCalledTimes(1);
    expect(apiClient.post).toHaveBeenCalledWith('/recommendations/rec-001/approve', {
      approver_person_id: 'PER-OPS-CHIEF',
      approver_role: 'EXPEDITION_LEADER',
      decision: 'APPROVED',
      comment: 'Approved for mission safety.',
    });

    // Verify state transition
    expect(await screen.findByText('APPROVED — READY TO APPLY')).toBeInTheDocument();

    // HARD INVARIANT CHECK: Verify /apply was NOT called automatically!
    expect(apiClient.post).not.toHaveBeenCalledWith(
      '/recommendations/rec-001/apply',
      expect.anything(),
    );

    // Apply button is now present and waiting for separate explicit click
    expect(screen.getByRole('button', { name: /apply recommendation/i })).toBeInTheDocument();
  });

  it('submits rejection and transitions to REJECTED state', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValue(mockRecommendationDetail);
    vi.mocked(apiClient.post).mockResolvedValue({
      ...mockApprovalResponse,
      decision: 'REJECTED',
      status: 'REJECTED',
    });

    renderWithProviders(
      <ApprovalModal recommendationId="rec-001" onClose={vi.fn()} expeditionId="exp-1" />,
    );

    await screen.findByText('Divert Cargo Flight to Maitri Airfield');

    const personInput = screen.getByTestId('approver-person-id-input');
    await user.type(personInput, 'PER-OPS-CHIEF');

    const rejectBtn = screen.getByRole('button', { name: /reject recommendation/i });
    await user.click(rejectBtn);

    expect(apiClient.post).toHaveBeenCalledWith('/recommendations/rec-001/reject', {
      approver_person_id: 'PER-OPS-CHIEF',
      approver_role: 'EXPEDITION_OPERATOR',
      decision: 'REJECTED',
      comment: undefined,
    });

    expect(await screen.findByText('RECOMMENDATION REJECTED')).toBeInTheDocument();
  });

  it('executes Apply after approval only upon separate explicit click', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValue({
      ...mockRecommendationDetail,
      approval_state: 'APPROVED',
    });
    vi.mocked(apiClient.post).mockResolvedValue(mockApplyResult);

    renderWithProviders(
      <ApprovalModal recommendationId="rec-001" onClose={vi.fn()} expeditionId="exp-1" />,
    );

    // Should already be in APPROVED — READY TO APPLY state
    expect(await screen.findByText('APPROVED — READY TO APPLY')).toBeInTheDocument();

    const actorInput = screen.getByTestId('apply-actor-person-id-input');
    await user.type(actorInput, 'PER-LOGISTICS-OFFICER');

    const applyBtn = screen.getByRole('button', { name: /apply recommendation/i });
    await user.click(applyBtn);

    // Verify /apply was called with correct ReplanApplyRequest payload
    expect(apiClient.post).toHaveBeenCalledWith('/recommendations/rec-001/apply', {
      actor_person_id: 'PER-LOGISTICS-OFFICER',
      comment: undefined,
    });

    // Verify terminal application message
    expect(await screen.findByText('RECOMMENDATION APPLIED')).toBeInTheDocument();
    expect(
      screen.getByText('Recommendation successfully enacted across transport domain.'),
    ).toBeInTheDocument();
  });

  it('displays application failure without losing approval state', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValue({
      ...mockRecommendationDetail,
      approval_state: 'APPROVED',
    });
    vi.mocked(apiClient.post).mockRejectedValueOnce(new Error('Downstream domain service unreachable'));

    renderWithProviders(
      <ApprovalModal recommendationId="rec-001" onClose={vi.fn()} expeditionId="exp-1" />,
    );

    expect(await screen.findByText('APPROVED — READY TO APPLY')).toBeInTheDocument();

    const actorInput = screen.getByTestId('apply-actor-person-id-input');
    await user.type(actorInput, 'PER-OPERATOR-1');

    const applyBtn = screen.getByRole('button', { name: /apply recommendation/i });
    await user.click(applyBtn);

    expect(
      await screen.findByText(/Application Failed: Downstream domain service unreachable/i),
    ).toBeInTheDocument();
    expect(screen.getByText('APPROVED — READY TO APPLY')).toBeInTheDocument();
  });

  it('proves the invariant: "click Approve" ≠ "Apply Recommendation"', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValue(mockRecommendationDetail);
    vi.mocked(apiClient.post).mockResolvedValueOnce(mockApprovalResponse);
    vi.mocked(apiClient.post).mockResolvedValueOnce(mockApplyResult);

    renderWithProviders(
      <ApprovalModal recommendationId="rec-001" onClose={vi.fn()} expeditionId="exp-1" />,
    );

    await screen.findByText('Divert Cargo Flight to Maitri Airfield');

    // Step 1: Invariant proof - Apply button does not exist
    expect(screen.queryByRole('button', { name: /apply recommendation/i })).toBeNull();

    // Step 2: Fill operator identity and click Approve
    const personInput = screen.getByTestId('approver-person-id-input');
    await user.type(personInput, 'PER-COMMANDER');

    const approveBtn = screen.getByRole('button', { name: /approve recommendation/i });
    await user.click(approveBtn);

    // Invariant proof: ONLY approve endpoint was called
    expect(apiClient.post).toHaveBeenCalledTimes(1);
    expect(apiClient.post).toHaveBeenCalledWith(
      '/recommendations/rec-001/approve',
      expect.objectContaining({
        approver_person_id: 'PER-COMMANDER',
        decision: 'APPROVED',
      }),
    );
    expect(apiClient.post).not.toHaveBeenCalledWith(
      '/recommendations/rec-001/apply',
      expect.anything(),
    );

    // Step 3: Transitioned to Ready to Apply
    expect(await screen.findByText('APPROVED — READY TO APPLY')).toBeInTheDocument();
    const applyBtn = screen.getByRole('button', { name: /apply recommendation/i });
    expect(applyBtn).toBeInTheDocument();

    // Step 4: Explicit click on Apply
    await user.click(applyBtn);

    // Invariant proof: Now and only now was apply called
    expect(apiClient.post).toHaveBeenCalledTimes(2);
    expect(apiClient.post).toHaveBeenLastCalledWith(
      '/recommendations/rec-001/apply',
      expect.objectContaining({
        actor_person_id: 'PER-COMMANDER',
      }),
    );
  });
});
