import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DecisionQueuePanel } from '../DecisionQueuePanel';
import { renderWithProviders } from '../../../../test-utils';
import { apiClient } from '../../../../lib/api/client';
import type { DecisionQueueSummary, RecommendationRead } from '../../../../lib/types/api';

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

const mockDecisionQueue: DecisionQueueSummary = {
  expedition_id: 'exp-1',
  total_pending_replans: 1,
  total_pending_recommendations: 2,
  total_pending_approvals: 1,
  pending_approvals: [
    {
      approval_id: 'appr-101',
      recommendation_id: 'rec-001',
      replan_id: 'rep-001',
      recommendation_title: 'Divert Cargo Flight to Maitri Airfield',
      status: 'PENDING',
      required_approver_role: 'FLIGHT_DIRECTOR',
      what_changed: 'Severe katabatic winds detected at Novolazarevskaya station.',
      why_it_matters: 'Prevents fuel exhaustion and guarantees safe landing window.',
      what_constraint_is_involved: 'CST-COLD-CHAIN-INTEGRITY',
      available_options_count: 2,
      created_at: '2026-09-18T14:30:00Z',
    },
  ],
  pending_recommendations: [
    {
      recommendation_id: 'rec-001',
      replan_id: 'rep-001',
      option_id: 'opt-001',
      title: 'Divert Cargo Flight to Maitri Airfield',
      summary: 'Re-routes flight FL-902 directly to Maitri airstrip due to local blizzard.',
      status: 'PROPOSED',
      approval_state: 'PENDING',
      what_is_affected: [{ entity_type: 'TRANSPORT_LEG', id: 'leg-401' }],
      rationale: ['Novolazarevskaya strip closed', 'Maitri clear for 6 hours'],
      proposed_changes: [{ action: 'DIVERT', target: 'Maitri' }],
      created_at: '2026-09-18T14:20:00Z',
    },
    {
      recommendation_id: 'rec-002',
      replan_id: 'rep-002',
      option_id: 'opt-002',
      title: 'Reallocate Generator Spares to Bharati Station',
      summary: 'Transfers secondary diesel generator components from coastal depot.',
      status: 'PROPOSED',
      approval_state: 'PENDING',
      what_is_affected: [{ entity_type: 'INVENTORY_ITEM', id: 'inv-88' }],
      rationale: ['Primary backup power failed test'],
      proposed_changes: [{ action: 'REASSIGN', target: 'Bharati' }],
      created_at: '2026-09-18T14:25:00Z',
    },
  ],
  pending_replans: [
    {
      replan_id: 'rep-001',
      replan_code: 'RPL-2026-001',
      expedition_id: 'exp-1',
      mission_id: 'mis-101',
      status: 'AWAITING_APPROVAL',
      trigger_mode: 'WEATHER_INDUCED',
      trigger_reason: 'Antarctic storm window closure',
      what_changed: 'Flight runway visibility fell below 500m',
      affected_entities_count: 3,
      violated_constraints_count: 1,
      created_at: '2026-09-18T14:15:00Z',
    },
  ],
  data_provenance: 'DERIVED',
  generated_at: '2026-09-18T14:35:00Z',
};

