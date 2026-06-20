from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.api_token import ApiToken
from app.schemas import BackendPoolCreate, BackendPoolResponse, BackendPoolUpdate, MessageResponse
from app.security.api_token_auth import require_api_scopes
from app.security.ip_allowlist import _client_ip
from app.services.audit_service import log_audit
from app.services.backend_pool_service import BackendPoolService

router = APIRouter(prefix="/backend-pools")


def get_pool_service(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> BackendPoolService:
    return BackendPoolService(settings, db)


def _audit_actor(token: ApiToken) -> str:
    return f"token:{token.name}"


@router.get("", response_model=list[BackendPoolResponse])
async def list_backend_pools(
    proxy_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: BackendPoolService = Depends(get_pool_service),
    _token: ApiToken = Depends(require_api_scopes("backend_pools:read")),
) -> list[BackendPoolResponse]:
    items, _ = service.list_pools(proxy_id=proxy_id, page=page, page_size=page_size)
    return items


@router.get("/{pool_id}", response_model=BackendPoolResponse)
async def get_backend_pool(
    pool_id: int,
    service: BackendPoolService = Depends(get_pool_service),
    _token: ApiToken = Depends(require_api_scopes("backend_pools:read")),
) -> BackendPoolResponse:
    pool = service.get_pool(pool_id)
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    return pool


@router.post("", response_model=BackendPoolResponse, status_code=status.HTTP_201_CREATED)
async def create_backend_pool(
    payload: BackendPoolCreate,
    request: Request,
    service: BackendPoolService = Depends(get_pool_service),
    db: Session = Depends(get_db),
    token: ApiToken = Depends(require_api_scopes("backend_pools:write")),
) -> BackendPoolResponse:
    try:
        pool = service.create_pool(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_audit(
        db,
        username=_audit_actor(token),
        action="backend_pool_create",
        resource=f"pool:{pool.id}",
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    return pool


@router.put("/{pool_id}", response_model=BackendPoolResponse)
async def update_backend_pool(
    pool_id: int,
    payload: BackendPoolUpdate,
    request: Request,
    service: BackendPoolService = Depends(get_pool_service),
    db: Session = Depends(get_db),
    token: ApiToken = Depends(require_api_scopes("backend_pools:write")),
) -> BackendPoolResponse:
    old = service.get_pool(pool_id)
    try:
        pool = service.update_pool(pool_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    log_audit(
        db,
        username=_audit_actor(token),
        action="backend_pool_update",
        resource=f"pool:{pool_id}",
        client_ip=_client_ip(request),
        old_value=old.model_dump() if old else None,
        new_value=payload.model_dump(exclude_unset=True),
    )
    return pool


@router.delete("/{pool_id}", response_model=MessageResponse)
async def delete_backend_pool(
    pool_id: int,
    request: Request,
    service: BackendPoolService = Depends(get_pool_service),
    db: Session = Depends(get_db),
    token: ApiToken = Depends(require_api_scopes("backend_pools:write")),
) -> MessageResponse:
    old = service.get_pool(pool_id)
    if not service.delete_pool(pool_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    log_audit(
        db,
        username=_audit_actor(token),
        action="backend_pool_delete",
        resource=f"pool:{pool_id}",
        client_ip=_client_ip(request),
        old_value=old.model_dump() if old else None,
    )
    return MessageResponse(message="Backend pool deleted")
