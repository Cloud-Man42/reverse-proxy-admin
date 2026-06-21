from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas import CustomHeader, DomainStr, ProxyAppCreate, ProxyRoute, TargetProtocol
from app.security.validators import validate_header_name, validate_header_value, validate_slug


class TemplateAvailabilityLevel(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TemplateHeader(BaseModel):
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


class ApplicationTemplate(BaseModel):
    slug: str
    name: str
    description: str
    group: str
    category: str
    icon: str = "app"
    tags: List[str] = Field(default_factory=list)
    availability_level: TemplateAvailabilityLevel = TemplateAvailabilityLevel.FREE
    optimized: bool = False
    default_upstream_protocol: str = "http"
    default_upstream_port: int = 8080
    websocket_support: bool = False
    large_upload_support: bool = False
    recommended_client_max_body_size: Optional[str] = None
    recommended_proxy_read_timeout: Optional[str] = None
    recommended_proxy_send_timeout: Optional[str] = None
    recommended_proxy_connect_timeout: Optional[str] = None
    https_upstream_supported: bool = False
    http_to_https_redirect_default: bool = True
    recommended_headers: List[TemplateHeader] = Field(default_factory=list)
    security_headers: List[TemplateHeader] = Field(default_factory=list)
    health_check_path: Optional[str] = None
    rate_limit_recommendation: Optional[str] = None
    notes: Optional[str] = None
    security_notes: Optional[str] = None
    documentation_url: Optional[str] = None
    long_description: Optional[str] = None
    slug_aliases: List[str] = Field(default_factory=list)
    hsts_recommended: bool = False

    @field_validator("slug")
    @classmethod
    def validate_template_slug(cls, value: str) -> str:
        return validate_slug(value)

    def to_defaults_dict(self) -> dict:
        return {
            "routes": [
                {
                    "path_prefix": "/",
                    "target_protocol": self.default_upstream_protocol,
                    "target_host": "127.0.0.1",
                    "target_port": self.default_upstream_port,
                    "websocket_enabled": self.websocket_support,
                }
            ],
            "force_https": self.http_to_https_redirect_default,
            "max_body_size": self.recommended_client_max_body_size or "",
            "notes": self.notes or "",
            "enabled": True,
            "custom_headers": [{"name": h.name, "value": h.value} for h in self.recommended_headers],
            "proxy_read_timeout": self.recommended_proxy_read_timeout,
            "proxy_send_timeout": self.recommended_proxy_send_timeout,
            "proxy_connect_timeout": self.recommended_proxy_connect_timeout,
            "hsts_enabled": self.hsts_recommended,
            "security_headers": [{"name": h.name, "value": h.value} for h in self.security_headers],
        }


class TemplateGroup(BaseModel):
    slug: str
    name: str
    description: str
    icon: str = "folder"
    sort_order: int = 0


class TemplateGroupResponse(TemplateGroup):
    template_count: int = 0


class ApplicationTemplateResponse(ApplicationTemplate):
    id: int
    defaults: dict = Field(default_factory=dict)
    builtin: bool = True


class TemplateListResponse(BaseModel):
    items: List[ApplicationTemplateResponse]
    total: int
    page: int
    page_size: int


class TemplatePreviewRequest(BaseModel):
    domain: DomainStr
    upstream_host: str = "127.0.0.1"
    upstream_port: Optional[int] = None
    upstream_protocol: Optional[str] = None
    name: Optional[str] = None
    websocket_enabled: Optional[bool] = None
    force_https: Optional[bool] = None
    large_upload_enabled: Optional[bool] = None
    max_body_size: Optional[str] = None
    proxy_read_timeout: Optional[str] = None
    proxy_send_timeout: Optional[str] = None
    proxy_connect_timeout: Optional[str] = None
    hsts_enabled: Optional[bool] = None
    apply_recommended_headers: bool = True
    apply_security_headers: bool = True


class TemplatePreviewResponse(BaseModel):
    rendered_config: str
    resolved_payload: dict
    warnings: List[str] = Field(default_factory=list)


class TemplateCreateProxyRequest(TemplatePreviewRequest):
    name: str
    enabled: bool = True


class TemplateCreateProxyResponse(BaseModel):
    success: bool
    message: str
    proxy: Optional[dict] = None
    failure_stage: Optional[str] = None


class CatalogFilter(BaseModel):
    q: Optional[str] = None
    group: Optional[str] = None
    tag: Optional[str] = None
    availability_level: Optional[TemplateAvailabilityLevel] = None
    optimized: Optional[bool] = None
    websocket: Optional[bool] = None
    large_upload: Optional[bool] = None
    https_upstream: Optional[bool] = None
    page: int = 1
    page_size: int = 100
