import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.config import Settings
from app.models.backend_server import BackendServer
from app.models.notification import NotificationLog, NotificationPreference, NotificationRecipient
from app.models.user import User
from app.schemas import (
    NotificationEventType,
    NotificationLogResponse,
    NotificationRecipientCreate,
    NotificationRecipientResponse,
    NotificationRecipientUpdate,
)
from app.security.tenant_context import filter_query_by_org, get_current_org
from app.services.smtp_service import SmtpService

CRITICAL_EVENTS = {
    NotificationEventType.BACKEND_OFFLINE,
    NotificationEventType.NGINX_VALIDATION_FAILED,
    NotificationEventType.NGINX_RELOAD_FAILED,
    NotificationEventType.SYSTEM_ERROR,
    NotificationEventType.LOGIN_SECURITY,
    NotificationEventType.SSL_EXPIRING,
}


class NotificationService:
    def __init__(self, settings: Settings, db: Session, user: Optional[User] = None) -> None:
        self.settings = settings
        self.db = db
        self.user = user
        self.smtp = SmtpService(settings, db)

    def _recipient_query(self):
        query = self.db.query(NotificationRecipient).options(joinedload(NotificationRecipient.preferences))
        if self.user:
            query = filter_query_by_org(query, NotificationRecipient, self.user)
        return query

    def _default_org_id(self) -> Optional[int]:
        if self.user:
            return get_current_org(self.user) or self.user.organization_id
        return None

    def list_recipients(self) -> list[NotificationRecipientResponse]:
        rows = self._recipient_query().order_by(NotificationRecipient.name).all()
        return [self._recipient_response(row) for row in rows]

    def create_recipient(self, payload: NotificationRecipientCreate) -> NotificationRecipientResponse:
        recipient = NotificationRecipient(
            name=payload.name,
            email=payload.email,
            enabled=payload.enabled,
            organization_id=self._default_org_id(),
        )
        self.db.add(recipient)
        self.db.flush()
        pref = NotificationPreference(
            recipient_id=recipient.id,
            email_enabled=payload.email_enabled,
            critical_only=payload.critical_only,
            all_notifications=payload.all_notifications,
            enabled_types=json.dumps([t.value for t in payload.enabled_types]),
        )
        self.db.add(pref)
        self.db.commit()
        self.db.refresh(recipient)
        return self._recipient_response(recipient)

    def update_recipient(self, recipient_id: int, payload: NotificationRecipientUpdate) -> Optional[NotificationRecipientResponse]:
        recipient = self._recipient_query().filter(NotificationRecipient.id == recipient_id).first()
        if not recipient:
            return None
        data = payload.model_dump(exclude_unset=True)
        pref_data = {}
        for key in ("email_enabled", "critical_only", "all_notifications", "enabled_types"):
            if key in data:
                pref_data[key] = data.pop(key)
        for key, value in data.items():
            setattr(recipient, key, value)
        if pref_data:
            pref = recipient.preferences or NotificationPreference(recipient_id=recipient.id)
            if "enabled_types" in pref_data and pref_data["enabled_types"] is not None:
                pref.enabled_types = json.dumps([t.value for t in pref_data["enabled_types"]])
                pref_data.pop("enabled_types")
            for key, value in pref_data.items():
                setattr(pref, key, value)
            if not recipient.preferences:
                self.db.add(pref)
        self.db.commit()
        return self._recipient_response(recipient)

    def delete_recipient(self, recipient_id: int) -> bool:
        recipient = self._recipient_query().filter(NotificationRecipient.id == recipient_id).first()
        if not recipient:
            return False
        self.db.delete(recipient)
        self.db.commit()
        return True

    def list_logs(self, page: int = 1, page_size: int = 50) -> tuple[list[NotificationLogResponse], int]:
        query = self.db.query(NotificationLog)
        if self.user and not self.user.is_super_admin():
            org_emails = [row.email for row in self._recipient_query().with_entities(NotificationRecipient.email).all()]
            if org_emails:
                query = query.filter(NotificationLog.recipient_email.in_(org_emails))
            else:
                query = query.filter(NotificationLog.id == -1)
        total = query.count()
        rows = (
            query.order_by(NotificationLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [
            NotificationLogResponse(
                id=row.id,
                event_type=row.event_type,
                subject=row.subject,
                recipient_email=row.recipient_email,
                status=row.status,
                detail=row.detail,
                created_at=row.created_at,
            )
            for row in rows
        ], total

    def dispatch(
        self,
        event_type: NotificationEventType,
        subject: str,
        body: str,
        *,
        severity: str = "info",
        dedupe_key: Optional[str] = None,
    ) -> int:
        if dedupe_key:
            existing = (
                self.db.query(NotificationLog)
                .filter(NotificationLog.dedupe_key == dedupe_key)
                .first()
            )
            if existing:
                return 0
        recipients = self._resolve_recipients(event_type, severity)
        sent = 0
        for email in recipients:
            ok, detail = self.smtp.send_email([email], subject, body)
            log = NotificationLog(
                event_type=event_type.value,
                subject=subject,
                recipient_email=email,
                status="sent" if ok else "failed",
                detail=detail,
                dedupe_key=dedupe_key,
            )
            self.db.add(log)
            if ok:
                sent += 1
        self.db.commit()
        return sent

    def _resolve_recipients(self, event_type: NotificationEventType, severity: str) -> list[str]:
        rows = (
            self.db.query(NotificationRecipient)
            .options(joinedload(NotificationRecipient.preferences))
            .filter(NotificationRecipient.enabled.is_(True))
            .all()
        )
        emails: list[str] = []
        for row in rows:
            pref = row.preferences
            if not pref or not pref.email_enabled:
                continue
            if pref.critical_only and event_type not in CRITICAL_EVENTS:
                continue
            if not pref.all_notifications:
                enabled_types = json.loads(pref.enabled_types or "[]")
                if event_type.value not in enabled_types:
                    continue
            emails.append(row.email)
        return emails

    def dispatch_backend_offline(self, server: BackendServer) -> None:
        pool_name = server.pool.name if server.pool else ""
        self.dispatch(
            NotificationEventType.BACKEND_OFFLINE,
            "Backend Server Offline",
            f"Backend server '{server.name}' ({server.host}:{server.port}) in pool '{pool_name}' is offline.",
            severity="critical",
        )

    def dispatch_backend_restored(self, server: BackendServer) -> None:
        pool_name = server.pool.name if server.pool else ""
        self.dispatch(
            NotificationEventType.BACKEND_RESTORED,
            "Backend Server Restored",
            f"Backend server '{server.name}' ({server.host}:{server.port}) in pool '{pool_name}' is healthy again.",
            severity="info",
        )

    def dispatch_ssl_expiring(self, domain: str, expiry: datetime, days_remaining: int) -> None:
        dedupe_key = f"ssl_expiring:{domain}:{days_remaining}:{datetime.utcnow().date().isoformat()}"
        self.dispatch(
            NotificationEventType.SSL_EXPIRING,
            "SSL Certificate Expiring",
            f"Domain: {domain}\nExpiration Date: {expiry.date().isoformat()}\nDays Remaining: {days_remaining}",
            severity="critical",
            dedupe_key=dedupe_key,
        )

    def dispatch_nginx_failure(self, action: str, output: str) -> None:
        event = (
            NotificationEventType.NGINX_VALIDATION_FAILED
            if "test" in action
            else NotificationEventType.NGINX_RELOAD_FAILED
        )
        self.dispatch(event, f"NGINX {action} failed", output, severity="critical")

    def dispatch_validation_failed(self, output: str) -> None:
        self.dispatch(
            NotificationEventType.NGINX_VALIDATION_FAILED,
            "NGINX config test failed",
            output,
            severity="critical",
        )

    def dispatch_reload_failed(self, output: str) -> None:
        self.dispatch(
            NotificationEventType.NGINX_RELOAD_FAILED,
            "NGINX reload failed",
            output,
            severity="critical",
        )

    def dispatch_ssl_renewed(self, domain: str) -> None:
        self.dispatch(
            NotificationEventType.SSL_RENEWED,
            "SSL Certificate Renewed",
            f"Certificate for '{domain}' was renewed successfully.",
            severity="info",
        )

    def dispatch_proxy_event(self, event_type: NotificationEventType, proxy_name: str) -> None:
        labels = {
            NotificationEventType.PROXY_CREATED: "created",
            NotificationEventType.PROXY_MODIFIED: "modified",
            NotificationEventType.PROXY_DELETED: "deleted",
        }
        self.dispatch(
            event_type,
            f"Proxy Host {labels[event_type].title()}",
            f"Proxy host '{proxy_name}' was {labels[event_type]}.",
            severity="info",
        )

    def dispatch_login_security(self, username: str, client_ip: str, success: bool) -> None:
        if success:
            return
        self.dispatch(
            NotificationEventType.LOGIN_SECURITY,
            "Login Security Event",
            f"Failed login attempt for user '{username}' from IP {client_ip}.",
            severity="critical",
        )

    def _recipient_response(self, row: NotificationRecipient) -> NotificationRecipientResponse:
        pref = row.preferences
        enabled_types = json.loads(pref.enabled_types) if pref else []
        return NotificationRecipientResponse(
            id=row.id,
            name=row.name,
            email=row.email,
            enabled=row.enabled,
            email_enabled=pref.email_enabled if pref else True,
            critical_only=pref.critical_only if pref else False,
            all_notifications=pref.all_notifications if pref else True,
            enabled_types=enabled_types,
            created_at=row.created_at,
        )
