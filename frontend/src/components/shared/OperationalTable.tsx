interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
  className?: string;
}

interface Props<T> {
  columns: Column<T>[];
  data: T[];
  getRowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  className?: string;
}

export function OperationalTable<T>({
  columns,
  data,
  getRowKey,
  onRowClick,
  className = '',
}: Props<T>) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-sm" role="table">
        <thead>
          <tr className="border-b border-slate-800">
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={`px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider ${col.className ?? ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {data.map((row) => (
            <tr
              key={getRowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`transition-colors ${
                onRowClick
                  ? 'cursor-pointer hover:bg-slate-800/60 focus-within:bg-slate-800/60'
                  : ''
              }`}
              tabIndex={onRowClick ? 0 : undefined}
              onKeyDown={
                onRowClick
                  ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') onRowClick(row);
                    }
                  : undefined
              }
              role={onRowClick ? 'button' : 'row'}
              aria-label={onRowClick ? `Open ${getRowKey(row)}` : undefined}
            >
              {columns.map((col) => (
                <td key={col.key} className={`px-4 py-3 text-slate-200 ${col.className ?? ''}`}>
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
