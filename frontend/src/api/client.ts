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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
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
  listUsers: () => request<import("../types").UserAccount[]>("/api/users"),
  createUser: (payload: unknown) =>
    request<import("../types").UserAccount>("/api/users", { method: "POST", body: JSON.stringify(payload) }),
  updateUser: (id: number, payload: unknown) =>
    request<import("../types").UserAccount>(`/api/users/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteUser: (id: number) => request<import("../types").MessageResponse>(`/api/users/${id}`, { method: "DELETE" }),
  listCertificates: () => request<import("../types").Certificate[]>("/api/certificates"),
  issueCertificate: (domain: string, email?: string) =>
    request<import("../types").MessageResponse>("/api/certificates", {
      method: "POST",
      body: JSON.stringify({ domain, email }),
    }),
  renewCertificate: (name: string) =>
    request<import("../types").MessageResponse>(`/api/certificates/${name}/renew`, { method: "POST" }),
  dryRunRenew: () =>
    request<import("../types").MessageResponse>("/api/certificates/actions/dry-run", { method: "POST" }),
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
};
