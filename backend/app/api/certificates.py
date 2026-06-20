from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.schemas import (
    CertificateCreateRequest,
    CertificateRenewalLogResponse,
    CertificateResponse,
    CertificateSettingsResponse,
    MessageResponse,
)
from app.security.permissions import Permission, require_permission
from app.security.ip_allowlist import _client_ip
from app.services.audit_service import log_audit
from app.services.certbot_ops import CertbotOps
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get("", response_model=List[CertificateResponse])
async def list_certificates(
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> List[CertificateResponse]:
    return CertbotOps(settings).list_certificates()


@router.get("/settings", response_model=CertificateSettingsResponse)
async def certificate_settings(
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> CertificateSettingsResponse:
    default_email, configured = CertbotOps(settings).get_settings_info()
    return CertificateSettingsResponse(default_email=default_email, email_configured=configured)


@router.get("/renewal-history", response_model=List[CertificateRenewalLogResponse])
async def renewal_history(
    certificate_name: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> List[CertificateRenewalLogResponse]:
    return CertbotOps(settings, db).list_renewal_history(certificate_name=certificate_name, limit=limit)


@router.post("", response_model=MessageResponse)
async def issue_certificate(
    payload: CertificateCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.CREATE)),
) -> MessageResponse:
    ok, output = CertbotOps(settings, db).issue_certificate(payload.domain, payload.email)
    log_audit(
        db,
        username=user.username,
        action="issue_certificate",
        resource=payload.domain,
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    return MessageResponse(message="Certificate issued", detail=output)


@router.post("/{cert_name}/renew", response_model=MessageResponse)
async def renew_certificate(
    cert_name: str,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> MessageResponse:
    ok, output = CertbotOps(settings, db).renew_certificate(cert_name)
    log_audit(
        db,
        username=user.username,
        action="renew_certificate",
        resource=cert_name,
        client_ip=_client_ip(request),
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    NotificationService(settings, db).dispatch_ssl_renewed(cert_name)
    return MessageResponse(message="Certificate renewed", detail=output)


@router.post("/actions/dry-run", response_model=MessageResponse)
async def dry_run_renew(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.READ)),
) -> MessageResponse:
    ok, output = CertbotOps(settings, db).dry_run_renew()
    log_audit(
        db,
        username=user.username,
        action="certbot_dry_run",
        resource="all",
        client_ip=_client_ip(request),
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    return MessageResponse(message="Dry run completed", detail=output)
