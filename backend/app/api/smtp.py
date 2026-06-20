from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from app.schemas import CertbotEmailStr
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.schemas import MessageResponse, SmtpSettingsResponse, SmtpSettingsUpdate, SmtpTestResponse
from app.security.ip_allowlist import _client_ip
from app.security.permissions import require_admin
from app.services.audit_service import log_audit
from app.services.smtp_service import SmtpService

router = APIRouter(prefix="/smtp", tags=["smtp"])


def get_service(settings: Settings = Depends(get_settings), db: Session = Depends(get_db)) -> SmtpService:
    return SmtpService(settings, db)


@router.get("", response_model=SmtpSettingsResponse)
async def get_smtp_settings(
    service: SmtpService = Depends(get_service),
    _user: User = Depends(require_admin),
) -> SmtpSettingsResponse:
    return service.get_settings()


@router.put("", response_model=SmtpSettingsResponse)
async def update_smtp_settings(
    payload: SmtpSettingsUpdate,
    request: Request,
    service: SmtpService = Depends(get_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> SmtpSettingsResponse:
    old = service.get_settings()
    try:
        updated = service.update_settings(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_audit(
        db,
        username=user.username,
        action="smtp_settings_update",
        resource="smtp",
        client_ip=_client_ip(request),
        old_value=old.model_dump(),
        new_value=updated.model_dump(),
    )
    return updated


@router.post("/test-connection", response_model=SmtpTestResponse)
async def test_smtp_connection(
    service: SmtpService = Depends(get_service),
    _user: User = Depends(require_admin),
) -> SmtpTestResponse:
    return service.test_connection()


class TestEmailRequest(BaseModel):
    email: CertbotEmailStr


@router.post("/send-test", response_model=SmtpTestResponse)
async def send_test_email(
    payload: TestEmailRequest,
    service: SmtpService = Depends(get_service),
    _user: User = Depends(require_admin),
) -> SmtpTestResponse:
    return service.send_test_email(payload.email)
