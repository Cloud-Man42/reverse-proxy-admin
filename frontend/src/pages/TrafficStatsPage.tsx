import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { TrafficChart } from "../components/TrafficChart";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { formatBytes } from "../lib/formatBytes";
import { AnalyticsSummaryItem } from "../types";

type Range = "24h" | "7d" | "30d";

export function TrafficStatsPage() {
  const [range, setRange] = useState<Range>("24h");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["analytics-summary", range],
    queryFn: () => api.analyticsSummary(range),
  });

  const { data: detail } = useQuery({
    queryKey: ["analytics-proxy", selectedId, range],
    queryFn: () => api.analyticsProxy(selectedId!, range),
    enabled: !!selectedId,
  });

  useAutoRefresh(true, 30000, refetch);

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Analytics</h2>
          <p className="text-sm text-white/60">
            Request rates, latency, status codes, and top clients per proxy app.
          </p>
        </div>
        <select
          className="rounded-lg bg-black/20 px-3 py-2 text-sm"
          value={range}
          onChange={(e) => setRange(e.target.value as Range)}
        >
          <option value="24h">Last 24 hours</option>
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
        </select>
      </div>

      <Card title="All Proxies">
        {isLoading ? (
          <p>Loading...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-white/60">
                  <th className="px-3 py-2">Proxy</th>
                  <th className="px-3 py-2">Domains</th>
                  <th className="px-3 py-2">RPS</th>
                  <th className="px-3 py-2">Latency</th>
                  <th className="px-3 py-2">Error rate</th>
                  <th className="px-3 py-2">Requests</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Details</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item: AnalyticsSummaryItem) => (
                  <tr key={item.proxy_id} className="border-b border-white/5">
                    <td className="px-3 py-3 font-medium">{item.proxy_name}</td>
                    <td className="px-3 py-3">{item.domains.join(", ")}</td>
                    <td className="px-3 py-3 font-mono text-xs">{item.rps.toFixed(3)}</td>
                    <td className="px-3 py-3 font-mono text-xs">{item.latency_avg_ms.toFixed(1)} ms</td>
                    <td className="px-3 py-3">{(item.error_rate * 100).toFixed(1)}%</td>
                    <td className="px-3 py-3">{item.requests.toLocaleString()}</td>
                    <td className="px-3 py-3">
                      <StatusBadge status={item.enabled ? "enabled" : "disabled"} />
                    </td>
                    <td className="px-3 py-3">
                      <button
                        type="button"
                        className="rounded bg-white/10 px-2 py-1"
                        onClick={() => setSelectedId(item.proxy_id === selectedId ? null : item.proxy_id)}
                      >
                        {selectedId === item.proxy_id ? "Hide" : "View"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {detail ? (
        <>
          <Card title={`${detail.proxy_name} — overview`}>
            <div className="grid gap-4 md:grid-cols-4">
              <Stat label="RPS" value={detail.rps.toFixed(3)} />
              <Stat label="Avg latency" value={`${detail.latency_avg_ms.toFixed(1)} ms`} />
              <Stat label="Upstream latency" value={`${detail.upstream_latency_avg_ms.toFixed(1)} ms`} />
              <Stat label="Error rate" value={`${(detail.error_rate * 100).toFixed(1)}%`} />
              <Stat label="Requests" value={detail.requests.toLocaleString()} />
              <Stat label="Traffic in" value={formatBytes(detail.bytes_in)} />
              <Stat label="Traffic out" value={formatBytes(detail.bytes_out)} />
            </div>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Status breakdown">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <StatusRow label="2xx" value={detail.status_2xx} tone="text-emerald-300" />
                <StatusRow label="3xx" value={detail.status_3xx} tone="text-sky-300" />
                <StatusRow label="4xx" value={detail.status_4xx} tone="text-amber-300" />
                <StatusRow label="5xx" value={detail.status_5xx} tone="text-red-300" />
              </div>
            </Card>

            <Card title="Top client IPs">
              {Object.keys(detail.top_clients).length === 0 ? (
                <p className="text-sm text-white/50">No client data yet.</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {Object.entries(detail.top_clients).map(([ip, count]) => (
                    <li key={ip} className="flex justify-between rounded bg-black/20 px-3 py-2 font-mono text-xs">
                      <span>{ip}</span>
                      <span>{count.toLocaleString()}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <Card title={`${detail.proxy_name} — traffic history`}>
            <div className="grid gap-6 lg:grid-cols-2">
              <div>
                <p className="mb-2 text-sm text-white/60">Outbound traffic over time</p>
                <TrafficChart data={detail.history} metric="bytes_out" />
              </div>
              <div>
                <p className="mb-2 text-sm text-white/60">Connections over time</p>
                <TrafficChart data={detail.history} metric="connections" />
              </div>
            </div>
          </Card>
        </>
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-black/20 p-4">
      <p className="text-xs uppercase tracking-wide text-white/50">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
    </div>
  );
}

function StatusRow({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-lg bg-black/20 p-3">
      <p className="text-xs uppercase tracking-wide text-white/50">{label}</p>
      <p className={`mt-1 text-lg font-semibold ${tone}`}>{value.toLocaleString()}</p>
    </div>
  );
}
