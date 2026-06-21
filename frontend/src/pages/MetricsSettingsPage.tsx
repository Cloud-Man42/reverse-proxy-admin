import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { Checkbox } from "../components/Checkbox";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { MetricsSettings } from "../types";

export function MetricsSettingsPage() {
  const { isAdmin } = useAuth();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<MetricsSettings | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["metrics-settings"],
    queryFn: api.getMetricsSettings,
  });

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () => api.updateMetricsSettings(form),
    onSuccess: () => {
      showSuccess("Metrics settings saved");
      queryClient.invalidateQueries({ queryKey: ["metrics-settings"] });
    },
    onError: (error) => showError(error instanceof ApiError ? error.message : "Could not save settings"),
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (form) saveMutation.mutate();
  }

  if (isLoading || !form) {
    return <p>Loading metrics settings...</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Metrics Settings</h2>
        <p className="text-sm text-white/60">Retention, stub_status URL, and sampling configuration.</p>
      </div>

      <Card title="Collector settings">
        <form className="grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
          <div>
            <label className="mb-1 block text-sm">Raw event retention (days)</label>
            <input
              type="number"
              className="w-full rounded-lg bg-black/20 px-3 py-2 text-sm"
              value={form.raw_retention_days}
              disabled={!isAdmin}
              onChange={(e) => setForm({ ...form, raw_retention_days: Number(e.target.value) })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm">Minute metric retention (days)</label>
            <input
              type="number"
              className="w-full rounded-lg bg-black/20 px-3 py-2 text-sm"
              value={form.minute_retention_days}
              disabled={!isAdmin}
              onChange={(e) => setForm({ ...form, minute_retention_days: Number(e.target.value) })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm">Hour metric retention (days)</label>
            <input
              type="number"
              className="w-full rounded-lg bg-black/20 px-3 py-2 text-sm"
              value={form.hour_retention_days}
              disabled={!isAdmin}
              onChange={(e) => setForm({ ...form, hour_retention_days: Number(e.target.value) })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm">Request event sample rate</label>
            <input
              type="number"
              className="w-full rounded-lg bg-black/20 px-3 py-2 text-sm"
              value={form.request_event_sample_rate}
              disabled={!isAdmin}
              onChange={(e) => setForm({ ...form, request_event_sample_rate: Number(e.target.value) })}
            />
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-sm">NGINX stub_status URL</label>
            <input
              className="w-full rounded-lg bg-black/20 px-3 py-2 text-sm"
              value={form.stub_status_url}
              disabled={!isAdmin}
              onChange={(e) => setForm({ ...form, stub_status_url: e.target.value })}
              placeholder="http://127.0.0.1:8081/nginx_status"
            />
          </div>
          <Checkbox
            labelClassName="md:col-span-2"
            checked={form.enhanced_logging_default}
            disabled={!isAdmin}
            onChange={(checked) => setForm({ ...form, enhanced_logging_default: checked })}
            label="Enable enhanced JSON logging by default for new proxies"
          />
          {isAdmin ? (
            <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm md:col-span-2">
              Save settings
            </button>
          ) : null}
        </form>
      </Card>
    </div>
  );
}
