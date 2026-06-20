from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import Settings
from app.db import SessionLocal
from app.services.health_check_service import HealthCheckService
from app.services.ssl_alert_service import SslAlertService
from app.services.system_monitor_service import SystemMonitorService

_scheduler: BackgroundScheduler | None = None


def _run_health_checks(settings: Settings) -> None:
    db = SessionLocal()
    try:
        HealthCheckService(settings, db).run_all()
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
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
