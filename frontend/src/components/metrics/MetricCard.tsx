type MetricTone = "default" | "success" | "warning" | "danger" | "muted";

const toneClasses: Record<MetricTone, string> = {
  default: "text-white",
  success: "text-emerald-400",
  warning: "text-amber-400",
  danger: "text-red-400",
  muted: "text-white/60",
};

interface MetricCardProps {
  label: string;
  value: string;
  hint?: string;
  tone?: MetricTone;
}

export function MetricCard({ label, value, hint, tone = "default" }: MetricCardProps) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/20 p-4">
      <p className="text-xs uppercase tracking-wide text-white/50">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${toneClasses[tone]}`}>{value}</p>
      {hint ? <p className="mt-1 text-xs text-white/50">{hint}</p> : null}
    </div>
  );
}
