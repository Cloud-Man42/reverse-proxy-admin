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

type EditServerRow = BackendServerFormData & { id?: number };

type EditPoolFormData = Omit<BackendPoolFormData, "servers"> & {
  servers: EditServerRow[];
};

function poolToEditForm(pool: BackendPool): EditPoolFormData {
  return {
    name: pool.name,
    proxy_id: pool.proxy_id || "",
    route_path: pool.route_path,
    load_balancing_method: pool.load_balancing_method,
    enabled: pool.enabled,
    notes: pool.notes || "",
    servers: pool.servers.map((server) => ({
      id: server.id,
      name: server.name,
      host: server.host,
      port: server.port,
      protocol: server.protocol,
      weight: server.weight,
      role: server.role,
      enabled: server.enabled,
      health_check_type: server.health_check_type,
      health_check_path: server.health_check_path,
      notes: server.notes || "",
    })),
  };
}

function ServerFields({
  server,
  index,
  onChange,
  onRemove,
  canRemove,
}: {
  server: EditServerRow;
  index: number;
  onChange: (index: number, patch: Partial<EditServerRow>) => void;
  onRemove: (index: number) => void;
  canRemove: boolean;
}) {
  return (
    <div className="grid gap-3 rounded-lg bg-white/5 p-3 md:grid-cols-4">
      <input className="rounded bg-black/20 px-2 py-1 text-sm" placeholder="Name" value={server.name} onChange={(e) => onChange(index, { name: e.target.value })} />
      <input className="rounded bg-black/20 px-2 py-1 text-sm" placeholder="IP" value={server.host} onChange={(e) => onChange(index, { host: e.target.value })} />
      <input type="number" className="rounded bg-black/20 px-2 py-1 text-sm" placeholder="Port" value={server.port} onChange={(e) => onChange(index, { port: Number(e.target.value) })} />
      <select className="rounded bg-black/20 px-2 py-1 text-sm" value={server.role} onChange={(e) => onChange(index, { role: e.target.value as BackendServerFormData["role"] })}>
        <option value="primary">Primary</option>
        <option value="backup">Backup</option>
      </select>
      <input type="number" className="rounded bg-black/20 px-2 py-1 text-sm" placeholder="Weight" value={server.weight} onChange={(e) => onChange(index, { weight: Number(e.target.value) })} />
      <select className="rounded bg-black/20 px-2 py-1 text-sm" value={server.health_check_type} onChange={(e) => onChange(index, { health_check_type: e.target.value as BackendServerFormData["health_check_type"] })}>
        <option value="tcp">TCP</option>
        <option value="http">HTTP</option>
        <option value="https">HTTPS</option>
        <option value="custom">Custom</option>
      </select>
      <input className="rounded bg-black/20 px-2 py-1 text-sm md:col-span-2" placeholder="Health check path" value={server.health_check_path} onChange={(e) => onChange(index, { health_check_path: e.target.value })} />
      {server.id ? <p className="text-xs text-white/50 md:col-span-4">Server ID: {server.id}</p> : null}
      {canRemove ? (
        <button type="button" className="rounded bg-red-600/70 px-2 py-1 text-xs text-white md:col-span-4 w-fit" onClick={() => onRemove(index)}>
          Remove server
        </button>
      ) : null}
    </div>
  );
}

