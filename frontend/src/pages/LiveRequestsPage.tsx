import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { AutoRefreshControl, DataTable } from "../components/metrics";
import { RequestEventItem } from "../types";

export function LiveRequestsPage() {
  const [page, setPage] = useState(1);
  const [domain, setDomain] = useState("");
  const [status, setStatus] = useState("");
  const [clientIp, setClientIp] = useState("");
  const [search, setSearch] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);

  const params = new URLSearchParams({ page: String(page), page_size: "100" });
  if (domain) params.set("domain", domain);
  if (status) params.set("status", status);
  if (clientIp) params.set("client_ip", clientIp);
  if (search) params.set("search", search);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["live-requests", params.toString()],
    queryFn: () => api.liveRequests(params),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Live Requests</h2>
          <p className="text-sm text-white/60">Sampled request events from enhanced access logs.</p>
        </div>
        <AutoRefreshControl enabled={autoRefresh} onEnabledChange={setAutoRefresh} onRefresh={() => refetch()} />
      </div>

      <Card title="Filters">
        <div className="grid gap-3 md:grid-cols-4">
          <input
            className="rounded-lg bg-black/20 px-3 py-2 text-sm"
            placeholder="Domain"
            value={domain}
            onChange={(e) => {
              setPage(1);
              setDomain(e.target.value);
            }}
          />
          <input
            className="rounded-lg bg-black/20 px-3 py-2 text-sm"
            placeholder="Status code"
            value={status}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value);
            }}
          />
          <input
            className="rounded-lg bg-black/20 px-3 py-2 text-sm"
            placeholder="Client IP"
            value={clientIp}
            onChange={(e) => {
              setPage(1);
              setClientIp(e.target.value);
            }}
          />
          <input
            className="rounded-lg bg-black/20 px-3 py-2 text-sm"
            placeholder="URI search"
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
          />
        </div>
      </Card>

      <Card title={`Requests (${data?.total ?? 0})`}>
        <DataTable<RequestEventItem>
          loading={isLoading}
          rows={data?.items ?? []}
          rowKey={(row) => `${row.timestamp}-${row.client_ip}-${row.uri}`}
          columns={[
            {
              key: "timestamp",
              label: "Time",
              render: (row) => new Date(row.timestamp).toLocaleString(),
            },
            { key: "client_ip", label: "Client", className: "font-mono text-xs" },
            { key: "host", label: "Host" },
            { key: "method", label: "Method" },
            { key: "uri", label: "URI", className: "max-w-xs truncate" },
            { key: "status", label: "Status" },
            {
              key: "response_time_ms",
              label: "RT",
              render: (row) => (row.response_time_ms != null ? `${row.response_time_ms.toFixed(1)} ms` : "—"),
            },
          ]}
        />

        <div className="mt-4 flex items-center justify-between">
          <button
            type="button"
            className="rounded bg-white/10 px-3 py-2 text-sm disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage((value) => Math.max(1, value - 1))}
          >
            Previous
          </button>
          <span className="text-sm text-white/60">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            className="rounded bg-white/10 px-3 py-2 text-sm disabled:opacity-40"
            disabled={page >= totalPages}
            onClick={() => setPage((value) => value + 1)}
          >
            Next
          </button>
        </div>
      </Card>
    </div>
  );
}
