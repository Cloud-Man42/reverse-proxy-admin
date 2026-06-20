import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User
from app.security.tenant_context import get_current_org


def log_audit(
    db: Session,
    *,
    username: str,
    action: str,
    resource: str,
    client_ip: str,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    organization_id: Optional[int] = None,
    user: Optional[User] = None,
) -> AuditLog:
    org_id = organization_id
    if org_id is None and user is not None:
        org_id = get_current_org(user) or user.organization_id
    entry = AuditLog(
        username=username,
        action=action,
        resource=resource,
        old_value=json.dumps(old_value, default=str) if old_value is not None else None,
        new_value=json.dumps(new_value, default=str) if new_value is not None else None,
        client_ip=client_ip,
        organization_id=org_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
