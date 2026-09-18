import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import { AssetsPage } from '../AssetsPage';
import { apiClient } from '../../../lib/api/client';
import type { Asset } from '../../../lib/types/api';

vi.mock('../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
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

const mockAssets: Asset[] = [
  {
    id: 'asset-001',
    code: 'GEN-BHARATI-01',
    serial_number: 'CAT-3512-9881',
    type: 'DIESEL_GENERATOR',
    status: 'AVAILABLE',
    criticality: 'LIFE_SUPPORT',
    condition: 'OPERATIONAL',
    location_id: 'loc-bharati-powerhouse',
    description: 'Station primary base load generator',
    commissioned_at: '2020-01-01T00:00:00Z',
    retired_at: null,
    operational_metadata: {},
    data_provenance: 'MEASURED',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'asset-002',
    code: 'SKIDOO-EXPL-04',
    serial_number: 'BRP-600-ACE-04',
    type: 'SNOWMOBILE',
    status: 'MAINTENANCE',
    criticality: 'STANDARD',
    condition: 'DEGRADED',
    location_id: 'loc-maitri-hangar',
    description: 'Field reconnaissance snow vehicle',
    commissioned_at: '2022-06-01T00:00:00Z',
    retired_at: null,
    operational_metadata: {},
    data_provenance: 'MEASURED',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

describe('AssetsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders asset registry with code, type, status, and condition', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockAssets);
    renderWithProviders(<AssetsPage />);

    expect(screen.getByRole('heading', { name: 'Assets & Maintenance' })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('GEN-BHARATI-01')).toBeInTheDocument();
      expect(screen.getByText('DIESEL_GENERATOR')).toBeInTheDocument();
      expect(screen.getAllByText('AVAILABLE').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('OPERATIONAL')).toBeInTheDocument();
      expect(screen.getByText('SKIDOO-EXPL-04')).toBeInTheDocument();
    });
  });

  it('filters assets by search query', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockAssets);
    const user = userEvent.setup();
    renderWithProviders(<AssetsPage />);

    await waitFor(() => {
      expect(screen.getByText('GEN-BHARATI-01')).toBeInTheDocument();
    });

    const searchInput = screen.getByLabelText('Search assets');
    await user.type(searchInput, 'CAT-3512');

    expect(screen.getByText('GEN-BHARATI-01')).toBeInTheDocument();
    expect(screen.queryByText('SKIDOO-EXPL-04')).not.toBeInTheDocument();
  });

  it('filters assets by status selection', async () => {
    vi.mocked(apiClient.get).mockResolvedValue([mockAssets[1]]);
    const user = userEvent.setup();
    renderWithProviders(<AssetsPage />);

    const select = screen.getByLabelText('Filter by Status');
    await user.selectOptions(select, 'MAINTENANCE');

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(expect.stringContaining('status=MAINTENANCE'));
    });
  });

  it('opens asset detail drawer on inspect button click', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/maintenance')) return Promise.resolve([]);
      if (path.includes('/timeline')) return Promise.resolve({ asset_id: 'asset-001', history: [] });
      return Promise.resolve(mockAssets);
    });

    const user = userEvent.setup();
    renderWithProviders(<AssetsPage />);

    await waitFor(() => {
      expect(screen.getByText('GEN-BHARATI-01')).toBeInTheDocument();
    });

    const inspectBtn = screen.getByLabelText('Inspect GEN-BHARATI-01');
    await user.click(inspectBtn);

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /Asset details for GEN-BHARATI-01/i })).toBeInTheDocument();
    });
  });
});
