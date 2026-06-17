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
    validate_header_name,
    validate_header_value,
)


class TargetProtocol(str, Enum):
    HTTP = "http"
    HTTPS = "https"


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
    target_host: IpStr
    target_port: PortInt
    websocket_enabled: bool = False


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


class CertificateCreateRequest(BaseModel):
    domain: DomainStr
    email: Optional[CertbotEmailStr] = None


class CertificateSettingsResponse(BaseModel):
    default_email: str
    email_configured: bool


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


class DashboardStats(BaseModel):
    active_proxies: int
    inactive_proxies: int
    nginx_active: bool
    expiring_certificates: int
    recent_errors: List[str]


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
