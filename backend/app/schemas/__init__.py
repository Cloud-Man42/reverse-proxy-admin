from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.security.validators import (
    CertbotEmailStr,
    DomainStr,
    IpStr,
    PathPrefixStr,
    PortInt,
    SlugStr,
    SmtpSenderEmailStr,
    validate_header_name,
    validate_header_value,
)


class TargetProtocol(str, Enum):
    HTTP = "http"
    HTTPS = "https"


class LoadBalancingMethod(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONN = "least_conn"
    IP_HASH = "ip_hash"
    RANDOM = "random"
    WEIGHTED = "weighted"


class BackendRole(str, Enum):
    PRIMARY = "primary"
    BACKUP = "backup"


class HealthCheckType(str, Enum):
    TCP = "tcp"
    HTTP = "http"
    HTTPS = "https"
    CUSTOM = "custom"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class NotificationEventType(str, Enum):
    BACKEND_OFFLINE = "backend_offline"
    BACKEND_RESTORED = "backend_restored"
    SSL_EXPIRING = "ssl_expiring"
    SSL_RENEWED = "ssl_renewed"
    PROXY_CREATED = "proxy_created"
    PROXY_MODIFIED = "proxy_modified"
    PROXY_DELETED = "proxy_deleted"
    NGINX_VALIDATION_FAILED = "nginx_validation_failed"
    NGINX_RELOAD_FAILED = "nginx_reload_failed"
    SYSTEM_ERROR = "system_error"
    LOGIN_SECURITY = "login_security"
    STATUS_REPORT = "status_report"


class StatusReportSection(str, Enum):
    PROXY_TRAFFIC = "proxy_traffic"
    PROXY_STATUS = "proxy_status"
    LOAD_BALANCER_HEALTH = "load_balancer_health"
    SSL_CERTIFICATES = "ssl_certificates"
    SYSTEM_METRICS = "system_metrics"


class CustomHeader(BaseModel):
    name: str
    value: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_header_name(value)

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str) -> str:
        return validate_header_value(value)


class ProxyRoute(BaseModel):
    path_prefix: PathPrefixStr = "/"
    target_protocol: TargetProtocol = TargetProtocol.HTTP
    target_host: Optional[IpStr] = None
    target_port: Optional[PortInt] = None
    websocket_enabled: bool = False
    backend_pool_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_target_or_pool(self) -> "ProxyRoute":
        if self.backend_pool_id is None and (self.target_host is None or self.target_port is None):
            raise ValueError("Either backend_pool_id or target_host/target_port is required")
        return self


class ProxyRateLimitKeyType(str, Enum):
    CLIENT_IP = "client_ip"
    URI = "uri"


class ProxyRateLimitBase(BaseModel):
    enabled: bool = False
    requests_per_minute: int = Field(default=60, ge=1, le=10000)
    burst: int = Field(default=20, ge=1, le=1000)
    nodelay: bool = True
    key_type: ProxyRateLimitKeyType = ProxyRateLimitKeyType.CLIENT_IP


class ProxyRateLimitUpdate(ProxyRateLimitBase):
    pass


class ProxyRateLimitResponse(ProxyRateLimitBase):
    proxy_id: str


class ProxyAppBase(BaseModel):
    name: SlugStr
    domains: List[DomainStr] = Field(min_length=1)
    routes: List[ProxyRoute] = Field(min_length=1, max_length=20)
    custom_headers: List[CustomHeader] = Field(default_factory=list)
    max_body_size: Optional[str] = None
    basic_auth_enabled: bool = False
    basic_auth_username: Optional[str] = None
    basic_auth_password: Optional[str] = None
    force_https: bool = False
    enabled: bool = True
    notes: Optional[str] = None
    rate_limit: Optional[ProxyRateLimitUpdate] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_target_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        if data.get("routes"):
            return data
        if data.get("target_host") is None or data.get("target_port") is None:
            return data
        data = dict(data)
        data["routes"] = [
            {
                "path_prefix": data.pop("path_prefix", "/"),
                "target_protocol": data.get("target_protocol", TargetProtocol.HTTP),
                "target_host": data["target_host"],
                "target_port": data["target_port"],
                "websocket_enabled": data.pop("websocket_enabled", False),
            }
        ]
        return data

    @model_validator(mode="after")
    def validate_unique_paths(self) -> "ProxyAppBase":
        paths = [route.path_prefix for route in self.routes]
        if len(paths) != len(set(paths)):
            raise ValueError("Each path prefix must be unique within a proxy app")
        return self

    @property
    def target_protocol(self) -> TargetProtocol:
        return self.routes[0].target_protocol

    @property
    def target_host(self) -> str:
        return self.routes[0].target_host

    @property
    def target_port(self) -> int:
        return self.routes[0].target_port

    @property
    def websocket_enabled(self) -> bool:
        return self.routes[0].websocket_enabled

    @property
    def upstream(self) -> str:
        route = self.routes[0]
        return f"{route.target_protocol.value}://{route.target_host}:{route.target_port}"


