export interface ProxyRoute {
  path_prefix: string;
  target_protocol: "http" | "https";
  target_host: string;
  target_port: number;
  websocket_enabled: boolean;
  backend_pool_id?: number | null;
}

export type LoadBalancingMethod = "round_robin" | "least_conn" | "ip_hash" | "random" | "weighted";
export type BackendRole = "primary" | "backup";
export type HealthStatus = "healthy" | "warning" | "offline" | "unknown";
export type HealthCheckType = "tcp" | "http" | "https" | "custom";

export interface BackendServer {
  id: number;
  pool_id: number;
  name: string;
  host: string;
  port: number;
  protocol: "http" | "https";
  weight: number;
  role: BackendRole;
  enabled: boolean;
  health_check_type: HealthCheckType;
  health_check_path: string;
  notes?: string | null;
  health_status: HealthStatus;
  last_check_at?: string | null;
  response_ms?: number | null;
  uptime_percent_24h?: number | null;
}

export interface BackendPool {
  id: number;
  name: string;
  proxy_id?: string | null;
  route_path: string;
  load_balancing_method: LoadBalancingMethod;
  enabled: boolean;
  notes?: string | null;
  servers: BackendServer[];
  primary_count: number;
  backup_count: number;
  failover_active: boolean;
}

export interface LoadBalancerSummary {
  pool_id: number;
  pool_name: string;
  proxy_id?: string | null;
  load_balancing_method: LoadBalancingMethod;
  server_count: number;
  primary_count: number;
  backup_count: number;
  healthy_count: number;
  offline_count: number;
}

export interface HealthCheckDashboard {
  healthy: number;
  warning: number;
  offline: number;
  unknown: number;
  servers: BackendServer[];
}

export interface HealthHistoryPoint {
  timestamp: string;
  uptime_percent: number;
  avg_response_ms?: number | null;
}

export type SmtpSecurityMode = "none" | "starttls" | "ssl";

export interface SmtpSettings {
  host: string;
  port: number;
  username: string;
  password_set: boolean;
  security_mode: SmtpSecurityMode;
  starttls_enabled: boolean;
  ssl_enabled: boolean;
  sender_name: string;
  sender_email: string;
  last_test_status: string;
}

export interface SmtpTestResult {
  status: string;
  message: string;
}

export interface NotificationRecipient {
  id: number;
  name: string;
  email: string;
  enabled: boolean;
  email_enabled: boolean;
  critical_only: boolean;
  all_notifications: boolean;
  enabled_types: string[];
  created_at: string;
}

export interface SystemAlertThresholds {
  cpu_percent: number;
  ram_percent: number;
  disk_percent: number;
  enabled: boolean;
}

export interface AuditLogList {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogEntry {
  id: number;
  username: string;
  action: string;
  resource: string;
  old_value?: string | null;
  new_value?: string | null;
  client_ip: string;
  created_at: string;
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
  total_backend_servers: number;
  healthy_backends: number;
  warning_backends: number;
  offline_backends: number;
  total_certificates: number;
  smtp_status: string;
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
  backend_pool_id?: number | null;
  use_pool: boolean;
}

export interface BackendServerFormData {
  name: string;
  host: string;
  port: number;
  protocol: "http" | "https";
  weight: number;
  role: BackendRole;
  enabled: boolean;
  health_check_type: HealthCheckType;
  health_check_path: string;
  notes: string;
}

export interface BackendPoolFormData {
  name: string;
  proxy_id: string;
  route_path: string;
  load_balancing_method: LoadBalancingMethod;
  enabled: boolean;
  notes: string;
  servers: BackendServerFormData[];
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
