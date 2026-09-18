import { PackageSearch } from 'lucide-react';

interface Props {
  title?: string;
  message?: string;
  icon?: React.ReactNode;
}

export function EmptyState({
  title = 'No records found',
  message = 'There are no items to display for the current filters.',
  icon,
}: Props) {
  return (
    <div
      className="flex flex-col items-center justify-center py-16 text-center"
      role="status"
      aria-label={title}
    >
      <div className="mb-4 text-slate-600">
        {icon ?? <PackageSearch className="w-12 h-12" aria-hidden="true" />}
      </div>
      <h3 className="text-slate-300 font-medium mb-1">{title}</h3>
      <p className="text-slate-500 text-sm max-w-sm">{message}</p>
    </div>
  );
}
