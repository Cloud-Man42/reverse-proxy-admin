from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.schemas import (
    ConfigVersionCompareResponse,
    ConfigVersionDetailResponse,
    ConfigVersionResponse,
    ConfigVersionRollbackResponse,
)
from app.security.ip_allowlist import _client_ip
from app.security.permissions import Permission, require_permission
from app.services.audit_service import log_audit
from app.services.config_version_service import ConfigVersionService

router = APIRouter(prefix="/config-versions", tags=["config-versions"])


def get_service(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> ConfigVersionService:
    return ConfigVersionService(settings, db)


@router.get("", response_model=List[ConfigVersionResponse])
async def list_config_versions(
    resource_type: Optional[str] = Query(default=None),
    resource_id: Optional[str] = Query(default=None),
    service: ConfigVersionService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> List[ConfigVersionResponse]:
    return service.list_versions(resource_type=resource_type, resource_id=resource_id)


@router.get("/compare", response_model=ConfigVersionCompareResponse)
async def compare_config_versions(
    id1: int = Query(..., ge=1),
    id2: int = Query(..., ge=1),
    service: ConfigVersionService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> ConfigVersionCompareResponse:
    result = service.compare(id1, id2)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both versions not found")
    return result


@router.get("/{version_id}", response_model=ConfigVersionDetailResponse)
async def get_config_version(
    version_id: int,
    service: ConfigVersionService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> ConfigVersionDetailResponse:
    row = service.get_detail(version_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config version not found")
    return ConfigVersionDetailResponse(
        id=row.id,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        version=row.version,
        username=row.username,
        summary=row.summary,
        has_old_config=row.old_config is not None,
        nginx_test_result=row.nginx_test_result,
        created_at=row.created_at,
        old_config=row.old_config,
        new_config=row.new_config,
    )


@router.post("/{version_id}/rollback", response_model=ConfigVersionRollbackResponse)
async def rollback_config_version(
    version_id: int,
    request: Request,
    db: Session = Depends(get_db),
    service: ConfigVersionService = Depends(get_service),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> ConfigVersionRollbackResponse:
    ok, message, version = service.rollback(version_id, user.username)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    log_audit(
        db,
        username=user.username,
        action="config_version_rollback",
        resource=str(version_id),
        client_ip=_client_ip(request),
        new_value={"version_id": version_id, "new_version": version.version if version else None},
    )
    return ConfigVersionRollbackResponse(success=True, message=message, version=version)
