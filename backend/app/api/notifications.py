from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.schemas import (
    MessageResponse,
    NotificationLogResponse,
    NotificationRecipientCreate,
    NotificationRecipientResponse,
    NotificationRecipientUpdate,
)
from app.security.ip_allowlist import _client_ip
from app.security.permissions import require_admin
from app.services.audit_service import log_audit
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_service(settings: Settings = Depends(get_settings), db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(settings, db)


@router.get("/recipients", response_model=list[NotificationRecipientResponse])
async def list_recipients(
    service: NotificationService = Depends(get_service),
    _user: User = Depends(require_admin),
) -> list[NotificationRecipientResponse]:
    return service.list_recipients()


@router.post("/recipients", response_model=NotificationRecipientResponse, status_code=status.HTTP_201_CREATED)
async def create_recipient(
    payload: NotificationRecipientCreate,
    request: Request,
    service: NotificationService = Depends(get_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> NotificationRecipientResponse:
    recipient = service.create_recipient(payload)
    log_audit(
        db,
        username=user.username,
        action="notification_recipient_create",
        resource=f"recipient:{recipient.id}",
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    return recipient


@router.put("/recipients/{recipient_id}", response_model=NotificationRecipientResponse)
async def update_recipient(
    recipient_id: int,
    payload: NotificationRecipientUpdate,
    request: Request,
    service: NotificationService = Depends(get_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> NotificationRecipientResponse:
    existing = next((r for r in service.list_recipients() if r.id == recipient_id), None)
    recipient = service.update_recipient(recipient_id, payload)
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")
    log_audit(
        db,
        username=user.username,
        action="notification_recipient_update",
        resource=f"recipient:{recipient_id}",
        client_ip=_client_ip(request),
        old_value=existing.model_dump() if existing else None,
        new_value=payload.model_dump(exclude_unset=True),
    )
    return recipient


@router.delete("/recipients/{recipient_id}", response_model=MessageResponse)
async def delete_recipient(
    recipient_id: int,
    request: Request,
    service: NotificationService = Depends(get_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> MessageResponse:
    existing = next((r for r in service.list_recipients() if r.id == recipient_id), None)
    if not service.delete_recipient(recipient_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")
    log_audit(
        db,
        username=user.username,
        action="notification_recipient_delete",
        resource=f"recipient:{recipient_id}",
        client_ip=_client_ip(request),
        old_value=existing.model_dump() if existing else None,
    )
    return MessageResponse(message="Recipient deleted")


@router.get("/log", response_model=list[NotificationLogResponse])
async def list_notification_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: NotificationService = Depends(get_service),
    _user: User = Depends(require_admin),
) -> list[NotificationLogResponse]:
    items, _ = service.list_logs(page=page, page_size=page_size)
    return items
