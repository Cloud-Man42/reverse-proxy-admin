import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import {
  MetricCard,
  MetricGrid,
  MetricsBarChart,
  MetricsDonutChart,
  MetricsPageHeader,
  TroubleshootingHint,
} from "../components/metrics";
import { MetricsRange } from "../types";

const GROUP_COLORS: Record<string, string> = {
  "2xx": "#22c55e",
  "3xx": "#38bdf8",
  "4xx": "#f59e0b",
  "5xx": "#ef4444",
};

export function StatusCodeAnalyticsPage() {
  const [range, setRange] = useState<MetricsRange>("24h");
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["metrics-status-codes", range],
    queryFn: () => api.metricsStatusCodes(range),
  });

  const donutData =
    data?.groups
      ? Object.entries(data.groups).map(([name, value]) => ({
          name,
          value,
          color: GROUP_COLORS[name] ?? "#94a3b8",
        }))
      : [];

  const topErrors =
    data?.top_errors.map(([code, count]) => ({ label: code, value: count })) ?? [];

  return (
    <div className="space-y-6">
      <MetricsPageHeader
        title="Status Code Analytics"
        description="HTTP status distribution and troubleshooting hints."
        range={range}
        onRangeChange={setRange}
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
        onRefresh={() => refetch()}
      />

      {isLoading || !data ? (
        <p>Loading status code metrics...</p>
      ) : (
        <>
          <MetricGrid columns={4}>
            {Object.entries(data.groups).map(([label, value]) => (
              <MetricCard key={label} label={label} value={value.toLocaleString()} />
            ))}
          </MetricGrid>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Status groups">
              <MetricsDonutChart data={donutData} />
            </Card>
            <Card title="Top error codes">
              {topErrors.length ? <MetricsBarChart data={topErrors} color="#ef4444" /> : <p className="text-sm text-white/50">No errors in this range.</p>}
            </Card>
          </div>

          {data.hints.length ? (
            <div className="space-y-3">
              {data.hints.map((hint) => (
                <TroubleshootingHint key={hint.code} title={`HTTP ${hint.code}`} message={hint.hint} />
              ))}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