function PoolFormFields({
  form,
  proxies,
  onChange,
  onServerChange,
  onAddServer,
  onRemoveServer,
}: {
  form: BackendPoolFormData | EditPoolFormData;
  proxies: { id: string; name: string }[];
  onChange: (patch: Partial<BackendPoolFormData>) => void;
  onServerChange: (index: number, patch: Partial<EditServerRow>) => void;
  onAddServer: () => void;
  onRemoveServer: (index: number) => void;
}) {
  const servers = form.servers as EditServerRow[];
  return (
    <>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-1 text-sm">
          Pool Name
          <input className="w-full" value={form.name} onChange={(e) => onChange({ name: e.target.value })} required />
        </label>
        <label className="space-y-1 text-sm">
          Proxy
          <select className="w-full" value={form.proxy_id} onChange={(e) => onChange({ proxy_id: e.target.value })}>
            <option value="">None</option>
            {proxies.map((proxy) => (
              <option key={proxy.id} value={proxy.id}>
                {proxy.name}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1 text-sm">
          Route Path
          <input className="w-full" value={form.route_path} onChange={(e) => onChange({ route_path: e.target.value })} />
        </label>
        <label className="space-y-1 text-sm">
          Load Balancing Method
          <select className="w-full" value={form.load_balancing_method} onChange={(e) => onChange({ load_balancing_method: e.target.value as BackendPoolFormData["load_balancing_method"] })}>
            <option value="round_robin">Round Robin</option>
            <option value="least_conn">Least Connections</option>
            <option value="ip_hash">IP Hash</option>
            <option value="random">Random</option>
            <option value="weighted">Weighted</option>
          </select>
        </label>
        <label className="space-y-1 text-sm md:col-span-2">
          Notes
          <textarea className="w-full rounded-lg bg-black/20 px-3 py-2 text-sm" rows={2} value={form.notes} onChange={(e) => onChange({ notes: e.target.value })} />
        </label>
      </div>
      <div className="space-y-3">
        <p className="text-sm font-medium">Backend Servers</p>
        {servers.map((server, index) => (
          <ServerFields
            key={server.id ?? `new-${index}`}
            server={server}
            index={index}
            onChange={onServerChange}
            onRemove={onRemoveServer}
            canRemove={servers.length > 1}
          />
        ))}
        <button type="button" className="rounded-lg bg-white/10 px-3 py-1 text-sm" onClick={onAddServer}>
          Add Server
        </button>
      </div>
    </>
  );
}

export function BackendPoolsPage() {
  const { canCreate, canEdit } = useAuth();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<BackendPoolFormData>(emptyPool());
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [editingPool, setEditingPool] = useState<BackendPool | null>(null);
  const [editForm, setEditForm] = useState<EditPoolFormData | null>(null);

  const { data: pools = [] } = useQuery({ queryKey: ["backend-pools"], queryFn: () => api.listBackendPools() });
  const { data: proxies = [] } = useQuery({ queryKey: ["proxies"], queryFn: api.listProxies });

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

  const updatePool = useMutation({
    mutationFn: async () => {
      if (!editingPool || !editForm) return;
      await api.updateBackendPool(editingPool.id, {
        name: editForm.name,
        proxy_id: editForm.proxy_id || null,
        route_path: editForm.route_path,
        load_balancing_method: editForm.load_balancing_method,
        enabled: editForm.enabled,
        notes: editForm.notes || null,
      });
      const existingIds = new Set(editingPool.servers.map((server) => server.id));
      const formIds = new Set(editForm.servers.filter((server) => server.id).map((server) => server.id!));

      for (const serverId of existingIds) {
        if (!formIds.has(serverId)) {
          await api.deleteBackendServer(serverId);
        }
      }

      for (const server of editForm.servers) {
        const payload = {
          name: server.name,
          host: server.host,
          port: server.port,
          protocol: server.protocol,
          weight: server.weight,
          role: server.role,
          enabled: server.enabled,
          health_check_type: server.health_check_type,
          health_check_path: server.health_check_path,
          notes: server.notes || null,
        };
        if (server.id) {
          await api.updateBackendServer(server.id, payload);
        } else {
          await api.createBackendServer({ ...payload, pool_id: editingPool.id });
        }
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backend-pools"] });
      setEditingPool(null);
      setEditForm(null);
      showSuccess("Backend pool updated");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Update failed"),
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

  const updateEditServer = (index: number, patch: Partial<EditServerRow>) => {
    setEditForm((current) =>
      current
        ? {
            ...current,
            servers: current.servers.map((server, i) => (i === index ? { ...server, ...patch } : server)),
          }
        : current,
    );
  };

  const openEdit = (pool: BackendPool) => {
    setEditingPool(pool);
    setEditForm(poolToEditForm(pool));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Backend Pools</h2>
        <Link to="/proxies" className="text-sm text-accent">
          Back to proxies
        </Link>
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
            <PoolFormFields
              form={form}
              proxies={proxies}
              onChange={(patch) => setForm({ ...form, ...patch })}
              onServerChange={updateServer}
              onAddServer={() => setForm({ ...form, servers: [...form.servers, emptyServer()] })}
              onRemoveServer={(index) =>
                setForm({
                  ...form,
                  servers: form.servers.filter((_, i) => i !== index),
                })
              }
            />
            <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm">
              Create Pool
            </button>
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
                <td className="space-x-2 text-right">
                  {canEdit && (
                    <>
                      <button type="button" className="rounded bg-white/10 px-2 py-1 text-xs" onClick={() => openEdit(pool)}>
                        Edit
                      </button>
                      <button type="button" className="text-red-300" onClick={() => setDeleteId(pool.id)}>
                        Delete
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {editingPool && editForm ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-xl border border-white/10 bg-surface-muted p-6">
            <h3 className="text-lg font-semibold">Edit pool: {editingPool.name}</h3>
            <form
              className="mt-4 space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                updatePool.mutate();
              }}
            >
              <PoolFormFields
                form={editForm}
                proxies={proxies}
                onChange={(patch) => setEditForm({ ...editForm, ...patch })}
                onServerChange={updateEditServer}
                onAddServer={() => setEditForm({ ...editForm, servers: [...editForm.servers, emptyServer()] })}
                onRemoveServer={(index) =>
                  setEditForm({
                    ...editForm,
                    servers: editForm.servers.filter((_, i) => i !== index),
                  })
                }
              />
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  className="rounded-lg px-4 py-2 text-sm hover:bg-white/10"
                  onClick={() => {
                    setEditingPool(null);
                    setEditForm(null);
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm text-white" disabled={updatePool.isPending}>
                  {updatePool.isPending ? "Saving..." : "Save changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

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
