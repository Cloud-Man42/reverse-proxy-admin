import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "../api/client";
import { Card } from "../components/Card";
import { NetworkMap } from "../components/NetworkMap";
import { StatusBadge } from "../components/StatusBadge";

export function DashboardPage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard,
    retry: 1,
  });

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
