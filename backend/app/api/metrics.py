from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.security.permissions import Permission, require_permission
from app.services.alert_rule_service import AlertRuleService
from app.services.metrics_service import MetricsService
from app.services.metrics_settings_service import MetricsSettingsService

router = APIRouter(tags=["metrics"])


class MetricAlertRuleCreate(BaseModel):
    name: str = Field(max_length=255)
    enabled: bool = True
    severity: str = "warning"
    metric_type: str
    condition: str = "gt"
    threshold: float = 0.0
    window_minutes: int = 5
    proxy_id: Optional[str] = None
    notify_email: bool = True


class MetricAlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    severity: Optional[str] = None
    metric_type: Optional[str] = None
    condition: Optional[str] = None
    threshold: Optional[float] = None
    window_minutes: Optional[int] = None
    proxy_id: Optional[str] = None
    notify_email: Optional[bool] = None


class MetricsSettingsUpdate(BaseModel):
    raw_retention_days: Optional[int] = None
    minute_retention_days: Optional[int] = None
    hour_retention_days: Optional[int] = None
    stub_status_url: Optional[str] = None
    enhanced_logging_default: Optional[bool] = None
    request_event_sample_rate: Optional[int] = None


@router.get("/metrics/dashboard")
async def metrics_dashboard(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    return MetricsService(settings, db).dashboard()


@router.get("/metrics/traffic")
async def metrics_traffic(
    range: str = Query("24h", alias="range"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    return MetricsService(settings, db).traffic(range)


@router.get("/metrics/status-codes")
async def metrics_status_codes(
    range: str = Query("24h", alias="range"),
    proxy_id: Optional[str] = None,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    return MetricsService(settings, db).status_codes(range, proxy_id)


@router.get("/metrics/proxy-hosts")
async def metrics_proxy_hosts(
    range: str = Query("24h", alias="range"),
    sort_by: str = Query("requests"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    return MetricsService(settings, db).proxy_hosts(range, sort_by)


@router.get("/metrics/client-ips")
async def metrics_client_ips(
    range: str = Query("24h", alias="range"),
    limit: int = Query(50, ge=1, le=500),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    return MetricsService(settings, db).client_ips(range, limit)


@router.get("/metrics/backends")
async def metrics_backends(
    range: str = Query("24h", alias="range"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    return MetricsService(settings, db).backends(range)


@router.get("/metrics/connections")
async def metrics_connections(
    range: str = Query("24h", alias="range"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    return MetricsService(settings, db).connections(range)


@router.get("/metrics/ssl")
async def metrics_ssl(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    return MetricsService(settings, db).ssl_stats()


@router.get("/metrics/security")
async def metrics_security(
    range: str = Query("24h", alias="range"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    return MetricsService(settings, db).security(range)


@router.get("/live-requests")
async def live_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    domain: Optional[str] = None,
    status: Optional[int] = None,
    client_ip: Optional[str] = None,
    search: Optional[str] = None,
    errors_only: bool = False,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    return MetricsService(settings, db).live_requests(
        page=page,
        page_size=page_size,
        domain=domain,
        status=status,
        client_ip=client_ip,
        search=search,
        errors_only=errors_only,
    )


@router.get("/failed-requests")
async def failed_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    return MetricsService(settings, db).failed_requests(page=page, page_size=page_size)


@router.get("/alerts")
async def list_alerts(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    service = AlertRuleService(settings, db)
    return {
        "rules": [
            {
                "id": row.id,
                "name": row.name,
                "enabled": row.enabled,
                "severity": row.severity,
                "metric_type": row.metric_type,
                "condition": row.condition,
                "threshold": row.threshold,
                "window_minutes": row.window_minutes,
                "proxy_id": row.proxy_id,
                "notify_email": row.notify_email,
            }
            for row in service.list_rules()
        ],
        "history": [
            {
                "id": row.id,
                "rule_id": row.rule_id,
                "alert_type": row.alert_type,
                "severity": row.severity,
                "status": row.status,
                "message": row.message,
                "metric_value": row.metric_value,
                "created_at": row.created_at.isoformat(),
            }
            for row in service.recent_history(50)
        ],
    }


@router.post("/alerts")
async def create_alert(
    payload: MetricAlertRuleCreate,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.EDIT)),
) -> dict:
    row = AlertRuleService(settings, db).create_rule(payload.model_dump())
    return {"id": row.id, "name": row.name}


@router.put("/alerts/{rule_id}")
async def update_alert(
    rule_id: int,
    payload: MetricAlertRuleUpdate,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.EDIT)),
) -> dict:
    row = AlertRuleService(settings, db).update_rule(rule_id, payload.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return {"id": row.id, "name": row.name}


@router.delete("/alerts/{rule_id}")
async def delete_alert(
    rule_id: int,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.EDIT)),
) -> dict:
    if not AlertRuleService(settings, db).delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return {"status": "deleted"}


@router.get("/metrics/settings")
async def get_metrics_settings(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> dict:
    service = MetricsSettingsService(db)
    return service.to_dict(service.get_or_create())


@router.put("/metrics/settings")
async def update_metrics_settings(
    payload: MetricsSettingsUpdate,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.EDIT)),
) -> dict:
    service = MetricsSettingsService(db)
    row = service.update(settings, payload.model_dump(exclude_unset=True))
    return service.to_dict(row)
