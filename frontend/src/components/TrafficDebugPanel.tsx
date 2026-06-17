import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { TrafficDebugEntry } from "../types";

interface TrafficDebugPanelProps {
  proxyId: string;
  domains: string[];
  title?: string;
}

function statusClass(status: number) {
  if (status >= 500) return "text-red-300";
  if (status >= 400) return "text-amber-300";
  if (status >= 300) return "text-sky-300";
  return "text-emerald-300";
}

export function TrafficDebugPanel({ proxyId, domains, title = "Inbound traffic debug" }: TrafficDebugPanelProps) {
  const [debugEnabled, setDebugEnabled] = useState(false);
  const [lines, setLines] = useState(100);

  const fetchDebug = useCallback(
    () => api.proxyTrafficDebug(proxyId, lines),
    [proxyId, lines],
  );

  const { data, refetch, isLoading, isFetching } = useQuery({
    queryKey: ["traffic-debug", proxyId, lines],
    queryFn: fetchDebug,
    enabled: debugEnabled,
  });

  useAutoRefresh(debugEnabled, 3000, refetch);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold">{title}</h3>
          <p className="text-sm text-white/60">
            Live view of requests hitting this proxy&apos;s inbound interface ({domains.join(", ")}).
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={debugEnabled} onChange={(e) => setDebugEnabled(e.target.checked)} />
          Debug mode
        </label>
      </div>

      {debugEnabled ? (
        <>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <label className="flex items-center gap-2">
              Lines
              <select
                value={lines}
                onChange={(e) => setLines(Number(e.target.value))}
                className="rounded bg-black/20 px-2 py-1"
              >
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
              </select>
            </label>
            <button type="button" className="rounded-lg bg-white/10 px-3 py-1" onClick={() => refetch()}>
              Refresh
            </button>
            {isFetching ? <span className="text-white/50">Updating...</span> : null}
          </div>

          {data && !data.dedicated_log ? (
            <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
              Per-proxy logging is not active yet. Save this proxy once to enable dedicated debug logs with client IP and
              Host header. Showing filtered entries from the global access log until then.
            </p>
          ) : null}

          {data ? (
            <p className="text-xs text-white/50">Source: {data.source}</p>
          ) : null}

          {isLoading ? (
            <p className="text-sm">Loading traffic...</p>
          ) : (
            <TrafficDebugTable entries={data?.entries || []} />
          )}
        </>
      ) : (
        <p className="text-sm text-white/50">Enable debug mode to watch incoming requests in near real time.</p>
      )}
    </div>
  );
}

function TrafficDebugTable({ entries }: { entries: TrafficDebugEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-sm text-white/60">No matching requests yet. Generate traffic to this proxy and refresh.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-white/10">
      <table className="min-w-full text-left text-xs">
        <thead className="bg-black/20 text-white/60">
          <tr>
            <th className="px-3 py-2">Time</th>
            <th className="px-3 py-2">Client IP</th>
            <th className="px-3 py-2">Host</th>
            <th className="px-3 py-2">Request</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Bytes</th>
            <th className="px-3 py-2">Forwarded for</th>
            <th className="px-3 py-2">User agent</th>
          </tr>
        </thead>
        <tbody>
          {[...entries].reverse().map((entry, index) => (
            <tr key={`${entry.timestamp}-${entry.client_ip}-${index}`} className="border-t border-white/5">
              <td className="whitespace-nowrap px-3 py-2 font-mono">{entry.timestamp}</td>
              <td className="whitespace-nowrap px-3 py-2 font-mono">{entry.client_ip}</td>
              <td className="px-3 py-2">{entry.host}</td>
              <td className="px-3 py-2 font-mono">
                {entry.method} {entry.path}
              </td>
              <td className={`px-3 py-2 font-mono ${statusClass(entry.status)}`}>{entry.status}</td>
              <td className="px-3 py-2 font-mono">{entry.bytes_sent}</td>
              <td className="px-3 py-2 font-mono">{entry.forwarded_for || "-"}</td>
              <td className="max-w-xs truncate px-3 py-2" title={entry.user_agent || ""}>
                {entry.user_agent || "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
