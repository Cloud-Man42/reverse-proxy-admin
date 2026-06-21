import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

interface DonutSlice {
  name: string;
  value: number;
  color: string;
}

interface DonutChartProps {
  data: DonutSlice[];
  height?: number;
}

export function MetricsDonutChart({ data, height = 256 }: DonutChartProps) {
  const filtered = data.filter((item) => item.value > 0);

  if (!filtered.length) {
    return <p className="text-sm text-white/50">No data for this range.</p>;
  }

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={filtered} dataKey="value" nameKey="name" innerRadius={60} outerRadius={90}>
            {filtered.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
