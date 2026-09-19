import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ScenarioCockpitBanner } from '../ScenarioCockpitBanner';
import { renderWithProviders } from '../../../../test-utils';
import { apiClient } from '../../../../lib/api/client';
import type { ScenarioInjectResult } from '../../../../lib/types/api';

vi.mock('../../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
  buildQuery: vi.fn(() => ''),
}));

describe('ScenarioCockpitBanner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all three benchmark scenario buttons with provenance and governance labels', () => {
    renderWithProviders(<ScenarioCockpitBanner expeditionId="exp-123" />);

    expect(
      screen.getByRole('heading', { name: /polar disruption simulation cockpit/i }),
    ).toBeInTheDocument();
    expect(screen.getByText('[SYNTHETIC/DEMO]')).toBeInTheDocument();
    expect(screen.getByText(/Autonomous Replanning Prohibited/i)).toBeInTheDocument();

    expect(screen.getByTestId('scenario-btn-flight_grounding')).toBeInTheDocument();
    expect(screen.getByTestId('scenario-btn-generator_failure')).toBeInTheDocument();
    expect(screen.getByTestId('scenario-btn-cold_chain_excursion')).toBeInTheDocument();
  });

  it('injects flight grounding scenario and renders result banner with affected entity', async () => {
    const user = userEvent.setup();
    const mockResult: ScenarioInjectResult = {
      scenario_key: 'FLIGHT_GROUNDING',
      summary: 'Transport leg T-AIR-01 delayed +5.0 days due to adverse polar weather.',
      trigger_event_id: 'event-abc-123',
      affected_entity_type: 'TRANSPORT_LEG',
      affected_entity_id: 'leg-uuid-1',
      affected_entity_code: 'T-AIR-01',
      data_provenance: 'SYNTHETIC_DEMO',
      timestamp: '2026-09-19T10:00:00Z',
    };

    vi.mocked(apiClient.post).mockResolvedValueOnce(mockResult);

    renderWithProviders(<ScenarioCockpitBanner expeditionId="exp-123" />);

    const flightBtn = screen.getByTestId('scenario-btn-flight_grounding');
    await user.click(flightBtn);

    expect(apiClient.post).toHaveBeenCalledWith('/control-tower/scenarios/inject', {
      scenario_key: 'FLIGHT_GROUNDING',
      expedition_id: 'exp-123',
    });

    await waitFor(() => {
      expect(screen.getByTestId('scenario-result-banner')).toBeInTheDocument();
    });

    expect(screen.getByText(/Disruption Injected: FLIGHT_GROUNDING/i)).toBeInTheDocument();
    expect(screen.getByText('T-AIR-01')).toBeInTheDocument();
    expect(screen.getByText(mockResult.summary)).toBeInTheDocument();
  });

  it('displays error banner when scenario injection fails', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.post).mockRejectedValueOnce(
      new Error('No active transport legs found for expedition exp-123.'),
    );

    renderWithProviders(<ScenarioCockpitBanner expeditionId="exp-123" />);

    const flightBtn = screen.getByTestId('scenario-btn-flight_grounding');
    await user.click(flightBtn);

    await waitFor(() => {
      expect(screen.getByTestId('scenario-error-banner')).toBeInTheDocument();
    });

    expect(
      screen.getByText(/No active transport legs found for expedition exp-123/i),
    ).toBeInTheDocument();
  });
});
