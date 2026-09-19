import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OperationalEventsFeed } from '../OperationalEventsFeed';
import { renderWithProviders } from '../../../../test-utils';
import { apiClient } from '../../../../lib/api/client';
import type { OperationalEventFeedItem } from '../../../../lib/types/api';

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

const mockEvents: OperationalEventFeedItem[] = [
  {
    event_id: 'ev-1',
    event_type: 'MissionApproved',
    entity_type: 'MISSION',
    entity_id: 'msn-1010101',
    previous_state: 'PROPOSED',
    new_state: 'APPROVED',
    occurred_at: '2026-09-19T09:30:00Z',
    source: 'API',
    actor_type: 'OPERATOR',
    actor_id: 'usr-901',
    location_id: null,
    correlation_id: 'cor-701',
    evidence: { approval_id: 'app-01', operator_notes: 'Weather window verified' },
    data_provenance: 'MEASURED',
  },
  {
    event_id: 'ev-2',
    event_type: 'TransportLegDeparted',
    entity_type: 'TRANSPORT_LEG',
    entity_id: 'leg-2020202',
    previous_state: 'READY',
    new_state: 'IN_TRANSIT',
    occurred_at: '2026-09-19T08:15:00Z',
    source: 'FIELD_DEVICE',
    actor_type: 'SYSTEM',
    actor_id: null,
    location_id: 'loc-01',
    correlation_id: null,
    evidence: { departure_fuel_liters: 4500 },
    data_provenance: 'DERIVED',
  },
];

describe('OperationalEventsFeed', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton while fetching events', () => {
    vi.mocked(apiClient.get).mockReturnValue(new Promise(() => {}));

    renderWithProviders(<OperationalEventsFeed expeditionId="exp-1" />);

    expect(
      screen.getByRole('heading', { name: /operational events feed/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/loading data/i)).toBeInTheDocument();
  });

  it('renders error display when API call fails', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Event service unavailable'));

    renderWithProviders(<OperationalEventsFeed expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load operational events/i)).toBeInTheDocument();
      expect(screen.getByText('Event service unavailable')).toBeInTheDocument();
    });
  });

  it('renders empty state when no events exist', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce([]);

    renderWithProviders(<OperationalEventsFeed expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText(/no operational events recorded/i)).toBeInTheDocument();
    });
  });

  it('renders chronological events with types, entities, timestamps, and state transitions', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockEvents);

    renderWithProviders(<OperationalEventsFeed expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('MissionApproved')).toBeInTheDocument();
      expect(screen.getByText('MISSION:msn-1010')).toBeInTheDocument();
      expect(screen.getByText('PROPOSED')).toBeInTheDocument();
      expect(screen.getByText('APPROVED')).toBeInTheDocument();

      expect(screen.getByText('TransportLegDeparted')).toBeInTheDocument();
      expect(screen.getByText('TRANSPORT_LEG:leg-2020')).toBeInTheDocument();
      expect(screen.getByText('READY')).toBeInTheDocument();
      expect(screen.getByText('IN_TRANSIT')).toBeInTheDocument();
    });

    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('/control-tower/expeditions/exp-1/events'),
    );
  });

  it('filters events by entity type dropdown and event type input', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockEvents);
    const user = userEvent.setup();

    renderWithProviders(<OperationalEventsFeed expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('MissionApproved')).toBeInTheDocument();
    });

    // Select Entity Type
    const entitySelect = screen.getByLabelText(/filter events by entity type/i);
    await user.selectOptions(entitySelect, 'MISSION');

    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('entity_type=MISSION'),
    );

    // Type Event Type
    const eventInput = screen.getByLabelText(/filter events by event type/i);
    await user.type(eventInput, 'MissionApproved');

    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('event_type=MissionApproved'),
    );
  });

  it('toggles evidence expansion to display structured event details', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockEvents);
    const user = userEvent.setup();

    renderWithProviders(<OperationalEventsFeed expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('MissionApproved')).toBeInTheDocument();
    });

    const toggleButton = screen.getAllByRole('button', {
      name: /show evidence & details/i,
    })[0];
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');

    // Expand
    await user.click(toggleButton);
    expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('operator_notes:')).toBeInTheDocument();
    expect(screen.getByText('Weather window verified')).toBeInTheDocument();

    // Collapse
    await user.click(toggleButton);
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Weather window verified')).not.toBeInTheDocument();
  });

  it('handles pagination navigation', async () => {
    // 20 items to allow "Next" button to be enabled
    const twentyEvents = Array.from({ length: 20 }).map((_, i) => ({
      ...mockEvents[0],
      event_id: `ev-${i}`,
    }));
    vi.mocked(apiClient.get).mockResolvedValue(twentyEvents);
    const user = userEvent.setup();

    renderWithProviders(<OperationalEventsFeed expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('Page 1')).toBeInTheDocument();
    });

    const nextBtn = screen.getByLabelText(/next events page/i);
    expect(nextBtn).toBeEnabled();

    await user.click(nextBtn);

    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('page=2'),
    );
  });
});
