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
  tls_server_name: string;
  verify_tls_certificate: boolean;
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
  notes?: string | null;
  rate_limit?: ProxyRateLimitSettings | null;
}

export interface Certificate {
  name: string;
  domains: string[];
  issuer: string;
  expiry: string;
  status: "valid" | "expiring" | "expired";
  source: "letsencrypt" | "imported";
  renewable: boolean;
}

export interface CertificateRenewalLogEntry {
  id: number;
  certificate_name: string;
  domain: string;
  action: string;
  status: string;
  detail?: string | null;
  created_at: string;
}

export type NotificationEventType =
  | "backend_offline"
  | "backend_restored"
  | "ssl_expiring"
  | "ssl_renewed"
  | "proxy_created"
  | "proxy_modified"
  | "proxy_deleted"
  | "nginx_validation_failed"
  | "nginx_reload_failed"
  | "system_error"
  | "login_security"
  | "status_report";

export interface NotificationLogEntry {
  id: number;
  event_type: string;
  subject: string;
  recipient_email: string;
  status: string;
  detail?: string | null;
  created_at: string;
}

export interface HealthCheckRunResult {
  server_id: number;
  status: HealthStatus;
  response_ms?: number | null;
  http_status?: number | null;
  error?: string | null;
  checked_at: string;
}

export interface CertificateSettings {
  default_email: string;
  email_configured: boolean;
}

export interface DashboardAlert {
  id: number;
  source: string;
  alert_type: string;
  title: string;
  message?: string | null;
  status: string;
  created_at: string;
}

export interface DashboardStats {
  active_proxies: number;
  inactive_proxies: number;
  disabled_proxies: number;
  nginx_active: boolean;
  expiring_certificates: number;
  recent_errors: string[];
  total_backend_servers: number;
  healthy_backends: number;
  warning_backends: number;
  offline_backends: number;
  total_certificates: number;
  smtp_status: string;
  traffic_bytes_in_24h: number;
  traffic_bytes_out_24h: number;
  cpu_percent?: number | null;
  ram_percent?: number | null;
  disk_percent?: number | null;
  recent_alerts: DashboardAlert[];
  traffic_history: ProxyTrafficHistoryPoint[];
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
  organization_id?: number | null;
  role: string;
}

export type UserRole = "super_admin" | "tenant_admin" | "operator" | "read_only";

export interface Organization {
  id: number;
  slug: string;
  name: string;
  enabled: boolean;
  created_at: string;
}

