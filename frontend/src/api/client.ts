function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

let csrfToken: string | null = null;

export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const token = csrfToken || getCookie("nginx_admin_csrf");
  if (token && options.method && options.method !== "GET") {
    headers.set("X-CSRF-Token", token);
  }

  const response = await fetch(path, {
    ...options,
    credentials: "include",
    headers,
  });

  if (!response.ok) {
    let detail = "Request failed";
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      detail = await response.text();
    }
    throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  login: (username: string, password: string) =>
    request<import("../types").LoginResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  me: () => request<import("../types").LoginResponse>("/api/auth/me"),
  dashboard: () => request<import("../types").DashboardStats>("/api/dashboard"),
  networkMap: () => request<import("../types").NetworkMapResponse>("/api/dashboard/network-map"),
  listProxies: () => request<import("../types").ProxyApp[]>("/api/proxies"),
  getProxy: (id: string) => request<import("../types").ProxyApp>(`/api/proxies/${id}`),
  createProxy: (payload: unknown) =>
    request<import("../types").ProxyApp>("/api/proxies", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateProxy: (id: string, payload: unknown) =>
    request<import("../types").ProxyApp>(`/api/proxies/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteProxy: (id: string) =>
    request<import("../types").MessageResponse>(`/api/proxies/${id}`, { method: "DELETE" }),
  enableProxy: (id: string) =>
    request<import("../types").ProxyApp>(`/api/proxies/${id}/enable`, { method: "POST" }),
  disableProxy: (id: string) =>
    request<import("../types").ProxyApp>(`/api/proxies/${id}/disable`, { method: "POST" }),
  testConfig: () =>
    request<import("../types").NginxTestResult>("/api/proxies/actions/test-config", { method: "POST" }),
  testFlowDraft: (payload: unknown) =>
    request<import("../types").TrafficFlowTestResult>("/api/proxies/actions/test-flow", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  testFlowProxy: (id: string) =>
    request<import("../types").TrafficFlowTestResult>(`/api/proxies/${id}/test-flow`, { method: "POST" }),
  proxyTrafficDebug: (id: string, lines = 100) =>
    request<import("../types").TrafficDebugResponse>(`/api/proxies/${id}/traffic-debug?lines=${lines}`),
  proxyTrafficSummary: (range = "24h") =>
    request<import("../types").ProxyTrafficSummary[]>(`/api/proxies/traffic/summary?range=${range}`),
  proxyTrafficStats: (id: string, range = "24h") =>
    request<import("../types").ProxyTrafficStats>(`/api/proxies/${id}/traffic-stats?range=${range}`),
  analyticsSummary: (range = "24h") =>
    request<import("../types").AnalyticsSummaryResponse>(`/api/analytics/summary?range=${range}`),
  analyticsProxy: (id: string, range = "24h") =>
    request<import("../types").AnalyticsProxyDetail>(`/api/analytics/proxy-hosts/${id}?range=${range}`),
  listUsers: () => request<import("../types").UserAccount[]>("/api/users"),
  createUser: (payload: unknown) =>
    request<import("../types").UserAccount>("/api/users", { method: "POST", body: JSON.stringify(payload) }),
  updateUser: (id: number, payload: unknown) =>
    request<import("../types").UserAccount>(`/api/users/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteUser: (id: number) => request<import("../types").MessageResponse>(`/api/users/${id}`, { method: "DELETE" }),
  listCertificates: () => request<import("../types").Certificate[]>("/api/certificates"),
  certificateSettings: () => request<import("../types").CertificateSettings>("/api/certificates/settings"),
  issueCertificate: (domain: string, email?: string) =>
    request<import("../types").MessageResponse>("/api/certificates", {
      method: "POST",
      body: JSON.stringify({ domain, email }),
    }),
  renewCertificate: (name: string) =>
    request<import("../types").MessageResponse>(`/api/certificates/${name}/renew`, { method: "POST" }),
  dryRunRenew: () =>
    request<import("../types").MessageResponse>("/api/certificates/actions/dry-run", { method: "POST" }),
  importCertificate: (payload: {
    name: string;
    domain: string;
    certificate: File;
    privateKey: File;
    chain?: File | null;
  }) => {
    const form = new FormData();
    form.append("name", payload.name);
    form.append("domain", payload.domain);
    form.append("certificate", payload.certificate);
    form.append("private_key", payload.privateKey);
    if (payload.chain) {
      form.append("chain", payload.chain);
    }
    return request<import("../types").MessageResponse>("/api/certificates/import", {
      method: "POST",
      body: form,
    });
  },
  deleteCertificate: (name: string) =>
    request<import("../types").MessageResponse>(`/api/certificates/${encodeURIComponent(name)}`, { method: "DELETE" }),
  errorLogs: (lines = 200) => request<import("../types").LogLines>(`/api/logs/error?lines=${lines}`),
  accessLogs: (lines = 200, domain?: string) => {
    const params = new URLSearchParams({ lines: String(lines) });
    if (domain) params.set("domain", domain);
    return request<import("../types").LogLines>(`/api/logs/access?${params.toString()}`);
  },
  systemHealth: () => request<import("../types").SystemHealth>("/api/system/health"),
  nginxStatus: () => request<import("../types").NginxStatus>("/api/system/nginx/status"),
  nginxTest: () => request<import("../types").NginxTestResult>("/api/system/nginx/test", { method: "POST" }),
  nginxReload: () => request<import("../types").MessageResponse>("/api/system/nginx/reload", { method: "POST" }),
  listBackendPools: (proxyId?: string) =>
    request<import("../types").BackendPool[]>(
      proxyId ? `/api/backend-pools?proxy_id=${encodeURIComponent(proxyId)}` : "/api/backend-pools"
    ),
  getBackendPool: (id: number) => request<import("../types").BackendPool>(`/api/backend-pools/${id}`),
  createBackendPool: (payload: unknown) =>
    request<import("../types").BackendPool>("/api/backend-pools", { method: "POST", body: JSON.stringify(payload) }),
  updateBackendPool: (id: number, payload: unknown) =>
    request<import("../types").BackendPool>(`/api/backend-pools/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteBackendPool: (id: number) =>
    request<import("../types").MessageResponse>(`/api/backend-pools/${id}`, { method: "DELETE" }),
  listLoadBalancers: () => request<import("../types").LoadBalancerSummary[]>("/api/load-balancers"),
  listBackendServers: (poolId?: number) =>
    request<import("../types").BackendServer[]>(
      poolId ? `/api/backend-servers?pool_id=${poolId}` : "/api/backend-servers"
    ),
  createBackendServer: (payload: unknown) =>
    request<import("../types").BackendServer>("/api/backend-servers", { method: "POST", body: JSON.stringify(payload) }),
  updateBackendServer: (id: number, payload: unknown) =>
    request<import("../types").BackendServer>(`/api/backend-servers/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteBackendServer: (id: number) =>
    request<import("../types").MessageResponse>(`/api/backend-servers/${id}`, { method: "DELETE" }),
  healthDashboard: () => request<import("../types").HealthCheckDashboard>("/api/health-checks/dashboard"),
  healthHistory: (serverId: number, range = "24h") =>
    request<import("../types").HealthHistoryPoint[]>(`/api/health-checks/servers/${serverId}/history?range=${range}`),
  getSmtpSettings: () => request<import("../types").SmtpSettings>("/api/smtp"),
  updateSmtpSettings: (payload: unknown) =>
    request<import("../types").SmtpSettings>("/api/smtp", { method: "PUT", body: JSON.stringify(payload) }),
  testSmtpConnection: () =>
    request<import("../types").SmtpTestResult>("/api/smtp/test-connection", { method: "POST" }),
  sendSmtpTestEmail: (email: string) =>
    request<import("../types").SmtpTestResult>("/api/smtp/send-test", { method: "POST", body: JSON.stringify({ email }) }),
  listNotificationRecipients: () =>
    request<import("../types").NotificationRecipient[]>("/api/notifications/recipients"),
  createNotificationRecipient: (payload: unknown) =>
    request<import("../types").NotificationRecipient>("/api/notifications/recipients", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateNotificationRecipient: (id: number, payload: unknown) =>
    request<import("../types").NotificationRecipient>(`/api/notifications/recipients/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteNotificationRecipient: (id: number) =>
    request<import("../types").MessageResponse>(`/api/notifications/recipients/${id}`, { method: "DELETE" }),
  listNotificationLog: (page = 1, pageSize = 50) =>
    request<import("../types").NotificationLogEntry[]>(
      `/api/notifications/log?page=${page}&page_size=${pageSize}`
    ),
  getCertificateRenewalHistory: (certificateName?: string) => {
    const params = certificateName ? `?certificate_name=${encodeURIComponent(certificateName)}` : "";
    return request<import("../types").CertificateRenewalLogEntry[]>(`/api/certificates/renewal-history${params}`);
  },
  runHealthCheck: (serverId: number) =>
    request<import("../types").HealthCheckRunResult>(`/api/health-checks/servers/${serverId}/run`, {
      method: "POST",
    }),
  getSystemAlertThresholds: () => request<import("../types").SystemAlertThresholds>("/api/system-alerts/thresholds"),
  updateSystemAlertThresholds: (payload: unknown) =>
    request<import("../types").SystemAlertThresholds>("/api/system-alerts/thresholds", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  listAuditLogs: (page = 1) => request<import("../types").AuditLogList>(`/api/audit?page=${page}`),
  getStatusReportSettings: () => request<import("../types").StatusReportSettings>("/api/status-reports/settings"),
  updateStatusReportSettings: (payload: unknown) =>
    request<import("../types").StatusReportSettings>("/api/status-reports/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  sendStatusReport: () =>
    request<import("../types").MessageResponse>("/api/status-reports/send", { method: "POST" }),
  listTemplates: () => request<import("../types").ProxyTemplate[]>("/api/templates"),
  getTemplate: (slug: string) => request<import("../types").ProxyTemplate>(`/api/templates/${slug}`),
  listConfigVersions: (resourceType?: string, resourceId?: string) => {
    const params = new URLSearchParams();
    if (resourceType) params.set("resource_type", resourceType);
    if (resourceId) params.set("resource_id", resourceId);
    const query = params.toString();
    return request<import("../types").ConfigVersion[]>(`/api/config-versions${query ? `?${query}` : ""}`);
  },
  getConfigVersion: (id: number) =>
    request<import("../types").ConfigVersionDetail>(`/api/config-versions/${id}`),
  compareConfigVersions: (id1: number, id2: number) =>
    request<import("../types").ConfigVersionCompare>(
      `/api/config-versions/compare?id1=${id1}&id2=${id2}`
    ),
  rollbackConfigVersion: (id: number) =>
    request<import("../types").ConfigVersionRollbackResult>(`/api/config-versions/${id}/rollback`, {
      method: "POST",
    }),
  listApiTokenScopes: () => request<{ scopes: string[] }>("/api/api-tokens/scopes"),
  listApiTokens: () => request<import("../types").ApiToken[]>("/api/api-tokens"),
  createApiToken: (payload: unknown) =>
    request<import("../types").ApiTokenCreated>("/api/api-tokens", { method: "POST", body: JSON.stringify(payload) }),
  updateApiToken: (id: number, payload: unknown) =>
    request<import("../types").ApiToken>(`/api/api-tokens/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  revokeApiToken: (id: number) =>
    request<import("../types").MessageResponse>(`/api/api-tokens/${id}`, { method: "DELETE" }),
  listOrganizations: () => request<import("../types").Organization[]>("/api/organizations"),
  createOrganization: (payload: import("../types").OrganizationFormData) =>
    request<import("../types").Organization>("/api/organizations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateOrganization: (id: number, payload: Partial<import("../types").OrganizationFormData>) =>
    request<import("../types").Organization>(`/api/organizations/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteOrganization: (id: number) =>
    request<import("../types").MessageResponse>(`/api/organizations/${id}`, { method: "DELETE" }),
  listIpRules: (scope?: string, proxyId?: string) => {
    const params = new URLSearchParams();
    if (scope) params.set("scope", scope);
    if (proxyId) params.set("proxy_id", proxyId);
    const query = params.toString();
    return request<import("../types").IpAccessRule[]>(`/api/security/ip-rules${query ? `?${query}` : ""}`);
  },
  createIpRule: (payload: unknown) =>
    request<import("../types").IpAccessRule>("/api/security/ip-rules", { method: "POST", body: JSON.stringify(payload) }),
  updateIpRule: (id: number, payload: unknown) =>
    request<import("../types").IpAccessRule>(`/api/security/ip-rules/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteIpRule: (id: number) =>
    request<import("../types").MessageResponse>(`/api/security/ip-rules/${id}`, { method: "DELETE" }),
  listGeoRules: (proxyId?: string) => {
    const query = proxyId ? `?proxy_id=${encodeURIComponent(proxyId)}` : "";
    return request<import("../types").GeoRule[]>(`/api/security/geo-rules${query}`);
  },
  createGeoRule: (payload: unknown) =>
    request<import("../types").GeoRule>("/api/security/geo-rules", { method: "POST", body: JSON.stringify(payload) }),
  updateGeoRule: (id: number, payload: unknown) =>
    request<import("../types").GeoRule>(`/api/security/geo-rules/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteGeoRule: (id: number) =>
    request<import("../types").MessageResponse>(`/api/security/geo-rules/${id}`, { method: "DELETE" }),
  listThreatFeeds: () => request<import("../types").ThreatFeed[]>("/api/security/threat-feeds"),
  createThreatFeed: (payload: unknown) =>
    request<import("../types").ThreatFeed>("/api/security/threat-feeds", { method: "POST", body: JSON.stringify(payload) }),
  updateThreatFeed: (id: number, payload: unknown) =>
    request<import("../types").ThreatFeed>(`/api/security/threat-feeds/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteThreatFeed: (id: number) =>
    request<import("../types").MessageResponse>(`/api/security/threat-feeds/${id}`, { method: "DELETE" }),
  syncThreatFeed: (id: number) =>
    request<import("../types").ThreatFeed>(`/api/security/threat-feeds/${id}/sync`, { method: "POST" }),
  getWafSettings: (proxyId: string) =>
    request<import("../types").ProxyWafSettings>(`/api/security/waf/${proxyId}`),
  updateWafSettings: (proxyId: string, payload: unknown) =>
    request<import("../types").ProxyWafSettings>(`/api/security/waf/${proxyId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  listSecurityEvents: (page = 1, pageSize = 50) =>
    request<import("../types").SecurityEventList>(`/api/security/events?page=${page}&page_size=${pageSize}`),
  exportAuditLogs: (params: URLSearchParams) =>
    fetch(`/api/audit/export?${params.toString()}`, { credentials: "include" }),
  exportSecurityEvents: (params: URLSearchParams) =>
    fetch(`/api/security/events/export?${params.toString()}`, { credentials: "include" }),
  listAuditLogsFiltered: (page = 1, pageSize = 50, action?: string, resource?: string) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (action) params.set("action", action);
    if (resource) params.set("resource", resource);
    return request<import("../types").AuditLogList>(`/api/audit?${params.toString()}`);
  },
};
