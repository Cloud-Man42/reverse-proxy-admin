import { MetricsRange } from "../../types";

const OPTIONS: { value: MetricsRange; label: string }[] = [
  { value: "15m", label: "Last 15 minutes" },
  { value: "1h", label: "Last hour" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

interface TimeRangeSelectorProps {
  value: MetricsRange;
  onChange: (value: MetricsRange) => void;
  className?: string;
}

export function TimeRangeSelector({ value, onChange, className = "" }: TimeRangeSelectorProps) {
  return (
    <select
      className={`text-sm ${className}`}
      value={value}
      onChange={(e) => onChange(e.target.value as MetricsRange)}
    >
      {OPTIONS.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
