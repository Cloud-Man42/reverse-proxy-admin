import shutil
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas import AuditLogResponse, DashboardStats, MessageResponse, NetworkMapResponse, NginxStatusResponse, NginxTestResult, SystemHealthResponse
from app.security.permissions import Permission, require_admin, require_permission
from app.security.ip_allowlist import _client_ip
from app.services.audit_service import log_audit
from app.services.certbot_ops import CertbotOps
from app.services.log_reader import LogReader
from app.services.network_map_service import NetworkMapService
from app.services.nginx_ops import NginxOps
from app.services.proxy_service import ProxyService

router = APIRouter(tags=["system"])


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> DashboardStats:
    proxies = ProxyService(settings).list_proxies()
    active = sum(1 for item in proxies if item.enabled)
    inactive = len(proxies) - active
    nginx_active, _ = NginxOps(settings).status()
    expiring = sum(1 for cert in CertbotOps(settings).list_certificates() if cert.status == "expiring")
    recent_errors = LogReader(settings).read_error_log(lines=10)
    return DashboardStats(
        active_proxies=active,
        inactive_proxies=inactive,
        nginx_active=nginx_active,
        expiring_certificates=expiring,
        recent_errors=recent_errors,
    )


@router.get("/dashboard/network-map", response_model=NetworkMapResponse)
async def network_map(
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> NetworkMapResponse:
    return NetworkMapService(settings).build()


@router.get("/system/health", response_model=SystemHealthResponse)
async def system_health(
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> SystemHealthResponse:
    nginx_active, _ = NginxOps(settings).status()
    usage = shutil.disk_usage(settings.data_dir if settings.data_dir.exists() else "/")
    total = usage.total / (1024**3)
    used = usage.used / (1024**3)
    free = usage.free / (1024**3)
    percent = (usage.used / usage.total) * 100 if usage.total else 0
    return SystemHealthResponse(
        nginx_active=nginx_active,
        disk_total_gb=round(total, 2),
        disk_used_gb=round(used, 2),
        disk_free_gb=round(free, 2),
        disk_percent=round(percent, 2),
    )


@router.get("/system/nginx/status", response_model=NginxStatusResponse)
async def nginx_status(
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> NginxStatusResponse:
    active, output = NginxOps(settings).status()
    return NginxStatusResponse(active=active, output=output)


@router.post("/system/nginx/test", response_model=NginxTestResult)
async def nginx_test(
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> NginxTestResult:
    ok, output = NginxOps(settings).test_config()
    return NginxTestResult(success=ok, output=output)


@router.post("/system/nginx/reload", response_model=MessageResponse)
async def nginx_reload(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> MessageResponse:
    ok, output = NginxOps(settings).reload()
    log_audit(
        db,
        username=user.username,
        action="nginx_reload",
        resource="nginx",
        client_ip=_client_ip(request),
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    return MessageResponse(message="Nginx reloaded", detail=output)


@router.get("/audit", response_model=List[AuditLogResponse])
async def list_audit_logs(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> List[AuditLogResponse]:
    entries = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    return [
        AuditLogResponse(
            id=entry.id,
            username=entry.username,
            action=entry.action,
            resource=entry.resource,
            old_value=entry.old_value,
            new_value=entry.new_value,
            client_ip=entry.client_ip,
            created_at=entry.created_at,
        )
        for entry in entries
    ]


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
