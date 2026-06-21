import { Link } from "react-router-dom";
import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { Checkbox } from "../components/Checkbox";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { NotificationEventType, NotificationRecipient, SmtpSettings, StatusReportSection, StatusReportSettings, SystemAlertThresholds } from "../types";

const NOTIFICATION_EVENT_OPTIONS: { id: NotificationEventType; label: string }[] = [
  { id: "backend_offline", label: "Backend offline" },
  { id: "backend_restored", label: "Backend restored" },
  { id: "ssl_expiring", label: "SSL expiring" },
  { id: "ssl_renewed", label: "SSL renewed" },
  { id: "proxy_created", label: "Proxy created" },
  { id: "proxy_modified", label: "Proxy modified" },
  { id: "proxy_deleted", label: "Proxy deleted" },
  { id: "nginx_validation_failed", label: "Nginx validation failed" },
  { id: "nginx_reload_failed", label: "Nginx reload failed" },
  { id: "system_error", label: "System error" },
  { id: "login_security", label: "Login security" },
  { id: "status_report", label: "Status report" },
];

type RecipientFormData = {
  name: string;
  email: string;
  enabled: boolean;
  email_enabled: boolean;
  critical_only: boolean;
  all_notifications: boolean;
  enabled_types: NotificationEventType[];
};

const emptyRecipientForm = (): RecipientFormData => ({
  name: "",
  email: "",
  enabled: true,
  email_enabled: true,
  critical_only: false,
  all_notifications: true,
  enabled_types: [],
});

type Tab = "smtp" | "notifications" | "alerts" | "reports" | "api-tokens";

export function SettingsPage() {
  const { isAdmin } = useAuth();
  const [tab, setTab] = useState<Tab>("smtp");
  if (!isAdmin) return <p className="text-amber-200">Admin access required.</p>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Settings</h2>
      <div className="flex gap-2">
        {(["smtp", "notifications", "alerts", "reports", "api-tokens"] as Tab[]).map((item) => (
          <button
            key={item}
            type="button"
            className={`rounded-lg px-4 py-2 text-sm capitalize ${tab === item ? "bg-accent text-white" : "bg-white/10"}`}
            onClick={() => setTab(item)}
          >
            {item === "api-tokens" ? "API tokens" : item}
          </button>
        ))}
      </div>
      {tab === "smtp" && <SmtpTab />}
      {tab === "notifications" && <NotificationsTab />}
      {tab === "alerts" && <AlertsTab />}
      {tab === "reports" && <StatusReportsTab />}
      {tab === "api-tokens" && (
        <Card title="API tokens">
          <p className="mb-3 text-sm text-white/70">
            Manage Bearer tokens for programmatic access to the public REST API.
          </p>
          <Link className="rounded-lg bg-accent px-4 py-2 text-sm text-white" to="/api-tokens">
            Open API tokens
          </Link>
        </Card>
      )}
    </div>
  );
}

