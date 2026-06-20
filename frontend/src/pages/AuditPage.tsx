import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { useAuth } from "../hooks/useAuth";
import { AuditLogEntry } from "../types";

export function AuditPage() {
  const { isAdmin } = useAuth();
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [resource, setResource] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", page, action, resource],
    queryFn: () => api.listAuditLogsFiltered(page, 50, action || undefined, resource || undefined),
    enabled: isAdmin,
  });

  if (!isAdmin) return <p className="text-amber-200">Admin access required.</p>;

  const exportLogs = async (format: "csv" | "json") => {
    const params = new URLSearchParams({ format });
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    if (action) params.set("action", action);
    if (resource) params.set("resource", resource);
    const response = await api.exportAuditLogs(params);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = format === "csv" ? "audit-log.csv" : "audit-log.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Audit Log</h2>
      <Card title="Filters">
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          <input
            className="rounded-lg bg-white/10 px-3 py-2 text-sm"
            placeholder="Action filter"
            value={action}
            onChange={(e) => {
              setAction(e.target.value);
              setPage(1);
            }}
          />
          <input
            className="rounded-lg bg-white/10 px-3 py-2 text-sm"
            placeholder="Resource filter"
            value={resource}
            onChange={(e) => {
              setResource(e.target.value);
              setPage(1);
            }}
          />
          <input
            type="datetime-local"
            className="rounded-lg bg-white/10 px-3 py-2 text-sm"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />
          <input
            type="datetime-local"
            className="rounded-lg bg-white/10 px-3 py-2 text-sm"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
        </div>
        <div className="mt-3 flex gap-2">
          <button className="rounded-lg bg-white/10 px-3 py-2 text-sm" onClick={() => exportLogs("csv")}>
            Export CSV
          </button>
          <button className="rounded-lg bg-white/10 px-3 py-2 text-sm" onClick={() => exportLogs("json")}>
            Export JSON
          </button>
        </div>
      </Card>
      <Card title={`Entries (${data?.total ?? 0})`}>
        {isLoading && <p className="text-sm text-white/60">Loading...</p>}
        <div className="space-y-2">
          {data?.items.map((entry: AuditLogEntry) => (
            <div key={entry.id} className="rounded-lg bg-white/5 px-3 py-2 text-sm">
              <div className="flex flex-wrap gap-2 text-white/70">
                <span>{new Date(entry.created_at).toLocaleString()}</span>
                <span>{entry.username}</span>
                <span className="text-accent">{entry.action}</span>
                <span>{entry.resource}</span>
                <span>{entry.client_ip}</span>
              </div>
            </div>
          ))}
          {!isLoading && !data?.items.length && <p className="text-sm text-white/60">No audit entries.</p>}
        </div>
        {data && data.total > data.page_size && (
          <div className="mt-4 flex gap-2">
            <button
              className="rounded bg-white/10 px-3 py-1 text-sm disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <span className="px-2 py-1 text-sm">
              Page {page} / {Math.ceil(data.total / data.page_size)}
            </span>
            <button
              className="rounded bg-white/10 px-3 py-1 text-sm disabled:opacity-40"
              disabled={page * data.page_size >= data.total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        )}
      </Card>
    </div>
  );
}
