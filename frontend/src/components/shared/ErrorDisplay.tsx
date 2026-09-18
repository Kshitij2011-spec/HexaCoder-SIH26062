import { AlertTriangle } from 'lucide-react';
import type { ApiError } from '../../lib/api/client';

interface Props {
  error: Error | ApiError | unknown;
  title?: string;
}

export function ErrorDisplay({ error, title = 'Request failed' }: Props) {
  const msg =
    error instanceof Error ? error.message : 'An unexpected error occurred.';
  const code = (error as ApiError)?.code;

  return (
    <div
      role="alert"
      className="flex items-start gap-3 p-4 rounded-lg bg-rose-950/40 border border-rose-800/60"
    >
      <AlertTriangle className="w-5 h-5 text-rose-400 mt-0.5 shrink-0" aria-hidden="true" />
      <div>
        <p className="text-rose-300 font-medium text-sm">{title}</p>
        <p className="text-rose-400 text-sm mt-0.5">{msg}</p>
        {code && (
          <p className="text-rose-500 text-xs font-mono mt-1">code: {code}</p>
        )}
      </div>
    </div>
  );
}
