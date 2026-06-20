import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { Organization, OrganizationFormData } from "../types";

const emptyTenant: OrganizationFormData = {
  slug: "",
  name: "",
  enabled: true,
};

export function TenantsPage() {
  const { isSuperAdmin } = useAuth();
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const [editing, setEditing] = useState<Organization | null>(null);
  const [form, setForm] = useState<OrganizationFormData>(emptyTenant);
  const [showForm, setShowForm] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<Organization | null>(null);

  const { data = [], isLoading } = useQuery({
    queryKey: ["organizations"],
    queryFn: api.listOrganizations,
    enabled: isSuperAdmin,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editing) {
        return api.updateOrganization(editing.id, {
          slug: form.slug,
          name: form.name,
          enabled: form.enabled,
        });
      }
      return api.createOrganization(form);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
      showSuccess(editing ? "Tenant updated" : "Tenant created");
      setShowForm(false);
      setEditing(null);
      setForm(emptyTenant);
    },
    onError: (error) => showError(error instanceof ApiError ? error.message : "Save failed"),
  });

  if (!isSuperAdmin) {
    return <p className="text-sm text-white/60">Super admin access required to manage tenants.</p>;
  }

  const openCreate = () => {
    setEditing(null);
    setForm(emptyTenant);
    setShowForm(true);
  };

  const openEdit = (org: Organization) => {
    setEditing(org);
    setForm({
      slug: org.slug,
      name: org.name,
      enabled: org.enabled,
    });
    setShowForm(true);
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    saveMutation.mutate();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Tenants</h2>
        <button className="rounded-lg bg-accent px-4 py-2 text-sm text-white" onClick={openCreate}>
          Create tenant
        </button>
      </div>

      {showForm ? (
        <Card title={editing ? "Edit tenant" : "Create tenant"}>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={onSubmit}>
            <div>
              <label className="mb-1 block text-sm">Slug</label>
              <input
                value={form.slug}
                onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase() })}
                pattern="[a-z0-9-]+"
                required
                disabled={editing?.slug === "default"}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm">Name</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <label className="flex items-center gap-2 text-sm md:col-span-2">
              <input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />
              Enabled
            </label>
            <div className="flex gap-2 md:col-span-2">
              <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm text-white" disabled={saveMutation.isPending}>
                Save
              </button>
              <button type="button" className="rounded-lg bg-white/10 px-4 py-2 text-sm" onClick={() => setShowForm(false)}>
                Cancel
              </button>
            </div>
          </form>
        </Card>
      ) : null}

      <Card title="Organizations">
        {isLoading ? (
          <p>Loading...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-white/60">
                  <th className="px-3 py-2">Slug</th>
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Created</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.map((org) => (
                  <tr key={org.id} className="border-b border-white/5">
                    <td className="px-3 py-3 font-medium">{org.slug}</td>
                    <td className="px-3 py-3">{org.name}</td>
                    <td className="px-3 py-3">
                      <StatusBadge status={org.enabled ? "enabled" : "disabled"} />
                    </td>
                    <td className="px-3 py-3 text-white/60">{new Date(org.created_at).toLocaleString()}</td>
                    <td className="px-3 py-3">
                      <div className="flex gap-2">
                        <button className="rounded bg-white/10 px-2 py-1" onClick={() => openEdit(org)}>
                          Edit
                        </button>
                        {org.slug !== "default" ? (
                          <button className="rounded bg-red-600/80 px-2 py-1 text-white" onClick={() => setConfirmDelete(org)}>
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
        open={!!confirmDelete}
        title="Delete tenant"
        message={`Delete tenant ${confirmDelete?.name}?`}
        onConfirm={async () => {
          if (!confirmDelete) return;
          try {
            await api.deleteOrganization(confirmDelete.id);
            showSuccess("Tenant deleted");
            queryClient.invalidateQueries({ queryKey: ["organizations"] });
          } catch (error) {
            showError(error instanceof ApiError ? error.message : "Delete failed");
          } finally {
            setConfirmDelete(null);
          }
        }}
        onCancel={() => setConfirmDelete(null)}
      />
    </div>
  );
}
