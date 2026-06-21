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
  default_recipient_email: string;
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
  enhanced_analytics_logging?: boolean;
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
  enhanced_analytics_logging: boolean;
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

export interface WafPlatformStatus {
  modsecurity_ready: boolean;
  crs_base_path: string;
  setup_script: string;
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

export type MetricsRange = "15m" | "1h" | "24h" | "7d" | "30d";

export interface MetricsSeriesPoint {
  timestamp: string;
  value: number;
}

export interface MetricsDashboardResponse {
  system_health: {
    nginx_status: string;
    health_check_service: string;
    smtp_status: string;
    ssl_certbot_status: string;
    background_worker_status: string;
    cpu_percent?: number | null;
    ram_percent?: number | null;
    disk_percent?: number | null;
  };
  proxy_overview: {
    total: number;
    active: number;
    disabled: number;
    total_backends: number;
    healthy_backends: number;
    warning_backends: number;
    offline_backends: number;
  };
  live_traffic: {
    requests_per_second: number;
    active_connections: number;
    bandwidth_in: number;
    bandwidth_out: number;
    avg_response_time_ms: number;
    error_rate_percent: number;
  };
  ssl_overview: {
    total: number;
    valid: number;
    expiring: number;
    expired: number;
    renewal_errors: number;
  };
  alerts: Array<{
    source: string;
    title: string;
    message?: string | null;
    status: string;
    severity: string;
    created_at: string;
  }>;
  traffic_history: Array<{
    timestamp: string;
    requests: number;
    bytes_in: number;
    bytes_out: number;
  }>;
  range: string;
}

export interface MetricsTrafficResponse {
  range: string;
  totals: {
    requests: number;
    bytes_in: number;
    bytes_out: number;
    avg_response_time_ms: number;
    error_rate: number;
    rps: number;
  };
  peak_rps: number;
  series: {
    requests: MetricsSeriesPoint[];
    bandwidth_in: MetricsSeriesPoint[];
    bandwidth_out: MetricsSeriesPoint[];
    response_time_ms: MetricsSeriesPoint[];
    error_rate: MetricsSeriesPoint[];
  };
}

export interface MetricsStatusCodesResponse {
  range: string;
  groups: Record<string, number>;
  specific: Record<string, number>;
  hints: Array<{ code: string; hint: string }>;
  top_errors: Array<[string, number]>;
}

export interface MetricsProxyHostItem {
  proxy_id: string;
  domains: string[];
  requests: number;
  bandwidth: number;
  error_count: number;
  error_rate: number;
  avg_response_time_ms: number;
  active_connections: number;
  backend_pool_status: string;
  enabled: boolean;
}

export interface MetricsClientIpItem {
  client_ip: string;
  requests: number;
  bandwidth: number;
  errors: number;
  last_seen?: string;
  user_agent?: string;
}

export interface MetricsBackendItem {
  backend_server_id: number;
  name: string;
  host: string;
  port: number;
  protocol: string;
  status: string;
  response_time_ms: number;
  uptime_percent_24h: number;
  history: Array<{
    timestamp: string;
    response_time_ms?: number | null;
    status?: string;
    errors?: number;
  }>;
}

export interface MetricsConnectionsResponse {
  range: string;
  latest: Record<string, number>;
  series: Array<{
    timestamp: string;
    active: number;
    reading: number;
    writing: number;
    waiting: number;
  }>;
}

export interface MetricsSslResponse {
  total: number;
  valid: number;
  expiring_soon: number;
  expired: number;
  items: Array<{
    domain: string;
    status: string;
    days_remaining: number;
    issuer: string;
    expires_at: string;
  }>;
}

export interface MetricsSecurityResponse {
  range: string;
  total_events: number;
  failed_logins: number;
  rate_limited: number;
  blocked_ips: number;
  top_blocked_ips: Array<[string, number]>;
  recent_events: SecurityEvent[];
}

export interface RequestEventItem {
  timestamp: string;
  client_ip: string;
  host: string;
  uri: string;
  method: string;
  status: number;
  backend_addr?: string | null;
  response_time_ms?: number | null;
  upstream_time_ms?: number | null;
  bytes_sent: number;
  user_agent?: string | null;
}

export interface PaginatedRequestEvents {
  total: number;
  page: number;
  page_size: number;
  items: RequestEventItem[];
}

export interface MetricAlertRule {
  id: number;
  name: string;
  enabled: boolean;
  severity: string;
  metric_type: string;
  condition: string;
  threshold: number;
  window_minutes: number;
  proxy_id?: string | null;
  notify_email: boolean;
}

export interface MetricAlertHistoryItem {
  id: number;
  rule_id?: number | null;
  alert_type: string;
  severity: string;
  status: string;
  message: string;
  metric_value?: number | null;
  created_at: string;
}

export interface MetricAlertsResponse {
  rules: MetricAlertRule[];
  history: MetricAlertHistoryItem[];
}

export interface MetricsSettings {
  raw_retention_days: number;
  minute_retention_days: number;
  hour_retention_days: number;
  stub_status_url: string;
  enhanced_logging_default: boolean;
  request_event_sample_rate: number;
}

export type TemplateAvailabilityLevel = "free" | "pro" | "enterprise";

export interface TemplateHeader {
  name: string;
  value: string;
}

export interface ApplicationTemplate extends ProxyTemplate {
  group: string;
  category: string;
  icon: string;
  tags: string[];
  availability_level: TemplateAvailabilityLevel;
  optimized: boolean;
  default_upstream_protocol: string;
  default_upstream_port: number;
  websocket_support: boolean;
  large_upload_support: boolean;
  recommended_client_max_body_size?: string | null;
  recommended_proxy_read_timeout?: string | null;
  recommended_proxy_send_timeout?: string | null;
  recommended_proxy_connect_timeout?: string | null;
  https_upstream_supported: boolean;
  http_to_https_redirect_default: boolean;
  recommended_headers: TemplateHeader[];
  security_headers: TemplateHeader[];
  health_check_path?: string | null;
  rate_limit_recommendation?: string | null;
  security_notes?: string | null;
  documentation_url?: string | null;
  long_description?: string | null;
  slug_aliases: string[];
  hsts_recommended: boolean;
}

export interface TemplateGroup {
  slug: string;
  name: string;
  description: string;
  icon: string;
  sort_order: number;
  template_count: number;
}

export interface TemplateListResponse {
  items: ApplicationTemplate[];
  total: number;
  page: number;
  page_size: number;
}

export interface CatalogFilters {
  q?: string;
  group?: string;
  tag?: string;
  availability_level?: TemplateAvailabilityLevel;
  optimized?: boolean;
  websocket?: boolean;
  large_upload?: boolean;
  https_upstream?: boolean;
  page?: number;
  page_size?: number;
}

export interface TemplatePreviewRequest {
  domain: string;
  upstream_host?: string;
  upstream_port?: number;
  upstream_protocol?: string;
  name?: string;
  websocket_enabled?: boolean;
  force_https?: boolean;
  large_upload_enabled?: boolean;
  max_body_size?: string;
  proxy_read_timeout?: string;
  proxy_send_timeout?: string;
  proxy_connect_timeout?: string;
  hsts_enabled?: boolean;
  apply_recommended_headers?: boolean;
  apply_security_headers?: boolean;
}

export interface TemplatePreviewResponse {
  rendered_config: string;
  resolved_payload: Record<string, unknown>;
  warnings: string[];
}

export interface TemplateCreateProxyRequest extends TemplatePreviewRequest {
  name: string;
  enabled?: boolean;
}

export interface TemplateCreateProxyResponse {
  success: boolean;
  message: string;
  proxy?: Record<string, unknown> | null;
  failure_stage?: string | null;
}

export interface TemplateWizardState {
  domain: string;
  upstream_host: string;
  upstream_port: number;
  upstream_protocol: "http" | "https";
  name: string;
  websocket_enabled: boolean;
  force_https: boolean;
  large_upload_enabled: boolean;
  max_body_size: string;
  hsts_enabled: boolean;
  apply_recommended_headers: boolean;
  apply_security_headers: boolean;
  proxy_read_timeout: string;
  proxy_send_timeout: string;
  proxy_connect_timeout: string;
  enabled: boolean;
}
