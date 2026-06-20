from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.schemas import (
    MessageResponse,
    NotificationEventType,
    NginxTestResult,
    ProxyAppCreate,
    ProxyAppResponse,
    ProxyAppUpdate,
    ProxyRateLimitResponse,
    ProxyRateLimitUpdate,
    ProxyTrafficStatsResponse,
    ProxyTrafficSummary,
    TrafficDebugResponse,
    TrafficFlowTestResult,
)
from app.services.notification_service import NotificationService
from app.security.ip_allowlist import _client_ip
from app.security.permissions import Permission, require_permission
from app.services.audit_service import log_audit
from app.services.nginx_ops import NginxOps
from app.services.proxy_service import ProxyService
from app.services.traffic_flow_service import TrafficFlowService
from app.services.traffic_debug_service import TrafficDebugService
from app.services.proxy_traffic_service import ProxyTrafficService
from app.services.rate_limit_service import RateLimitService

router = APIRouter(prefix="/proxies", tags=["proxies"])


def _dispatch_nginx_failure(
    db: Session,
    settings: Settings,
    failure_stage: str | None,
    output: str,
) -> None:
    if not failure_stage:
        return
    notifications = NotificationService(settings, db)
    if failure_stage == "validation":
        notifications.dispatch_validation_failed(output)
    elif failure_stage == "reload":
        notifications.dispatch_reload_failed(output)


def get_service(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> ProxyService:
    return ProxyService(settings, db)


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
    ok, output, proxy, failure = service.create_proxy(payload, username=user.username)
    if not ok or not proxy:
        _dispatch_nginx_failure(db, get_settings(), failure, output)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    log_audit(
        db,
        username=user.username,
        action="create_proxy",
        resource=payload.name,
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    NotificationService(get_settings(), db).dispatch_proxy_event(NotificationEventType.PROXY_CREATED, payload.name)
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
    ok, output, proxy, failure = service.update_proxy(proxy_id, payload, username=user.username)
    if not ok or not proxy:
        _dispatch_nginx_failure(db, get_settings(), failure, output)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    log_audit(
        db,
        username=user.username,
        action="update_proxy",
        resource=proxy_id,
        client_ip=_client_ip(request),
        old_value=old.model_dump() if old else None,
        new_value=payload.model_dump(),
    )
    NotificationService(get_settings(), db).dispatch_proxy_event(NotificationEventType.PROXY_MODIFIED, payload.name)
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
    ok, output, failure = service.delete_proxy(proxy_id, username=user.username)
    if not ok:
        _dispatch_nginx_failure(db, get_settings(), failure, output)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    log_audit(
        db,
        username=user.username,
        action="delete_proxy",
        resource=proxy_id,
        client_ip=_client_ip(request),
        old_value=old.model_dump() if old else None,
    )
    NotificationService(get_settings(), db).dispatch_proxy_event(NotificationEventType.PROXY_DELETED, proxy_id)
    return MessageResponse(message="Proxy deleted", detail=output)


@router.post("/{proxy_id}/enable", response_model=ProxyAppResponse)
async def enable_proxy(
    proxy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    service: ProxyService = Depends(get_service),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> ProxyAppResponse:
    ok, output, proxy, failure = service.set_enabled(proxy_id, True)
    log_audit(
        db,
        username=user.username,
        action="enable_proxy",
        resource=proxy_id,
        client_ip=_client_ip(request),
        new_value={"enabled": True},
    )
    if not ok or not proxy:
        _dispatch_nginx_failure(db, get_settings(), failure, output)
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
    ok, output, proxy, failure = service.set_enabled(proxy_id, False)
    log_audit(
        db,
        username=user.username,
        action="disable_proxy",
        resource=proxy_id,
        client_ip=_client_ip(request),
        new_value={"enabled": False},
    )
    if not ok or not proxy:
        _dispatch_nginx_failure(db, get_settings(), failure, output)
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


@router.get("/{proxy_id}/rate-limit", response_model=ProxyRateLimitResponse)
async def get_proxy_rate_limit(
    proxy_id: str,
    service: ProxyService = Depends(get_service),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> ProxyRateLimitResponse:
    if not service.get_proxy(proxy_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found")
    return RateLimitService(db).get(proxy_id)


@router.put("/{proxy_id}/rate-limit", response_model=ProxyRateLimitResponse)
async def update_proxy_rate_limit(
    proxy_id: str,
    payload: ProxyRateLimitUpdate,
    request: Request,
    db: Session = Depends(get_db),
    service: ProxyService = Depends(get_service),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> ProxyRateLimitResponse:
    proxy = service.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found")
    result = RateLimitService(db).upsert(proxy_id, payload)
    from app.schemas import ProxyAppUpdate

    update_payload = ProxyAppUpdate(
        name=proxy.name,
        domains=proxy.domains,
        routes=proxy.routes,
        custom_headers=proxy.custom_headers,
        max_body_size=proxy.max_body_size,
        basic_auth_enabled=proxy.basic_auth_enabled,
        force_https=proxy.force_https,
        enabled=proxy.enabled,
        notes=proxy.notes,
    )
    ok, output, _, failure = service.update_proxy(proxy_id, update_payload)
    if not ok:
        _dispatch_nginx_failure(db, get_settings(), failure, output)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    log_audit(
        db,
        username=user.username,
        action="update_proxy_rate_limit",
        resource=proxy_id,
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    return result


@router.get("/traffic/summary", response_model=list[ProxyTrafficSummary])
async def proxy_traffic_summary(
    range: str = Query(default="24h", pattern="^(24h|7d|30d)$"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[ProxyTrafficSummary]:
    return ProxyTrafficService(settings, db).list_summary(range)


@router.get("/{proxy_id}/traffic-stats", response_model=ProxyTrafficStatsResponse)
async def proxy_traffic_stats(
    proxy_id: str,
    range: str = Query(default="24h", pattern="^(24h|7d|30d)$"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> ProxyTrafficStatsResponse:
    stats = ProxyTrafficService(settings, db).get_proxy_stats(proxy_id, range)
    if not stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found")
    return stats


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
