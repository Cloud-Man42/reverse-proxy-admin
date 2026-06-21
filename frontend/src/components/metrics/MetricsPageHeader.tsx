import { ReactNode } from "react";
import { AutoRefreshControl } from "./AutoRefreshControl";
import { TimeRangeSelector } from "./TimeRangeSelector";
import { MetricsRange } from "../../types";

interface MetricsPageHeaderProps {
  title: string;
  description: string;
  range: MetricsRange;
  onRangeChange: (range: MetricsRange) => void;
  autoRefresh: boolean;
  onAutoRefreshChange: (enabled: boolean) => void;
  onRefresh: () => void;
  actions?: ReactNode;
}

export function MetricsPageHeader({
  title,
  description,
  range,
  onRangeChange,
  autoRefresh,
  onAutoRefreshChange,
  onRefresh,
  actions,
}: MetricsPageHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-2xl font-semibold">{title}</h2>
        <p className="text-sm text-white/60">{description}</p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {actions}
        <TimeRangeSelector value={range} onChange={onRangeChange} />
        <AutoRefreshControl
          enabled={autoRefresh}
          onEnabledChange={onAutoRefreshChange}
          onRefresh={onRefresh}
        />
      </div>
    </div>
  );
}
