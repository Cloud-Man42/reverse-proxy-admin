import shutil
from typing import Optional

import psutil
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.api_token import ApiToken
from app.schemas import MessageResponse, NginxStatusResponse, NginxTestResult, SystemHealthResponse
from app.security.api_token_auth import require_api_scopes
from app.security.ip_allowlist import _client_ip
from app.services.audit_service import log_audit
from app.services.nginx_ops import NginxOps

router = APIRouter(prefix="/system")


def _audit_actor(token: ApiToken) -> str:
    return f"token:{token.name}"


@router.get("/health", response_model=SystemHealthResponse)
async def system_health(
    settings: Settings = Depends(get_settings),
    _token: ApiToken = Depends(require_api_scopes("system:read")),
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


@router.get("/metrics")
async def system_metrics(
    settings: Settings = Depends(get_settings),
    _token: ApiToken = Depends(require_api_scopes("system:read")),
) -> dict:
    try:
        cpu = round(psutil.cpu_percent(interval=0.1), 1)
        ram = round(psutil.virtual_memory().percent, 1)
        usage = shutil.disk_usage(settings.data_dir if settings.data_dir.exists() else "/")
        disk = round((usage.used / usage.total) * 100, 1) if usage.total else 0.0
        return {"cpu_percent": cpu, "ram_percent": ram, "disk_percent": disk}
    except Exception:
        return {"cpu_percent": None, "ram_percent": None, "disk_percent": None}


@router.get("/nginx/status", response_model=NginxStatusResponse)
async def nginx_status(
    settings: Settings = Depends(get_settings),
    _token: ApiToken = Depends(require_api_scopes("system:read")),
) -> NginxStatusResponse:
    active, output = NginxOps(settings).status()
    return NginxStatusResponse(active=active, output=output)


@router.post("/nginx/test", response_model=NginxTestResult)
async def nginx_test(
    settings: Settings = Depends(get_settings),
    _token: ApiToken = Depends(require_api_scopes("system:read")),
) -> NginxTestResult:
    ok, output = NginxOps(settings).test_config()
    return NginxTestResult(success=ok, output=output)


@router.post("/nginx/reload", response_model=MessageResponse)
async def nginx_reload(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    token: ApiToken = Depends(require_api_scopes("system:write")),
) -> MessageResponse:
    ok, output = NginxOps(settings).reload()
    log_audit(
        db,
        username=_audit_actor(token),
        action="nginx_reload",
        resource="nginx",
        client_ip=_client_ip(request),
        new_value={"success": ok, "output": output},
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    return MessageResponse(message="Nginx reloaded", detail=output)
