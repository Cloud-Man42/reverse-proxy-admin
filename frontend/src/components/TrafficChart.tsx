import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatBytes } from "../lib/formatBytes";
import { ProxyTrafficHistoryPoint } from "../types";

interface Props {
  data: ProxyTrafficHistoryPoint[];
  metric: "bytes_out" | "connections";
}

export function TrafficChart({ data, metric }: Props) {
  const chartData = data.map((point) => ({
    time: new Date(point.timestamp).toLocaleString(),
    value: metric === "connections" ? point.connections : point.bytes_out,
    label: metric === "connections" ? `${point.connections} conn` : formatBytes(point.bytes_out),
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <XAxis dataKey="time" hide />
          <YAxis />
          <Tooltip formatter={(value) => (metric === "connections" ? value : formatBytes(Number(value)))} />
          <Line type="monotone" dataKey="value" stroke="#38bdf8" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
