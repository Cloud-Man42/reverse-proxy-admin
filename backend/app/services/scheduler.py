from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import Settings
from app.db import SessionLocal
from app.services.health_check_service import HealthCheckService
from app.services.nginx_regen_service import NginxRegenService
from app.services.proxy_traffic_service import ProxyTrafficService
from app.services.ssl_alert_service import SslAlertService
from app.services.status_report_service import StatusReportService
from app.services.system_monitor_service import SystemMonitorService
from app.services.threat_feed_service import ThreatFeedService
from app.services.metrics_collector_service import (
    BackendMetricCollector,
    ConnectionMetricService,
    MetricsRetentionService,
)

_scheduler: BackgroundScheduler | None = None


def _run_health_checks(settings: Settings) -> None:
    db = SessionLocal()
    try:
        HealthCheckService(settings, db).run_all()
        NginxRegenService(settings, db).process_pending()
    finally:
        db.close()


def _run_nginx_regen(settings: Settings) -> None:
    db = SessionLocal()
    try:
        NginxRegenService(settings, db).process_pending()
    finally:
        db.close()


def _run_system_monitor(settings: Settings) -> None:
    db = SessionLocal()
    try:
        SystemMonitorService(settings, db).run_checks()
    finally:
        db.close()


def _run_ssl_alerts(settings: Settings) -> None:
    db = SessionLocal()
    try:
        SslAlertService(settings, db).run_daily_checks()
    finally:
        db.close()


def _run_health_rollup(settings: Settings) -> None:
    db = SessionLocal()
    try:
        HealthCheckService(settings, db).rollup_aggregates()
    finally:
        db.close()


def _run_proxy_traffic_collect(settings: Settings) -> None:
    db = SessionLocal()
    try:
        ProxyTrafficService(settings, db).collect_all()
    finally:
        db.close()


def _run_status_reports(settings: Settings) -> None:
    db = SessionLocal()
    try:
        StatusReportService(settings, db).maybe_send_scheduled()
    finally:
        db.close()


def _run_metrics_retention(settings: Settings) -> None:
    db = SessionLocal()
    try:
        MetricsRetentionService(db).cleanup()
    finally:
        db.close()


def _run_connection_metrics(settings: Settings) -> None:
    db = SessionLocal()
    try:
        ConnectionMetricService(settings, db).collect()
    finally:
        db.close()


def _run_backend_metrics(settings: Settings) -> None:
    db = SessionLocal()
    try:
        BackendMetricCollector(settings, db).collect()
    finally:
        db.close()


def _run_daily_traffic_rollup(settings: Settings) -> None:
    db = SessionLocal()
    try:
        ProxyTrafficService(settings, db).rollup_daily()
    finally:
        db.close()


def _run_metric_alerts(settings: Settings) -> None:
    db = SessionLocal()
    try:
        from app.services.alert_rule_service import AlertRuleService

        AlertRuleService(settings, db).evaluate_all()
    finally:
        db.close()


def _run_threat_feed_sync(settings: Settings) -> None:
    db = SessionLocal()
    try:
        ThreatFeedService(settings, db).sync_all()
    finally:
        db.close()


def start_scheduler(settings: Settings) -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_health_checks,
        IntervalTrigger(seconds=settings.health_check_interval_seconds),
        args=[settings],
        id="health_checks",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_nginx_regen,
        IntervalTrigger(seconds=settings.nginx_regen_check_interval_seconds),
        args=[settings],
        id="nginx_regen",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_system_monitor,
        IntervalTrigger(seconds=settings.system_monitor_interval_seconds),
        args=[settings],
        id="system_monitor",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_ssl_alerts,
        IntervalTrigger(seconds=settings.ssl_alert_interval_seconds),
        args=[settings],
        id="ssl_alerts",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_health_rollup,
        IntervalTrigger(hours=1),
        args=[settings],
        id="health_rollup",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_proxy_traffic_collect,
        IntervalTrigger(seconds=settings.proxy_traffic_interval_seconds),
        args=[settings],
        id="proxy_traffic_collect",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_status_reports,
        IntervalTrigger(seconds=settings.status_report_check_interval_seconds),
        args=[settings],
        id="status_reports",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_threat_feed_sync,
        IntervalTrigger(seconds=settings.threat_feed_sync_interval_seconds),
        args=[settings],
        id="threat_feed_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_connection_metrics,
        IntervalTrigger(seconds=settings.connection_metric_interval_seconds),
        args=[settings],
        id="connection_metrics",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_backend_metrics,
        IntervalTrigger(seconds=settings.backend_metric_interval_seconds),
        args=[settings],
        id="backend_metrics",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_metrics_retention,
        IntervalTrigger(seconds=settings.metrics_retention_interval_seconds),
        args=[settings],
        id="metrics_retention",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_daily_traffic_rollup,
        IntervalTrigger(hours=24),
        args=[settings],
        id="traffic_daily_rollup",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_metric_alerts,
        IntervalTrigger(seconds=settings.metrics_alert_interval_seconds),
        args=[settings],
        id="metric_alerts",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
