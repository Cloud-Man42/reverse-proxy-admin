import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { useAutoRefresh } from "../hooks/useAutoRefresh";

export function LogsPage() {
  const [tab, setTab] = useState<"error" | "access">("error");
  const [domain, setDomain] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(false);

  const queryKey = ["logs", tab, domain];
  const fetchLogs = useCallback(
    () => (tab === "error" ? api.errorLogs() : api.accessLogs(200, domain || undefined)),
    [tab, domain],
  );

  const { data, refetch, isLoading } = useQuery({ queryKey, queryFn: fetchLogs });
  useAutoRefresh(autoRefresh, 5000, refetch);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-semibold">Logs</h2>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
          Auto-refresh
        </label>
      </div>

      <div className="flex gap-2">
        <button className={`rounded-lg px-3 py-2 text-sm ${tab === "error" ? "bg-accent text-white" : "bg-white/10"}`} onClick={() => setTab("error")}>
          Error log
        </button>
        <button className={`rounded-lg px-3 py-2 text-sm ${tab === "access" ? "bg-accent text-white" : "bg-white/10"}`} onClick={() => setTab("access")}>
          Access log
        </button>
      </div>

      {tab === "access" ? (
        <div className="flex gap-2">
          <input value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="Filter by domain" />
          <button className="rounded-lg bg-white/10 px-4 py-2 text-sm" onClick={() => refetch()}>
            Apply filter
          </button>
        </div>
      ) : null}

      <Card title={data?.source || "Logs"}>
        {isLoading ? (
          <p>Loading...</p>
        ) : (
          <div className="max-h-[32rem] overflow-auto rounded-lg bg-black/20 p-3 font-mono text-xs">
            {data?.lines.map((line, index) => (
              <div key={index} className="whitespace-pre-wrap break-all">
                {line}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
