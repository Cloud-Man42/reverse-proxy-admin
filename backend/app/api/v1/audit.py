from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.api_token import ApiToken
from app.models.audit import AuditLog
from app.schemas import AuditLogListResponse, AuditLogResponse
from app.security.api_token_auth import require_api_scopes

router = APIRouter(prefix="/audit")


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    resource: Optional[str] = None,
    _token: ApiToken = Depends(require_api_scopes("audit:read")),
) -> AuditLogListResponse:
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource:
        query = query.filter(AuditLog.resource.contains(resource))
    total = query.count()
    entries = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AuditLogListResponse(
        items=[
            AuditLogResponse(
                id=entry.id,
                username=entry.username,
                action=entry.action,
                resource=entry.resource,
                old_value=entry.old_value,
                new_value=entry.new_value,
                client_ip=entry.client_ip,
                created_at=entry.created_at,
            )
            for entry in entries
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
