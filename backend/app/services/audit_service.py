import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_audit(
    db: Session,
    *,
    username: str,
    action: str,
    resource: str,
    client_ip: str,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
) -> AuditLog:
    entry = AuditLog(
        username=username,
        action=action,
        resource=resource,
        old_value=json.dumps(old_value, default=str) if old_value is not None else None,
        new_value=json.dumps(new_value, default=str) if new_value is not None else None,
        client_ip=client_ip,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
