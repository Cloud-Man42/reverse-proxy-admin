from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.schemas import CertificateCreateRequest, CertificateResponse, MessageResponse
from app.security.permissions import Permission, require_permission
from app.security.ip_allowlist import _client_ip
from app.services.audit_service import log_audit
from app.services.certbot_ops import CertbotOps

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get("", response_model=List[CertificateResponse])
async def list_certificates(
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> List[CertificateResponse]:
    return CertbotOps(settings).list_certificates()


@router.post("", response_model=MessageResponse)
async def issue_certificate(
    payload: CertificateCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.CREATE)),
) -> MessageResponse:
    ok, output = CertbotOps(settings).issue_certificate(payload.domain, payload.email)
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
    ok, output = CertbotOps(settings).renew_certificate(cert_name)
    log_audit(
        db,
        username=user.username,
        action="renew_certificate",
        resource=cert_name,
        client_ip=_client_ip(request),
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    return MessageResponse(message="Certificate renewed", detail=output)


@router.post("/actions/dry-run", response_model=MessageResponse)
async def dry_run_renew(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.READ)),
) -> MessageResponse:
    ok, output = CertbotOps(settings).dry_run_renew()
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