class ProxyAppCreate(ProxyAppBase):
    pass


class ProxyAppUpdate(ProxyAppBase):
    pass


class ProxyAppResponse(BaseModel):
    id: str
    name: str
    config_file: str
    domains: List[str]
    routes: List[ProxyRoute]
    target_protocol: TargetProtocol
    target_host: str
    target_port: int
    websocket_enabled: bool
    custom_headers: List[CustomHeader] = Field(default_factory=list)
    max_body_size: Optional[str] = None
    basic_auth_enabled: bool
    basic_auth_username: Optional[str] = None
    basic_auth_password: Optional[str] = None
    force_https: bool
    enabled: bool
    https_enabled: bool
    upstream: str
    managed: bool = True
    notes: Optional[str] = None
    rate_limit: Optional[ProxyRateLimitResponse] = None


class NginxTestResult(BaseModel):
    success: bool
    output: str


class NginxStatusResponse(BaseModel):
    active: bool
    output: str


class CertificateResponse(BaseModel):
    name: str
    domains: List[str]
    issuer: str
    expiry: datetime
    status: str
    source: str = "letsencrypt"
    renewable: bool = True


class CertificateCreateRequest(BaseModel):
    domain: DomainStr
    email: Optional[CertbotEmailStr] = None


class CertificateSettingsResponse(BaseModel):
    default_email: str
    email_configured: bool


class CertificateRenewalLogResponse(BaseModel):
    id: int
    certificate_name: str
    domain: str
    action: str
    status: str
    detail: Optional[str]
    created_at: datetime


class LogLinesResponse(BaseModel):
    lines: List[str]
    source: str


class TrafficDebugEntry(BaseModel):
    client_ip: str
    timestamp: str
    host: str
    method: str
    path: str
    status: int
    bytes_sent: int
    forwarded_for: Optional[str] = None
    user_agent: Optional[str] = None


class TrafficDebugResponse(BaseModel):
    proxy_id: str
    proxy_name: str
    domains: List[str]
    dedicated_log: bool
    source: str
    entries: List[TrafficDebugEntry]


class SystemHealthResponse(BaseModel):
    nginx_active: bool
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    disk_percent: float


class AuditLogResponse(BaseModel):
    id: int
    username: str
    action: str
    resource: str
    old_value: Optional[str]
    new_value: Optional[str]
    client_ip: str
    created_at: datetime


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    username: str
    csrf_token: str
    is_admin: bool = False
    permissions: dict = Field(default_factory=dict)
    organization_id: Optional[int] = None
    role: str = "operator"


class OrganizationBase(BaseModel):
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=128)
    enabled: bool = True


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    slug: Optional[str] = Field(default=None, min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    enabled: Optional[bool] = None


class OrganizationResponse(BaseModel):
    id: int
    slug: str
    name: str
    enabled: bool
    created_at: datetime


class UserPermissions(BaseModel):
    read: bool = True
    create: bool = False
    edit: bool = False


class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    is_active: bool = True
    is_admin: bool = False
    perm_read: bool = True
    perm_create: bool = False
    perm_edit: bool = False


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=256)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=1, max_length=64)
    password: Optional[str] = Field(default=None, min_length=8, max_length=256)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    perm_read: Optional[bool] = None
    perm_create: Optional[bool] = None
    perm_edit: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    is_admin: bool
    perm_read: bool
    perm_create: bool
    perm_edit: bool
    created_at: datetime


class TrafficFlowCheck(BaseModel):
    name: str
    success: bool
    message: str


class TrafficFlowTestResult(BaseModel):
    success: bool
    summary: str
    checks: List[TrafficFlowCheck]


class DashboardAlert(BaseModel):
    id: int
    source: str
    alert_type: str
    title: str
    message: Optional[str] = None
    status: str
    created_at: datetime


