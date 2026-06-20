import json
import shutil
from datetime import datetime, timedelta
from typing import Optional

import psutil
from sqlalchemy.orm import Session, joinedload

from app.config import Settings
from app.models.notification import NotificationLog, NotificationRecipient
from app.models.status_report import StatusReportSettings
from app.schemas import (
    NotificationEventType,
    StatusReportSection,
    StatusReportSettingsResponse,
    StatusReportSettingsUpdate,
)
from app.services.backend_pool_service import BackendPoolService
from app.services.certificate_service import CertificateService
from app.services.proxy_service import ProxyService
from app.services.proxy_traffic_service import ProxyTrafficService
from app.services.smtp_service import SmtpService

DEFAULT_SECTIONS = [section.value for section in StatusReportSection]


class StatusReportService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db
        self.smtp = SmtpService(settings, db)
        self.traffic = ProxyTrafficService(settings, db)
        self.proxies = ProxyService(settings, db)
        self.pools = BackendPoolService(settings, db)

    def get_settings(self) -> StatusReportSettingsResponse:
        row = self._get_or_create_settings()
        return self._to_response(row)

    def update_settings(self, payload: StatusReportSettingsUpdate) -> StatusReportSettingsResponse:
        row = self._get_or_create_settings()
        data = payload.model_dump(exclude_unset=True)
        if "enabled_sections" in data and data["enabled_sections"] is not None:
            row.enabled_sections = json.dumps([section.value for section in data["enabled_sections"]])
            data.pop("enabled_sections")
        for key, value in data.items():
            setattr(row, key, value)
        row.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def maybe_send_scheduled(self) -> int:
        row = self._get_or_create_settings()
        if not row.enabled:
            return 0
        now = datetime.utcnow()
        if row.last_sent_at:
            next_due = row.last_sent_at + timedelta(hours=row.interval_hours)
            if now < next_due:
                return 0
        return self.send_report()

    def send_report(self) -> int:
        row = self._get_or_create_settings()
        sections = self._enabled_sections(row)
        body = self.build_report(sections)
        subject = f"Reverse Proxy Status Report ({datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})"
        recipients = self._report_recipients()
        if not recipients:
            return 0

        sent = 0
        for email in recipients:
            ok, detail = self.smtp.send_email([email], subject, body)
            self.db.add(
                NotificationLog(
                    event_type=NotificationEventType.STATUS_REPORT.value,
                    subject=subject,
                    recipient_email=email,
                    status="sent" if ok else "failed",
                    detail=detail,
                    dedupe_key=None,
                )
            )
            if ok:
                sent += 1
        row.last_sent_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        self.db.commit()
        return sent

    def build_report(self, sections: list[str]) -> str:
        lines = ["Reverse Proxy Admin — Status Report", ""]
        if StatusReportSection.PROXY_TRAFFIC.value in sections:
            lines.extend(self._section_proxy_traffic())
        if StatusReportSection.PROXY_STATUS.value in sections:
            lines.extend(self._section_proxy_status())
        if StatusReportSection.LOAD_BALANCER_HEALTH.value in sections:
            lines.extend(self._section_load_balancer_health())
        if StatusReportSection.SSL_CERTIFICATES.value in sections:
            lines.extend(self._section_ssl_certificates())
        if StatusReportSection.SYSTEM_METRICS.value in sections:
            lines.extend(self._section_system_metrics())
        if len(lines) <= 2:
            lines.append("No report sections enabled.")
        return "\n".join(lines)

    def _section_proxy_traffic(self) -> list[str]:
        lines = ["=== Proxy Traffic (last 24h) ==="]
        summaries = self.traffic.list_summary("24h")
        if not summaries:
            lines.append("No proxy apps configured.")
            return lines + [""]
        for item in summaries:
            lines.append(
                f"- {item.proxy_name}: "
                f"In {_format_bytes(item.bytes_in)}, "
                f"Out {_format_bytes(item.bytes_out)}, "
                f"Connections {item.connections}"
            )
        return lines + [""]

    def _section_proxy_status(self) -> list[str]:
        lines = ["=== Proxy Status ==="]
        proxies = self.proxies.list_proxies()
        if not proxies:
            lines.append("No proxy apps configured.")
            return lines + [""]
        for proxy in proxies:
            state = "enabled" if proxy.enabled else "disabled"
            https = "HTTPS" if proxy.https_enabled else "HTTP"
            lines.append(
                f"- {proxy.name} ({', '.join(proxy.domains)}): {state}, {https}, "
                f"{len(proxy.routes)} route(s)"
            )
        return lines + [""]

    def _section_load_balancer_health(self) -> list[str]:
        lines = ["=== Load Balancer Health ==="]
        pools, _ = self.pools.list_pools(page_size=1000)
        if not pools:
            lines.append("No backend pools configured.")
            return lines + [""]
        for pool in pools:
            healthy = sum(1 for server in pool.servers if server.health_status == "healthy")
            offline = sum(1 for server in pool.servers if server.health_status == "offline")
            lines.append(
                f"- {pool.name} ({pool.load_balancing_method}): "
                f"{healthy} healthy, {offline} offline, {len(pool.servers)} server(s)"
            )
        return lines + [""]

    def _section_ssl_certificates(self) -> list[str]:
        lines = ["=== SSL Certificates ==="]
        certs = CertificateService(self.settings, self.db).list_certificates()
        if not certs:
            lines.append("No certificates found.")
            return lines + [""]
        expiring = [cert for cert in certs if cert.status != "valid"]
        lines.append(f"Total: {len(certs)}, Expiring/invalid: {len(expiring)}")
        for cert in certs[:20]:
            lines.append(
                f"- {cert.name}: {cert.status}, expires {cert.expiry.date().isoformat()}"
            )
        return lines + [""]

    def _section_system_metrics(self) -> list[str]:
        lines = ["=== System Metrics ==="]
        usage = shutil.disk_usage(self.settings.data_dir if self.settings.data_dir.exists() else "/")
        disk_percent = (usage.used / usage.total) * 100 if usage.total else 0
        lines.append(
            f"- Disk: {usage.used / (1024 ** 3):.1f} GB / {usage.total / (1024 ** 3):.1f} GB "
            f"({disk_percent:.1f}%)"
        )
        lines.append(f"- CPU: {psutil.cpu_percent(interval=0.1):.1f}%")
        lines.append(f"- RAM: {psutil.virtual_memory().percent:.1f}%")
        return lines + [""]

    def _report_recipients(self) -> list[str]:
        rows = (
            self.db.query(NotificationRecipient)
            .options(joinedload(NotificationRecipient.preferences))
            .filter(NotificationRecipient.enabled.is_(True))
            .all()
        )
        emails: list[str] = []
        for row in rows:
            pref = row.preferences
            if pref and pref.email_enabled:
                emails.append(row.email)
        return emails

    def _get_or_create_settings(self) -> StatusReportSettings:
        row = self.db.query(StatusReportSettings).first()
        if row:
            return row
        row = StatusReportSettings(
            enabled=False,
            interval_hours=24,
            enabled_sections=json.dumps(DEFAULT_SECTIONS),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def _enabled_sections(self, row: StatusReportSettings) -> list[str]:
        try:
            sections = json.loads(row.enabled_sections or "[]")
        except json.JSONDecodeError:
            sections = []
        return sections or DEFAULT_SECTIONS

    def _to_response(self, row: StatusReportSettings) -> StatusReportSettingsResponse:
        try:
            sections = json.loads(row.enabled_sections or "[]")
        except json.JSONDecodeError:
            sections = DEFAULT_SECTIONS
        return StatusReportSettingsResponse(
            enabled=row.enabled,
            interval_hours=row.interval_hours,
            enabled_sections=sections,
            last_sent_at=row.last_sent_at,
            updated_at=row.updated_at,
        )


def _format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{value} B"
