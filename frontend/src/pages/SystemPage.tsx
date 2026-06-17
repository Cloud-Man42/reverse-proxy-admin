import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../hooks/useToast";

export function SystemPage() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const [confirmReload, setConfirmReload] = useState(false);

  const health = useQuery({ queryKey: ["health"], queryFn: api.systemHealth });
  const status = useQuery({ queryKey: ["nginx-status"], queryFn: api.nginxStatus });

  const runTest = async () => {
    try {
      const result = await api.nginxTest();
      if (result.success) {
        showSuccess("nginx -t passed");
      } else {
        showError(result.output || "nginx -t failed");
      }
    } catch (error) {
      showError(error instanceof ApiError ? error.message : "Test failed");
    }
  };

  const runReload = async () => {
    try {
      const result = await api.nginxReload();
      showSuccess(result.message);
      queryClient.invalidateQueries({ queryKey: ["health"] });
      queryClient.invalidateQueries({ queryKey: ["nginx-status"] });
    } catch (error) {
      showError(error instanceof ApiError ? error.message : "Reload failed");
    } finally {
      setConfirmReload(false);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold">System</h2>

      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Service health">
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span>Nginx</span>
              <StatusBadge status={health.data?.nginx_active ? "running" : "stopped"} />
            </div>
            <p>Disk used: {health.data?.disk_used_gb ?? "-"} GB / {health.data?.disk_total_gb ?? "-"} GB</p>
            <p>Disk free: {health.data?.disk_free_gb ?? "-"} GB ({health.data?.disk_percent ?? "-"}% used)</p>
          </div>
        </Card>

        <Card title="Actions">
          <div className="flex flex-wrap gap-2">
            <button className="rounded-lg bg-white/10 px-4 py-2 text-sm" onClick={runTest}>
              Run nginx -t
            </button>
            <button className="rounded-lg bg-red-600 px-4 py-2 text-sm text-white" onClick={() => setConfirmReload(true)}>
              Reload nginx
            </button>
          </div>
        </Card>
      </div>

      <Card title="systemctl status nginx">
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-black/20 p-3 text-xs">
          {status.data?.output || "Loading..."}
        </pre>
      </Card>

      <ConfirmDialog
        open={confirmReload}
        title="Reload nginx"
        message="Reload nginx now? Configuration must pass nginx -t first."
        confirmLabel="Reload"
        onConfirm={runReload}
        onCancel={() => setConfirmReload(false)}
      />
    </div>
  );
}
