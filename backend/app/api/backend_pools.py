from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.schemas import (
    AuditLogListResponse,
    BackendPoolCreate,
    BackendPoolResponse,
    BackendPoolUpdate,
    BackendServerCreate,
    BackendServerResponse,
    BackendServerUpdate,
    LoadBalancerSummary,
    MessageResponse,
)
from app.security.ip_allowlist import _client_ip
from app.security.permissions import Permission, require_permission
from app.services.audit_service import log_audit
from app.services.backend_pool_service import BackendPoolService
from app.services.proxy_service import ProxyService

router = APIRouter(prefix="/backend-pools", tags=["backend-pools"])


def get_pool_service(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> BackendPoolService:
    return BackendPoolService(settings, db)


@router.get("", response_model=list[BackendPoolResponse])
async def list_pools(
    proxy_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: BackendPoolService = Depends(get_pool_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[BackendPoolResponse]:
    items, _ = service.list_pools(proxy_id=proxy_id, page=page, page_size=page_size)
    return items


@router.get("/{pool_id}", response_model=BackendPoolResponse)
async def get_pool(
    pool_id: int,
    service: BackendPoolService = Depends(get_pool_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> BackendPoolResponse:
    pool = service.get_pool(pool_id)
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    return pool


@router.post("", response_model=BackendPoolResponse, status_code=status.HTTP_201_CREATED)
async def create_pool(
    payload: BackendPoolCreate,
    request: Request,
    service: BackendPoolService = Depends(get_pool_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.CREATE)),
) -> BackendPoolResponse:
    try:
        pool = service.create_pool(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_audit(
        db,
        username=user.username,
        action="backend_pool_create",
        resource=f"pool:{pool.id}",
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    if payload.proxy_id:
        _rerender_proxy(payload.proxy_id, db, get_settings())
    return pool


@router.put("/{pool_id}", response_model=BackendPoolResponse)
async def update_pool(
    pool_id: int,
    payload: BackendPoolUpdate,
    request: Request,
    service: BackendPoolService = Depends(get_pool_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> BackendPoolResponse:
    existing = service.get_pool(pool_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    pool = service.update_pool(pool_id, payload)
    log_audit(
        db,
        username=user.username,
        action="backend_pool_update",
        resource=f"pool:{pool_id}",
        client_ip=_client_ip(request),
        old_value=existing.model_dump(),
        new_value=payload.model_dump(exclude_unset=True),
    )
    if pool and pool.proxy_id:
        _rerender_proxy(pool.proxy_id, db, get_settings())
    return pool


@router.delete("/{pool_id}", response_model=MessageResponse)
async def delete_pool(
    pool_id: int,
    request: Request,
    service: BackendPoolService = Depends(get_pool_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> MessageResponse:
    existing = service.get_pool(pool_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    proxy_id = existing.proxy_id
    if not service.delete_pool(pool_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    log_audit(
        db,
        username=user.username,
        action="backend_pool_delete",
        resource=f"pool:{pool_id}",
        client_ip=_client_ip(request),
        old_value=existing.model_dump(),
    )
    if proxy_id:
        _rerender_proxy(proxy_id, db, get_settings())
    return MessageResponse(message="Pool deleted")


def _rerender_proxy(proxy_id: str, db: Session, settings: Settings) -> None:
    proxy = ProxyService(settings, db).get_proxy(proxy_id)
    if not proxy:
        return
    from app.schemas import ProxyAppUpdate

    ProxyService(settings, db).update_proxy(proxy_id, ProxyAppUpdate(**proxy.model_dump()))


router_servers = APIRouter(prefix="/backend-servers", tags=["backend-servers"])


@router_servers.get("", response_model=list[BackendServerResponse])
async def list_servers(
    pool_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: BackendPoolService = Depends(get_pool_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[BackendServerResponse]:
    items, _ = service.list_servers(pool_id=pool_id, page=page, page_size=page_size)
    return items


@router_servers.post("", response_model=BackendServerResponse, status_code=status.HTTP_201_CREATED)
async def create_server(
    payload: BackendServerCreate,
    request: Request,
    service: BackendPoolService = Depends(get_pool_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.CREATE)),
) -> BackendServerResponse:
    try:
        server = service.create_server(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    pool = service.get_pool(payload.pool_id)
    log_audit(
        db,
        username=user.username,
        action="backend_server_create",
        resource=f"server:{server.id}",
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    if pool and pool.proxy_id:
        _rerender_proxy(pool.proxy_id, db, get_settings())
    return server


@router_servers.put("/{server_id}", response_model=BackendServerResponse)
async def update_server(
    server_id: int,
    payload: BackendServerUpdate,
    request: Request,
    service: BackendPoolService = Depends(get_pool_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> BackendServerResponse:
    servers, _ = service.list_servers(page_size=1000)
    existing = next((s for s in servers if s.id == server_id), None)
    server = service.update_server(server_id, payload)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    pool = service.get_pool(server.pool_id)
    log_audit(
        db,
        username=user.username,
        action="backend_server_update",
        resource=f"server:{server_id}",
        client_ip=_client_ip(request),
        old_value=existing.model_dump() if existing else None,
        new_value=payload.model_dump(exclude_unset=True),
    )
    if pool and pool.proxy_id:
        _rerender_proxy(pool.proxy_id, db, get_settings())
    return server


@router_servers.delete("/{server_id}", response_model=MessageResponse)
async def delete_server(
    server_id: int,
    request: Request,
    service: BackendPoolService = Depends(get_pool_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> MessageResponse:
    servers, _ = service.list_servers(page_size=1000)
    existing = next((s for s in servers if s.id == server_id), None)
    pool_id = existing.pool_id if existing else None
    if not service.delete_server(server_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    log_audit(
        db,
        username=user.username,
        action="backend_server_delete",
        resource=f"server:{server_id}",
        client_ip=_client_ip(request),
        old_value=existing.model_dump() if existing else None,
    )
    if pool_id:
        pool = service.get_pool(pool_id)
        if pool and pool.proxy_id:
            _rerender_proxy(pool.proxy_id, db, get_settings())
    return MessageResponse(message="Server deleted")


load_balancers_router = APIRouter(prefix="/load-balancers", tags=["load-balancers"])


@load_balancers_router.get("", response_model=list[LoadBalancerSummary])
async def list_load_balancers(
    service: BackendPoolService = Depends(get_pool_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[LoadBalancerSummary]:
    return service.list_load_balancers()
