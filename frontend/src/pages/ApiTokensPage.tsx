import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { Checkbox } from "../components/Checkbox";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { ApiToken, ApiTokenFormData } from "../types";

const emptyForm = (): ApiTokenFormData => ({
  name: "",
  scopes: ["proxies:read"],
});

export function ApiTokensPage() {
  const { isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const [form, setForm] = useState<ApiTokenFormData>(emptyForm);
  const [showForm, setShowForm] = useState(false);
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [confirmRevoke, setConfirmRevoke] = useState<ApiToken | null>(null);

  const { data: scopes = [] } = useQuery({
    queryKey: ["api-token-scopes"],
    queryFn: async () => (await api.listApiTokenScopes()).scopes,
    enabled: isAdmin,
  });

  const { data: tokens = [], isLoading } = useQuery({
    queryKey: ["api-tokens"],
    queryFn: api.listApiTokens,
    enabled: isAdmin,
  });

  const createMutation = useMutation({
    mutationFn: () => api.createApiToken(form),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["api-tokens"] });
      setCreatedToken(data.token);
      setShowForm(false);
      setForm(emptyForm());
      showSuccess("API token created");
    },
    onError: (error) => showError(error instanceof ApiError ? error.message : "Create failed"),
  });

  const revokeMutation = useMutation({
    mutationFn: (id: number) => api.revokeApiToken(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-tokens"] });
      showSuccess("API token revoked");
      setConfirmRevoke(null);
    },
    onError: (error) => showError(error instanceof ApiError ? error.message : "Revoke failed"),
  });

  if (!isAdmin) {
    return <p className="text-sm text-white/60">Admin access required to manage API tokens.</p>;
  }

  const toggleScope = (scope: string) => {
    setForm((current) => ({
      ...current,
      scopes: current.scopes.includes(scope)
        ? current.scopes.filter((item) => item !== scope)
        : [...current.scopes, scope],
    }));
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    createMutation.mutate();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">API Tokens</h2>
          <p className="text-sm text-white/60">Bearer tokens for the public REST API at /api/v1</p>
        </div>
        <button className="rounded-lg bg-accent px-4 py-2 text-sm text-white" onClick={() => setShowForm(true)}>
          Create token
        </button>
      </div>

      {createdToken ? (
        <Card title="Token created — copy now">
          <p className="mb-3 text-sm text-amber-200">This token is shown only once. Store it securely.</p>
          <code className="block break-all rounded-lg bg-black/30 p-3 text-sm">{createdToken}</code>
          <button
            className="mt-3 rounded-lg bg-white/10 px-4 py-2 text-sm"
            onClick={() => {
              navigator.clipboard.writeText(createdToken);
              showSuccess("Copied to clipboard");
            }}
          >
            Copy
          </button>
          <button className="ml-2 mt-3 rounded-lg bg-white/10 px-4 py-2 text-sm" onClick={() => setCreatedToken(null)}>
            Dismiss
          </button>
        </Card>
      ) : null}

      {showForm ? (
        <Card title="Create API token">
          <form className="space-y-4" onSubmit={onSubmit}>
            <label className="block space-y-1">
              <span className="text-sm text-white/70">Name</span>
              <input
                className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
              />
            </label>
            <div>
              <p className="mb-2 text-sm text-white/70">Scopes</p>
              <div className="ui-checkbox-grid">
                {scopes.map((scope) => (
                  <Checkbox
                    key={scope}
                    checked={form.scopes.includes(scope)}
                    onChange={() => toggleScope(scope)}
                    label={scope}
                  />
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm text-white">
                Create
              </button>
              <button type="button" className="rounded-lg bg-white/10 px-4 py-2 text-sm" onClick={() => setShowForm(false)}>
                Cancel
              </button>
            </div>
          </form>
        </Card>
      ) : null}

      <Card title="Active tokens">
        {isLoading ? (
          <p className="text-sm text-white/60">Loading...</p>
        ) : tokens.length === 0 ? (
          <p className="text-sm text-white/60">No API tokens yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-white/60">
                  <th className="py-2 pr-4">Name</th>
                  <th className="py-2 pr-4">Prefix</th>
                  <th className="py-2 pr-4">Scopes</th>
                  <th className="py-2 pr-4">Last used</th>
                  <th className="py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {tokens.map((token) => (
                  <tr key={token.id} className="border-b border-white/5">
                    <td className="py-3 pr-4">{token.name}</td>
                    <td className="py-3 pr-4 font-mono">{token.token_prefix}…</td>
                    <td className="py-3 pr-4">{token.scopes.join(", ")}</td>
                    <td className="py-3 pr-4">{token.last_used_at ? new Date(token.last_used_at).toLocaleString() : "Never"}</td>
                    <td className="py-3">
                      <button
                        className="rounded-lg bg-red-500/20 px-3 py-1 text-red-200"
                        onClick={() => setConfirmRevoke(token)}
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={!!confirmRevoke}
        title="Revoke API token"
        message={`Revoke token "${confirmRevoke?.name}"? This cannot be undone.`}
        confirmLabel="Revoke"
        onConfirm={() => confirmRevoke && revokeMutation.mutate(confirmRevoke.id)}
        onCancel={() => setConfirmRevoke(null)}
      />
    </div>
  );
}
