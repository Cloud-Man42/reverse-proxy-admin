from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.metrics import MetricAlertHistory, MetricAlertRule, RequestEvent
from app.models.proxy_traffic import ProxyTrafficAggregate
from app.models.system_alert import SystemAlertHistory
from app.schemas import NotificationEventType
from app.services.health_check_service import HealthCheckService
from app.services.metrics.base import resolve_range
from app.services.metrics_collector_service import ConnectionMetricService
from app.services.notification_service import NotificationService
from app.services.proxy_traffic_service import ProxyTrafficService


class AlertRuleService:
    DEDUPE_MINUTES = 15

    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db
        self.traffic = ProxyTrafficService(settings, db)
        self.notifications = NotificationService(settings, db)

    def list_rules(self) -> list[MetricAlertRule]:
        return self.db.query(MetricAlertRule).order_by(MetricAlertRule.name.asc()).all()

    def get_rule(self, rule_id: int) -> MetricAlertRule | None:
        return self.db.get(MetricAlertRule, rule_id)

    def create_rule(self, payload: dict) -> MetricAlertRule:
        row = MetricAlertRule(**payload)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_rule(self, rule_id: int, payload: dict) -> MetricAlertRule | None:
        row = self.get_rule(rule_id)
        if not row:
            return None
        for key, value in payload.items():
            if value is not None and hasattr(row, key):
                setattr(row, key, value)
        row.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_rule(self, rule_id: int) -> bool:
        row = self.get_rule(rule_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def _recent_fire(self, rule_id: int) -> bool:
        cutoff = datetime.utcnow() - timedelta(minutes=self.DEDUPE_MINUTES)
        return (
            self.db.query(MetricAlertHistory)
            .filter(
                MetricAlertHistory.rule_id == rule_id,
                MetricAlertHistory.status == "fired",
                MetricAlertHistory.created_at >= cutoff,
            )
            .first()
            is not None
        )

    def _fire(self, rule: MetricAlertRule, message: str, metric_value: float | None) -> None:
        if self._recent_fire(rule.id):
            return
        self.db.add(
            MetricAlertHistory(
                rule_id=rule.id,
                alert_type=rule.metric_type,
                severity=rule.severity,
                status="fired",
                message=message,
                metric_value=metric_value,
            )
        )
        self.db.commit()
        if rule.notify_email:
            self.notifications.dispatch(
                NotificationEventType.SYSTEM_ERROR,
                f"Metric alert: {rule.name}",
                message,
                severity=rule.severity,
            )

    def _metric_value(self, rule: MetricAlertRule) -> float | None:
        window = timedelta(minutes=rule.window_minutes)
        start = datetime.utcnow() - window
        if rule.metric_type == "error_rate":
            query = self.db.query(
                func.coalesce(func.sum(ProxyTrafficAggregate.status_4xx), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.status_5xx), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.requests), 0),
            ).filter(ProxyTrafficAggregate.period_start >= start)
            if rule.proxy_id:
                query = query.filter(ProxyTrafficAggregate.proxy_id == rule.proxy_id)
            s4, s5, total = query.one()
            total = int(total)
            return (int(s4) + int(s5)) / total if total else 0.0
        if rule.metric_type == "5xx_count":
            query = self.db.query(func.coalesce(func.sum(ProxyTrafficAggregate.status_5xx), 0)).filter(
                ProxyTrafficAggregate.period_start >= start
            )
            if rule.proxy_id:
                query = query.filter(ProxyTrafficAggregate.proxy_id == rule.proxy_id)
            return float(query.scalar() or 0)
        if rule.metric_type == "response_time_ms":
            query = self.db.query(
                func.coalesce(
                    func.sum(ProxyTrafficAggregate.latency_avg_ms * ProxyTrafficAggregate.requests),
                    0.0,
                ),
                func.coalesce(func.sum(ProxyTrafficAggregate.requests), 0),
            ).filter(ProxyTrafficAggregate.period_start >= start)
            if rule.proxy_id:
                query = query.filter(ProxyTrafficAggregate.proxy_id == rule.proxy_id)
            total_ms, total = query.one()
            total = int(total)
            return float(total_ms) / total if total else 0.0
        if rule.metric_type == "bandwidth_bytes":
            query = self.db.query(
                func.coalesce(func.sum(ProxyTrafficAggregate.bytes_in), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.bytes_out), 0),
            ).filter(ProxyTrafficAggregate.period_start >= start)
            if rule.proxy_id:
                query = query.filter(ProxyTrafficAggregate.proxy_id == rule.proxy_id)
            inbound, outbound = query.one()
            return float(int(inbound) + int(outbound))
        if rule.metric_type == "active_connections":
            latest = ConnectionMetricService(self.settings, self.db).latest()
            return float(latest.active if latest else 0)
        if rule.metric_type == "backend_offline":
            dashboard = HealthCheckService(self.settings, self.db).get_dashboard()
            return float(dashboard.offline)
        return None

    def evaluate_all(self) -> int:
        fired = 0
        for rule in self.list_rules():
            if not rule.enabled:
                continue
            value = self._metric_value(rule)
            if value is None:
                continue
            triggered = value > rule.threshold if rule.condition == "gt" else value < rule.threshold
            if triggered:
                self._fire(rule, f"{rule.metric_type}={value:.2f} threshold={rule.threshold}", value)
                fired += 1
        return fired

    def recent_history(self, limit: int = 20) -> list[MetricAlertHistory]:
        return (
            self.db.query(MetricAlertHistory)
            .order_by(MetricAlertHistory.created_at.desc())
            .limit(limit)
            .all()
        )

    def merge_dashboard_alerts(self, existing: list[dict]) -> list[dict]:
        for row in self.recent_history(10):
            existing.append(
                {
                    "source": "metric_rule",
                    "title": row.alert_type.replace("_", " ").title(),
                    "message": row.message,
                    "status": row.status,
                    "severity": row.severity,
                    "created_at": row.created_at.isoformat(),
                }
            )
        system_rows = (
            self.db.query(SystemAlertHistory)
            .order_by(SystemAlertHistory.created_at.desc())
            .limit(5)
            .all()
        )
        for row in system_rows:
            existing.append(
                {
                    "source": "system",
                    "title": row.alert_type.replace("_", " ").title(),
                    "message": row.message or "",
                    "status": row.status,
                    "severity": "critical" if row.status == "breached" else "info",
                    "created_at": row.created_at.isoformat(),
                }
            )
        return existing
