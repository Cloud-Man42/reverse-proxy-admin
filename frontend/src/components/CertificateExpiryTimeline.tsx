import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { StatusBadge } from "./StatusBadge";
import { Certificate } from "../types";

function daysRemaining(expiry: string): number {
  return Math.ceil((new Date(expiry).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
}

function barColor(days: number): string {
  if (days < 0) return "bg-red-500";
  if (days <= 14) return "bg-red-400";
  if (days <= 30) return "bg-amber-400";
  return "bg-emerald-400";
}

function barWidth(days: number): string {
  const clamped = Math.max(0, Math.min(days, 90));
  return `${Math.max(4, (clamped / 90) * 100)}%`;
}

export function CertificateExpiryTimeline() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["certificates"],
    queryFn: api.listCertificates,
  });

  if (isLoading) {
    return <p className="text-sm text-white/60">Loading certificates...</p>;
  }

  if (!data.length) {
    return <p className="text-sm text-white/60">No certificates installed.</p>;
  }

  const sorted = [...data].sort(
    (a: Certificate, b: Certificate) => new Date(a.expiry).getTime() - new Date(b.expiry).getTime(),
  );

  return (
    <div className="space-y-3">
      {sorted.map((cert) => {
        const days = daysRemaining(cert.expiry);
        const label = cert.domains[0] || cert.name;
        return (
          <div key={cert.name} className="space-y-1">
            <div className="flex items-center justify-between gap-3 text-sm">
              <div className="min-w-0">
                <p className="truncate font-medium">{label}</p>
                <p className="text-xs text-white/50">{new Date(cert.expiry).toLocaleDateString()}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <span className={`text-xs ${days <= 30 ? "text-amber-300" : "text-white/60"}`}>
                  {days < 0 ? `${Math.abs(days)}d ago` : `${days}d left`}
                </span>
                <StatusBadge status={cert.status} />
              </div>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-black/30">
              <div className={`h-full rounded-full ${barColor(days)}`} style={{ width: barWidth(days) }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
