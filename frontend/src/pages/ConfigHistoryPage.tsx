import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";

export function ConfigHistoryPanel({ proxyId }: { proxyId: string }) {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { canEdit } = useAuth();
  const [rollbackId, setRollbackId] = useState<number | null>(null);
  const [compareIds, setCompareIds] = useState<[number | null, number | null]>([null, null]);
  const [diff, setDiff] = useState<string | null>(null);

  const { data = [], isLoading } = useQuery({
    queryKey: ["config-versions", proxyId],
    queryFn: () => api.listConfigVersions("proxy", proxyId),
  });

  const rollbackMutation = useMutation({
    mutationFn: (id: number) => api.rollbackConfigVersion(id),
    onSuccess: (result) => {
      showSuccess(result.message || "Rollback completed");
      queryClient.invalidateQueries({ queryKey: ["config-versions", proxyId] });
      queryClient.invalidateQueries({ queryKey: ["proxy", proxyId] });
      queryClient.invalidateQueries({ queryKey: ["proxies"] });
      setRollbackId(null);
    },
    onError: (error) => {
      showError(error instanceof ApiError ? error.message : "Rollback failed");
      setRollbackId(null);
    },
  });

  const runCompare = async () => {
    if (compareIds[0] == null || compareIds[1] == null) {
      showError("Select two versions to compare");
      return;
    }
    try {
      const result = await api.compareConfigVersions(compareIds[0], compareIds[1]);
      setDiff(result.diff || "(no differences)");
    } catch (error) {
      showError(error instanceof ApiError ? error.message : "Compare failed");
    }
  };

  return (
    <div className="space-y-4">
      <Card title="Configuration history">
        {isLoading ? (
          <p>Loading versions...</p>
        ) : data.length === 0 ? (
          <p className="text-sm text-white/60">No configuration versions recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-white/60">
                  <th className="px-3 py-2">Version</th>
                  <th className="px-3 py-2">Summary</th>
                  <th className="px-3 py-2">User</th>
                  <th className="px-3 py-2">Created</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.map((version) => (
                  <tr key={version.id} className="border-b border-white/5">
                    <td className="px-3 py-3 font-mono">v{version.version}</td>
                    <td className="px-3 py-3">{version.summary}</td>
                    <td className="px-3 py-3">{version.username}</td>
                    <td className="px-3 py-3">{new Date(version.created_at).toLocaleString()}</td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="rounded bg-white/10 px-2 py-1"
                          onClick={() => setCompareIds((current) => [current[0], version.id])}
                        >
                          Compare B
                        </button>
                        <button
                          type="button"
                          className="rounded bg-white/10 px-2 py-1"
                          onClick={() => setCompareIds((current) => [version.id, current[1]])}
                        >
                          Compare A
                        </button>
                        {canEdit && version.has_old_config ? (
                          <button
                            type="button"
                            className="rounded bg-amber-600/80 px-2 py-1 text-white"
                            onClick={() => setRollbackId(version.id)}
                          >
                            Rollback
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

      {data.length > 0 ? (
        <Card title="Compare versions">
          <div className="mb-3 flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block text-xs">Version A</label>
              <select
                className="rounded bg-black/30 px-2 py-1"
                value={compareIds[0] ?? ""}
                onChange={(e) => setCompareIds([Number(e.target.value) || null, compareIds[1]])}
              >
                <option value="">Select...</option>
                {data.map((version) => (
                  <option key={`a-${version.id}`} value={version.id}>
                    v{version.version} — {version.summary}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs">Version B</label>
              <select
                className="rounded bg-black/30 px-2 py-1"
                value={compareIds[1] ?? ""}
                onChange={(e) => setCompareIds([compareIds[0], Number(e.target.value) || null])}
              >
                <option value="">Select...</option>
                {data.map((version) => (
                  <option key={`b-${version.id}`} value={version.id}>
                    v{version.version} — {version.summary}
                  </option>
                ))}
              </select>
            </div>
            <button type="button" className="rounded-lg bg-white/10 px-3 py-2 text-sm" onClick={runCompare}>
              Compare
            </button>
          </div>
          {diff ? (
            <pre className="max-h-96 overflow-auto rounded-lg bg-black/40 p-3 text-xs text-white/80">{diff}</pre>
          ) : null}
        </Card>
      ) : null}

      <ConfirmDialog
        open={rollbackId !== null}
        title="Rollback configuration"
        message="Restore nginx config to the state before this version was applied?"
        confirmLabel="Rollback"
        onConfirm={() => rollbackId && rollbackMutation.mutate(rollbackId)}
        onCancel={() => setRollbackId(null)}
      />
    </div>
  );
}

export function ConfigHistoryPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Configuration History</h2>
        <Link to="/proxies" className="rounded-lg bg-white/10 px-4 py-2 text-sm">
          Back to proxies
        </Link>
      </div>
      <Card>
        <p className="text-sm text-white/60">
          Open a proxy for editing to view and rollback its nginx configuration versions.
        </p>
      </Card>
    </div>
  );
}
