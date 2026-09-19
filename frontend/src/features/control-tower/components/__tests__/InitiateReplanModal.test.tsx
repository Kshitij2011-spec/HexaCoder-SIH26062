import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { InitiateReplanModal } from '../InitiateReplanModal';
import { renderWithProviders } from '../../../../test-utils';
import { apiClient } from '../../../../lib/api/client';
import type { ReplanRead } from '../../../../lib/types/api';

vi.mock('../../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
  buildQuery: vi.fn(() => ''),
}));

const mockCreatedReplan: ReplanRead = {
  id: 'replan-new-789',
  replan_code: 'REP-A6-NEW',
  expedition_id: 'exp-123',
  mission_id: 'mission-456',
  trigger_reason: 'Operational disruption affecting mission M-01',
  status: 'REQUESTED',
  current_state_evidence: {},
  violated_constraints: [],
  affected_entities: [],
  generated_at: '2026-09-19T10:00:00Z',
  data_provenance: 'SYNTHETIC_DEMO',
  created_at: '2026-09-19T10:00:00Z',
  updated_at: '2026-09-19T10:00:00Z',
};

describe('InitiateReplanModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders modal with target context and submits operator replan request', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    const handleCreated = vi.fn();

    vi.mocked(apiClient.post).mockResolvedValueOnce(mockCreatedReplan);

    renderWithProviders(
      <InitiateReplanModal
        isOpen={true}
        onClose={handleClose}
        expeditionId="exp-123"
        missionId="mission-456"
        missionCode="M-SURVEY-01"
        missionTitle="Glaciological Survey"
        onReplanCreated={handleCreated}
      />,
    );

    expect(screen.getByRole('heading', { name: /initiate operational replan/i })).toBeInTheDocument();
    expect(screen.getByText('M-SURVEY-01')).toBeInTheDocument();
    expect(screen.getByText(/Glaciological Survey/i)).toBeInTheDocument();

    const submitBtn = screen.getByTestId('submit-initiate-replan');
    await user.click(submitBtn);

    expect(apiClient.post).toHaveBeenCalledWith('/replans', {
      trigger_mode: 'OPERATOR_REQUESTED',
      expedition_id: 'exp-123',
      mission_id: 'mission-456',
      reason: expect.stringContaining('M-SURVEY-01'),
    });

    await waitFor(() => {
      expect(handleClose).toHaveBeenCalled();
      expect(handleCreated).toHaveBeenCalledWith('replan-new-789');
    });
  });
});
