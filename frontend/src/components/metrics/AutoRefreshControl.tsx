import { useAutoRefresh } from "../../hooks/useAutoRefresh";

interface AutoRefreshControlProps {
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  intervalMs?: number;
  onRefresh: () => void;
}

export function AutoRefreshControl({
  enabled,
  onEnabledChange,
  intervalMs = 30000,
  onRefresh,
}: AutoRefreshControlProps) {
  useAutoRefresh(enabled, intervalMs, onRefresh);

  return (
    <div className="flex items-center gap-2">
      <label className="flex items-center gap-2 text-sm text-white/70">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onEnabledChange(e.target.checked)}
          className="rounded border-white/20 bg-black/20"
        />
        Auto-refresh
      </label>
      <button type="button" className="rounded-lg bg-white/10 px-3 py-2 text-sm hover:bg-white/20" onClick={onRefresh}>
        Refresh now
      </button>
    </div>
  );
}
