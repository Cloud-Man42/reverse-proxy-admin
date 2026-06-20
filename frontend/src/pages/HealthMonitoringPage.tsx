import { FormEvent, MouseEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { UptimeChartLoader } from "../components/UptimeChart";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { useToast } from "../hooks/useToast";
import { BackendServer } from "../types";

function healthBadge(status: string) {
  if (status === "healthy") return <StatusBadge status="running" label="Healthy" />;
  if (status === "warning") return <StatusBadge status="warning" label="Warning" />;
  if (status === "offline") return <StatusBadge status="stopped" label="Offline" />;
  return <StatusBadge status="unknown" label="Unknown" />;
}

export function HealthMonitoringPage() {
  const [selectedServer, setSelectedServer] = useState<BackendServer | null>(null);
  const [range, setRange] = useState("24h");
  const [runningId, setRunningId] = useState<number | null>(null);
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { data, refetch } = useQuery({ queryKey: ["health-dashboard"], queryFn: api.healthDashboard });
  useAutoRefresh(true, 30000, refetch);

  const runCheck = useMutation({
    mutationFn: (serverId: number) => api.runHealthCheck(serverId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["health-dashboard"] });
      showSuccess(`Check complete: ${result.status}`);
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Health check failed"),
    onSettled: () => setRunningId(null),
  });

  const handleRunCheck = (event: MouseEvent, serverId: number) => {
    event.stopPropagation();
    setRunningId(serverId);
    runCheck.mutate(serverId);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Backend Health Monitoring</h2>
      <div className="grid gap-4 md:grid-cols-4">
        <Card title="Healthy"><p className="text-3xl font-bold text-green-400">{data?.healthy ?? 0}</p></Card>
        <Card title="Warning"><p className="text-3xl font-bold text-amber-400">{data?.warning ?? 0}</p></Card>
        <Card title="Offline"><p className="text-3xl font-bold text-red-400">{data?.offline ?? 0}</p></Card>
        <Card title="Unknown"><p className="text-3xl font-bold">{data?.unknown ?? 0}</p></Card>
      </div>
      <Card title="Backend Status">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-white/60">
              <th className="py-2">Server</th>
              <th>Host</th>
              <th>Status</th>
              <th>Response</th>
              <th>Uptime 24h</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(data?.servers || []).map((server) => (
              <tr
                key={server.id}
                className="cursor-pointer border-t border-white/10 hover:bg-white/5"
                onClick={() => setSelectedServer(server)}
              >
                <td className="py-2">{server.name}</td>
                <td>{server.host}:{server.port}</td>
                <td>{healthBadge(server.health_status)}</td>
                <td>{server.response_ms != null ? `${server.response_ms} ms` : "—"}</td>
                <td>{server.uptime_percent_24h != null ? `${server.uptime_percent_24h}%` : "—"}</td>
                <td className="text-right">
                  <button
                    type="button"
                    className="rounded bg-white/10 px-2 py-1 text-xs"
                    disabled={runningId === server.id}
                    onClick={(e) => handleRunCheck(e, server.id)}
                  >
                    {runningId === server.id ? "Running…" : "Run check now"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {selectedServer && (
        <Card title={`Uptime: ${selectedServer.name}`}>
          <div className="mb-4 flex gap-2">
            {["24h", "7d", "30d"].map((item) => (
              <button
                key={item}
                type="button"
                className={`rounded-lg px-3 py-1 text-sm ${range === item ? "bg-accent text-white" : "bg-white/10"}`}
                onClick={() => setRange(item)}
              >
                {item}
              </button>
            ))}
          </div>
          <UptimeChartLoader serverId={selectedServer.id} range={range} />
        </Card>
      )}
    </div>
  );
}
