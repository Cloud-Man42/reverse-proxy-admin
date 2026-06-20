import shutil
from typing import Optional

import psutil
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.system_alert import SystemAlertHistory, SystemAlertThreshold
from app.schemas import NotificationEventType, SystemAlertThresholdResponse, SystemAlertThresholdUpdate
from app.services.notification_service import NotificationService


class SystemMonitorService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db
        self.notifications = NotificationService(settings, db)
        self._active_alerts: dict[str, bool] = {}

    def _get_or_create_thresholds(self) -> SystemAlertThreshold:
        row = self.db.query(SystemAlertThreshold).first()
        if row:
            return row
        row = SystemAlertThreshold()
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_thresholds(self) -> SystemAlertThresholdResponse:
        row = self._get_or_create_thresholds()
        return SystemAlertThresholdResponse(
            cpu_percent=row.cpu_percent,
            ram_percent=row.ram_percent,
            disk_percent=row.disk_percent,
            enabled=row.enabled,
        )

    def update_thresholds(self, payload: SystemAlertThresholdUpdate) -> SystemAlertThresholdResponse:
        row = self._get_or_create_thresholds()
        row.cpu_percent = payload.cpu_percent
        row.ram_percent = payload.ram_percent
        row.disk_percent = payload.disk_percent
        row.enabled = payload.enabled
        self.db.commit()
        return self.get_thresholds()

    def list_history(self, page: int = 1, page_size: int = 50) -> tuple[list[SystemAlertHistory], int]:
        query = self.db.query(SystemAlertHistory)
        total = query.count()
        rows = (
            query.order_by(SystemAlertHistory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def run_checks(self) -> int:
        thresholds = self._get_or_create_thresholds()
        if not thresholds.enabled:
            return 0
        alerts = 0
        cpu = psutil.cpu_percent(interval=0.5)
        alerts += self._evaluate("cpu", cpu, thresholds.cpu_percent)
        ram = psutil.virtual_memory().percent
        alerts += self._evaluate("ram", ram, thresholds.ram_percent)
        usage = shutil.disk_usage(self.settings.data_dir if self.settings.data_dir.exists() else "/")
        disk_percent = (usage.used / usage.total) * 100 if usage.total else 0
        alerts += self._evaluate("disk", disk_percent, thresholds.disk_percent)
        return alerts

    def _evaluate(self, metric: str, value: float, threshold: float) -> int:
        key = f"{metric}_high"
        breached = value >= threshold
        was_active = self._active_alerts.get(key, False)
        if breached and not was_active:
            message = f"{metric.upper()} usage {value:.1f}% exceeded threshold {threshold:.1f}%"
            history = SystemAlertHistory(
                alert_type="system_threshold",
                metric=metric,
                value=value,
                threshold=threshold,
                status="breached",
                message=message,
            )
            self.db.add(history)
            self.notifications.dispatch(
                NotificationEventType.SYSTEM_ERROR,
                f"System Alert: {metric.upper()}",
                message,
                severity="critical",
            )
            self._active_alerts[key] = True
            self.db.commit()
            return 1
        if not breached and was_active:
            message = f"{metric.upper()} usage recovered to {value:.1f}%"
            history = SystemAlertHistory(
                alert_type="system_threshold",
                metric=metric,
                value=value,
                threshold=threshold,
                status="recovered",
                message=message,
            )
            self.db.add(history)
            self._active_alerts[key] = False
            self.db.commit()
        return 0

