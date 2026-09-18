import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import { InventoryPage } from '../InventoryPage';
import { apiClient } from '../../../lib/api/client';
import type { InventoryItem } from '../../../lib/types/api';

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

const mockItems: InventoryItem[] = [
  {
    id: 'item-001',
    code: 'MED-KIT-01',
    name: 'Polar Trauma Kit',
    category: 'MEDICAL',
    description: 'First response extreme cold trauma kit',
    criticality: 'LIFE_SUPPORT',
    unit_of_measure: 'KIT',
    minimum_temperature_c: '-40',
    maximum_temperature_c: '25',
    hazmat_class: null,
    is_shelf_life_controlled: true,
    default_shelf_life_days: 365,
    data_provenance: 'MEASURED',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'item-002',
    code: 'FUEL-JET-A1',
    name: 'Aviation Turbine Fuel',
    category: 'FUEL',
    description: 'Low-freeze aviation fuel drums',
    criticality: 'MISSION_CRITICAL',
    unit_of_measure: 'DRUM',
    minimum_temperature_c: '-55',
    maximum_temperature_c: '30',
    hazmat_class: 'FLAMMABLE_3',
    is_shelf_life_controlled: false,
    default_shelf_life_days: null,
    data_provenance: 'MEASURED',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

describe('InventoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders inventory catalog items with code, name, and criticality', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockItems);
    renderWithProviders(<InventoryPage />);

    expect(screen.getByRole('heading', { name: 'Inventory Operations' })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('MED-KIT-01')).toBeInTheDocument();
      expect(screen.getByText('Polar Trauma Kit')).toBeInTheDocument();
      expect(screen.getAllByText('LIFE_SUPPORT').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('FUEL-JET-A1')).toBeInTheDocument();
    });
  });

  it('filters items by search input', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockItems);
    const user = userEvent.setup();
    renderWithProviders(<InventoryPage />);

    await waitFor(() => {
      expect(screen.getByText('MED-KIT-01')).toBeInTheDocument();
    });

    const searchInput = screen.getByLabelText('Search inventory items');
    await user.type(searchInput, 'Trauma');

    expect(screen.getByText('Polar Trauma Kit')).toBeInTheDocument();
    expect(screen.queryByText('Aviation Turbine Fuel')).not.toBeInTheDocument();
  });

  it('filters items by criticality select', async () => {
    vi.mocked(apiClient.get).mockResolvedValue([mockItems[0]]);
    const user = userEvent.setup();
    renderWithProviders(<InventoryPage />);

    const select = screen.getByLabelText('Filter by Criticality');
    await user.selectOptions(select, 'LIFE_SUPPORT');

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(expect.stringContaining('criticality=LIFE_SUPPORT'));
    });
  });

  it('opens item detail panel when inspect button is clicked', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/items')) return Promise.resolve(mockItems);
      if (path.includes('/stock-lots')) return Promise.resolve([]);
      return Promise.resolve(null);
    });

    const user = userEvent.setup();
    renderWithProviders(<InventoryPage />);

    await waitFor(() => {
      expect(screen.getByText('MED-KIT-01')).toBeInTheDocument();
    });

    const inspectBtn = screen.getByLabelText('Inspect Polar Trauma Kit');
    await user.click(inspectBtn);

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /Inventory details for Polar Trauma Kit/i })).toBeInTheDocument();
    });
  });
});
