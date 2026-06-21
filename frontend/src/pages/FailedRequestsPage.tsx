import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { AutoRefreshControl, DataTable, TroubleshootingHint } from "../components/metrics";
import { RequestEventItem } from "../types";

const HINTS: Record<number, string> = {
  502: "Check backend connectivity and upstream definitions.",
  504: "Increase upstream timeouts or investigate slow backends.",
  503: "Verify backend pool has healthy members.",
  429: "Review rate limiting thresholds and abusive clients.",
};

export function FailedRequestsPage() {
  const [page, setPage] = useState(1);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["failed-requests", page],
    queryFn: () => api.failedRequests(page),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Failed Requests</h2>
          <p className="text-sm text-white/60">5xx, 429, and correlated error patterns.</p>
        </div>
        <AutoRefreshControl enabled={autoRefresh} onEnabledChange={setAutoRefresh} onRefresh={() => refetch()} />
      </div>

      <TroubleshootingHint
        title="NGINX enhanced logging"
        message="Enable enhanced JSON analytics logging on proxy apps for richer failed-request context. Ensure log_format proxy_json is loaded in nginx http {}."
      />

      <Card title={`Failed requests (${data?.total ?? 0})`}>
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
            { key: "status", label: "Status" },
            { key: "host", label: "Host" },
            { key: "uri", label: "URI", className: "max-w-sm truncate" },
            { key: "backend_addr", label: "Upstream", render: (row) => row.backend_addr || "—" },
            {
              key: "hint",
              label: "Hint",
              render: (row) => HINTS[row.status] ?? "Review nginx error log and backend health.",
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