function SmtpTab() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { data, isLoading, isError, error } = useQuery({ queryKey: ["smtp"], queryFn: api.getSmtpSettings });
  const [form, setForm] = useState<Partial<SmtpSettings & { password: string }>>({});
  const [testEmail, setTestEmail] = useState("");

  const save = useMutation({
    mutationFn: () => {
      if (!data) {
        throw new Error("SMTP settings are still loading");
      }
      const password = form.password?.trim();
      return api.updateSmtpSettings({
        host: current.host || "",
        port: current.port || 587,
        username: current.username || "",
        password: password ? password : undefined,
        security_mode: current.security_mode || "starttls",
        sender_name: current.sender_name || "",
        sender_email: current.sender_email || "",
        default_recipient_email: current.default_recipient_email || "",
        tls_server_name: current.tls_server_name || "",
        verify_tls_certificate: current.verify_tls_certificate ?? true,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["smtp"] });
      setForm({});
      showSuccess("SMTP settings saved");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Save failed"),
  });

  const testConn = useMutation({
    mutationFn: api.testSmtpConnection,
    onSuccess: (result) => showSuccess(result.message),
    onError: (e) => showError(e instanceof ApiError ? e.message : "Test failed"),
  });

  const sendTest = useMutation({
    mutationFn: () => api.sendSmtpTestEmail(testEmail.trim() || undefined),
    onSuccess: (result) => showSuccess(result.message),
    onError: (e) => showError(e instanceof ApiError ? e.message : "Send failed"),
  });

  const current = { ...data, ...form } as SmtpSettings & { password?: string };

  useEffect(() => {
    if (data?.default_recipient_email && !testEmail) {
      setTestEmail(data.default_recipient_email);
    }
  }, [data?.default_recipient_email, testEmail]);

  return (
    <Card title="SMTP Configuration">
      {isError ? (
        <p className="mb-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-100">
          Failed to load SMTP settings: {error instanceof ApiError ? error.message : "Unknown error"}
        </p>
      ) : null}
      <form
        className="grid gap-4 md:grid-cols-2"
        autoComplete="off"
        noValidate
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <input type="text" tabIndex={-1} autoComplete="username" className="hidden" aria-hidden="true" />
        <input type="password" tabIndex={-1} autoComplete="current-password" className="hidden" aria-hidden="true" />
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
          <input
            className="w-full"
            name="smtp-username"
            autoComplete="off"
            spellCheck={false}
            readOnly={isLoading}
            onFocus={(e) => e.currentTarget.removeAttribute("readonly")}
            value={current.username || ""}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            disabled={isLoading || !data}
          />
        </label>
        <label className="space-y-1 text-sm">
          Password {data?.password_set ? "(leave blank to keep saved password)" : ""}
          <input
            type="password"
            className="w-full"
            name="smtp-password"
            autoComplete="new-password"
            placeholder={data?.password_set ? "Saved password is stored securely" : ""}
            value={form.password ?? ""}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            disabled={isLoading || !data}
          />
        </label>
        <label className="space-y-1 text-sm">
          Sender Name
          <input className="w-full" value={current.sender_name || ""} onChange={(e) => setForm({ ...form, sender_name: e.target.value })} />
        </label>
        <label className="space-y-1 text-sm">
          Sender Email
          <input
            type="text"
            inputMode="email"
            className="w-full"
            placeholder="Leave blank to use SMTP username"
            value={current.sender_email || ""}
            onChange={(e) => setForm({ ...form, sender_email: e.target.value })}
          />
        </label>
        <label className="space-y-1 text-sm">
          Default Notification Recipient
          <input
            type="text"
            inputMode="email"
            className="w-full"
            placeholder="alerts@yourdomain.com"
            value={current.default_recipient_email || ""}
            onChange={(e) => setForm({ ...form, default_recipient_email: e.target.value })}
            required
          />
        </label>
        <label className="space-y-1 text-sm">
          TLS Server Name
          <input
            className="w-full"
            placeholder="e.g. mail.example.com when host is an IP address"
            value={current.tls_server_name || ""}
            onChange={(e) => setForm({ ...form, tls_server_name: e.target.value })}
          />
        </label>
        <Checkbox
          labelClassName="md:col-span-2"
          checked={current.verify_tls_certificate ?? true}
          onChange={(checked) => setForm({ ...form, verify_tls_certificate: checked })}
          label="Verify TLS certificate (disable only for trusted internal SMTP servers)"
        />
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
          Default notification recipient receives all proxy alerts, status reports, and other outgoing emails unless
          additional recipients are configured under Notifications.
        </p>
        <p className="md:col-span-2 text-xs text-white/50">
          If SMTP host is an IP address (for example 192.168.1.55), enter the hostname shown on the mail server
          certificate in TLS Server Name. For internal servers with self-signed certificates, you can disable
          certificate verification.
        </p>
        <p className="md:col-span-2 text-xs text-white/50">
          STARTTLS upgrades a plain connection with TLS after connect. SSL/SMTPS uses encrypted connection from the start.
        </p>
        <div className="md:col-span-2 flex flex-wrap items-center gap-3">
          <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm" disabled={isLoading || !data || save.isPending}>
            Save
          </button>
          <button type="button" className="rounded-lg bg-white/10 px-4 py-2 text-sm" onClick={() => testConn.mutate()}>
            Test Connection
          </button>
          <input className="rounded-lg bg-black/20 px-3 py-2 text-sm" placeholder="Override test recipient (optional)" value={testEmail} onChange={(e) => setTestEmail(e.target.value)} />
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
  const { data: notificationLog = [] } = useQuery({
    queryKey: ["notification-log"],
    queryFn: () => api.listNotificationLog(1, 50),
  });
  const [form, setForm] = useState<RecipientFormData>(emptyRecipientForm());
  const [editing, setEditing] = useState<NotificationRecipient | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const resetForm = () => {
    setForm(emptyRecipientForm());
    setEditing(null);
  };

  const save = useMutation({
    mutationFn: () => {
      const payload = {
        name: form.name,
        email: form.email,
        enabled: form.enabled,
        email_enabled: form.email_enabled,
        critical_only: form.critical_only,
        all_notifications: form.all_notifications,
        enabled_types: form.all_notifications ? [] : form.enabled_types,
      };
      if (editing) return api.updateNotificationRecipient(editing.id, payload);
      return api.createNotificationRecipient(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      resetForm();
      showSuccess(editing ? "Recipient updated" : "Recipient added");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Save failed"),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteNotificationRecipient(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      setDeleteId(null);
      showSuccess("Recipient deleted");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Delete failed"),
  });

  const openEdit = (recipient: NotificationRecipient) => {
    setEditing(recipient);
    setForm({
      name: recipient.name,
      email: recipient.email,
      enabled: recipient.enabled,
      email_enabled: recipient.email_enabled,
      critical_only: recipient.critical_only,
      all_notifications: recipient.all_notifications,
      enabled_types: recipient.enabled_types as NotificationEventType[],
    });
  };

  const toggleEventType = (eventType: NotificationEventType) => {
    const types = new Set(form.enabled_types);
    if (types.has(eventType)) types.delete(eventType);
    else types.add(eventType);
    setForm({ ...form, enabled_types: Array.from(types) });
  };

  return (
    <div className="space-y-6">
      <Card title={editing ? "Edit recipient" : "Add recipient"}>
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <input className="rounded-lg bg-black/20 px-3 py-2 text-sm" placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            <input className="rounded-lg bg-black/20 px-3 py-2 text-sm" placeholder="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </div>
          <div className="ui-checkbox-group">
            <Checkbox checked={form.enabled} onChange={(checked) => setForm({ ...form, enabled: checked })} label="Enabled" />
            <Checkbox
              checked={form.email_enabled}
              onChange={(checked) => setForm({ ...form, email_enabled: checked })}
              label="Email enabled"
            />
            <Checkbox
              checked={form.critical_only}
              onChange={(checked) => setForm({ ...form, critical_only: checked })}
              label="Critical only"
            />
            <Checkbox
              checked={form.all_notifications}
              onChange={(checked) =>
                setForm({ ...form, all_notifications: checked, enabled_types: checked ? [] : form.enabled_types })
              }
              label="All notification types"
            />
          </div>
          {!form.all_notifications ? (
            <div>
              <p className="mb-2 text-sm font-medium">Event types</p>
              <div className="ui-checkbox-grid">
                {NOTIFICATION_EVENT_OPTIONS.map((option) => (
                  <Checkbox
                    key={option.id}
                    checked={form.enabled_types.includes(option.id)}
                    onChange={() => toggleEventType(option.id)}
                    label={option.label}
                  />
                ))}
              </div>
            </div>
          ) : null}
          <div className="flex gap-2">
            <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm">
              {editing ? "Update recipient" : "Add recipient"}
            </button>
            {editing ? (
              <button type="button" className="rounded-lg bg-white/10 px-4 py-2 text-sm" onClick={resetForm}>
                Cancel
              </button>
            ) : null}
          </div>
        </form>
      </Card>

      <Card title="Notification Recipients">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-white/60">
              <th className="py-2">Name</th>
              <th>Email</th>
              <th>Mode</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.map((recipient: NotificationRecipient) => (
              <tr key={recipient.id} className="border-t border-white/10">
                <td className="py-2">{recipient.name}</td>
                <td>{recipient.email}</td>
                <td>{recipient.critical_only ? "Critical only" : recipient.all_notifications ? "All" : "Custom"}</td>
                <td>
                  <StatusBadge status={recipient.enabled && recipient.email_enabled ? "running" : "stopped"} label={recipient.enabled && recipient.email_enabled ? "Active" : "Inactive"} />
                </td>
                <td className="space-x-2 text-right">
                  <button type="button" className="rounded bg-white/10 px-2 py-1 text-xs" onClick={() => openEdit(recipient)}>
                    Edit
                  </button>
                  <button type="button" className="rounded bg-red-600/70 px-2 py-1 text-xs text-white" onClick={() => setDeleteId(recipient.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="Notification log">
        {notificationLog.length === 0 ? (
          <p className="text-sm text-white/50">No notifications sent yet.</p>
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-white/60">
                <th className="py-2">Time</th>
                <th>Event</th>
                <th>Recipient</th>
                <th>Subject</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {notificationLog.map((entry) => (
                <tr key={entry.id} className="border-t border-white/10">
                  <td className="py-2">{new Date(entry.created_at).toLocaleString()}</td>
                  <td>{entry.event_type.replace(/_/g, " ")}</td>
                  <td>{entry.recipient_email}</td>
                  <td>{entry.subject}</td>
                  <td>
                    <StatusBadge status={entry.status === "sent" ? "running" : "warning"} label={entry.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {deleteId !== null ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-xl border border-white/10 bg-surface-muted p-6">
            <h3 className="text-lg font-semibold">Delete recipient?</h3>
            <p className="mt-2 text-sm text-white/70">This recipient will stop receiving notifications.</p>
            <div className="mt-6 flex justify-end gap-3">
              <button className="rounded-lg px-4 py-2 text-sm hover:bg-white/10" onClick={() => setDeleteId(null)}>
                Cancel
              </button>
              <button className="rounded-lg bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-500" onClick={() => remove.mutate(deleteId)}>
                Delete
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function StatusReportsTab() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { data } = useQuery({ queryKey: ["status-reports"], queryFn: api.getStatusReportSettings });
  const [form, setForm] = useState<Partial<StatusReportSettings>>({});

  const sectionOptions: { id: StatusReportSection; label: string; description: string }[] = [
    { id: "proxy_traffic", label: "Proxy traffic", description: "Bytes in/out and connections per proxy (24h)" },
    { id: "proxy_status", label: "Proxy status", description: "Enabled/disabled state, HTTPS, routes" },
    { id: "load_balancer_health", label: "Load balancer health", description: "Backend pool health and offline servers" },
    { id: "ssl_certificates", label: "SSL certificates", description: "Certificate expiry summary" },
    { id: "system_metrics", label: "System metrics", description: "CPU, RAM, and disk usage" },
  ];

  const save = useMutation({
    mutationFn: () =>
      api.updateStatusReportSettings({
        enabled: current.enabled,
        interval_hours: current.interval_hours,
        enabled_sections: current.enabled_sections,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["status-reports"] });
      showSuccess("Status report settings saved");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Save failed"),
  });

  const sendNow = useMutation({
    mutationFn: api.sendStatusReport,
    onSuccess: (result) => showSuccess(result.message),
    onError: (e) => showError(e instanceof ApiError ? e.message : "Send failed"),
  });

  const current = {
    enabled: false,
    interval_hours: 24,
    enabled_sections: sectionOptions.map((item) => item.id),
    ...data,
    ...form,
  } as StatusReportSettings;

  const toggleSection = (section: StatusReportSection) => {
    const sections = new Set(current.enabled_sections || []);
    if (sections.has(section)) sections.delete(section);
    else sections.add(section);
    setForm({ ...form, enabled_sections: Array.from(sections) });
  };

  return (
    <Card title="Email Status Reports">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <Checkbox
          checked={current.enabled}
          onChange={(checked) => setForm({ ...form, enabled: checked })}
          label="Enable scheduled status report emails"
        />
        <label className="block space-y-1 text-sm">
          Send interval (hours)
          <input
            type="number"
            min={1}
            max={168}
            className="w-full max-w-xs"
            value={current.interval_hours}
            onChange={(e) => setForm({ ...form, interval_hours: Number(e.target.value) })}
          />
        </label>
        <div>
          <p className="mb-2 text-sm font-medium">Include in report</p>
          <div className="ui-checkbox-grid">
            {sectionOptions.map((section) => (
              <Checkbox
                key={section.id}
                variant="card"
                checked={current.enabled_sections?.includes(section.id) ?? false}
                onChange={() => toggleSection(section.id)}
                label={section.label}
                description={section.description}
              />
            ))}
          </div>
        </div>
        <p className="text-xs text-white/50">
          Reports are sent to the default SMTP recipient and any notification recipients with email enabled.
        </p>
        {data?.last_sent_at ? (
          <p className="text-xs text-white/50">Last sent: {new Date(data.last_sent_at).toLocaleString()}</p>
        ) : null}
        <div className="flex flex-wrap gap-3">
          <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm">
            Save
          </button>
          <button type="button" className="rounded-lg bg-white/10 px-4 py-2 text-sm" onClick={() => sendNow.mutate()}>
            Send report now
          </button>
        </div>
      </form>
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
