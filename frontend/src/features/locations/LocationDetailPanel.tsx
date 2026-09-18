import { X, MapPin } from 'lucide-react';
import { useLocation } from './hooks/useLocation';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { LocationStatusBadge } from './LocationStatusBadge';
import { LocationStateActions } from './LocationStateActions';
import { LocationHierarchyTree } from './LocationHierarchyTree';
import { EntityCode } from '../../components/shared/EntityCode';
import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import type { Location } from '../../lib/types/api';

interface Props {
  locationId: string | null;
  onClose: () => void;
  onNavigate?: (location: Location) => void;
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-slate-800/60 last:border-0">
      <span className="text-slate-500 text-xs w-36 shrink-0 pt-0.5">{label}</span>
      <span className="text-slate-200 text-sm break-all">{value ?? <span className="text-slate-600 italic">—</span>}</span>
    </div>
  );
}

export function LocationDetailPanel({ locationId, onClose, onNavigate }: Props) {
  const { data: location, isLoading, error } = useLocation(locationId);

  return (
    <div
      className="fixed inset-y-0 right-0 z-40 w-full max-w-xl flex flex-col bg-slate-900 border-l border-slate-700 shadow-2xl"
      role="dialog"
      aria-modal="true"
      aria-label="Location details"
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm">
        <MapPin className="w-5 h-5 text-cyan-400" aria-hidden="true" />
        <h2 className="text-slate-100 font-semibold flex-1 text-sm">
          {isLoading ? 'Loading…' : (location?.name ?? 'Location Details')}
        </h2>
        {location && <ProvenanceTag provenance={location.data_provenance} />}
        <button
          type="button"
          onClick={onClose}
          className="text-slate-500 hover:text-slate-200 transition-colors ml-2"
          aria-label="Close panel"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {isLoading && <LoadingSkeleton lines={8} />}
        {error && <ErrorDisplay error={error} title="Failed to load location" />}

        {location && (
          <>
            {/* Core details */}
            <section aria-label="Location details">
              <div className="flex items-center gap-3 mb-4">
                <EntityCode code={location.code} />
                <LocationStatusBadge status={location.status} />
                <span className="text-xs text-slate-500 font-mono">{location.type}</span>
              </div>

              <div className="divide-y divide-slate-800/60">
                <DetailRow label="Name" value={location.name} />
                <DetailRow label="Type" value={location.type} />
                <DetailRow
                  label="Coordinates"
                  value={
                    location.latitude && location.longitude
                      ? `${location.latitude}°, ${location.longitude}°`
                      : null
                  }
                />
                <DetailRow label="Description" value={location.description} />
                <DetailRow
                  label="Created"
                  value={new Date(location.created_at).toLocaleString()}
                />
                <DetailRow
                  label="Updated"
                  value={new Date(location.updated_at).toLocaleString()}
                />
              </div>
            </section>

            {/* Hierarchy */}
            <section aria-label="Location hierarchy">
              <h3 className="text-xs text-slate-500 uppercase tracking-wider mb-3">Hierarchy</h3>
              <LocationHierarchyTree
                locationId={location.id}
                onSelect={onNavigate}
              />
            </section>

            {/* State Actions */}
            <section aria-label="State transitions">
              <h3 className="text-xs text-slate-500 uppercase tracking-wider mb-3">
                Operational Actions
              </h3>
              <LocationStateActions location={location} />
            </section>
          </>
        )}
      </div>
    </div>
  );
}
