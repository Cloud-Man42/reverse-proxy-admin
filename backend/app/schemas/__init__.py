from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.security.validators import DomainStr, IpStr, PortInt, SlugStr, validate_header_name, validate_header_value


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


class ProxyAppBase(BaseModel):
    name: SlugStr
    domains: List[DomainStr] = Field(min_length=1)
    target_protocol: TargetProtocol = TargetProtocol.HTTP
    target_host: IpStr
    target_port: PortInt
    websocket_enabled: bool = False
    custom_headers: List[CustomHeader] = Field(default_factory=list)
    max_body_size: Optional[str] = None
    basic_auth_enabled: bool = False
    basic_auth_username: Optional[str] = None
    basic_auth_password: Optional[str] = None
    force_https: bool = False
    enabled: bool = True


class ProxyAppCreate(ProxyAppBase):
    pass


class ProxyAppUpdate(ProxyAppBase):
    pass


class ProxyAppResponse(ProxyAppBase):
    id: str
    config_file: str
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
    email: Optional[str] = None


class LogLinesResponse(BaseModel):
    lines: List[str]
    source: str


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
