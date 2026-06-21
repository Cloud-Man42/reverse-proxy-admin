import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { MetricCard, MetricGrid, MetricsLineChart, MetricsPageHeader } from "../components/metrics";
import { StatusBadge } from "../components/StatusBadge";
import { MetricsBackendItem, MetricsRange } from "../types";

export function BackendAnalyticsPage() {
  const [range, setRange] = useState<MetricsRange>("24h");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["metrics-backends", range],
    queryFn: () => api.metricsBackends(range),
  });

  const selected = data?.items.find((item) => item.backend_server_id === selectedId) ?? null;

  return (
    <div className="space-y-6">
      <MetricsPageHeader
        title="Backend Analytics"
        description="Per-server health, latency, and historical metrics."
        range={range}
        onRangeChange={setRange}
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
        onRefresh={() => refetch()}
      />

      {isLoading || !data ? (
        <p>Loading backend metrics...</p>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            {data.items.map((item) => (
              <button
                key={item.backend_server_id}
                type="button"
                className={`rounded-lg border p-4 text-left ${
                  selectedId === item.backend_server_id ? "border-accent bg-accent/10" : "border-white/10 bg-black/20"
                }`}
                onClick={() =>
                  setSelectedId(selectedId === item.backend_server_id ? null : item.backend_server_id)
                }
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{item.name}</p>
                    <p className="text-xs text-white/50">
                      {item.protocol}://{item.host}:{item.port}
                    </p>
                  </div>
                  <StatusBadge status={item.status} />
                </div>
                <MetricGrid columns={3}>
                  <MetricCard label="Response" value={`${item.response_time_ms.toFixed(1)} ms`} />
                  <MetricCard label="Uptime 24h" value={`${item.uptime_percent_24h.toFixed(1)}%`} />
                </MetricGrid>
              </button>
            ))}
          </div>

          {selected ? (
            <Card title={`${selected.name} history`}>
              <MetricsLineChart
                data={selected.history.map((point) => ({
                  timestamp: point.timestamp,
                  value: point.response_time_ms ?? 0,
                }))}
                valueFormatter={(value) => `${value.toFixed(1)} ms`}
              />
            </Card>
          ) : null}
        </>
      )}
    </div>
  );
}
