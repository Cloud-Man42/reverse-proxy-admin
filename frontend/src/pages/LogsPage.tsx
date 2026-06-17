import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { TrafficDebugPanel } from "../components/TrafficDebugPanel";
import { useAutoRefresh } from "../hooks/useAutoRefresh";

export function LogsPage() {
  const [tab, setTab] = useState<"error" | "access" | "debug">("error");
  const [domain, setDomain] = useState("");
  const [debugProxyId, setDebugProxyId] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(false);

  const { data: proxies = [] } = useQuery({ queryKey: ["proxies"], queryFn: api.listProxies });

  const queryKey = ["logs", tab, domain];
  const fetchLogs = useCallback(
    () => (tab === "error" ? api.errorLogs() : api.accessLogs(200, domain || undefined)),
    [tab, domain],
  );

  const { data, refetch, isLoading } = useQuery({
    queryKey,
    queryFn: fetchLogs,
    enabled: tab !== "debug",
  });
  useAutoRefresh(autoRefresh && tab !== "debug", 5000, refetch);

  const selectedProxy = proxies.find((proxy) => proxy.id === debugProxyId) || proxies[0];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-semibold">Logs</h2>
        {tab !== "debug" ? (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
            Auto-refresh
          </label>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        <button className={`rounded-lg px-3 py-2 text-sm ${tab === "error" ? "bg-accent text-white" : "bg-white/10"}`} onClick={() => setTab("error")}>
          Error log
        </button>
        <button className={`rounded-lg px-3 py-2 text-sm ${tab === "access" ? "bg-accent text-white" : "bg-white/10"}`} onClick={() => setTab("access")}>
          Access log
        </button>
        <button className={`rounded-lg px-3 py-2 text-sm ${tab === "debug" ? "bg-accent text-white" : "bg-white/10"}`} onClick={() => setTab("debug")}>
          Traffic debug
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

      {tab === "debug" ? (
        <Card>
          <div className="mb-4">
            <label className="mb-1 block text-sm">Proxy app</label>
            <select
              value={debugProxyId || selectedProxy?.id || ""}
              onChange={(e) => setDebugProxyId(e.target.value)}
              className="min-w-[16rem]"
            >
              {proxies.map((proxy) => (
                <option key={proxy.id} value={proxy.id}>
                  {proxy.name} ({proxy.domains.join(", ")})
                </option>
              ))}
            </select>
          </div>
          {selectedProxy ? (
            <TrafficDebugPanel proxyId={selectedProxy.id} domains={selectedProxy.domains} title="Proxy traffic debug" />
          ) : (
            <p className="text-sm text-white/60">No proxy apps configured yet.</p>
          )}
        </Card>
      ) : (
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
      )}
    </div>
  );
}
