import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MitigationOptionsExplorer } from '../MitigationOptionsExplorer';
import { renderWithProviders } from '../../../../test-utils';
import { apiClient } from '../../../../lib/api/client';
import type {
  ReplanRead,
  ReplanOptionRead,
  RecommendationRead,
  ReplanGenerationResult,
} from '../../../../lib/types/api';

vi.mock('../../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
  buildQuery: vi.fn(() => ''),
}));

const mockReplan: ReplanRead = {
  id: 'replan-123',
  replan_code: 'REP-A6-01',
  expedition_id: 'exp-123',
  mission_id: 'mission-456',
  trigger_reason: 'Flight grounding delayed survey logistics',
  status: 'REQUESTED',
  current_state_evidence: {},
  violated_constraints: [],
  affected_entities: [],
  generated_at: '2026-09-19T10:00:00Z',
  data_provenance: 'SYNTHETIC_DEMO',
  created_at: '2026-09-19T10:00:00Z',
  updated_at: '2026-09-19T10:00:00Z',
};

const mockGenerationResult: ReplanGenerationResult = {
  replan_id: 'replan-123',
  options: [
    {
      id: 'opt-1',
      option_code: 'OPT-RESCHEDULE',
      title: 'Reschedule Mission Survey Window (+5 Days)',
      description: 'Extends mission required-by date to match aircraft recovery window.',
      action_type: 'RESCHEDULE_MISSION',
      feasibility: 'FEASIBLE',
      estimated_delay_hours: 120,
      estimated_cost_delta: 0,
      risk_score: 15,
      affected_entities: [],
      violated_constraints: [],
      proposed_changes: [],
      assumptions: ['Weather clears within 5 days'],
      operational_tradeoffs: {},
      data_provenance: 'SYNTHETIC_DEMO',
      created_at: '2026-09-19T10:05:00Z',
    },
    {
      id: 'opt-2',
      option_code: 'OPT-CANCEL',
      title: 'Cancel Mission Survey',
      description: 'Aborts the glaciological survey completely.',
      action_type: 'CANCEL_MISSION',
      feasibility: 'CONSTRAINED',
      estimated_delay_hours: 0,
      estimated_cost_delta: -5000,
      risk_score: 85,
      affected_entities: [],
      violated_constraints: [],
      proposed_changes: [],
      assumptions: [],
      operational_tradeoffs: {},
      data_provenance: 'SYNTHETIC_DEMO',
      created_at: '2026-09-19T10:05:00Z',
    },
  ],
  recommendations: [
    {
      id: 'rec-1',
      replan_id: 'replan-123',
      option_id: 'opt-1',
      title: 'Recommend Reschedule Mission Survey Window (+5 Days)',
      summary: 'Optimal mitigation balancing science objective and safety.',
      rationale: ['Minimal cost impact', 'Preserves mission deliverables'],
      supporting_evidence: {},
      constraint_evaluation_summary: {},
      affected_entities: [],
      violated_constraints: [],
      proposed_changes: [],
      expected_impact: {},
      assumptions: [],
      status: 'PROPOSED',
      approval_state: 'PENDING',
      data_provenance: 'SYNTHETIC_DEMO',
      generated_at: '2026-09-19T10:05:00Z',
      created_at: '2026-09-19T10:05:00Z',
    },
  ],
};

describe('MitigationOptionsExplorer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders replan details and handles option generation with feasibility display', async () => {
    const user = userEvent.setup();
    const handleSelectRec = vi.fn();

    vi.mocked(apiClient.get).mockResolvedValue(mockReplan);
    vi.mocked(apiClient.post).mockResolvedValue(mockGenerationResult);

    renderWithProviders(
      <MitigationOptionsExplorer
        isOpen={true}
        onClose={vi.fn()}
        replanId="replan-123"
        expeditionId="exp-123"
        onSelectRecommendation={handleSelectRec}
      />,
    );

    // Replan header loaded
    await waitFor(() => {
      expect(screen.getByText('REP-A6-01')).toBeInTheDocument();
      expect(screen.getByText(/Flight grounding delayed survey logistics/i)).toBeInTheDocument();
    });

    // Generate Options button clicked
    const generateBtn = screen.getByTestId('generate-options-btn');
    await user.click(generateBtn);

    expect(apiClient.post).toHaveBeenCalledWith('/replans/replan-123/generate-options', {});

    // Options rendered with feasibility badges
    await waitFor(() => {
      expect(screen.getByTestId('mitigation-option-card-opt-reschedule')).toBeInTheDocument();
      expect(screen.getByTestId('mitigation-option-card-opt-cancel')).toBeInTheDocument();
    });

    expect(screen.getByText('FEASIBLE')).toBeInTheDocument();
    expect(screen.getByText('CONSTRAINED')).toBeInTheDocument();

    // Recommendation action button clicked
    const reviewBtn = screen.getByTestId('select-recommendation-rec-1');
    await user.click(reviewBtn);

    expect(handleSelectRec).toHaveBeenCalledWith('rec-1');
  });
});
