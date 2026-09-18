interface Props {
  code: string;
  onClick?: () => void;
  className?: string;
}

export function EntityCode({ code, onClick, className = '' }: Props) {
  const base = 'font-mono text-xs px-1.5 py-0.5 rounded bg-slate-800 text-sky-300 border border-slate-700 tracking-wide';
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`${base} hover:bg-slate-700 hover:border-sky-600 transition-colors cursor-pointer ${className}`}
        aria-label={`View details for ${code}`}
      >
        {code}
      </button>
    );
  }
  return (
    <span className={`${base} ${className}`} aria-label={`Entity code: ${code}`}>
      {code}
    </span>
  );
}
