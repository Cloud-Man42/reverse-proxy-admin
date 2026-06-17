from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.schemas import (
    MessageResponse,
    NginxTestResult,
    ProxyAppCreate,
    ProxyAppResponse,
    ProxyAppUpdate,
    TrafficDebugResponse,
    TrafficFlowTestResult,
)
from app.security.ip_allowlist import _client_ip
from app.security.permissions import Permission, require_permission
from app.services.audit_service import log_audit
from app.services.nginx_ops import NginxOps
from app.services.proxy_service import ProxyService
from app.services.traffic_flow_service import TrafficFlowService
from app.services.traffic_debug_service import TrafficDebugService

router = APIRouter(prefix="/proxies", tags=["proxies"])


def get_service(settings: Settings = Depends(get_settings)) -> ProxyService:
    return ProxyService(settings)


@router.get("", response_model=List[ProxyAppResponse])
async def list_proxies(
    service: ProxyService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> List[ProxyAppResponse]:
    return service.list_proxies()


@router.get("/{proxy_id}", response_model=ProxyAppResponse)
async def get_proxy(
    proxy_id: str,
    service: ProxyService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> ProxyAppResponse:
    proxy = service.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found")
    return proxy


@router.post("", response_model=ProxyAppResponse)
async def create_proxy(
    payload: ProxyAppCreate,
    request: Request,
    db: Session = Depends(get_db),
    service: ProxyService = Depends(get_service),
    user: User = Depends(require_permission(Permission.CREATE)),
) -> ProxyAppResponse:
    ok, output, proxy = service.create_proxy(payload)
    log_audit(
        db,
        username=user.username,
        action="create_proxy",
        resource=payload.name,
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    if not ok or not proxy:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    return proxy


@router.put("/{proxy_id}", response_model=ProxyAppResponse)
async def update_proxy(
    proxy_id: str,
    payload: ProxyAppUpdate,
    request: Request,
    db: Session = Depends(get_db),
    service: ProxyService = Depends(get_service),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> ProxyAppResponse:
    old = service.get_proxy(proxy_id)
    ok, output, proxy = service.update_proxy(proxy_id, payload)
    log_audit(
        db,
        username=user.username,
        action="update_proxy",
        resource=proxy_id,
        client_ip=_client_ip(request),
        old_value=old.model_dump() if old else None,
        new_value=payload.model_dump(),
    )
    if not ok or not proxy:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    return proxy


@router.delete("/{proxy_id}", response_model=MessageResponse)
async def delete_proxy(
    proxy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    service: ProxyService = Depends(get_service),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> MessageResponse:
    old = service.get_proxy(proxy_id)
    ok, output = service.delete_proxy(proxy_id)
    log_audit(
        db,
        username=user.username,
        action="delete_proxy",
        resource=proxy_id,
        client_ip=_client_ip(request),
        old_value=old.model_dump() if old else None,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    return MessageResponse(message="Proxy deleted", detail=output)


@router.post("/{proxy_id}/enable", response_model=ProxyAppResponse)
async def enable_proxy(
    proxy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    service: ProxyService = Depends(get_service),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> ProxyAppResponse:
    ok, output, proxy = service.set_enabled(proxy_id, True)
    log_audit(
        db,
        username=user.username,
        action="enable_proxy",
        resource=proxy_id,
        client_ip=_client_ip(request),
        new_value={"enabled": True},
    )
    if not ok or not proxy:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    return proxy


@router.post("/{proxy_id}/disable", response_model=ProxyAppResponse)
async def disable_proxy(
    proxy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    service: ProxyService = Depends(get_service),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> ProxyAppResponse:
    ok, output, proxy = service.set_enabled(proxy_id, False)
    log_audit(
        db,
        username=user.username,
        action="disable_proxy",
        resource=proxy_id,
        client_ip=_client_ip(request),
        new_value={"enabled": False},
    )
    if not ok or not proxy:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    return proxy


@router.post("/actions/test-config", response_model=NginxTestResult)
async def test_config(
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> NginxTestResult:
    ops = NginxOps(settings)
    ok, output = ops.test_config()
    return NginxTestResult(success=ok, output=output)


@router.post("/actions/test-flow", response_model=TrafficFlowTestResult)
async def test_flow_draft(
    payload: ProxyAppCreate,
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> TrafficFlowTestResult:
    return TrafficFlowService(settings).test_traffic_flow(payload)


@router.post("/{proxy_id}/test-flow", response_model=TrafficFlowTestResult)
async def test_flow_existing(
    proxy_id: str,
    service: ProxyService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> TrafficFlowTestResult:
    proxy = service.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found")
    payload = ProxyAppUpdate(
        name=proxy.name,
        domains=proxy.domains,
        routes=proxy.routes,
        custom_headers=proxy.custom_headers,
        max_body_size=proxy.max_body_size,
        basic_auth_enabled=proxy.basic_auth_enabled,
        force_https=proxy.force_https,
        enabled=proxy.enabled,
    )
    return TrafficFlowService(settings).test_traffic_flow(payload)


@router.get("/{proxy_id}/traffic-debug", response_model=TrafficDebugResponse)
async def proxy_traffic_debug(
    proxy_id: str,
    lines: int = Query(default=100, ge=1, le=500),
    service: ProxyService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> TrafficDebugResponse:
    if not service.get_proxy(proxy_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found")
    return TrafficDebugService(settings).read_proxy_traffic(proxy_id, lines=lines)
