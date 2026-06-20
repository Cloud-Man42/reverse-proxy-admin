interface StatusBadgeProps {
  status: string;
  label?: string;
}

const styles: Record<string, string> = {
  valid: "bg-emerald-500/20 text-emerald-300",
  expiring: "bg-amber-500/20 text-amber-300",
  expired: "bg-red-500/20 text-red-300",
  enabled: "bg-emerald-500/20 text-emerald-300",
  disabled: "bg-slate-500/20 text-slate-300",
  running: "bg-emerald-500/20 text-emerald-300",
  stopped: "bg-red-500/20 text-red-300",
  warning: "bg-amber-500/20 text-amber-300",
  unknown: "bg-slate-500/20 text-slate-300",
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const key = status.toLowerCase();
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${styles[key] || "bg-slate-500/20 text-slate-300"}`}>
      {label || status}
    </span>
  );
}