import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { MetricCard, MetricGrid, MetricsAreaChart, MetricsPageHeader } from "../components/metrics";
import { MetricsRange } from "../types";

export function ConnectionStatsPage() {
  const [range, setRange] = useState<MetricsRange>("24h");
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["metrics-connections", range],
    queryFn: () => api.metricsConnections(range),
  });

  const latest = data?.latest ?? {};

  return (
    <div className="space-y-6">
      <MetricsPageHeader
        title="Connection Stats"
        description="NGINX stub_status connection metrics and trends."
        range={range}
        onRangeChange={setRange}
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
        onRefresh={() => refetch()}
      />

      {isLoading || !data ? (
        <p>Loading connection metrics...</p>
      ) : (
        <>
          <MetricGrid columns={4}>
            <MetricCard label="Active" value={String(latest.active ?? 0)} />
            <MetricCard label="Reading" value={String(latest.reading ?? 0)} />
            <MetricCard label="Writing" value={String(latest.writing ?? 0)} />
            <MetricCard label="Waiting" value={String(latest.waiting ?? 0)} />
            <MetricCard label="Accepts" value={String(latest.accepts ?? 0)} />
            <MetricCard label="Handled" value={String(latest.handled ?? 0)} />
            <MetricCard label="Requests" value={String(latest.requests ?? 0)} />
          </MetricGrid>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Active connections">
              <MetricsAreaChart
                data={data.series.map((point) => ({ timestamp: point.timestamp, value: point.active }))}
              />
            </Card>
            <Card title="Waiting connections">
              <MetricsAreaChart
                data={data.series.map((point) => ({ timestamp: point.timestamp, value: point.waiting }))}
                color="#f59e0b"
              />
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
