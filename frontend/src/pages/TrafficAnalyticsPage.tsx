import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import {
  MetricCard,
  MetricGrid,
  MetricsAreaChart,
  MetricsLineChart,
  MetricsPageHeader,
  formatBandwidth,
} from "../components/metrics";
import { formatBytes } from "../lib/formatBytes";
import { MetricsRange } from "../types";

export function TrafficAnalyticsPage() {
  const [range, setRange] = useState<MetricsRange>("24h");
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["metrics-traffic", range],
    queryFn: () => api.metricsTraffic(range),
  });

  return (
    <div className="space-y-6">
      <MetricsPageHeader
        title="Traffic Analytics"
        description="Requests, bandwidth, latency, and error rate over time."
        range={range}
        onRangeChange={setRange}
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
        onRefresh={() => refetch()}
      />

      {isLoading || !data ? (
        <p>Loading traffic metrics...</p>
      ) : (
        <>
          <MetricGrid>
            <MetricCard label="Requests" value={data.totals.requests.toLocaleString()} />
            <MetricCard label="RPS" value={data.totals.rps.toFixed(3)} />
            <MetricCard label="Peak RPS" value={data.peak_rps.toFixed(3)} />
            <MetricCard label="Avg latency" value={`${data.totals.avg_response_time_ms.toFixed(1)} ms`} />
            <MetricCard
              label="Error rate"
              value={`${(data.totals.error_rate * 100).toFixed(2)}%`}
              tone={data.totals.error_rate > 0.05 ? "danger" : "success"}
            />
            <MetricCard label="Bandwidth in" value={formatBytes(data.totals.bytes_in)} />
            <MetricCard label="Bandwidth out" value={formatBytes(data.totals.bytes_out)} />
          </MetricGrid>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Requests">
              <MetricsLineChart data={data.series.requests} />
            </Card>
            <Card title="Bandwidth in">
              <MetricsAreaChart data={data.series.bandwidth_in} valueFormatter={formatBandwidth} />
            </Card>
            <Card title="Bandwidth out">
              <MetricsAreaChart data={data.series.bandwidth_out} valueFormatter={formatBandwidth} color="#38bdf8" />
            </Card>
            <Card title="Error rate">
              <MetricsLineChart
                data={data.series.error_rate}
                valueFormatter={(value) => `${(value * 100).toFixed(2)}%`}
                color="#ef4444"
              />
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