const mockRecommendationDetail: RecommendationRead = {
  id: 'rec-001',
  replan_id: 'rep-001',
  title: 'Divert Cargo Flight to Maitri Airfield',
  summary: 'Re-routes flight FL-902 directly to Maitri airstrip due to local blizzard.',
  rationale: ['Novolazarevskaya strip closed', 'Maitri clear for 6 hours'],
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

describe('DecisionQueuePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton while fetching decision queue', () => {
    vi.mocked(apiClient.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<DecisionQueuePanel expeditionId="exp-1" />);

    expect(screen.getByText('Decision Queue & Human Governance')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /pending approvals/i })).toBeInTheDocument();
  });

  it('renders error display when fetching fails and allows retry', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Decision service unavailable'));
    renderWithProviders(<DecisionQueuePanel expeditionId="exp-1" />);

    expect(
      await screen.findByText('Failed to load operational decision queue'),
    ).toBeInTheDocument();
    expect(screen.getByText('Decision service unavailable')).toBeInTheDocument();
  });

  it('renders pending approvals tab and correct counts', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockDecisionQueue);
    renderWithProviders(<DecisionQueuePanel expeditionId="exp-1" />);

    expect(await screen.findByText('Divert Cargo Flight to Maitri Airfield')).toBeInTheDocument();
    expect(screen.getByText(/Role Required: FLIGHT_DIRECTOR/i)).toBeInTheDocument();
    expect(screen.getByText(/Severe katabatic winds detected/i)).toBeInTheDocument();
    expect(screen.getByText(/CST-COLD-CHAIN-INTEGRITY/i)).toBeInTheDocument();

    // Check tab badge counts
    expect(screen.getByTestId('tab-approvals')).toHaveTextContent('1');
    expect(screen.getByTestId('tab-recommendations')).toHaveTextContent('2');
    expect(screen.getByTestId('tab-replans')).toHaveTextContent('1');
  });

  it('switches to recommendations tab and displays candidate items', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValue(mockDecisionQueue);
    renderWithProviders(<DecisionQueuePanel expeditionId="exp-1" />);

    const recTab = await screen.findByTestId('tab-recommendations');
    await user.click(recTab);

    expect(
      screen.getByText('Reallocate Generator Spares to Bharati Station'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Transfers secondary diesel generator components from coastal depot.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Primary backup power failed test')).toBeInTheDocument();
  });

  it('switches to replans tab and displays active replan items', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValue(mockDecisionQueue);
    renderWithProviders(<DecisionQueuePanel expeditionId="exp-1" />);

    const replansTab = await screen.findByTestId('tab-replans');
    await user.click(replansTab);

    expect(screen.getByText('RPL-2026-001')).toBeInTheDocument();
    expect(screen.getByText(/Mode: WEATHER_INDUCED/i)).toBeInTheDocument();
    expect(screen.getByText(/Flight runway visibility fell below 500m/i)).toBeInTheDocument();
    expect(screen.getByText(/Affected entities: 3/i)).toBeInTheDocument();
    expect(screen.getByText(/Violated constraints: 1/i)).toBeInTheDocument();
  });

  it('renders explicit empty states when queues are empty', async () => {
    const user = userEvent.setup();
    const emptyQueue: DecisionQueueSummary = {
      ...mockDecisionQueue,
      pending_approvals: [],
      pending_recommendations: [],
      pending_replans: [],
      total_pending_approvals: 0,
      total_pending_recommendations: 0,
      total_pending_replans: 0,
    };
    vi.mocked(apiClient.get).mockResolvedValue(emptyQueue);
    renderWithProviders(<DecisionQueuePanel expeditionId="exp-1" />);

    // Approvals tab empty state
    expect(await screen.findByText('No pending approvals')).toBeInTheDocument();

    // Recommendations tab empty state
    await user.click(screen.getByTestId('tab-recommendations'));
    expect(screen.getByText('No pending recommendations')).toBeInTheDocument();

    // Replans tab empty state
    await user.click(screen.getByTestId('tab-replans'));
    expect(screen.getByText('No pending replans')).toBeInTheDocument();
  });

  it('opens ApprovalModal when Review & Decide button is clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (url.includes('/decisions')) return mockDecisionQueue;
      if (url.includes('/recommendations/rec-001')) return mockRecommendationDetail;
      return null;
    });

    const onSelectRec = vi.fn();
    renderWithProviders(
      <DecisionQueuePanel expeditionId="exp-1" onSelectRecommendation={onSelectRec} />,
    );

    const reviewButton = await screen.findByRole('button', { name: /review & decide/i });
    await user.click(reviewButton);

    expect(onSelectRec).toHaveBeenCalledWith('rec-001');
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /operational decision review/i })).toBeInTheDocument();
  });
});
