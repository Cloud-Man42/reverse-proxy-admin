import { Area, AreaChart as RechartsAreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { MetricsSeriesPoint } from "../../types";

interface AreaChartProps {
  data: MetricsSeriesPoint[];
  valueFormatter?: (value: number) => string;
  color?: string;
  height?: number;
}

export function MetricsAreaChart({
  data,
  valueFormatter,
  color = "#22c55e",
  height = 256,
}: AreaChartProps) {
  const chartData = data.map((point) => ({
    time: new Date(point.timestamp).toLocaleString(),
    value: point.value,
  }));

  const formatter = valueFormatter ?? ((value: number) => String(value));

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsAreaChart data={chartData}>
          <XAxis dataKey="time" hide />
          <YAxis />
          <Tooltip formatter={(value) => formatter(Number(value))} />
          <Area type="monotone" dataKey="value" stroke={color} fill={color} fillOpacity={0.2} />
        </RechartsAreaChart>
      </ResponsiveContainer>
    </div>
  );
}
