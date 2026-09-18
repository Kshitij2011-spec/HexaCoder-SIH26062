interface Props {
  provenance?: string;
  className?: string;
}

const PROVENANCE_STYLES: Record<string, string> = {
  SYNTHETIC_DEMO: 'text-slate-400 border-slate-600',
  MEASURED:       'text-emerald-400 border-emerald-700',
  DERIVED:        'text-sky-400 border-sky-700',
  FORECAST:       'text-violet-400 border-violet-700',
  SCENARIO:       'text-amber-400 border-amber-700',
  ADVISORY:       'text-cyan-400 border-cyan-700',
};

export function ProvenanceTag({ provenance = 'SYNTHETIC_DEMO', className = '' }: Props) {
  const style = PROVENANCE_STYLES[provenance] ?? PROVENANCE_STYLES.SYNTHETIC_DEMO;
  const label = provenance === 'SYNTHETIC_DEMO' ? 'SYNTHETIC/DEMO' : provenance;
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono border ${style} ${className}`}
      title={`Data provenance: ${label}`}
      aria-label={`Data provenance: ${label}`}
    >
      [{label}]
    </span>
  );
}
