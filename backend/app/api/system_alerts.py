from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.schemas import SystemAlertHistoryResponse, SystemAlertThresholdResponse, SystemAlertThresholdUpdate
from app.security.ip_allowlist import _client_ip
from app.security.permissions import require_admin
from app.services.audit_service import log_audit
from app.services.system_monitor_service import SystemMonitorService

router = APIRouter(prefix="/system-alerts", tags=["system-alerts"])


def get_service(settings: Settings = Depends(get_settings), db: Session = Depends(get_db)) -> SystemMonitorService:
    return SystemMonitorService(settings, db)


@router.get("/thresholds", response_model=SystemAlertThresholdResponse)
async def get_thresholds(
    service: SystemMonitorService = Depends(get_service),
    _user: User = Depends(require_admin),
) -> SystemAlertThresholdResponse:
    return service.get_thresholds()


@router.put("/thresholds", response_model=SystemAlertThresholdResponse)
async def update_thresholds(
    payload: SystemAlertThresholdUpdate,
    request: Request,
    service: SystemMonitorService = Depends(get_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> SystemAlertThresholdResponse:
    old = service.get_thresholds()
    updated = service.update_thresholds(payload)
    log_audit(
        db,
        username=user.username,
        action="system_alert_threshold_update",
        resource="system-alerts",
        client_ip=_client_ip(request),
        old_value=old.model_dump(),
        new_value=updated.model_dump(),
    )
    return updated


@router.get("/history", response_model=list[SystemAlertHistoryResponse])
async def list_alert_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: SystemMonitorService = Depends(get_service),
    _user: User = Depends(require_admin),
) -> list[SystemAlertHistoryResponse]:
    rows, _ = service.list_history(page=page, page_size=page_size)
    return [
        SystemAlertHistoryResponse(
            id=row.id,
            alert_type=row.alert_type,
            metric=row.metric,
            value=row.value,
            threshold=row.threshold,
            status=row.status,
            message=row.message,
            created_at=row.created_at,
        )
        for row in rows
    ]
