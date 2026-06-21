import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { MetricCard, MetricGrid, MetricsPageHeader } from "../components/metrics";
import { MetricsRange } from "../types";

export function SecurityOverviewPage() {
  const [range, setRange] = useState<MetricsRange>("24h");
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["metrics-security", range],
    queryFn: () => api.metricsSecurity(range),
  });

  return (
    <div className="space-y-6">
      <MetricsPageHeader
        title="Security Overview"
        description="Security events, rate limits, and blocked clients."
        range={range}
        onRangeChange={setRange}
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
        onRefresh={() => refetch()}
      />

      {isLoading || !data ? (
        <p>Loading security metrics...</p>
      ) : (
        <>
          <MetricGrid columns={4}>
            <MetricCard label="Total events" value={String(data.total_events)} />
            <MetricCard label="Failed logins" value={String(data.failed_logins)} tone="warning" />
            <MetricCard label="Rate limited" value={String(data.rate_limited)} />
            <MetricCard label="Blocked IPs" value={String(data.blocked_ips)} tone="danger" />
          </MetricGrid>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Top blocked IPs">
              {data.top_blocked_ips.length ? (
                <ul className="space-y-2 text-sm">
                  {data.top_blocked_ips.map(([ip, count]) => (
                    <li key={ip} className="flex justify-between rounded bg-black/20 px-3 py-2 font-mono text-xs">
                      <span>{ip}</span>
                      <span>{count}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-white/50">No blocked IP activity in this range.</p>
              )}
            </Card>

            <Card title="Recent events">
              {data.recent_events.length ? (
                <ul className="space-y-2 text-sm">
                  {data.recent_events.map((event) => (
                    <li key={event.id} className="rounded bg-black/20 px-3 py-2">
                      <div className="flex justify-between gap-3">
                        <span className="font-medium">{event.event_type}</span>
                        <span className="text-xs text-white/40">{new Date(event.created_at).toLocaleString()}</span>
                      </div>
                      <p className="mt-1 text-xs text-white/60">{event.message}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-white/50">No recent security events.</p>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
