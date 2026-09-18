import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import { OperationalTimeline } from '../OperationalTimeline';
import { apiClient } from '../../../lib/api/client';
import type { TimelineResponse } from '../../../lib/types/api';

vi.mock('../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
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

const mockTimelineData: TimelineResponse = {
  entity_type: 'ASSET',
  entity_id: 'asset-test-123',
  entity_name: 'PistenBully Snowcat',
  total_entries: 2,
  page: 1,
  page_size: 20,
  total_pages: 1,
  related_entities_included: false,
  entries: [
    {
      id: 'entry-01',
      entry_type: 'OPERATIONAL_EVENT',
      timestamp: '2026-09-18T12:00:00Z',
      event_or_action: 'AssetStatusTransitioned',
      audit_action: 'TRANSITION_ASSET',
      entity_type: 'ASSET',
      entity_id: 'asset-test-123',
      entity_name: 'PistenBully Snowcat',
      source: 'EVENT_JOURNAL+TRANSITION_ASSET',
      previous_state: 'AVAILABLE',
      new_state: 'MAINTENANCE',
      status: 'MAINTENANCE',
      actor_type: 'USER',
      actor_id: 'person-operator-1',
      correlation_id: 'corr-uuid-001',
      data_provenance: 'SYNTHETIC_DEMO',
      description: 'Status: AVAILABLE -> MAINTENANCE',
      details: {
        reason: 'Hydraulic line replacement',
        before_snapshot: { status: 'AVAILABLE' },
        after_snapshot: { status: 'MAINTENANCE' },
      },
    },
    {
      id: 'entry-02',
      entry_type: 'PROPAGATION_RECORD',
      timestamp: '2026-09-18T10:00:00Z',
      event_or_action: 'IncidentPropagation:MAINTENANCE_ASSET',
      audit_action: null,
      entity_type: 'INCIDENT_PROPAGATION',
      entity_id: 'prop-uuid-002',
      entity_name: 'PROP-MAINTENANCE_ASSET',
      source: 'INCIDENT_PROPAGATION_ENGINE',
      previous_state: 'AVAILABLE',
      new_state: 'MAINTENANCE',
      status: 'APPLIED',
      actor_type: 'SYSTEM',
      actor_id: null,
      correlation_id: 'corr-uuid-002',
      data_provenance: 'SYNTHETIC_DEMO',
      description: 'Propagation (MAINTENANCE_ASSET): APPLIED on ASSET',
      details: {
        reference_type: 'ASSET',
        reference_id: 'asset-test-123',
        action: 'MAINTENANCE_ASSET',
        status: 'APPLIED',
      },
    },
  ],
};

describe('OperationalTimeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    vi.mocked(apiClient.get).mockReturnValue(new Promise(() => {})); // pending
    renderWithProviders(<OperationalTimeline entityType="ASSET" entityId="asset-test-123" />);

    expect(screen.getByText('Operational History & Event Journal')).toBeInTheDocument();
  });

  it('renders operational timeline entries with badges and state transitions', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockTimelineData);
    renderWithProviders(<OperationalTimeline entityType="ASSET" entityId="asset-test-123" />);

    await waitFor(() => {
      expect(screen.getByText('AssetStatusTransitioned')).toBeInTheDocument();
    });

    expect(screen.getByText('EVENT')).toBeInTheDocument();
    expect(screen.getByText('Audit: TRANSITION_ASSET')).toBeInTheDocument();
    expect(screen.getByText('IncidentPropagation:MAINTENANCE_ASSET')).toBeInTheDocument();
    expect(screen.getByText('PROPAGATION')).toBeInTheDocument();

    // Check state transition
    expect(screen.getAllByText('AVAILABLE').length).toBeGreaterThan(0);
    expect(screen.getAllByText('MAINTENANCE').length).toBeGreaterThan(0);
  });

  it('toggles expandable details to display json evidence', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValue(mockTimelineData);
    renderWithProviders(<OperationalTimeline entityType="ASSET" entityId="asset-test-123" />);

    await waitFor(() => {
      expect(screen.getByText('AssetStatusTransitioned')).toBeInTheDocument();
    });

    const viewDetailsButtons = screen.getAllByRole('button', { name: /view details/i });
    expect(viewDetailsButtons.length).toBeGreaterThan(0);

    // Click View Details
    await user.click(viewDetailsButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Hydraulic line replacement/i)).toBeInTheDocument();
    });

    // Click Hide Details
    const hideDetailsButton = screen.getByRole('button', { name: /hide details/i });
    await user.click(hideDetailsButton);

    await waitFor(() => {
      expect(screen.queryByText(/Hydraulic line replacement/i)).not.toBeInTheDocument();
    });
  });

  it('renders empty state when no timeline entries exist', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      entity_type: 'ASSET',
      entity_id: 'asset-test-empty',
      total_entries: 0,
      page: 1,
      page_size: 20,
      total_pages: 1,
      entries: [],
      related_entities_included: false,
    });

    renderWithProviders(<OperationalTimeline entityType="ASSET" entityId="asset-test-empty" />);

    await waitFor(() => {
      expect(
        screen.getByText('No operational history or events recorded for this entity.'),
      ).toBeInTheDocument();
    });
  });

  it('triggers refetch when include related checkbox is toggled', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValue(mockTimelineData);
    renderWithProviders(<OperationalTimeline entityType="ASSET" entityId="asset-test-123" />);

    await waitFor(() => {
      expect(screen.getByText('AssetStatusTransitioned')).toBeInTheDocument();
    });

    const checkbox = screen.getByLabelText(/include related/i);
    expect(checkbox).not.toBeChecked();

    await user.click(checkbox);
    expect(checkbox).toBeChecked();

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('include_related=true'),
      );
    });
  });
});
