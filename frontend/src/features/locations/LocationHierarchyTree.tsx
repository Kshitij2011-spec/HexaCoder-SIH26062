import { ChevronRight, MapPin } from 'lucide-react';
import { EntityCode } from '../../components/shared/EntityCode';
import { LocationStatusBadge } from './LocationStatusBadge';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { useLocationHierarchy } from './hooks/useLocationHierarchy';
import type { Location } from '../../lib/types/api';

interface Props {
  locationId: string;
  onSelect?: (location: Location) => void;
}

export function LocationHierarchyTree({ locationId, onSelect }: Props) {
  const { data, isLoading, error } = useLocationHierarchy(locationId);

  if (isLoading) return <LoadingSkeleton lines={3} />;
  if (error) return <ErrorDisplay error={error} title="Failed to load hierarchy" />;
  if (!data) return null;

  return (
    <div className="space-y-4">
      {/* Ancestors */}
      {data.ancestors.length > 0 && (
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Ancestors</p>
          <div className="space-y-1">
            {data.ancestors.map((ancestor, i) => (
              <div
                key={ancestor.id}
                className="flex items-center gap-2 text-sm text-slate-400"
                style={{ paddingLeft: `${i * 12}px` }}
              >
                <ChevronRight className="w-3 h-3 shrink-0" aria-hidden="true" />
                <MapPin className="w-3 h-3 shrink-0" aria-hidden="true" />
                <button
                  type="button"
                  onClick={() => onSelect?.(ancestor)}
                  className="hover:text-slate-200 transition-colors text-left"
                >
                  {ancestor.name}
                </button>
                <EntityCode code={ancestor.code} />
                <LocationStatusBadge status={ancestor.status} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Current */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700">
        <MapPin className="w-4 h-4 text-cyan-400 shrink-0" aria-hidden="true" />
        <span className="text-slate-200 font-medium text-sm">{data.location.name}</span>
        <EntityCode code={data.location.code} />
        <LocationStatusBadge status={data.location.status} />
        <span className="ml-auto text-xs text-slate-500">{data.location.type}</span>
      </div>

      {/* Children */}
      {data.children.length > 0 && (
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
            Sub-locations ({data.children.length})
          </p>
          <div className="space-y-1">
            {data.children.map((child) => (
              <div key={child.id} className="flex items-center gap-2 text-sm text-slate-400 pl-4">
                <ChevronRight className="w-3 h-3 shrink-0" aria-hidden="true" />
                <button
                  type="button"
                  onClick={() => onSelect?.(child)}
                  className="hover:text-slate-200 transition-colors text-left"
                >
                  {child.name}
                </button>
                <EntityCode code={child.code} />
                <LocationStatusBadge status={child.status} />
              </div>
            ))}
          </div>
        </div>
      )}

      {data.ancestors.length === 0 && data.children.length === 0 && (
        <p className="text-slate-500 text-sm">No hierarchy relationships.</p>
      )}
    </div>
  );
}