class DashboardStats(BaseModel):
    active_proxies: int
    inactive_proxies: int
    disabled_proxies: int = 0
    nginx_active: bool
    expiring_certificates: int
    recent_errors: List[str]
    total_backend_servers: int = 0
    healthy_backends: int = 0
    warning_backends: int = 0
    offline_backends: int = 0
    total_certificates: int = 0
    smtp_status: str = "unknown"
    traffic_bytes_in_24h: int = 0
    traffic_bytes_out_24h: int = 0
    cpu_percent: Optional[float] = None
    ram_percent: Optional[float] = None
    disk_percent: Optional[float] = None
    recent_alerts: List[DashboardAlert] = Field(default_factory=list)
    traffic_history: List["ProxyTrafficHistoryPoint"] = Field(default_factory=list)


class BackendServerBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    host: IpStr
    port: PortInt
    protocol: TargetProtocol = TargetProtocol.HTTP
    weight: int = Field(default=1, ge=1, le=100)
    role: BackendRole = BackendRole.PRIMARY
    enabled: bool = True
    health_check_type: HealthCheckType = HealthCheckType.TCP
    health_check_path: str = Field(default="/", max_length=255)
    notes: Optional[str] = None


class BackendServerCreate(BackendServerBase):
    pool_id: int


class BackendServerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    host: Optional[IpStr] = None
    port: Optional[PortInt] = None
    protocol: Optional[TargetProtocol] = None
    weight: Optional[int] = Field(default=None, ge=1, le=100)
    role: Optional[BackendRole] = None
    enabled: Optional[bool] = None
    health_check_type: Optional[HealthCheckType] = None
    health_check_path: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class BackendServerResponse(BackendServerBase):
    id: int
    pool_id: int
    health_status: HealthStatus = HealthStatus.UNKNOWN
    last_check_at: Optional[datetime] = None
    response_ms: Optional[float] = None
    uptime_percent_24h: Optional[float] = None


class BackendPoolBase(BaseModel):
    name: SlugStr
    proxy_id: Optional[str] = None
    route_path: PathPrefixStr = "/"
    load_balancing_method: LoadBalancingMethod = LoadBalancingMethod.ROUND_ROBIN
    enabled: bool = True
    notes: Optional[str] = None


class BackendPoolCreate(BackendPoolBase):
    servers: List[BackendServerBase] = Field(default_factory=list)


class BackendPoolUpdate(BaseModel):
    name: Optional[SlugStr] = None
    proxy_id: Optional[str] = None
    route_path: Optional[PathPrefixStr] = None
    load_balancing_method: Optional[LoadBalancingMethod] = None
    enabled: Optional[bool] = None
    notes: Optional[str] = None


class BackendPoolResponse(BackendPoolBase):
    id: int
    servers: List[BackendServerResponse] = Field(default_factory=list)
    primary_count: int = 0
    backup_count: int = 0
    failover_active: bool = False


class LoadBalancerSummary(BaseModel):
    pool_id: int
    pool_name: str
    proxy_id: Optional[str]
    load_balancing_method: LoadBalancingMethod
    server_count: int
    primary_count: int
    backup_count: int
    healthy_count: int
    offline_count: int


class HealthCheckResultResponse(BaseModel):
    id: int
    server_id: int
    server_name: str
    pool_name: str
    status: HealthStatus
    response_ms: Optional[float]
    http_status: Optional[int]
    error: Optional[str]
    checked_at: datetime


class HealthCheckDashboard(BaseModel):
    healthy: int
    warning: int
    offline: int
    unknown: int
    servers: List[BackendServerResponse]


class HealthHistoryPoint(BaseModel):
    timestamp: datetime
    uptime_percent: float
    avg_response_ms: Optional[float]


class SmtpSecurityMode(str, Enum):
    NONE = "none"
    STARTTLS = "starttls"
    SSL = "ssl"


class SmtpSettingsUpdate(BaseModel):
    host: str = Field(max_length=255)
    port: PortInt
    username: str = Field(max_length=255)
    password: Optional[str] = None
    security_mode: Optional[SmtpSecurityMode] = None
    starttls_enabled: bool = True
    ssl_enabled: bool = False
    sender_name: str = Field(max_length=255)
    sender_email: SmtpSenderEmailStr = ""
    default_recipient_email: SmtpSenderEmailStr = ""
    tls_server_name: str = Field(default="", max_length=255)
    verify_tls_certificate: bool = True

    @model_validator(mode="after")
    def validate_security_options(self) -> "SmtpSettingsUpdate":
        if self.security_mode is not None:
            return self
        if self.ssl_enabled and self.starttls_enabled:
            raise ValueError("Enable either STARTTLS or SSL, not both")
        return self


