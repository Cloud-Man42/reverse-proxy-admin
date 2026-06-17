export interface ProxyRoute {
  path_prefix: string;
  target_protocol: "http" | "https";
  target_host: string;
  target_port: number;
  websocket_enabled: boolean;
}

export interface ProxyApp {
  id: string;
  name: string;
  config_file: string;
  domains: string[];
  routes: ProxyRoute[];
  target_protocol: "http" | "https";
  target_host: string;
  target_port: number;
  websocket_enabled: boolean;
  custom_headers: { name: string; value: string }[];
  max_body_size?: string | null;
  basic_auth_enabled: boolean;
  basic_auth_username?: string | null;
  basic_auth_password?: string | null;
  force_https: boolean;
  enabled: boolean;
  https_enabled: boolean;
  upstream: string;
  managed: boolean;
}

export interface Certificate {
  name: string;
  domains: string[];
  issuer: string;
  expiry: string;
  status: "valid" | "expiring" | "expired";
}

export interface CertificateSettings {
  default_email: string;
  email_configured: boolean;
}

export interface DashboardStats {
  active_proxies: number;
  inactive_proxies: number;
  nginx_active: boolean;
  expiring_certificates: number;
  recent_errors: string[];
}

export interface NetworkMapNode {
  id: string;
  type: string;
  label: string;
  subtitle?: string | null;
  status: string;
  metadata: Record<string, unknown>;
}

export interface NetworkMapEdge {
  id: string;
  source: string;
  target: string;
  label?: string | null;
}

export interface NetworkMapResponse {
  nodes: NetworkMapNode[];
  edges: NetworkMapEdge[];
  generated_at: string;
}

export interface SystemHealth {
  nginx_active: boolean;
  disk_total_gb: number;
  disk_used_gb: number;
  disk_free_gb: number;
  disk_percent: number;
}

export interface NginxStatus {
  active: boolean;
  output: string;
}

export interface NginxTestResult {
  success: boolean;
  output: string;
}

export interface LogLines {
  lines: string[];
  source: string;
}

export interface MessageResponse {
  message: string;
  detail?: string | null;
}

export interface LoginResponse {
  username: string;
  csrf_token: string;
  is_admin: boolean;
  permissions: UserPermissions;
}

export interface UserPermissions {
  is_admin: boolean;
  read: boolean;
  create: boolean;
  edit: boolean;
}

export interface UserAccount {
  id: number;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  perm_read: boolean;
  perm_create: boolean;
  perm_edit: boolean;
  created_at: string;
}

export interface UserFormData {
  username: string;
  password: string;
  is_active: boolean;
  is_admin: boolean;
  perm_read: boolean;
  perm_create: boolean;
  perm_edit: boolean;
}

export interface TrafficFlowCheck {
  name: string;
  success: boolean;
  message: string;
}

export interface TrafficFlowTestResult {
  success: boolean;
  summary: string;
  checks: TrafficFlowCheck[];
}

export interface TrafficDebugEntry {
  client_ip: string;
  timestamp: string;
  host: string;
  method: string;
  path: string;
  status: number;
  bytes_sent: number;
  forwarded_for?: string | null;
  user_agent?: string | null;
}

export interface TrafficDebugResponse {
  proxy_id: string;
  proxy_name: string;
  domains: string[];
  dedicated_log: boolean;
  source: string;
  entries: TrafficDebugEntry[];
}

export interface ProxyRouteFormData {
  path_prefix: string;
  target_protocol: "http" | "https";
  target_host: string;
  target_port: number;
  websocket_enabled: boolean;
}

export interface ProxyFormData {
  name: string;
  domains: string;
  routes: ProxyRouteFormData[];
  custom_headers: { name: string; value: string }[];
  max_body_size: string;
  basic_auth_enabled: boolean;
  basic_auth_username: string;
  basic_auth_password: string;
  force_https: boolean;
  enabled: boolean;
}
