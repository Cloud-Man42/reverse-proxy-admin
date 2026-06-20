import csv
import io
import json
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.security_event import SecurityEvent
from app.schemas import SecurityEventResponse
from app.security.tenant_context import filter_query_by_org
from app.models.user import User


class SecurityEventService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log(
        self,
        *,
        event_type: str,
        source: str,
        message: str,
        client_ip: Optional[str] = None,
        proxy_id: Optional[str] = None,
    ) -> SecurityEvent:
        event = SecurityEvent(
            event_type=event_type,
            source=source,
            client_ip=client_ip,
            proxy_id=proxy_id,
            message=message,
            created_at=datetime.utcnow(),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_events(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        proxy_id: Optional[str] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> Tuple[List[SecurityEventResponse], int]:
        query = self.db.query(SecurityEvent)
        if event_type:
            query = query.filter(SecurityEvent.event_type == event_type)
        if source:
            query = query.filter(SecurityEvent.source == source)
        if proxy_id:
            query = query.filter(SecurityEvent.proxy_id == proxy_id)
        if from_dt:
            query = query.filter(SecurityEvent.created_at >= from_dt)
        if to_dt:
            query = query.filter(SecurityEvent.created_at <= to_dt)
        total = query.count()
        rows = (
            query.order_by(SecurityEvent.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [self._to_response(row) for row in rows], total

    def export_events(
        self,
        *,
        format: str,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> Tuple[str, str, str]:
        items, _ = self.list_events(
            page=1,
            page_size=100000,
            event_type=event_type,
            source=source,
            from_dt=from_dt,
            to_dt=to_dt,
        )
        if format == "csv":
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["id", "event_type", "source", "client_ip", "proxy_id", "message", "created_at"])
            for item in items:
                writer.writerow(
                    [
                        item.id,
                        item.event_type,
                        item.source,
                        item.client_ip or "",
                        item.proxy_id or "",
                        item.message,
                        item.created_at.isoformat(),
                    ]
                )
            return buffer.getvalue(), "text/csv", "security-events.csv"
        payload = json.dumps([item.model_dump(mode="json") for item in items], indent=2)
        return payload, "application/json", "security-events.json"

    @staticmethod
    def _to_response(row: SecurityEvent) -> SecurityEventResponse:
        return SecurityEventResponse(
            id=row.id,
            event_type=row.event_type,
            source=row.source,
            client_ip=row.client_ip,
            proxy_id=row.proxy_id,
            message=row.message,
            created_at=row.created_at,
        )


class AuditExportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def export(
        self,
        user: User,
        *,
        format: str,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        query = filter_query_by_org(self.db.query(AuditLog), AuditLog, user)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource:
            query = query.filter(AuditLog.resource.contains(resource))
        if from_dt:
            query = query.filter(AuditLog.created_at >= from_dt)
        if to_dt:
            query = query.filter(AuditLog.created_at <= to_dt)
        entries = query.order_by(AuditLog.created_at.desc()).limit(100000).all()

        if format == "csv":
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["id", "username", "action", "resource", "client_ip", "old_value", "new_value", "created_at"])
            for entry in entries:
                writer.writerow(
                    [
                        entry.id,
                        entry.username,
                        entry.action,
                        entry.resource,
                        entry.client_ip,
                        entry.old_value or "",
                        entry.new_value or "",
                        entry.created_at.isoformat(),
                    ]
                )
            return buffer.getvalue(), "text/csv", "audit-log.csv"

        payload = json.dumps(
            [
                {
                    "id": entry.id,
                    "username": entry.username,
                    "action": entry.action,
                    "resource": entry.resource,
                    "client_ip": entry.client_ip,
                    "old_value": entry.old_value,
                    "new_value": entry.new_value,
                    "created_at": entry.created_at.isoformat(),
                }
                for entry in entries
            ],
            indent=2,
        )
        return payload, "application/json", "audit-log.json"
