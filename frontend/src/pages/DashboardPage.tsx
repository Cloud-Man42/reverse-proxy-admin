import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "../api/client";
import { Card } from "../components/Card";
import { NetworkMap } from "../components/NetworkMap";
import { StatusBadge } from "../components/StatusBadge";
import { useAutoRefresh } from "../hooks/useAutoRefresh";

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
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Proxy Hosts"><p className="text-3xl font-bold">{data.active_proxies + data.inactive_proxies}</p></Card>
        <Card title="Backend Servers"><p className="text-3xl font-bold">{data.total_backend_servers}</p></Card>
        <Card title="Healthy Backends"><p className="text-3xl font-bold text-green-400">{data.healthy_backends}</p></Card>
        <Card title="Offline Backends"><p className="text-3xl font-bold text-red-400">{data.offline_backends}</p></Card>
        <Card title="Certificates"><p className="text-3xl font-bold">{data.total_certificates}</p></Card>
        <Card title="Expiring Certificates"><p className="text-3xl font-bold text-amber-400">{data.expiring_certificates}</p></Card>
        <Card title="NGINX Status"><StatusBadge status={data.nginx_active ? "running" : "stopped"} /></Card>
        <Card title="SMTP Status"><StatusBadge status={data.smtp_status === "connected" ? "running" : "unknown"} label={data.smtp_status} /></Card>
      </div>

      <Card title="Backend Status">
        <div className="grid gap-4 md:grid-cols-3">
          <div><p className="text-sm text-white/60">Healthy</p><p className="text-2xl font-bold text-green-400">{data.healthy_backends}</p></div>
          <div><p className="text-sm text-white/60">Warning</p><p className="text-2xl font-bold text-amber-400">{data.warning_backends}</p></div>
          <div><p className="text-sm text-white/60">Offline</p><p className="text-2xl font-bold text-red-400">{data.offline_backends}</p></div>
        </div>
      </Card>

      <Card title="Network map">
        <p className="mb-3 text-sm text-white/60">
          Traffic flow: Internet → Firewall → Nginx → web apps/upstreams. Click an app node to edit it.
        </p>
        <NetworkMap />
      </Card>

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
