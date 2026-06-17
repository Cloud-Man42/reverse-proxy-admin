import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { TrafficDebugPanel } from "../components/TrafficDebugPanel";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { toPayload } from "../lib/proxyPayload";
import { ProxyFormData, ProxyRouteFormData, TrafficFlowTestResult } from "../types";

const FLOW_CHECK_LABELS: Record<string, string> = {
  input_validation: "Input validation",
  nginx_syntax: "Nginx syntax",
  upstream_connectivity: "Upstream connectivity",
  ssl_readiness: "SSL readiness",
  traffic_path: "Traffic path",
};

const emptyRoute = (): ProxyRouteFormData => ({
  path_prefix: "/",
  target_protocol: "http",
  target_host: "",
  target_port: 8080,
  websocket_enabled: false,
});

const emptyForm: ProxyFormData = {
  name: "",
  domains: "",
  routes: [emptyRoute()],
  custom_headers: [],
  max_body_size: "",
  basic_auth_enabled: false,
  basic_auth_username: "",
  basic_auth_password: "",
  force_https: false,
  enabled: true,
};

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
        routes: data.routes.length
          ? data.routes.map((route) => ({
              path_prefix: route.path_prefix,
              target_protocol: route.target_protocol,
              target_host: route.target_host,
              target_port: route.target_port,
              websocket_enabled: route.websocket_enabled,
            }))
          : [emptyRoute()],
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
      const result = await api.testFlowDraft(payload);
      setFlowResult(result);
      if (result.success) {
        showSuccess("Traffic flow test passed");
      } else {
        const failed = result.checks.filter((check) => !check.success);
        const details = failed.map((check) => `${check.name}: ${check.message}`).join(" | ");
        showError(details || result.summary);
      }
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

  const updateRoute = <K extends keyof ProxyRouteFormData>(index: number, key: K, value: ProxyRouteFormData[K]) =>
    setForm((prev) => ({
      ...prev,
      routes: prev.routes.map((route, routeIndex) => (routeIndex === index ? { ...route, [key]: value } : route)),
    }));

  const addRoute = () => update("routes", [...form.routes, emptyRoute()]);

  const removeRoute = (index: number) => {
    if (form.routes.length <= 1) return;
    update(
      "routes",
      form.routes.filter((_, routeIndex) => routeIndex !== index),
    );
  };

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
            <input value={form.name} onChange={(e) => update("name", e.target.value)} required />
          </div>
          <div>
            <label className="mb-1 block text-sm">Domains (comma separated)</label>
            <input value={form.domains} onChange={(e) => update("domains", e.target.value)} required />
          </div>

          <div className="md:col-span-2">
            <div className="mb-2 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium">Upstream routes</h3>
                <p className="text-xs text-white/60">
                  Map path prefixes on the same domain to different ports on one or more backend hosts.
                </p>
              </div>
              <button type="button" className="rounded-lg bg-white/10 px-3 py-1 text-sm" onClick={addRoute}>
                Add route
              </button>
            </div>
            <div className="space-y-3">
              {form.routes.map((route, index) => (
                <div key={index} className="grid gap-3 rounded-lg border border-white/10 bg-black/20 p-3 md:grid-cols-6">
                  <div>
                    <label className="mb-1 block text-xs">Path prefix</label>
                    <input
                      value={route.path_prefix}
                      onChange={(e) => updateRoute(index, "path_prefix", e.target.value)}
                      placeholder="/ or /api"
                      required
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs">Protocol</label>
                    <select
                      value={route.target_protocol}
                      onChange={(e) => updateRoute(index, "target_protocol", e.target.value as "http" | "https")}
                    >
                      <option value="http">http</option>
                      <option value="https">https</option>
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs">Target host</label>
                    <input
                      value={route.target_host}
                      onChange={(e) => updateRoute(index, "target_host", e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs">Target port</label>
                    <input
                      type="number"
                      value={route.target_port}
                      onChange={(e) => updateRoute(index, "target_port", Number(e.target.value))}
                      required
                    />
                  </div>
                  <label className="flex items-end gap-2 pb-2 text-xs">
                    <input
                      type="checkbox"
                      checked={route.websocket_enabled}
                      onChange={(e) => updateRoute(index, "websocket_enabled", e.target.checked)}
                    />
                    WebSocket
                  </label>
                  <div className="flex items-end justify-end pb-1">
                    <button
                      type="button"
                      className="rounded bg-red-600/70 px-2 py-1 text-xs text-white disabled:opacity-40"
                      onClick={() => removeRoute(index)}
                      disabled={form.routes.length <= 1}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm">Max body size</label>
            <input value={form.max_body_size} onChange={(e) => update("max_body_size", e.target.value)} placeholder="50m" />
          </div>

          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <input type="checkbox" checked={form.force_https} onChange={(e) => update("force_https", e.target.checked)} />
            Redirect HTTP to HTTPS
          </label>
          {form.force_https ? (
            <p className="text-sm text-amber-200 md:col-span-2">
              Requires a valid Let&apos;s Encrypt certificate for the domain. Issue the certificate on the Certificates page
              before saving with this option enabled.
            </p>
          ) : null}
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
                  <p className="font-medium">{FLOW_CHECK_LABELS[check.name] || check.name.replace(/_/g, " ")}</p>
                  <p className="text-white/60">{check.message}</p>
                </div>
                <StatusBadge status={check.success ? "valid" : "expired"} />
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      {isEdit && id && canRead ? (
        <Card>
          <TrafficDebugPanel
            proxyId={id}
            domains={form.domains.split(",").map((d) => d.trim()).filter(Boolean)}
          />
        </Card>
      ) : null}
    </div>
  );
}
