import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { Checkbox } from "../components/Checkbox";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { UserAccount, UserFormData } from "../types";

const emptyUser: UserFormData = {
  username: "",
  password: "",
  is_active: true,
  is_admin: false,
  perm_read: true,
  perm_create: false,
  perm_edit: false,
};

export function UsersPage() {
  const { isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const [editing, setEditing] = useState<UserAccount | null>(null);
  const [form, setForm] = useState<UserFormData>(emptyUser);
  const [showForm, setShowForm] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<UserAccount | null>(null);

  const { data = [], isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: api.listUsers,
    enabled: isAdmin,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        username: form.username,
        is_active: form.is_active,
        is_admin: form.is_admin,
        perm_read: form.perm_read,
        perm_create: form.perm_create,
        perm_edit: form.perm_edit,
        ...(form.password ? { password: form.password } : {}),
      };
      if (editing) return api.updateUser(editing.id, payload);
      return api.createUser({ ...payload, password: form.password });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      showSuccess(editing ? "User updated" : "User created");
      setShowForm(false);
      setEditing(null);
      setForm(emptyUser);
    },
    onError: (error) => showError(error instanceof ApiError ? error.message : "Save failed"),
  });

  if (!isAdmin) {
    return <p className="text-sm text-white/60">Admin access required to manage users.</p>;
  }

  const openCreate = () => {
    setEditing(null);
    setForm(emptyUser);
    setShowForm(true);
  };

  const openEdit = (user: UserAccount) => {
    setEditing(user);
    setForm({
      username: user.username,
      password: "",
      is_active: user.is_active,
      is_admin: user.is_admin,
      perm_read: user.perm_read,
      perm_create: user.perm_create,
      perm_edit: user.perm_edit,
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
        <h2 className="text-2xl font-semibold">Users</h2>
        <button className="rounded-lg bg-accent px-4 py-2 text-sm text-white" onClick={openCreate}>
          Create user
        </button>
      </div>

      {showForm ? (
        <Card title={editing ? "Edit user" : "Create user"}>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={onSubmit}>
            <div>
              <label className="mb-1 block text-sm">Username</label>
              <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
            </div>
            <div>
              <label className="mb-1 block text-sm">{editing ? "New password (optional)" : "Password"}</label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required={!editing}
              />
            </div>
            <div className="ui-checkbox-group md:col-span-2">
              <Checkbox
                checked={form.is_active}
                onChange={(checked) => setForm({ ...form, is_active: checked })}
                label="Active"
              />
              <Checkbox
                checked={form.is_admin}
                onChange={(checked) => setForm({ ...form, is_admin: checked })}
                label="Admin (all permissions)"
              />
              {!form.is_admin ? (
                <>
                  <Checkbox
                    checked={form.perm_read}
                    onChange={(checked) => setForm({ ...form, perm_read: checked })}
                    label="Read"
                  />
                  <Checkbox
                    checked={form.perm_create}
                    onChange={(checked) => setForm({ ...form, perm_create: checked })}
                    label="Create"
                  />
                  <Checkbox
                    checked={form.perm_edit}
                    onChange={(checked) => setForm({ ...form, perm_edit: checked })}
                    label="Edit"
                  />
                </>
              ) : null}
            </div>
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

      <Card title="User database">
        {isLoading ? (
          <p>Loading...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-white/60">
                  <th className="px-3 py-2">Username</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Permissions</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.map((user) => (
                  <tr key={user.id} className="border-b border-white/5">
                    <td className="px-3 py-3 font-medium">{user.username}</td>
                    <td className="px-3 py-3">
                      <StatusBadge status={user.is_active ? "enabled" : "disabled"} />
                      {user.is_admin ? <span className="ml-2 rounded-full bg-blue-500/20 px-2 py-0.5 text-xs">admin</span> : null}
                    </td>
                    <td className="px-3 py-3 text-xs">
                      {user.is_admin
                        ? "read, create, edit"
                        : [user.perm_read && "read", user.perm_create && "create", user.perm_edit && "edit"].filter(Boolean).join(", ") ||
                          "none"}
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex gap-2">
                        <button className="rounded bg-white/10 px-2 py-1" onClick={() => openEdit(user)}>
                          Edit
                        </button>
                        <button className="rounded bg-red-600/80 px-2 py-1 text-white" onClick={() => setConfirmDelete(user)}>
                          Delete
                        </button>
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
        title="Delete user"
        message={`Delete user ${confirmDelete?.username}?`}
        onConfirm={async () => {
          if (!confirmDelete) return;
          try {
            await api.deleteUser(confirmDelete.id);
            showSuccess("User deleted");
            queryClient.invalidateQueries({ queryKey: ["users"] });
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
