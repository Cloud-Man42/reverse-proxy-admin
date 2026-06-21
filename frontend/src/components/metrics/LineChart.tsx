import { Line, LineChart as RechartsLineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { MetricsSeriesPoint } from "../../types";
import { formatBytes } from "../../lib/formatBytes";

interface LineChartProps {
  data: MetricsSeriesPoint[];
  valueFormatter?: (value: number) => string;
  color?: string;
  height?: number;
}

export function MetricsLineChart({
  data,
  valueFormatter,
  color = "#38bdf8",
  height = 256,
}: LineChartProps) {
  const chartData = data.map((point) => ({
    time: new Date(point.timestamp).toLocaleString(),
    value: point.value,
  }));

  const formatter = valueFormatter ?? ((value: number) => String(value));

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart data={chartData}>
          <XAxis dataKey="time" hide />
          <YAxis />
          <Tooltip formatter={(value) => formatter(Number(value))} />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function formatBandwidth(value: number) {
  return formatBytes(value);
}
