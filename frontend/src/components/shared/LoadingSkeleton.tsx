interface Props {
  lines?: number;
  className?: string;
}

export function LoadingSkeleton({ lines = 5, className = '' }: Props) {
  return (
    <div className={`space-y-3 ${className}`} aria-busy="true" aria-label="Loading data…">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="animate-pulse flex space-x-4">
          <div className="flex-1 space-y-2">
            <div
              className="h-4 bg-slate-800 rounded"
              style={{ width: `${60 + ((i * 17) % 40)}%` }}
            />
          </div>
          <div className="h-4 w-16 bg-slate-800 rounded" />
        </div>
      ))}
    </div>
  );
}
