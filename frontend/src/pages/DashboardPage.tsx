import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "../api/client";
import { Card } from "../components/Card";
import { CertificateExpiryTimeline } from "../components/CertificateExpiryTimeline";
import { NetworkMap } from "../components/NetworkMap";
import { StatusBadge } from "../components/StatusBadge";
import { TrafficChart } from "../components/TrafficChart";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { formatBytes } from "../lib/formatBytes";
import { DashboardAlert } from "../types";

function ResourceMeter({ label, value }: { label: string; value?: number | null }) {
  const percent = value ?? 0;
  const tone =
    percent >= 90 ? "text-red-400" : percent >= 75 ? "text-amber-400" : "text-emerald-400";
  const barTone =
    percent >= 90 ? "bg-red-500" : percent >= 75 ? "bg-amber-400" : "bg-emerald-400";

  return (
    <Card title={label}>
      {value == null ? (
        <p className="text-sm text-white/60">Unavailable</p>
      ) : (
        <div className="space-y-2">
          <p className={`text-3xl font-bold ${tone}`}>{percent.toFixed(1)}%</p>
          <div className="h-2 overflow-hidden rounded-full bg-black/30">
            <div className={`h-full rounded-full ${barTone}`} style={{ width: `${Math.min(percent, 100)}%` }} />
          </div>
        </div>
      )}
    </Card>
  );
}

function alertTone(alert: DashboardAlert): string {
  if (alert.source === "system" && alert.status === "breached") return "border-red-500/30 bg-red-500/10";
  if (alert.status === "failed") return "border-red-500/30 bg-red-500/10";
  if (alert.status === "recovered") return "border-emerald-500/30 bg-emerald-500/10";
  return "border-white/10 bg-black/20";
}

export function DashboardPage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard,
    retry: 1,
  });
  useAutoRefresh(true, 30000, refetch);

  if (isLoading) {
    return <p>Loading dashboard...</p>;
  }

  if (isError || !data) {
    const message = error instanceof ApiError ? error.message : "Could not load dashboard data.";
    return (
      <div className="space-y-3">
        <p className="text-amber-200">{message}</p>
        <button type="button" className="rounded-lg bg-white/10 px-4 py-2 text-sm" onClick={() => refetch()}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Global Dashboard</h2>
        <p className="text-sm text-white/60">Platform overview — proxies, resources, traffic, and alerts.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Active Proxies">
          <p className="text-3xl font-bold text-emerald-400">{data.active_proxies}</p>
          <p className="mt-1 text-xs text-white/50">Enabled proxy hosts</p>
        </Card>
        <Card title="Inactive Proxies">
          <p className="text-3xl font-bold text-slate-300">{data.inactive_proxies}</p>
          <p className="mt-1 text-xs text-white/50">{data.disabled_proxies} disabled</p>
        </Card>
        <Card title="Backend Servers"><p className="text-3xl font-bold">{data.total_backend_servers}</p></Card>
        <Card title="Certificates"><p className="text-3xl font-bold">{data.total_certificates}</p></Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Healthy Backends"><p className="text-3xl font-bold text-green-400">{data.healthy_backends}</p></Card>
        <Card title="Warning Backends"><p className="text-3xl font-bold text-amber-400">{data.warning_backends}</p></Card>
        <Card title="Offline Backends"><p className="text-3xl font-bold text-red-400">{data.offline_backends}</p></Card>
        <Card title="Expiring Certificates"><p className="text-3xl font-bold text-amber-400">{data.expiring_certificates}</p></Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <ResourceMeter label="CPU" value={data.cpu_percent} />
        <ResourceMeter label="RAM" value={data.ram_percent} />
        <ResourceMeter label="Disk" value={data.disk_percent} />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Traffic In (24h)">
          <p className="text-2xl font-bold font-mono">{formatBytes(data.traffic_bytes_in_24h)}</p>
        </Card>
        <Card title="Traffic Out (24h)">
          <p className="text-2xl font-bold font-mono">{formatBytes(data.traffic_bytes_out_24h)}</p>
        </Card>
        <Card title="NGINX Status"><StatusBadge status={data.nginx_active ? "running" : "stopped"} /></Card>
        <Card title="SMTP Status"><StatusBadge status={data.smtp_status === "connected" ? "running" : "unknown"} label={data.smtp_status} /></Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Aggregate traffic (24h)">
          {data.traffic_history.length ? (
            <TrafficChart data={data.traffic_history} metric="bytes_out" />
          ) : (
            <p className="text-sm text-white/60">No traffic data recorded in the last 24 hours.</p>
          )}
        </Card>

        <Card title="Recent alerts">
          <div className="max-h-72 space-y-2 overflow-auto">
            {data.recent_alerts.length ? (
              data.recent_alerts.map((alert) => (
                <div
                  key={`${alert.source}-${alert.id}`}
                  className={`rounded-lg border px-3 py-2 ${alertTone(alert)}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{alert.title}</p>
                      {alert.message ? <p className="mt-1 text-xs text-white/60">{alert.message}</p> : null}
                    </div>
                    <span className="shrink-0 text-xs text-white/40">
                      {new Date(alert.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="mt-2 flex gap-2 text-xs text-white/50">
                    <span className="rounded bg-white/10 px-1.5 py-0.5">{alert.source}</span>
                    <span className="rounded bg-white/10 px-1.5 py-0.5">{alert.alert_type}</span>
                    <span className="rounded bg-white/10 px-1.5 py-0.5">{alert.status}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-white/60">No recent alerts.</p>
            )}
          </div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Certificate expiry timeline">
          <CertificateExpiryTimeline />
        </Card>

        <Card title="Network map">
          <p className="mb-3 text-sm text-white/60">
            Traffic flow: Internet → Firewall → Nginx → web apps/upstreams. Click an app node to edit it.
          </p>
          <NetworkMap />
        </Card>
      </div>

      <Card title="Recent Nginx errors">
        <div className="max-h-72 overflow-auto rounded-lg bg-black/20 p-3 font-mono text-xs">
          {data.recent_errors.length ? (
            data.recent_errors.map((line, index) => <div key={index}>{line}</div>)
          ) : (
            <p className="text-white/60">No recent errors.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
