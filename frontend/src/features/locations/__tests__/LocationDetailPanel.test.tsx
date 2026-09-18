import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { LocationDetailPanel } from '../LocationDetailPanel';
import { renderWithProviders } from '../../../test-utils';
import { apiClient } from '../../../lib/api/client';
import type { Location, LocationHierarchy } from '../../../lib/types/api';

vi.mock('../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  buildQuery: vi.fn(),
}));

const mockLocation: Location = {
  id: 'loc-1',
  code: 'LOC-MAITRI',
  name: 'Maitri Research Station',
  type: 'RESEARCH_STATION',
  status: 'AVAILABLE',
  parent_location_id: null,
  latitude: '-70.7667',
  longitude: '11.7333',
  description: 'Indian Antarctic Research Base',
  data_provenance: 'SYNTHETIC_DEMO',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockHierarchy: LocationHierarchy = {
  location: mockLocation,
  ancestors: [],
  children: [],
};

describe('LocationDetailPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders location details and state action buttons', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/hierarchy')) {
        return Promise.resolve(mockHierarchy);
      }
      return Promise.resolve(mockLocation);
    });

    renderWithProviders(
      <LocationDetailPanel locationId="loc-1" onClose={vi.fn()} />,
    );

    await waitFor(() => {
      expect(screen.getAllByText('Maitri Research Station').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('LOC-MAITRI')).toBeInTheDocument();
      expect(screen.getByText('-70.7667°, 11.7333°')).toBeInTheDocument();
      expect(screen.getByText('Indian Antarctic Research Base')).toBeInTheDocument();
    });

    // Valid transitions from AVAILABLE: RESTRICTED, INACCESSIBLE, CLOSED
    expect(screen.getByRole('button', { name: /transition location to restricted/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /transition location to inaccessible/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /transition location to closed/i })).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/hierarchy')) return Promise.resolve(mockHierarchy);
      return Promise.resolve(mockLocation);
    });

    const onClose = vi.fn();
    renderWithProviders(
      <LocationDetailPanel locationId="loc-1" onClose={onClose} />,
    );

    await waitFor(() => {
      expect(screen.getAllByText('Maitri Research Station').length).toBeGreaterThanOrEqual(1);
    });

    const closeBtn = screen.getByRole('button', { name: /close panel/i });
    closeBtn.click();
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
