import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { Checkbox } from "../components/Checkbox";
import { DataTable } from "../components/metrics";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { MetricAlertRule } from "../types";

const emptyRule = {
  name: "",
  enabled: true,
  severity: "warning",
  metric_type: "error_rate",
  condition: "gt",
  threshold: 0.05,
  window_minutes: 5,
  proxy_id: "",
  notify_email: true,
};

export function AlertsPage() {
  const { isAdmin } = useAuth();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState(emptyRule);

  const { data, isLoading } = useQuery({
    queryKey: ["metric-alerts"],
    queryFn: api.listMetricAlerts,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createMetricAlert({
        ...form,
        proxy_id: form.proxy_id || null,
      }),
    onSuccess: () => {
      showSuccess("Alert rule created");
      setForm(emptyRule);
      queryClient.invalidateQueries({ queryKey: ["metric-alerts"] });
    },
    onError: (error) => showError(error instanceof ApiError ? error.message : "Could not create rule"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteMetricAlert(id),
    onSuccess: () => {
      showSuccess("Alert rule deleted");
      queryClient.invalidateQueries({ queryKey: ["metric-alerts"] });
    },
    onError: (error) => showError(error instanceof ApiError ? error.message : "Could not delete rule"),
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    createMutation.mutate();
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Metric Alerts</h2>
        <p className="text-sm text-white/60">Configurable alert rules evaluated against aggregated metrics.</p>
      </div>

      {isAdmin ? (
        <Card title="Create rule">
          <form className="grid gap-3 md:grid-cols-2" onSubmit={handleSubmit}>
            <input
              className="rounded-lg bg-black/20 px-3 py-2 text-sm md:col-span-2"
              placeholder="Rule name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
            <select
              className="text-sm"
              value={form.metric_type}
              onChange={(e) => setForm({ ...form, metric_type: e.target.value })}
            >
              <option value="error_rate">Error rate</option>
              <option value="5xx_count">5xx count</option>
              <option value="response_time_ms">Response time</option>
              <option value="active_connections">Active connections</option>
              <option value="bandwidth">Bandwidth</option>
            </select>
            <input
              type="number"
              step="0.01"
              className="text-sm"
              value={form.threshold}
              onChange={(e) => setForm({ ...form, threshold: Number(e.target.value) })}
            />
            <input
              type="number"
              className="text-sm"
              value={form.window_minutes}
              onChange={(e) => setForm({ ...form, window_minutes: Number(e.target.value) })}
            />
            <input
              className="text-sm"
              placeholder="Proxy ID (optional)"
              value={form.proxy_id}
              onChange={(e) => setForm({ ...form, proxy_id: e.target.value })}
            />
            <Checkbox
              checked={form.notify_email}
              onChange={(checked) => setForm({ ...form, notify_email: checked })}
              label="Send email notification"
            />
            <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm md:col-span-2">
              Create alert rule
            </button>
          </form>
        </Card>
      ) : null}

      <Card title="Alert rules">
        <DataTable<MetricAlertRule>
          loading={isLoading}
          rows={data?.rules ?? []}
          rowKey={(row) => row.id}
          columns={[
            { key: "name", label: "Name" },
            { key: "metric_type", label: "Metric" },
            { key: "threshold", label: "Threshold" },
            { key: "window_minutes", label: "Window (min)" },
            { key: "severity", label: "Severity" },
            {
              key: "enabled",
              label: "Enabled",
              render: (row) => (row.enabled ? "Yes" : "No"),
            },
            {
              key: "actions",
              label: "Actions",
              render: (row) =>
                isAdmin ? (
                  <button
                    type="button"
                    className="rounded bg-red-600/70 px-2 py-1 text-xs"
                    onClick={() => deleteMutation.mutate(row.id)}
                  >
                    Delete
                  </button>
                ) : (
                  "—"
                ),
            },
          ]}
        />
      </Card>

      <Card title="Recent alert history">
        <DataTable
          loading={isLoading}
          rows={data?.history ?? []}
          rowKey={(row) => row.id}
          columns={[
            {
              key: "created_at",
              label: "Time",
              render: (row) => new Date(row.created_at).toLocaleString(),
            },
            { key: "alert_type", label: "Type" },
            { key: "severity", label: "Severity" },
            { key: "status", label: "Status" },
            { key: "message", label: "Message" },
          ]}
        />
      </Card>
    </div>
  );
}
