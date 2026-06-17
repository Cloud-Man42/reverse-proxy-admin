import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { ProxyFormData, TrafficFlowTestResult } from "../types";

const emptyForm: ProxyFormData = {
  name: "",
  domains: "",
  target_protocol: "http",
  target_host: "",
  target_port: 8080,
  websocket_enabled: false,
  custom_headers: [],
  max_body_size: "",
  basic_auth_enabled: false,
  basic_auth_username: "",
  basic_auth_password: "",
  force_https: false,
  enabled: true,
};

function toPayload(form: ProxyFormData) {
  return {
    name: form.name,
    domains: form.domains.split(",").map((d) => d.trim()).filter(Boolean),
    target_protocol: form.target_protocol,
    target_host: form.target_host,
    target_port: Number(form.target_port),
    websocket_enabled: form.websocket_enabled,
    custom_headers: form.custom_headers,
    max_body_size: form.max_body_size || null,
    basic_auth_enabled: form.basic_auth_enabled,
    basic_auth_username: form.basic_auth_username || null,
    basic_auth_password: form.basic_auth_password || null,
    force_https: form.force_https,
    enabled: form.enabled,
  };
}

export function ProxyFormPage() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { canCreate, canEdit, canRead } = useAuth();
  const [form, setForm] = useState<ProxyFormData>(emptyForm);
  const [flowResult, setFlowResult] = useState<TrafficFlowTestResult | null>(null);
  const [testingFlow, setTestingFlow] = useState(false);

  const { data } = useQuery({
    queryKey: ["proxy", id],
    queryFn: () => api.getProxy(id!),
    enabled: isEdit,
  });

  useEffect(() => {
    if (data) {
      setForm({
        name: data.name,
        domains: data.domains.join(", "),
        target_protocol: data.target_protocol,
        target_host: data.target_host,
        target_port: data.target_port,
        websocket_enabled: data.websocket_enabled,
        custom_headers: data.custom_headers,
        max_body_size: data.max_body_size || "",
        basic_auth_enabled: data.basic_auth_enabled,
        basic_auth_username: "",
        basic_auth_password: "",
        force_https: data.force_https,
        enabled: data.enabled,
      });
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: async () => {
      const payload = toPayload(form);
      if (isEdit) return api.updateProxy(id!, payload);
      return api.createProxy(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["proxies"] });
      showSuccess(isEdit ? "Proxy updated" : "Proxy created");
      navigate("/proxies");
    },
    onError: (error) => showError(error instanceof ApiError ? error.message : "Save failed"),
  });

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    mutation.mutate();
  };

  const runFlowTest = async () => {
    setTestingFlow(true);
    setFlowResult(null);
    try {
      const payload = toPayload(form);
      const result = isEdit ? await api.testFlowProxy(id!) : await api.testFlowDraft(payload);
      setFlowResult(result);
      showSuccess(result.success ? "Traffic flow test passed" : "Traffic flow test found issues");
    } catch (error) {
      showError(error instanceof ApiError ? error.message : "Flow test failed");
    } finally {
      setTestingFlow(false);
    }
  };

  if ((isEdit && !canEdit) || (!isEdit && !canCreate)) {
    return <p className="text-sm text-white/60">You do not have permission to modify proxy configurations.</p>;
  }

  const update = <K extends keyof ProxyFormData>(key: K, value: ProxyFormData[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">{isEdit ? "Edit proxy" : "Create proxy"}</h2>
        <Link to="/proxies" className="text-sm text-accent">
          Back
        </Link>
      </div>

      <Card>
        <form className="grid gap-4 md:grid-cols-2" onSubmit={onSubmit}>
          <div>
            <label className="mb-1 block text-sm">App name</label>
            <input value={form.name} disabled={isEdit} onChange={(e) => update("name", e.target.value)} required />
          </div>
          <div>
            <label className="mb-1 block text-sm">Domains (comma separated)</label>
            <input value={form.domains} onChange={(e) => update("domains", e.target.value)} required />
          </div>
          <div>
            <label className="mb-1 block text-sm">Target protocol</label>
            <select value={form.target_protocol} onChange={(e) => update("target_protocol", e.target.value as "http" | "https")}>
              <option value="http">http</option>
              <option value="https">https</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm">Target host/IP</label>
            <input value={form.target_host} onChange={(e) => update("target_host", e.target.value)} required />
          </div>
          <div>
            <label className="mb-1 block text-sm">Target port</label>
            <input
              type="number"
              value={form.target_port}
              onChange={(e) => update("target_port", Number(e.target.value))}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm">Max body size</label>
            <input value={form.max_body_size} onChange={(e) => update("max_body_size", e.target.value)} placeholder="50m" />
          </div>

          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <input type="checkbox" checked={form.websocket_enabled} onChange={(e) => update("websocket_enabled", e.target.checked)} />
            WebSocket support
          </label>
          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <input type="checkbox" checked={form.force_https} onChange={(e) => update("force_https", e.target.checked)} />
            Redirect HTTP to HTTPS
          </label>
          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <input type="checkbox" checked={form.enabled} onChange={(e) => update("enabled", e.target.checked)} />
            Enabled
          </label>
          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <input type="checkbox" checked={form.basic_auth_enabled} onChange={(e) => update("basic_auth_enabled", e.target.checked)} />
            Basic auth
          </label>
          {form.basic_auth_enabled ? (
            <>
              <div>
                <label className="mb-1 block text-sm">Basic auth username</label>
                <input value={form.basic_auth_username} onChange={(e) => update("basic_auth_username", e.target.value)} />
              </div>
              <div>
                <label className="mb-1 block text-sm">Basic auth password</label>
                <input
                  type="password"
                  value={form.basic_auth_password}
                  onChange={(e) => update("basic_auth_password", e.target.value)}
                />
              </div>
            </>
          ) : null}

          <div className="flex flex-wrap gap-2 md:col-span-2">
            <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm text-white" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving..." : "Save"}
            </button>
            {canRead ? (
              <button
                type="button"
                className="rounded-lg bg-white/10 px-4 py-2 text-sm"
                onClick={runFlowTest}
                disabled={testingFlow}
              >
                {testingFlow ? "Testing flow..." : "Test traffic flow"}
              </button>
            ) : null}
          </div>
        </form>
      </Card>

      {flowResult ? (
        <Card title="Traffic flow test">
          <p className={`mb-3 text-sm ${flowResult.success ? "text-emerald-300" : "text-amber-300"}`}>{flowResult.summary}</p>
          <div className="space-y-2">
            {flowResult.checks.map((check) => (
              <div key={check.name} className="flex items-start justify-between gap-3 rounded-lg bg-black/20 p-3 text-sm">
                <div>
                  <p className="font-medium">{check.name.replace(/_/g, " ")}</p>
                  <p className="text-white/60">{check.message}</p>
                </div>
                <StatusBadge status={check.success ? "valid" : "expired"} />
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  );
}
