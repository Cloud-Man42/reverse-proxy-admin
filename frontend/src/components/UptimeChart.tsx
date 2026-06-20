import { useQuery } from "@tanstack/react-query";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { HealthHistoryPoint } from "../types";

interface Props {
  data: HealthHistoryPoint[];
}

export function UptimeChart({ data }: Props) {
  const chartData = data.map((point) => ({
    time: new Date(point.timestamp).toLocaleString(),
    uptime: point.uptime_percent,
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <XAxis dataKey="time" hide />
          <YAxis domain={[0, 100]} />
          <Tooltip />
          <Line type="monotone" dataKey="uptime" stroke="#22c55e" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function UptimeChartLoader({ serverId, range }: { serverId: number; range: string }) {
  const { data = [] } = useQuery({
    queryKey: ["health-history", serverId, range],
    queryFn: () => api.healthHistory(serverId, range),
  });
  return data.length ? <UptimeChart data={data} /> : <p className="text-sm text-white/60">No history yet.</p>;
}
