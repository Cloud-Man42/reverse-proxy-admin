from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.api_token import ApiToken
from app.schemas import (
    CertificateCreateRequest,
    CertificateRenewalLogResponse,
    CertificateResponse,
    CertificateSettingsResponse,
    MessageResponse,
)
from app.security.api_token_auth import require_api_scopes
from app.security.ip_allowlist import _client_ip
from app.services.audit_service import log_audit
from app.services.certbot_ops import CertbotOps

router = APIRouter(prefix="/certificates")


def _audit_actor(token: ApiToken) -> str:
    return f"token:{token.name}"


@router.get("", response_model=List[CertificateResponse])
async def list_certificates(
    settings: Settings = Depends(get_settings),
    _token: ApiToken = Depends(require_api_scopes("certificates:read")),
) -> List[CertificateResponse]:
    return CertbotOps(settings).list_certificates()


@router.get("/settings", response_model=CertificateSettingsResponse)
async def certificate_settings(
    settings: Settings = Depends(get_settings),
    _token: ApiToken = Depends(require_api_scopes("certificates:read")),
) -> CertificateSettingsResponse:
    default_email, configured = CertbotOps(settings).get_settings_info()
    return CertificateSettingsResponse(default_email=default_email, email_configured=configured)


@router.get("/renewal-history", response_model=List[CertificateRenewalLogResponse])
async def renewal_history(
    certificate_name: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _token: ApiToken = Depends(require_api_scopes("certificates:read")),
) -> List[CertificateRenewalLogResponse]:
    return CertbotOps(settings, db).list_renewal_history(certificate_name=certificate_name, limit=limit)


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def issue_certificate(
    payload: CertificateCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    token: ApiToken = Depends(require_api_scopes("certificates:write")),
) -> MessageResponse:
    ok, output = CertbotOps(settings, db).issue_certificate(payload.domain, payload.email)
    log_audit(
        db,
        username=_audit_actor(token),
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
    token: ApiToken = Depends(require_api_scopes("certificates:write")),
) -> MessageResponse:
    ok, output = CertbotOps(settings, db).renew_certificate(cert_name)
    log_audit(
        db,
        username=_audit_actor(token),
        action="renew_certificate",
        resource=cert_name,
        client_ip=_client_ip(request),
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)
    return MessageResponse(message="Certificate renewed", detail=output)