class SmtpSettingsResponse(BaseModel):
    host: str
    port: int
    username: str
    password_set: bool
    security_mode: SmtpSecurityMode
    starttls_enabled: bool
    ssl_enabled: bool
    sender_name: str
    sender_email: str
    default_recipient_email: str
    tls_server_name: str
    verify_tls_certificate: bool
    last_test_status: str


class SmtpTestResponse(BaseModel):
    status: str
    message: str


class NotificationRecipientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    email: CertbotEmailStr
    enabled: bool = True
    email_enabled: bool = True
    critical_only: bool = False
    all_notifications: bool = True
    enabled_types: List[NotificationEventType] = Field(default_factory=list)


class NotificationRecipientUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    email: Optional[CertbotEmailStr] = None
    enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    critical_only: Optional[bool] = None
    all_notifications: Optional[bool] = None
    enabled_types: Optional[List[NotificationEventType]] = None


class NotificationRecipientResponse(BaseModel):
    id: int
    name: str
    email: str
    enabled: bool
    email_enabled: bool
    critical_only: bool
    all_notifications: bool
    enabled_types: List[str]
    created_at: datetime


class NotificationLogResponse(BaseModel):
    id: int
    event_type: str
    subject: str
    recipient_email: str
    status: str
    detail: Optional[str]
    created_at: datetime


class SystemAlertThresholdUpdate(BaseModel):
    cpu_percent: float = Field(ge=1, le=100)
    ram_percent: float = Field(ge=1, le=100)
    disk_percent: float = Field(ge=1, le=100)
    enabled: bool = True


class SystemAlertThresholdResponse(BaseModel):
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    enabled: bool


class SystemAlertHistoryResponse(BaseModel):
    id: int
    alert_type: str
    metric: str
    value: float
    threshold: float
    status: str
    message: Optional[str]
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class NetworkMapNode(BaseModel):
    id: str
    type: str
    label: str
    subtitle: Optional[str] = None
    status: str
    metadata: dict = Field(default_factory=dict)


class NetworkMapEdge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = None


class NetworkMapResponse(BaseModel):
    nodes: List[NetworkMapNode]
    edges: List[NetworkMapEdge]
    generated_at: datetime


class ProxyTrafficHistoryPoint(BaseModel):
    timestamp: datetime
    connections: int
    bytes_in: int
    bytes_out: int


class ProxyTrafficStatsResponse(BaseModel):
    proxy_id: str
    proxy_name: str
    domains: List[str]
    range: str
    connections: int
    bytes_in: int
    bytes_out: int
    upstream_bytes_in: int
    upstream_bytes_out: int
    history: List[ProxyTrafficHistoryPoint] = Field(default_factory=list)


class ProxyTrafficSummary(BaseModel):
    proxy_id: str
    proxy_name: str
    domains: List[str]
    enabled: bool
    connections: int
    bytes_in: int
    bytes_out: int


class AnalyticsSummaryItem(BaseModel):
    proxy_id: str
    proxy_name: str
    domains: List[str]
    enabled: bool
    requests: int
    rps: float
    latency_avg_ms: float
    upstream_latency_avg_ms: float
    error_rate: float
    status_2xx: int
    status_3xx: int
    status_4xx: int
    status_5xx: int
    bytes_in: int
    bytes_out: int


class AnalyticsSummaryResponse(BaseModel):
    range: str
    items: List[AnalyticsSummaryItem]


class AnalyticsProxyResponse(BaseModel):
    proxy_id: str
    proxy_name: str
    domains: List[str]
    range: str
    requests: int
    rps: float
    latency_avg_ms: float
    upstream_latency_avg_ms: float
    error_rate: float
    status_2xx: int
    status_3xx: int
    status_4xx: int
    status_5xx: int
    bytes_in: int
    bytes_out: int
    top_clients: Dict[str, int] = Field(default_factory=dict)
    top_paths: Dict[str, int] = Field(default_factory=dict)
    history: List[ProxyTrafficHistoryPoint] = Field(default_factory=list)


class StatusReportSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    interval_hours: Optional[int] = Field(default=None, ge=1, le=168)
    enabled_sections: Optional[List[StatusReportSection]] = None


class StatusReportSettingsResponse(BaseModel):
    enabled: bool
    interval_hours: int
    enabled_sections: List[str]
    last_sent_at: Optional[datetime] = None
    updated_at: datetime


class ProxyTemplateResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: Optional[str] = None
    defaults: dict = Field(default_factory=dict)
    builtin: bool


class ConfigVersionResponse(BaseModel):
    id: int
    resource_type: str
    resource_id: str
    version: int
    username: str
    summary: str
    has_old_config: bool
    nginx_test_result: Optional[str] = None
    created_at: datetime


class ConfigVersionDetailResponse(ConfigVersionResponse):
    old_config: Optional[str] = None
    new_config: str


class ConfigVersionCompareResponse(BaseModel):
    id1: int
    id2: int
    resource_type: str
    resource_id: str
    version1: int
    version2: int
    diff: str


class ConfigVersionRollbackResponse(BaseModel):
    success: bool
    message: str
    version: Optional[ConfigVersionResponse] = None


class ApiTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    scopes: List[str] = Field(min_length=1)
    expires_at: Optional[datetime] = None


class ApiTokenUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class ApiTokenResponse(BaseModel):
    id: int
    name: str
    token_prefix: str
    scopes: List[str]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    revoked: bool
    created_at: datetime


class ApiTokenCreatedResponse(ApiTokenResponse):
    token: str


class ApiTokenScopesResponse(BaseModel):
    scopes: List[str]


class IpAccessRuleType(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class IpAccessScope(str, Enum):
    GLOBAL = "global"
    PROXY = "proxy"


class IpAccessRuleBase(BaseModel):
    scope: IpAccessScope
    proxy_id: Optional[str] = None
    rule_type: IpAccessRuleType
    cidr: str = Field(min_length=1, max_length=64)
    enabled: bool = True
    notes: Optional[str] = None


class IpAccessRuleCreate(IpAccessRuleBase):
    pass


class IpAccessRuleUpdate(BaseModel):
    scope: Optional[IpAccessScope] = None
    proxy_id: Optional[str] = None
    rule_type: Optional[IpAccessRuleType] = None
    cidr: Optional[str] = Field(default=None, min_length=1, max_length=64)
    enabled: Optional[bool] = None
    notes: Optional[str] = None


class IpAccessRuleResponse(IpAccessRuleBase):
    id: int


class GeoRuleMode(str, Enum):
    BLOCK = "block"
    ALLOW = "allow"


class GeoRuleBase(BaseModel):
    proxy_id: str
    mode: GeoRuleMode = GeoRuleMode.BLOCK
    countries: List[str] = Field(default_factory=list)
    default_policy: str = "allow"
    enabled: bool = False


class GeoRuleCreate(GeoRuleBase):
    pass


class GeoRuleUpdate(BaseModel):
    proxy_id: Optional[str] = None
    mode: Optional[GeoRuleMode] = None
    countries: Optional[List[str]] = None
    default_policy: Optional[str] = None
    enabled: Optional[bool] = None


class GeoRuleResponse(GeoRuleBase):
    id: int


class ThreatFeedType(str, Enum):
    CIDR = "cidr"
    IP = "ip"


class ThreatFeedBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    url: str = Field(min_length=1, max_length=512)
    feed_type: ThreatFeedType = ThreatFeedType.CIDR
    enabled: bool = False


class ThreatFeedCreate(ThreatFeedBase):
    pass


class ThreatFeedUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    url: Optional[str] = Field(default=None, min_length=1, max_length=512)
    feed_type: Optional[ThreatFeedType] = None
    enabled: Optional[bool] = None


class ThreatFeedResponse(ThreatFeedBase):
    id: int
    last_sync_at: Optional[datetime] = None
    ip_count: int = 0
    last_error: Optional[str] = None


class WafMode(str, Enum):
    DETECTION = "detection"
    BLOCKING = "blocking"


class WafProfile(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProxyWafSettingsBase(BaseModel):
    enabled: bool = False
    mode: WafMode = WafMode.DETECTION
    profile: WafProfile = WafProfile.MEDIUM
    exclusions: List[str] = Field(default_factory=list)


class ProxyWafSettingsUpdate(ProxyWafSettingsBase):
    pass


class ProxyWafSettingsResponse(ProxyWafSettingsBase):
    proxy_id: str


class SecurityEventResponse(BaseModel):
    id: int
    event_type: str
    source: str
    client_ip: Optional[str] = None
    proxy_id: Optional[str] = None
    message: str
    created_at: datetime


class SecurityEventListResponse(BaseModel):
    items: List[SecurityEventResponse]
    total: int
    page: int
    page_size: int
