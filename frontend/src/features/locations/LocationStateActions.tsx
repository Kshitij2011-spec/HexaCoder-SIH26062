import { useState } from 'react';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { LOCATION_TRANSITIONS } from '../../lib/types/api';
import type { Location, LocationStatus } from '../../lib/types/api';
import { useLocationStateTransition } from './hooks/useLocationStateTransition';

interface Props {
  location: Location;
}

const CONSEQUENTIAL: LocationStatus[] = ['INACCESSIBLE', 'CLOSED', 'RESTRICTED'];

export function LocationStateActions({ location }: Props) {
  const [pending, setPending] = useState<LocationStatus | null>(null);
  const transition = useLocationStateTransition();

  const allowed = LOCATION_TRANSITIONS[location.status] ?? [];
  if (allowed.length === 0) {
    return (
      <p className="text-slate-500 text-sm italic">
        No state transitions available from <span className="font-mono">{location.status}</span>.
      </p>
    );
  }

  const handleClick = (target: LocationStatus) => {
    if (CONSEQUENTIAL.includes(target)) {
      setPending(target);
    } else {
      doTransition(target);
    }
  };

  const doTransition = (target: LocationStatus) => {
    transition.mutate({ id: location.id, body: { status: target } });
    setPending(null);
  };

  const STYLE: Record<string, string> = {
    AVAILABLE:    'border-emerald-700 text-emerald-300 hover:bg-emerald-900/30',
    RESTRICTED:   'border-amber-700 text-amber-300 hover:bg-amber-900/30',
    INACCESSIBLE: 'border-rose-700 text-rose-300 hover:bg-rose-900/30',
    CLOSED:       'border-slate-600 text-slate-400 hover:bg-slate-800/60',
  };

  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Transition State</p>
      <div className="flex flex-wrap gap-2">
        {allowed.map((target: LocationStatus) => (
          <button
            key={target}
            type="button"
            disabled={transition.isPending}
            onClick={() => handleClick(target)}
            className={`px-3 py-1.5 rounded border text-xs font-medium transition-colors disabled:opacity-50 ${STYLE[target] ?? 'border-slate-600 text-slate-300 hover:bg-slate-800'}`}
            aria-label={`Transition location to ${target}`}
          >
            → {target}
          </button>
        ))}
      </div>

      {transition.isError && (
        <ErrorDisplay error={transition.error} title="Transition failed" />
      )}

      <ConfirmDialog
        open={!!pending}
        title={`Confirm: ${pending}`}
        message={`This will mark location "${location.name}" as ${pending}. This is a consequential operational change. Are you sure?`}
        confirmLabel={`Set ${pending}`}
        confirmVariant="danger"
        isLoading={transition.isPending}
        onClose={() => setPending(null)}
        onConfirm={() => pending && doTransition(pending)}
      />
    </div>
  );
}
