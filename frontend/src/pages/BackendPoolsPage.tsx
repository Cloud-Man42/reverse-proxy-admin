import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { BackendPool, BackendPoolFormData, BackendServerFormData } from "../types";

const emptyServer = (): BackendServerFormData => ({
  name: "",
  host: "",
  port: 443,
  protocol: "https",
  weight: 10,
  role: "primary",
  enabled: true,
  health_check_type: "tcp",
  health_check_path: "/",
  notes: "",
});

const emptyPool = (): BackendPoolFormData => ({
  name: "",
  proxy_id: "",
  route_path: "/",
  load_balancing_method: "round_robin",
  enabled: true,
  notes: "",
  servers: [emptyServer()],
});

export function BackendPoolsPage() {
  const { canCreate, canEdit } = useAuth();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<BackendPoolFormData>(emptyPool());
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const { data: pools = [] } = useQuery({ queryKey: ["backend-pools"], queryFn: () => api.listBackendPools() });

  const createPool = useMutation({
    mutationFn: () =>
      api.createBackendPool({
        name: form.name,
        proxy_id: form.proxy_id || null,
        route_path: form.route_path,
        load_balancing_method: form.load_balancing_method,
        enabled: form.enabled,
        notes: form.notes || null,
        servers: form.servers,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backend-pools"] });
      setForm(emptyPool());
      showSuccess("Backend pool created");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Create failed"),
  });

  const deletePool = useMutation({
    mutationFn: (id: number) => api.deleteBackendPool(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backend-pools"] });
      setDeleteId(null);
      showSuccess("Pool deleted");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Delete failed"),
  });

  const updateServer = (index: number, patch: Partial<BackendServerFormData>) => {
    setForm((current) => ({
      ...current,
      servers: current.servers.map((server, i) => (i === index ? { ...server, ...patch } : server)),
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Backend Pools</h2>
        <Link to="/proxies" className="text-sm text-accent">Back to proxies</Link>
      </div>

      {canCreate && (
        <Card title="Create Backend Pool">
          <form
            className="space-y-4"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createPool.mutate();
            }}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1 text-sm">Pool Name<input className="w-full" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
              <label className="space-y-1 text-sm">Proxy ID<input className="w-full" value={form.proxy_id} onChange={(e) => setForm({ ...form, proxy_id: e.target.value })} placeholder="my-app" /></label>
              <label className="space-y-1 text-sm">Route Path<input className="w-full" value={form.route_path} onChange={(e) => setForm({ ...form, route_path: e.target.value })} /></label>
              <label className="space-y-1 text-sm">
                Load Balancing Method
                <select className="w-full" value={form.load_balancing_method} onChange={(e) => setForm({ ...form, load_balancing_method: e.target.value as BackendPoolFormData["load_balancing_method"] })}>
                  <option value="round_robin">Round Robin</option>
                  <option value="least_conn">Least Connections</option>
                  <option value="ip_hash">IP Hash</option>
                  <option value="random">Random</option>
                  <option value="weighted">Weighted</option>
                </select>
              </label>
            </div>
            <div className="space-y-3">
              <p className="text-sm font-medium">Backend Servers</p>
              {form.servers.map((server, index) => (
                <div key={index} className="grid gap-3 rounded-lg bg-white/5 p-3 md:grid-cols-4">
                  <input className="rounded bg-black/20 px-2 py-1 text-sm" placeholder="Name" value={server.name} onChange={(e) => updateServer(index, { name: e.target.value })} />
                  <input className="rounded bg-black/20 px-2 py-1 text-sm" placeholder="IP" value={server.host} onChange={(e) => updateServer(index, { host: e.target.value })} />
                  <input type="number" className="rounded bg-black/20 px-2 py-1 text-sm" placeholder="Port" value={server.port} onChange={(e) => updateServer(index, { port: Number(e.target.value) })} />
                  <select className="rounded bg-black/20 px-2 py-1 text-sm" value={server.role} onChange={(e) => updateServer(index, { role: e.target.value as BackendServerFormData["role"] })}>
                    <option value="primary">Primary</option>
                    <option value="backup">Backup</option>
                  </select>
                  <input type="number" className="rounded bg-black/20 px-2 py-1 text-sm" placeholder="Weight" value={server.weight} onChange={(e) => updateServer(index, { weight: Number(e.target.value) })} />
                </div>
              ))}
              <button type="button" className="rounded-lg bg-white/10 px-3 py-1 text-sm" onClick={() => setForm({ ...form, servers: [...form.servers, emptyServer()] })}>
                Add Server
              </button>
            </div>
            <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm">Create Pool</button>
          </form>
        </Card>
      )}

      <Card title="Existing Pools">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-white/60">
              <th className="py-2">Name</th>
              <th>Proxy</th>
              <th>Method</th>
              <th>Servers</th>
              <th>Failover</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {pools.map((pool: BackendPool) => (
              <tr key={pool.id} className="border-t border-white/10">
                <td className="py-2">{pool.name}</td>
                <td>{pool.proxy_id || "—"}</td>
                <td>{pool.load_balancing_method}</td>
                <td>{pool.servers.length}</td>
                <td>{pool.failover_active ? <StatusBadge status="warning" label="Active" /> : "—"}</td>
                <td className="text-right">
                  {canEdit && (
                    <button type="button" className="text-red-300" onClick={() => setDeleteId(pool.id)}>
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <ConfirmDialog
        open={deleteId !== null}
        title="Delete backend pool?"
        message="This removes the pool and all servers."
        onConfirm={() => deleteId && deletePool.mutate(deleteId)}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  );
}
