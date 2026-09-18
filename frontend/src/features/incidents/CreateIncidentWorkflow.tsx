import { useState } from 'react';
import { AlertOctagon, Plus, X } from 'lucide-react';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { useCreateIncident } from './hooks/useIncidentMutations';
import type { IncidentSeverity } from '../../lib/types/api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onCreated?: () => void;
}

const SEVERITIES: IncidentSeverity[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

export function CreateIncidentWorkflow({ isOpen, onClose, onCreated }: Props) {
  const [code, setCode] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [incidentType, setIncidentType] = useState('EQUIPMENT_FAILURE');
  const [severity, setSeverity] = useState<IncidentSeverity>('HIGH');
  const [priority, setPriority] = useState(2);
  const [locationId, setLocationId] = useState('');
  const [assetId, setAssetId] = useState('');

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const createMutation = useCreateIncident();

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!code.trim() || !title.trim() || !description.trim()) {
      setErrorMessage('Incident code, title, and description are required.');
      return;
    }

    setConfirmOpen(true);
  };

  const handleExecuteCreate = async () => {
    try {
      await createMutation.mutateAsync({
        code: code.trim(),
        title: title.trim(),
        description: description.trim(),
        incident_type: incidentType,
        severity,
        priority: Number(priority),
        location_id: locationId.trim() || null,
        asset_id: assetId.trim() || null,
      });

      setConfirmOpen(false);
      onCreated?.();
      onClose();
    } catch (err) {
      setConfirmOpen(false);
      setErrorMessage(err instanceof Error ? err.message : 'Failed to declare incident.');
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-incident-title"
    >
      <div className="w-full max-w-lg bg-slate-950 border border-slate-800 rounded-xl shadow-2xl overflow-hidden font-mono text-xs">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-2 text-rose-400">
            <AlertOctagon className="w-5 h-5" aria-hidden="true" />
            <h2 id="create-incident-title" className="text-sm font-semibold text-slate-100 font-sans">
              Declare Operational Incident
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-200"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {errorMessage && (
            <ErrorDisplay error={new Error(errorMessage)} title="Declaration Failed" />
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="inc-code" className="block text-slate-400 mb-1">
                Incident Code <span className="text-rose-400">*</span>
              </label>
              <input
                id="inc-code"
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g. INC-2026-004"
                className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                required
              />
            </div>

            <div>
              <label htmlFor="inc-type" className="block text-slate-400 mb-1">
                Incident Type <span className="text-rose-400">*</span>
              </label>
              <select
                id="inc-type"
                value={incidentType}
                onChange={(e) => setIncidentType(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="EQUIPMENT_FAILURE">EQUIPMENT_FAILURE</option>
                <option value="WEATHER_EXCURSION">WEATHER_EXCURSION</option>
                <option value="COLD_CHAIN_EXCURSION">COLD_CHAIN_EXCURSION</option>
                <option value="COMMUNICATIONS_LOSS">COMMUNICATIONS_LOSS</option>
                <option value="PERSONNEL_MEDICAL">PERSONNEL_MEDICAL</option>
                <option value="ROUTE_BLOCKED">ROUTE_BLOCKED</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="inc-title" className="block text-slate-400 mb-1">
              Title <span className="text-rose-400">*</span>
            </label>
            <input
              id="inc-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Generator #2 Auxiliary Coolant Line Breach"
              className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>

          <div>
            <label htmlFor="inc-desc" className="block text-slate-400 mb-1">
              Description <span className="text-rose-400">*</span>
            </label>
            <textarea
              id="inc-desc"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detailed operational impact, observations, and immediate hazard summary"
              className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="inc-severity" className="block text-slate-400 mb-1">
                Severity Level <span className="text-rose-400">*</span>
              </label>
              <select
                id="inc-severity"
                value={severity}
                onChange={(e) => setSeverity(e.target.value as IncidentSeverity)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="inc-priority" className="block text-slate-400 mb-1">
                Priority (1 = Highest)
              </label>
              <input
                id="inc-priority"
                type="number"
                min="1"
                max="5"
                value={priority}
                onChange={(e) => setPriority(parseInt(e.target.value, 10))}
                className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="inc-loc" className="block text-slate-400 mb-1">
                Location ID (Optional)
              </label>
              <input
                id="inc-loc"
                type="text"
                value={locationId}
                onChange={(e) => setLocationId(e.target.value)}
                placeholder="Location UUID"
                className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label htmlFor="inc-asset" className="block text-slate-400 mb-1">
                Asset ID (Optional)
              </label>
              <input
                id="inc-asset"
                type="text"
                value={assetId}
                onChange={(e) => setAssetId(e.target.value)}
                placeholder="Asset UUID"
                className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded bg-rose-700 hover:bg-rose-600 disabled:opacity-50 text-white font-medium transition-colors"
            >
              <Plus className="w-4 h-4" aria-hidden="true" />
              {createMutation.isPending ? 'Declaring...' : 'Declare Incident'}
            </button>
          </div>
        </form>

        <ConfirmDialog
          open={confirmOpen}
          title="Declare Operational Incident"
          message={`Confirm declaration of incident ${code}: "${title}" with severity ${severity}?`}
          confirmLabel="Declare Incident"
          onConfirm={handleExecuteCreate}
          onCancel={() => setConfirmOpen(false)}
        />
      </div>
    </div>
  );
}
