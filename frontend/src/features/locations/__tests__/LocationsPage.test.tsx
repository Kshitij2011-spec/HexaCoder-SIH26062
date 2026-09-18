import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LocationsPage } from '../LocationsPage';
import { renderWithProviders } from '../../../test-utils';
import { apiClient } from '../../../lib/api/client';
import type { Location } from '../../../lib/types/api';

vi.mock('../../../lib/api/client', () => ({
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

const mockLocations: Location[] = [
  {
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
  },
  {
    id: 'loc-2',
    code: 'LOC-BHARATI',
    name: 'Bharati Station',
    type: 'RESEARCH_STATION',
    status: 'RESTRICTED',
    parent_location_id: null,
    latitude: '-69.4072',
    longitude: '76.1872',
    description: 'Larsemann Hills Station',
    data_provenance: 'SYNTHETIC_DEMO',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

describe('LocationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders locations list successfully', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockLocations);

    renderWithProviders(<LocationsPage />);

    expect(screen.getByText('Locations')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Maitri Research Station')).toBeInTheDocument();
      expect(screen.getByText('LOC-MAITRI')).toBeInTheDocument();
      expect(screen.getByText('Bharati Station')).toBeInTheDocument();
      expect(screen.getByText('LOC-BHARATI')).toBeInTheDocument();
    });
  });

  it('renders empty state when no locations returned', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce([]);

    renderWithProviders(<LocationsPage />);

    await waitFor(() => {
      expect(screen.getByText('No locations found')).toBeInTheDocument();
    });
  });

  it('filters locations by search input', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockLocations);
    const user = userEvent.setup();

    renderWithProviders(<LocationsPage />);

    await waitFor(() => {
      expect(screen.getByText('Maitri Research Station')).toBeInTheDocument();
    });

    const searchInput = screen.getByRole('searchbox', { name: /search locations/i });
    await user.type(searchInput, 'Bharati');

    expect(screen.queryByText('Maitri Research Station')).not.toBeInTheDocument();
    expect(screen.getByText('Bharati Station')).toBeInTheDocument();
  });

  it('renders error display when API call fails', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Internal Server Error'));

    renderWithProviders(<LocationsPage />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load locations')).toBeInTheDocument();
      expect(screen.getByText('Internal Server Error')).toBeInTheDocument();
    });
  });
});