export interface OrganizationFormData {
  slug: string;
  name: string;
  enabled: boolean;
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

export type StatusReportSection =
  | "proxy_traffic"
  | "proxy_status"
  | "load_balancer_health"
  | "ssl_certificates"
  | "system_metrics";

export interface ProxyTrafficSummary {
  proxy_id: string;
  proxy_name: string;
  domains: string[];
  enabled: boolean;
  connections: number;
  bytes_in: number;
  bytes_out: number;
}

export interface ProxyTrafficHistoryPoint {
  timestamp: string;
  connections: number;
  bytes_in: number;
  bytes_out: number;
}

export interface ProxyTrafficStats {
  proxy_id: string;
  proxy_name: string;
  domains: string[];
  range: string;
  connections: number;
  bytes_in: number;
  bytes_out: number;
  upstream_bytes_in: number;
  upstream_bytes_out: number;
  history: ProxyTrafficHistoryPoint[];
}

export interface AnalyticsSummaryItem {
  proxy_id: string;
  proxy_name: string;
  domains: string[];
  enabled: boolean;
  requests: number;
  rps: number;
  latency_avg_ms: number;
  upstream_latency_avg_ms: number;
  error_rate: number;
  status_2xx: number;
  status_3xx: number;
  status_4xx: number;
  status_5xx: number;
  bytes_in: number;
  bytes_out: number;
}

export interface AnalyticsSummaryResponse {
  range: string;
  items: AnalyticsSummaryItem[];
}

export interface AnalyticsProxyDetail {
  proxy_id: string;
  proxy_name: string;
  domains: string[];
  range: string;
  requests: number;
  rps: number;
  latency_avg_ms: number;
  upstream_latency_avg_ms: number;
  error_rate: number;
  status_2xx: number;
  status_3xx: number;
  status_4xx: number;
  status_5xx: number;
  bytes_in: number;
  bytes_out: number;
  top_clients: Record<string, number>;
  top_paths: Record<string, number>;
  history: ProxyTrafficHistoryPoint[];
}

export type ProxyRateLimitKeyType = "client_ip" | "uri";

export interface ProxyRateLimitSettings {
  proxy_id?: string;
  enabled: boolean;
  requests_per_minute: number;
  burst: number;
  nodelay: boolean;
  key_type: ProxyRateLimitKeyType;
}

export interface StatusReportSettings {
  enabled: boolean;
  interval_hours: number;
  enabled_sections: StatusReportSection[];
  last_sent_at?: string | null;
  updated_at: string;
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
  notes: string;
  rate_limit: ProxyRateLimitSettings;
}

export const defaultRateLimit = (): ProxyRateLimitSettings => ({
  enabled: false,
  requests_per_minute: 60,
  burst: 20,
  nodelay: true,
  key_type: "client_ip",
});

export interface ProxyTemplate {
  id: number;
  slug: string;
  name: string;
  description?: string | null;
  defaults: {
    routes?: Array<{
      path_prefix?: string;
      target_protocol?: "http" | "https";
      target_host?: string;
      target_port?: number;
      websocket_enabled?: boolean;
    }>;
    force_https?: boolean;
    max_body_size?: string;
    notes?: string;
    enabled?: boolean;
  };
  builtin: boolean;
}

export interface ConfigVersion {
  id: number;
  resource_type: string;
  resource_id: string;
  version: number;
  username: string;
  summary: string;
  has_old_config: boolean;
  nginx_test_result?: string | null;
  created_at: string;
}

export interface ConfigVersionDetail extends ConfigVersion {
  old_config?: string | null;
  new_config: string;
}

export interface ConfigVersionCompare {
  id1: number;
  id2: number;
  resource_type: string;
  resource_id: string;
  version1: number;
  version2: number;
  diff: string;
}

export interface ConfigVersionRollbackResult {
  success: boolean;
  message: string;
  version?: ConfigVersion | null;
}

export interface ApiToken {
  id: number;
  name: string;
  token_prefix: string;
  scopes: string[];
  expires_at?: string | null;
  last_used_at?: string | null;
  revoked: boolean;
  created_at: string;
}

export interface ApiTokenCreated extends ApiToken {
  token: string;
}

export interface ApiTokenFormData {
  name: string;
  scopes: string[];
  expires_at?: string;
}

export interface IpAccessRule {
  id: number;
  scope: "global" | "proxy";
  proxy_id?: string | null;
  rule_type: "allow" | "deny";
  cidr: string;
  enabled: boolean;
  notes?: string | null;
}

export interface GeoRule {
  id: number;
  proxy_id: string;
  mode: "block" | "allow";
  countries: string[];
  default_policy: string;
  enabled: boolean;
}

export interface ThreatFeed {
  id: number;
  name: string;
  url: string;
  feed_type: "cidr" | "ip";
  enabled: boolean;
  last_sync_at?: string | null;
  ip_count: number;
  last_error?: string | null;
}

export interface ProxyWafSettings {
  proxy_id: string;
  enabled: boolean;
  mode: "detection" | "blocking";
  profile: "low" | "medium" | "high";
  exclusions: string[];
}

export interface SecurityEvent {
  id: number;
  event_type: string;
  source: string;
  client_ip?: string | null;
  proxy_id?: string | null;
  message: string;
  created_at: string;
}

export interface SecurityEventList {
  items: SecurityEvent[];
  total: number;
  page: number;
  page_size: number;
}
