import { Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './AppLayout';
import { ControlTowerPage } from '../features/control-tower/ControlTowerPage';
import { LocationsPage } from '../features/locations/LocationsPage';
import { CargoPage } from '../features/cargo/CargoPage';
import { TransportPage } from '../features/transport/TransportPage';
import { InventoryPage } from '../features/inventory/InventoryPage';
import { AssetsPage } from '../features/assets/AssetsPage';
import { IncidentsPage } from '../features/incidents/IncidentsPage';

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/control-tower" replace />} />
        <Route path="/control-tower" element={<ControlTowerPage />} />
        <Route path="/locations" element={<LocationsPage />} />
        <Route path="/cargo" element={<CargoPage />} />
        <Route path="/transport" element={<TransportPage />} />
        <Route path="/inventory" element={<InventoryPage />} />
        <Route path="/assets" element={<AssetsPage />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="*" element={<Navigate to="/control-tower" replace />} />
      </Routes>
    </AppLayout>
  );
}
