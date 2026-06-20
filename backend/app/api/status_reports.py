from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.schemas import (
    MessageResponse,
    ProxyTrafficStatsResponse,
    ProxyTrafficSummary,
    StatusReportSettingsResponse,
    StatusReportSettingsUpdate,
)
from app.security.ip_allowlist import _client_ip
from app.security.permissions import Permission, require_permission
from app.services.audit_service import log_audit
from app.services.proxy_traffic_service import ProxyTrafficService
from app.services.status_report_service import StatusReportService

router = APIRouter(prefix="/status-reports", tags=["status-reports"])


def get_service(settings: Settings = Depends(get_settings), db: Session = Depends(get_db)) -> StatusReportService:
    return StatusReportService(settings, db)


@router.get("/settings", response_model=StatusReportSettingsResponse)
async def get_status_report_settings(
    service: StatusReportService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> StatusReportSettingsResponse:
    return service.get_settings()


@router.put("/settings", response_model=StatusReportSettingsResponse)
async def update_status_report_settings(
    payload: StatusReportSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    service: StatusReportService = Depends(get_service),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> StatusReportSettingsResponse:
    result = service.update_settings(payload)
    log_audit(
        db,
        username=user.username,
        action="status_report_settings_update",
        resource="status_reports",
        client_ip=_client_ip(request),
        new_value=payload.model_dump(exclude_unset=True),
    )
    return result


@router.post("/send", response_model=MessageResponse)
async def send_status_report_now(
    request: Request,
    db: Session = Depends(get_db),
    service: StatusReportService = Depends(get_service),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> MessageResponse:
    sent = service.send_report()
    log_audit(
        db,
        username=user.username,
        action="status_report_send",
        resource="status_reports",
        client_ip=_client_ip(request),
        new_value={"sent": sent},
    )
    if sent == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No report sent. Configure SMTP and notification recipients first.",
        )
    return MessageResponse(message=f"Status report sent to {sent} recipient(s)")
