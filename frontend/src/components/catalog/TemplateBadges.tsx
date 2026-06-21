import { ApplicationTemplate } from "../../types";

const AVAILABILITY_LABELS: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  enterprise: "Enterprise",
};

const AVAILABILITY_CLASSES: Record<string, string> = {
  free: "bg-emerald-500/20 text-emerald-200",
  pro: "bg-blue-500/20 text-blue-200",
  enterprise: "bg-purple-500/20 text-purple-200",
};

export function TemplateBadges({ template }: { template: Pick<ApplicationTemplate, "availability_level" | "optimized" | "websocket_support" | "large_upload_support"> }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      <span className={`rounded px-2 py-0.5 text-xs font-medium ${AVAILABILITY_CLASSES[template.availability_level] || "bg-white/10 text-white/70"}`}>
        {AVAILABILITY_LABELS[template.availability_level] || template.availability_level}
      </span>
      {template.optimized ? (
        <span className="rounded bg-amber-500/20 px-2 py-0.5 text-xs font-medium text-amber-200">Optimized</span>
      ) : null}
      {template.websocket_support ? (
        <span className="rounded bg-white/10 px-2 py-0.5 text-xs text-white/70">WebSocket</span>
      ) : null}
      {template.large_upload_support ? (
        <span className="rounded bg-white/10 px-2 py-0.5 text-xs text-white/70">Large upload</span>
      ) : null}
    </div>
  );
}
