import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { NotificationRecipient, SmtpSettings, SystemAlertThresholds } from "../types";

type Tab = "smtp" | "notifications" | "alerts";

export function SettingsPage() {
  const { isAdmin } = useAuth();
  const [tab, setTab] = useState<Tab>("smtp");
  if (!isAdmin) return <p className="text-amber-200">Admin access required.</p>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Settings</h2>
      <div className="flex gap-2">
        {(["smtp", "notifications", "alerts"] as Tab[]).map((item) => (
          <button
            key={item}
            type="button"
            className={`rounded-lg px-4 py-2 text-sm capitalize ${tab === item ? "bg-accent text-white" : "bg-white/10"}`}
            onClick={() => setTab(item)}
          >
            {item}
          </button>
        ))}
      </div>
      {tab === "smtp" && <SmtpTab />}
      {tab === "notifications" && <NotificationsTab />}
      {tab === "alerts" && <AlertsTab />}
    </div>
  );
}

function SmtpTab() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { data } = useQuery({ queryKey: ["smtp"], queryFn: api.getSmtpSettings });
  const [form, setForm] = useState<Partial<SmtpSettings & { password: string }>>({});
  const [testEmail, setTestEmail] = useState("");

  const save = useMutation({
    mutationFn: () =>
      api.updateSmtpSettings({
        host: current.host || "",
        port: current.port || 587,
        username: current.username || "",
        password: form.password || undefined,
        security_mode: current.security_mode || "starttls",
        sender_name: current.sender_name || "",
        sender_email: current.sender_email || "",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["smtp"] });
      showSuccess("SMTP settings saved");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Save failed"),
  });

  const testConn = useMutation({
    mutationFn: api.testSmtpConnection,
    onSuccess: (result) => showSuccess(result.message),
    onError: (e) => showError(e instanceof ApiError ? e.message : "Test failed"),
  });

  const sendTest = useMutation({
    mutationFn: () => api.sendSmtpTestEmail(testEmail),
    onSuccess: (result) => showSuccess(result.message),
    onError: (e) => showError(e instanceof ApiError ? e.message : "Send failed"),
  });

  const current = { ...data, ...form } as SmtpSettings & { password?: string };

  return (
    <Card title="SMTP Configuration">
      <form
        className="grid gap-4 md:grid-cols-2"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <label className="space-y-1 text-sm">
          SMTP Server
          <input className="w-full" value={current.host || ""} onChange={(e) => setForm({ ...form, host: e.target.value })} />
        </label>
        <label className="space-y-1 text-sm">
          SMTP Port
          <input type="number" className="w-full" value={current.port || 587} onChange={(e) => setForm({ ...form, port: Number(e.target.value) })} />
        </label>
        <label className="space-y-1 text-sm">
          Username
          <input className="w-full" value={current.username || ""} onChange={(e) => setForm({ ...form, username: e.target.value })} />
        </label>
        <label className="space-y-1 text-sm">
          Password {data?.password_set ? "(leave blank to keep)" : ""}
          <input type="password" className="w-full" onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </label>
        <label className="space-y-1 text-sm">
          Sender Name
          <input className="w-full" value={current.sender_name || ""} onChange={(e) => setForm({ ...form, sender_name: e.target.value })} />
        </label>
        <label className="space-y-1 text-sm">
          Sender Email
          <input className="w-full" value={current.sender_email || ""} onChange={(e) => setForm({ ...form, sender_email: e.target.value })} />
        </label>
        <label className="space-y-1 text-sm md:col-span-2">
          Encryption
          <select
            className="w-full"
            value={current.security_mode || "starttls"}
            onChange={(e) => {
              const mode = e.target.value as SmtpSettings["security_mode"];
              setForm({
                ...form,
                security_mode: mode,
                starttls_enabled: mode === "starttls",
                ssl_enabled: mode === "ssl",
              });
            }}
          >
            <option value="none">None (plain SMTP)</option>
            <option value="starttls">STARTTLS (recommended, e.g. port 587)</option>
            <option value="ssl">SSL / SMTPS (implicit TLS, e.g. port 465)</option>
          </select>
        </label>
        <p className="md:col-span-2 text-xs text-white/50">
          STARTTLS upgrades a plain connection with TLS after connect. SSL/SMTPS uses encrypted connection from the start.
        </p>
        <div className="md:col-span-2 flex flex-wrap items-center gap-3">
          <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm">Save</button>
          <button type="button" className="rounded-lg bg-white/10 px-4 py-2 text-sm" onClick={() => testConn.mutate()}>
            Test Connection
          </button>
          <input className="rounded-lg bg-black/20 px-3 py-2 text-sm" placeholder="test@example.com" value={testEmail} onChange={(e) => setTestEmail(e.target.value)} />
          <button type="button" className="rounded-lg bg-white/10 px-4 py-2 text-sm" onClick={() => sendTest.mutate()}>
            Send Test Email
          </button>
          <StatusBadge status={current.last_test_status === "connected" ? "running" : "unknown"} label={current.last_test_status || "unknown"} />
        </div>
      </form>
    </Card>
  );
}

