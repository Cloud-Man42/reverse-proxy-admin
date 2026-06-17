import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { NetworkMap } from "../components/NetworkMap";
import { StatusBadge } from "../components/StatusBadge";

export function DashboardPage() {
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });

  if (isLoading || !data) {
    return <p>Loading dashboard...</p>;
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Active proxies">
          <p className="text-3xl font-bold">{data.active_proxies}</p>
        </Card>
        <Card title="Inactive proxies">
          <p className="text-3xl font-bold">{data.inactive_proxies}</p>
        </Card>
        <Card title="Nginx status">
          <StatusBadge status={data.nginx_active ? "running" : "stopped"} />
        </Card>
        <Card title="Expiring certificates">
          <p className="text-3xl font-bold">{data.expiring_certificates}</p>
        </Card>
      </div>

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
