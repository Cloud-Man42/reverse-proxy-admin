from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.api_token import ApiToken
from app.schemas import MessageResponse, NotificationEventType, ProxyAppCreate, ProxyAppResponse, ProxyAppUpdate
from app.security.api_token_auth import require_api_scopes
from app.security.ip_allowlist import _client_ip
from app.services.audit_service import log_audit
from app.services.notification_service import NotificationService
from app.services.proxy_service import ProxyService

router = APIRouter(prefix="/proxy-hosts")


def get_service(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> ProxyService:
    return ProxyService(settings, db)


def _audit_actor(token: ApiToken) -> str:
    return f"token:{token.name}"


@router.get("", response_model=List[ProxyAppResponse])
async def list_proxy_hosts(
    service: ProxyService = Depends(get_service),
    _token: ApiToken = Depends(require_api_scopes("proxies:read")),
) -> List[ProxyAppResponse]:
    return service.list_proxies()


@router.get("/{proxy_id}", response_model=ProxyAppResponse)
async def get_proxy_host(
    proxy_id: str,
    service: ProxyService = Depends(get_service),
    _token: ApiToken = Depends(require_api_scopes("proxies:read")),
) -> ProxyAppResponse:
    proxy = service.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found")
    return proxy


@router.post("", response_model=ProxyAppResponse, status_code=status.HTTP_201_CREATED)
async def create_proxy_host(
    payload: ProxyAppCreate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    service: ProxyService = Depends(get_service),
    token: ApiToken = Depends(require_api_scopes("proxies:write")),
) -> ProxyAppResponse:
    ok, output, proxy, failure = service.create_proxy(payload)
    if not ok or not proxy:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    log_audit(
        db,
        username=_audit_actor(token),
        action="create_proxy",
        resource=payload.name,
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    NotificationService(settings, db).dispatch_proxy_event(NotificationEventType.PROXY_CREATED, payload.name)
    return proxy


@router.put("/{proxy_id}", response_model=ProxyAppResponse)
async def update_proxy_host(
    proxy_id: str,
    payload: ProxyAppUpdate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    service: ProxyService = Depends(get_service),
    token: ApiToken = Depends(require_api_scopes("proxies:write")),
) -> ProxyAppResponse:
    old = service.get_proxy(proxy_id)
    ok, output, proxy, _failure = service.update_proxy(proxy_id, payload)
    if not ok or not proxy:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    log_audit(
        db,
        username=_audit_actor(token),
        action="update_proxy",
        resource=proxy_id,
        client_ip=_client_ip(request),
        old_value=old.model_dump() if old else None,
        new_value=payload.model_dump(),
    )
    NotificationService(settings, db).dispatch_proxy_event(NotificationEventType.PROXY_MODIFIED, payload.name)
    return proxy


@router.delete("/{proxy_id}", response_model=MessageResponse)
async def delete_proxy_host(
    proxy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    service: ProxyService = Depends(get_service),
    token: ApiToken = Depends(require_api_scopes("proxies:write")),
) -> MessageResponse:
    old = service.get_proxy(proxy_id)
    ok, output, _failure = service.delete_proxy(proxy_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    log_audit(
        db,
        username=_audit_actor(token),
        action="delete_proxy",
        resource=proxy_id,
        client_ip=_client_ip(request),
        old_value=old.model_dump() if old else None,
    )
    NotificationService(settings, db).dispatch_proxy_event(NotificationEventType.PROXY_DELETED, proxy_id)
    return MessageResponse(message="Proxy deleted", detail=output)
