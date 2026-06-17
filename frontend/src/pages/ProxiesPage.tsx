import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { ProxyApp } from "../types";

const CONFIRM_ACTION_LABELS: Record<string, string> = {
  delete: "Delete",
  enable: "Enable",
  disable: "Disable",
  test: "Run config test for",
};

export function ProxiesPage() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { canCreate, canEdit, canRead } = useAuth();
  const [confirm, setConfirm] = useState<{ action: string; proxy: ProxyApp } | null>(null);

  const { data = [], isLoading } = useQuery({ queryKey: ["proxies"], queryFn: api.listProxies });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["proxies"] });

  const runAction = async () => {
    if (!confirm) return;
    try {
      if (confirm.action === "delete") {
        await api.deleteProxy(confirm.proxy.id);
        showSuccess("Proxy deleted");
      } else if (confirm.action === "enable") {
        await api.enableProxy(confirm.proxy.id);
        showSuccess("Proxy enabled");
      } else if (confirm.action === "disable") {
        await api.disableProxy(confirm.proxy.id);
        showSuccess("Proxy disabled");
      } else if (confirm.action === "test") {
        const result = await api.testConfig();
        showSuccess(result.success ? "Config test passed" : "Config test failed");
      }
      invalidate();
    } catch (error) {
      showError(error instanceof ApiError ? error.message : "Action failed");
    } finally {
      setConfirm(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Proxy Apps</h2>
        {canCreate ? (
          <Link to="/proxies/new" className="rounded-lg bg-accent px-4 py-2 text-sm text-white">
            Create app
          </Link>
        ) : null}
      </div>

      <Card>
        {isLoading ? (
          <p>Loading...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-white/60">
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Domain</th>
                  <th className="px-3 py-2">Upstream</th>
                  <th className="px-3 py-2">Enabled</th>
                  <th className="px-3 py-2">HTTPS</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.map((proxy) => (
                  <tr key={proxy.id} className="border-b border-white/5">
                    <td className="px-3 py-3 font-medium">{proxy.name}</td>
                    <td className="px-3 py-3">{proxy.domains.join(", ")}</td>
                    <td className="px-3 py-3 font-mono text-xs">
                      {proxy.routes.length > 1
                        ? `${proxy.routes.length} routes`
                        : `${proxy.routes[0]?.target_protocol || proxy.target_protocol}://${proxy.routes[0]?.target_host || proxy.target_host}:${proxy.routes[0]?.target_port || proxy.target_port}`}
                    </td>
                    <td className="px-3 py-3">
                      <StatusBadge status={proxy.enabled ? "enabled" : "disabled"} />
                    </td>
                    <td className="px-3 py-3">
                      <StatusBadge status={proxy.https_enabled ? "valid" : "disabled"} />
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-2">
                        {canEdit ? (
                          <Link to={`/proxies/${proxy.id}/edit`} className="rounded bg-white/10 px-2 py-1">
                            Edit
                          </Link>
                        ) : null}
                        {canEdit ? (
                          <button className="rounded bg-white/10 px-2 py-1" onClick={() => setConfirm({ action: proxy.enabled ? "disable" : "enable", proxy })}>
                            {proxy.enabled ? "Disable" : "Enable"}
                          </button>
                        ) : null}
                        {canRead ? (
                          <button className="rounded bg-white/10 px-2 py-1" onClick={() => setConfirm({ action: "test", proxy })}>
                            Test
                          </button>
                        ) : null}
                        {canEdit ? (
                          <button className="rounded bg-red-600/80 px-2 py-1 text-white" onClick={() => setConfirm({ action: "delete", proxy })}>
                            Delete
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={!!confirm}
        title="Confirm action"
        message={confirm ? `${CONFIRM_ACTION_LABELS[confirm.action]} ${confirm.proxy.name}?` : ""}
        confirmLabel="Continue"
        onConfirm={runAction}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}
