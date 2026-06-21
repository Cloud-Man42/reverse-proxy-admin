import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { Checkbox } from "../components/Checkbox";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { GeoRule, IpAccessRule, ProxyWafSettings, ThreatFeed } from "../types";

const COUNTRY_OPTIONS = [
  "US", "CA", "GB", "DE", "FR", "NL", "AU", "JP", "CN", "RU", "BR", "IN", "KR", "IT", "ES", "SE", "NO", "PL", "UA", "IR",
];

type Tab = "ip-rules" | "geo" | "threat-feeds" | "waf" | "events";

export function SecurityPage() {
  const { isAdmin } = useAuth();
  const [tab, setTab] = useState<Tab>("ip-rules");

  if (!isAdmin) return <p className="text-amber-200">Admin access required.</p>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Security</h2>
      <div className="flex flex-wrap gap-2">
        {(
          [
            ["ip-rules", "IP rules"],
            ["geo", "Geo blocking"],
            ["threat-feeds", "Threat feeds"],
            ["waf", "WAF"],
            ["events", "Events"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`rounded-lg px-4 py-2 text-sm ${tab === id ? "bg-accent text-white" : "bg-white/10"}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "ip-rules" && <IpRulesSection />}
      {tab === "geo" && <GeoRulesSection />}
      {tab === "threat-feeds" && <ThreatFeedsSection />}
      {tab === "waf" && <WafSection />}
      {tab === "events" && <EventsSection />}
    </div>
  );
}

function IpRulesSection() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { data: rules = [] } = useQuery({ queryKey: ["ip-rules"], queryFn: () => api.listIpRules() });
  const { data: proxies = [] } = useQuery({ queryKey: ["proxies"], queryFn: api.listProxies });
  const [form, setForm] = useState({
    scope: "global" as "global" | "proxy",
    proxy_id: "",
    rule_type: "deny" as "allow" | "deny",
    cidr: "",
    enabled: true,
    notes: "",
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createIpRule({
        ...form,
        proxy_id: form.scope === "proxy" ? form.proxy_id : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ip-rules"] });
      setForm({ scope: "global", proxy_id: "", rule_type: "deny", cidr: "", enabled: true, notes: "" });
      showSuccess("IP rule created");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Failed"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteIpRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ip-rules"] });
      showSuccess("Rule deleted");
    },
  });

  return (
    <div className="space-y-4">
      <Card title="Add IP rule">
        <form
          className="grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            createMutation.mutate();
          }}
        >
          <label className="text-sm">
            Scope
            <select
              className="mt-1 w-full rounded-lg bg-white/10 px-3 py-2"
              value={form.scope}
              onChange={(e) => setForm({ ...form, scope: e.target.value as "global" | "proxy" })}
            >
              <option value="global">Global</option>
              <option value="proxy">Per proxy</option>
            </select>
          </label>
          {form.scope === "proxy" && (
            <label className="text-sm">
              Proxy
              <select
                className="mt-1 w-full rounded-lg bg-white/10 px-3 py-2"
                value={form.proxy_id}
                onChange={(e) => setForm({ ...form, proxy_id: e.target.value })}
              >
                <option value="">Select proxy</option>
                {proxies.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="text-sm">
            Type
            <select
              className="mt-1 w-full rounded-lg bg-white/10 px-3 py-2"
              value={form.rule_type}
              onChange={(e) => setForm({ ...form, rule_type: e.target.value as "allow" | "deny" })}
            >
              <option value="allow">Allow</option>
              <option value="deny">Deny</option>
            </select>
          </label>
          <label className="text-sm">
            CIDR
            <input
              className="mt-1 w-full rounded-lg bg-white/10 px-3 py-2"
              value={form.cidr}
              onChange={(e) => setForm({ ...form, cidr: e.target.value })}
              placeholder="10.0.0.0/8"
              required
            />
          </label>
          <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm text-white md:col-span-2">
            Add rule
          </button>
        </form>
      </Card>
      <Card title="IP allow/block rules">
        <div className="space-y-2">
          {rules.map((rule: IpAccessRule) => (
            <div key={rule.id} className="flex items-center justify-between rounded-lg bg-white/5 px-3 py-2 text-sm">
              <div>
                <StatusBadge status={rule.rule_type === "allow" ? "healthy" : "offline"} label={rule.rule_type} />
                <span className="ml-2">{rule.cidr}</span>
                <span className="ml-2 text-white/50">
                  ({rule.scope}
                  {rule.proxy_id ? `: ${rule.proxy_id}` : ""})
                </span>
              </div>
              <button className="text-red-300 hover:text-red-200" onClick={() => deleteMutation.mutate(rule.id)}>
                Delete
              </button>
            </div>
          ))}
          {!rules.length && <p className="text-sm text-white/60">No IP rules configured.</p>}
        </div>
      </Card>
    </div>
  );
}

function GeoRulesSection() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { data: rules = [] } = useQuery({ queryKey: ["geo-rules"], queryFn: () => api.listGeoRules() });
  const { data: proxies = [] } = useQuery({ queryKey: ["proxies"], queryFn: api.listProxies });
  const [form, setForm] = useState({
    proxy_id: "",
    mode: "block" as "block" | "allow",
    countries: [] as string[],
    enabled: true,
  });

  const createMutation = useMutation({
    mutationFn: () => api.createGeoRule(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["geo-rules"] });
      showSuccess("Geo rule created");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Failed"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteGeoRule(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["geo-rules"] }),
  });

  const toggleCountry = (code: string) => {
    setForm((prev) => ({
      ...prev,
      countries: prev.countries.includes(code)
        ? prev.countries.filter((c) => c !== code)
        : [...prev.countries, code],
    }));
  };

  return (
    <div className="space-y-4">
      <Card title="Add geo rule">
        <form
          className="space-y-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            createMutation.mutate();
          }}
        >
          <label className="block text-sm">
            Proxy
            <select
              className="mt-1 w-full rounded-lg bg-white/10 px-3 py-2"
              value={form.proxy_id}
              onChange={(e) => setForm({ ...form, proxy_id: e.target.value })}
              required
            >
              <option value="">Select proxy</option>
              {proxies.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            Mode
            <select
              className="mt-1 w-full rounded-lg bg-white/10 px-3 py-2"
              value={form.mode}
              onChange={(e) => setForm({ ...form, mode: e.target.value as "block" | "allow" })}
            >
              <option value="block">Block selected countries</option>
              <option value="allow">Allow only selected countries</option>
            </select>
          </label>
          <div>
            <p className="text-sm text-white/70">Countries</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {COUNTRY_OPTIONS.map((code) => (
                <button
                  key={code}
                  type="button"
                  className={`rounded px-2 py-1 text-xs ${form.countries.includes(code) ? "bg-accent text-white" : "bg-white/10"}`}
                  onClick={() => toggleCountry(code)}
                >
                  {code}
                </button>
              ))}
            </div>
          </div>
          <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm text-white">
            Save geo rule
          </button>
        </form>
      </Card>
      <Card title="Geo rules">
        {rules.map((rule: GeoRule) => (
          <div key={rule.id} className="mb-2 flex items-center justify-between rounded-lg bg-white/5 px-3 py-2 text-sm">
            <div>
              <strong>{rule.proxy_id}</strong> — {rule.mode}: {rule.countries.join(", ") || "none"}
            </div>
            <button className="text-red-300" onClick={() => deleteMutation.mutate(rule.id)}>
              Delete
            </button>
          </div>
        ))}
        {!rules.length && <p className="text-sm text-white/60">No geo rules. Requires GeoIP2 module — see deploy/setup-geoip.sh</p>}
      </Card>
    </div>
  );
}

function ThreatFeedsSection() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const { data: feeds = [] } = useQuery({ queryKey: ["threat-feeds"], queryFn: api.listThreatFeeds });
  const [form, setForm] = useState({ name: "", url: "", feed_type: "cidr" as "cidr" | "ip", enabled: true });

  const createMutation = useMutation({
    mutationFn: () => api.createThreatFeed(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["threat-feeds"] });
      setForm({ name: "", url: "", feed_type: "cidr", enabled: true });
      showSuccess("Threat feed added");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Failed"),
  });

  const syncMutation = useMutation({
    mutationFn: (id: number) => api.syncThreatFeed(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["threat-feeds"] });
      showSuccess("Feed synced");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Sync failed"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteThreatFeed(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["threat-feeds"] }),
  });

  return (
    <div className="space-y-4">
      <Card title="Add threat feed">
        <form
          className="grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            createMutation.mutate();
          }}
        >
          <input
            className="rounded-lg bg-white/10 px-3 py-2 text-sm"
            placeholder="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <input
            className="rounded-lg bg-white/10 px-3 py-2 text-sm md:col-span-2"
            placeholder="URL"
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
            required
          />
          <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm text-white md:col-span-2">
            Add feed
          </button>
        </form>
      </Card>
      <Card title="Threat feeds">
        {feeds.map((feed: ThreatFeed) => (
          <div key={feed.id} className="mb-2 flex items-center justify-between rounded-lg bg-white/5 px-3 py-2 text-sm">
            <div>
              <strong>{feed.name}</strong> — {feed.ip_count} IPs
              {feed.last_error && <span className="ml-2 text-red-300">{feed.last_error}</span>}
            </div>
            <div className="flex gap-2">
              <button className="text-accent" onClick={() => syncMutation.mutate(feed.id)}>
                Sync
              </button>
              <button className="text-red-300" onClick={() => deleteMutation.mutate(feed.id)}>
                Delete
              </button>
            </div>
          </div>
        ))}
        {!feeds.length && <p className="text-sm text-white/60">No threat feeds configured.</p>}
      </Card>
    </div>
  );
}

function WafSection() {
  const { showSuccess, showError } = useToast();
  const { data: proxies = [] } = useQuery({ queryKey: ["proxies"], queryFn: api.listProxies });
  const [proxyId, setProxyId] = useState("");
  const { data: waf, refetch } = useQuery({
    queryKey: ["waf", proxyId],
    queryFn: () => api.getWafSettings(proxyId),
    enabled: Boolean(proxyId),
  });
  const [form, setForm] = useState<ProxyWafSettings | null>(null);

  const effective = form ?? waf;

  const saveMutation = useMutation({
    mutationFn: () => api.updateWafSettings(proxyId, effective),
    onSuccess: () => {
      refetch();
      showSuccess("WAF settings saved");
    },
    onError: (e) => showError(e instanceof ApiError ? e.message : "Failed"),
  });

  return (
    <Card title="WAF settings (ModSecurity)">
      <p className="mb-3 text-sm text-white/60">Requires ModSecurity — see deploy/setup-modsecurity.sh</p>
      <label className="block text-sm">
        Proxy
        <select
          className="mt-1 w-full rounded-lg bg-white/10 px-3 py-2"
          value={proxyId}
          onChange={(e) => {
            setProxyId(e.target.value);
            setForm(null);
          }}
        >
          <option value="">Select proxy</option>
          {proxies.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      {effective && (
        <div className="mt-4 space-y-3">
          <Checkbox
            checked={effective.enabled}
            onChange={(checked) => setForm({ ...effective, enabled: checked })}
            label="Enabled"
          />
          <label className="block text-sm">
            Mode
            <select
              className="mt-1 w-full rounded-lg bg-white/10 px-3 py-2"
              value={effective.mode}
              onChange={(e) => setForm({ ...effective, mode: e.target.value as ProxyWafSettings["mode"] })}
            >
              <option value="detection">Detection only</option>
              <option value="blocking">Blocking</option>
            </select>
          </label>
          <label className="block text-sm">
            Profile
            <select
              className="mt-1 w-full rounded-lg bg-white/10 px-3 py-2"
              value={effective.profile}
              onChange={(e) => setForm({ ...effective, profile: e.target.value as ProxyWafSettings["profile"] })}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
          <button
            type="button"
            className="rounded-lg bg-accent px-4 py-2 text-sm text-white"
            onClick={() => saveMutation.mutate()}
          >
            Save WAF settings
          </button>
        </div>
      )}
    </Card>
  );
}

function EventsSection() {
  const [page, setPage] = useState(1);
  const { data } = useQuery({
    queryKey: ["security-events", page],
    queryFn: () => api.listSecurityEvents(page),
  });

  const exportEvents = async (format: "csv" | "json") => {
    const params = new URLSearchParams({ format });
    const response = await api.exportSecurityEvents(params);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = format === "csv" ? "security-events.csv" : "security-events.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button className="rounded-lg bg-white/10 px-3 py-2 text-sm" onClick={() => exportEvents("csv")}>
          Export CSV
        </button>
        <button className="rounded-lg bg-white/10 px-3 py-2 text-sm" onClick={() => exportEvents("json")}>
          Export JSON
        </button>
      </div>
      <Card title="Security events">
        <div className="space-y-2">
          {data?.items.map((event) => (
            <div key={event.id} className="rounded-lg bg-white/5 px-3 py-2 text-sm">
              <div className="flex flex-wrap gap-2">
                <StatusBadge status="warning" label={event.event_type} />
                <span className="text-white/50">{event.source}</span>
                <span className="text-white/50">{new Date(event.created_at).toLocaleString()}</span>
              </div>
              <p className="mt-1">{event.message}</p>
              {event.client_ip && <p className="text-white/50">IP: {event.client_ip}</p>}
            </div>
          ))}
          {!data?.items.length && <p className="text-sm text-white/60">No security events yet.</p>}
        </div>
        {data && data.total > data.page_size && (
          <div className="mt-4 flex gap-2">
            <button
              className="rounded bg-white/10 px-3 py-1 text-sm disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <button
              className="rounded bg-white/10 px-3 py-1 text-sm disabled:opacity-40"
              disabled={page * data.page_size >= data.total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        )}
      </Card>
    </div>
  );
}