function NotificationsTab() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { data = [] } = useQuery({ queryKey: ["notifications"], queryFn: api.listNotificationRecipients });
  const [form, setForm] = useState({ name: "", email: "", enabled: true, email_enabled: true, critical_only: false, all_notifications: true });

  const create = useMutation({
    mutationFn: () => api.createNotificationRecipient({ ...form, enabled_types: [] }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      setForm({ name: "", email: "", enabled: true, email_enabled: true, critical_only: false, all_notifications: true });
      showSuccess("Recipient added");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Create failed"),
  });

  return (
    <Card title="Notification Recipients">
      <form
        className="mb-4 grid gap-3 md:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <input className="rounded-lg bg-black/20 px-3 py-2 text-sm" placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className="rounded-lg bg-black/20 px-3 py-2 text-sm" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm">Add Recipient</button>
      </form>
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-white/60">
            <th className="py-2">Name</th>
            <th>Email</th>
            <th>Mode</th>
          </tr>
        </thead>
        <tbody>
          {data.map((recipient: NotificationRecipient) => (
            <tr key={recipient.id} className="border-t border-white/10">
              <td className="py-2">{recipient.name}</td>
              <td>{recipient.email}</td>
              <td>{recipient.critical_only ? "Critical only" : recipient.all_notifications ? "All" : "Custom"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function AlertsTab() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { data } = useQuery({ queryKey: ["alert-thresholds"], queryFn: api.getSystemAlertThresholds });
  const [form, setForm] = useState<Partial<SystemAlertThresholds>>({});

  const save = useMutation({
    mutationFn: () => api.updateSystemAlertThresholds({ ...data, ...form }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-thresholds"] });
      showSuccess("Thresholds saved");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Save failed"),
  });

  const current = { ...data, ...form } as SystemAlertThresholds;

  return (
    <Card title="System Alert Thresholds">
      <form
        className="grid gap-4 md:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <label className="space-y-1 text-sm">CPU %<input type="number" className="w-full" value={current.cpu_percent ?? 90} onChange={(e) => setForm({ ...form, cpu_percent: Number(e.target.value) })} /></label>
        <label className="space-y-1 text-sm">RAM %<input type="number" className="w-full" value={current.ram_percent ?? 90} onChange={(e) => setForm({ ...form, ram_percent: Number(e.target.value) })} /></label>
        <label className="space-y-1 text-sm">Disk %<input type="number" className="w-full" value={current.disk_percent ?? 90} onChange={(e) => setForm({ ...form, disk_percent: Number(e.target.value) })} /></label>
        <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm md:col-span-3 w-fit">Save Thresholds</button>
      </form>
    </Card>
  );
}
