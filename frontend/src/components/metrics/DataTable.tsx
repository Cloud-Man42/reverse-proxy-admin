import { ReactNode } from "react";

export interface DataTableColumn<T> {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (row: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  sortKey?: string;
  sortDirection?: "asc" | "desc";
  onSort?: (key: string) => void;
  loading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  rowKey: (row: T) => string | number;
}

export function DataTable<T>({
  columns,
  rows,
  sortKey,
  sortDirection = "desc",
  onSort,
  loading,
  error,
  emptyMessage = "No data available.",
  rowKey,
}: DataTableProps<T>) {
  if (loading) {
    return <p className="text-sm text-white/60">Loading...</p>;
  }

  if (error) {
    return <p className="text-sm text-amber-200">{error}</p>;
  }

  if (!rows.length) {
    return <p className="text-sm text-white/50">{emptyMessage}</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-white/10 text-left text-white/60">
            {columns.map((column) => (
              <th key={column.key} className={`px-3 py-2 ${column.className ?? ""}`}>
                {column.sortable && onSort ? (
                  <button type="button" className="hover:text-white" onClick={() => onSort(column.key)}>
                    {column.label}
                    {sortKey === column.key ? (sortDirection === "asc" ? " ↑" : " ↓") : null}
                  </button>
                ) : (
                  column.label
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-b border-white/5">
              {columns.map((column) => (
                <td key={column.key} className={`px-3 py-3 ${column.className ?? ""}`}>
                  {column.render ? column.render(row) : String((row as Record<string, unknown>)[column.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
