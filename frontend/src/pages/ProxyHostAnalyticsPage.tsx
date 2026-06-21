import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { DataTable, MetricsPageHeader } from "../components/metrics";
import { StatusBadge } from "../components/StatusBadge";
import { formatBytes } from "../lib/formatBytes";
import { MetricsProxyHostItem, MetricsRange } from "../types";

export function ProxyHostAnalyticsPage() {
  const [range, setRange] = useState<MetricsRange>("24h");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [sortBy, setSortBy] = useState("requests");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["metrics-proxy-hosts", range, sortBy],
    queryFn: () => api.metricsProxyHosts(range, sortBy),
  });

  return (
    <div className="space-y-6">
      <MetricsPageHeader
        title="Proxy Host Analytics"
        description="Sortable traffic and error metrics per proxy host."
        range={range}
        onRangeChange={setRange}
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
        onRefresh={() => refetch()}
        actions={
          <select
            className="text-sm"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="requests">Sort by requests</option>
            <option value="errors">Sort by errors</option>
            <option value="error_rate">Sort by error rate</option>
            <option value="response_time">Sort by response time</option>
            <option value="bandwidth">Sort by bandwidth</option>
          </select>
        }
      />

      <Card title="Proxy hosts">
        <DataTable<MetricsProxyHostItem>
          loading={isLoading}
          rows={data?.items ?? []}
          rowKey={(row) => row.proxy_id}
          columns={[
            {
              key: "proxy_id",
              label: "Proxy",
              render: (row) => (
                <Link className="text-sky-300 hover:underline" to={`/proxies/${row.proxy_id}/edit`}>
                  {row.proxy_id}
                </Link>
              ),
            },
            { key: "domains", label: "Domains", render: (row) => row.domains.join(", ") },
            { key: "requests", label: "Requests", render: (row) => row.requests.toLocaleString() },
            { key: "bandwidth", label: "Bandwidth", render: (row) => formatBytes(row.bandwidth) },
            { key: "error_count", label: "Errors", render: (row) => row.error_count.toLocaleString() },
            {
              key: "error_rate",
              label: "Error rate",
              render: (row) => `${(row.error_rate * 100).toFixed(1)}%`,
            },
            {
              key: "avg_response_time_ms",
              label: "Avg RT",
              render: (row) => `${row.avg_response_time_ms.toFixed(1)} ms`,
            },
            {
              key: "backend_pool_status",
              label: "Pool",
              render: (row) => <StatusBadge status={row.backend_pool_status} />,
            },
            {
              key: "enabled",
              label: "Status",
              render: (row) => <StatusBadge status={row.enabled ? "enabled" : "disabled"} />,
            },
          ]}
        />
      </Card>
    </div>
  );
}
