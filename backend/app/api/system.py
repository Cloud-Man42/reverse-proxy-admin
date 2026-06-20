import shutil

from typing import List, Optional



import psutil

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from sqlalchemy.orm import Session



from app.config import Settings, get_settings

from app.db import get_db

from app.models.audit import AuditLog

from app.models.notification import NotificationLog

from app.models.system_alert import SystemAlertHistory

from app.models.user import User

from app.schemas import AuditLogListResponse, AuditLogResponse, DashboardAlert, DashboardStats, MessageResponse, NetworkMapResponse, NginxStatusResponse, NginxTestResult, SystemHealthResponse

from app.security.permissions import Permission, require_admin, require_permission
from app.security.tenant_context import filter_query_by_org

from app.security.ip_allowlist import _client_ip

from app.services.audit_service import log_audit
from app.services.security_event_service import AuditExportService

from app.services.backend_pool_service import BackendPoolService

from app.services.certbot_ops import CertbotOps

from app.services.health_check_service import HealthCheckService

from app.services.log_reader import LogReader

from app.services.network_map_service import NetworkMapService

from app.services.nginx_ops import NginxOps

from app.services.notification_service import NotificationService

from app.services.proxy_service import ProxyService

from app.services.proxy_traffic_service import ProxyTrafficService

from app.services.smtp_service import SmtpService

router = APIRouter(tags=["system"])





def _recent_alerts(db: Session, limit: int = 15) -> List[DashboardAlert]:

    notifications = (

        db.query(NotificationLog)

        .order_by(NotificationLog.created_at.desc())

        .limit(limit)

        .all()

    )

    system_alerts = (

        db.query(SystemAlertHistory)

        .order_by(SystemAlertHistory.created_at.desc())

        .limit(limit)

        .all()

    )

    alerts: List[DashboardAlert] = [

        DashboardAlert(

            id=row.id,

            source="notification",

            alert_type=row.event_type,

            title=row.subject,

            message=row.detail,

            status=row.status,

            created_at=row.created_at,

        )

        for row in notifications

    ]

    alerts.extend(

        DashboardAlert(

            id=row.id,

            source="system",

            alert_type=row.alert_type,

            title=f"{row.metric.upper()} {row.status}",

            message=row.message,

            status=row.status,

            created_at=row.created_at,

        )

        for row in system_alerts

    )

    alerts.sort(key=lambda item: item.created_at, reverse=True)

    return alerts[:limit]





def _system_metrics(settings: Settings) -> tuple[Optional[float], Optional[float], Optional[float]]:

    try:

        cpu = round(psutil.cpu_percent(interval=0.1), 1)

        ram = round(psutil.virtual_memory().percent, 1)

        usage = shutil.disk_usage(settings.data_dir if settings.data_dir.exists() else "/")

        disk = round((usage.used / usage.total) * 100, 1) if usage.total else 0.0

        return cpu, ram, disk

    except Exception:

        return None, None, None





@router.get("/dashboard", response_model=DashboardStats)

async def dashboard(

    settings: Settings = Depends(get_settings),

    db: Session = Depends(get_db),

    _user: User = Depends(require_permission(Permission.READ)),

) -> DashboardStats:

    proxies = ProxyService(settings, db).list_proxies()

    active = sum(1 for item in proxies if item.enabled)

    disabled = sum(1 for item in proxies if not item.enabled)

    inactive = len(proxies) - active

    nginx_active, _ = NginxOps(settings).status()

    total_certs = 0

    expiring = 0

    try:

        certs = CertbotOps(settings).list_certificates()

        total_certs = len(certs)

        expiring = sum(1 for cert in certs if cert.status == "expiring")

    except Exception:

        pass

    try:

        recent_errors = LogReader(settings).read_error_log(lines=10)

    except Exception:

        recent_errors = []

    health = HealthCheckService(settings, db).get_dashboard()

    servers, _ = BackendPoolService(settings, db).list_servers(page_size=1000)

    smtp_status = SmtpService(settings, db).status_label()

    traffic_service = ProxyTrafficService(settings, db)

    bytes_in, bytes_out = traffic_service.total_bytes("24h")

    traffic_history = traffic_service.aggregate_history("24h")

    cpu_percent, ram_percent, disk_percent = _system_metrics(settings)

    recent_alerts = _recent_alerts(db)

    return DashboardStats(

        active_proxies=active,

        inactive_proxies=inactive,

        disabled_proxies=disabled,

        nginx_active=nginx_active,

        expiring_certificates=expiring,

        recent_errors=recent_errors,

        total_backend_servers=len(servers),

        healthy_backends=health.healthy,

        warning_backends=health.warning,

        offline_backends=health.offline,

        total_certificates=total_certs,

        smtp_status=smtp_status,

        traffic_bytes_in_24h=bytes_in,

        traffic_bytes_out_24h=bytes_out,

        cpu_percent=cpu_percent,

        ram_percent=ram_percent,

        disk_percent=disk_percent,

        recent_alerts=recent_alerts,

        traffic_history=traffic_history,

    )



@router.get("/dashboard/network-map", response_model=NetworkMapResponse)

async def network_map(

    settings: Settings = Depends(get_settings),

    _user: User = Depends(require_permission(Permission.READ)),

) -> NetworkMapResponse:

    return NetworkMapService(settings).build()





@router.get("/system/health", response_model=SystemHealthResponse)

async def system_health(

    settings: Settings = Depends(get_settings),

    _user: User = Depends(require_permission(Permission.READ)),

) -> SystemHealthResponse:

    nginx_active, _ = NginxOps(settings).status()

    usage = shutil.disk_usage(settings.data_dir if settings.data_dir.exists() else "/")

    total = usage.total / (1024**3)

    used = usage.used / (1024**3)

    free = usage.free / (1024**3)

    percent = (usage.used / usage.total) * 100 if usage.total else 0

    return SystemHealthResponse(

        nginx_active=nginx_active,

        disk_total_gb=round(total, 2),

        disk_used_gb=round(used, 2),

        disk_free_gb=round(free, 2),

        disk_percent=round(percent, 2),

    )





@router.get("/system/nginx/status", response_model=NginxStatusResponse)

async def nginx_status(

    settings: Settings = Depends(get_settings),

    _user: User = Depends(require_permission(Permission.READ)),

) -> NginxStatusResponse:

    active, output = NginxOps(settings).status()

    return NginxStatusResponse(active=active, output=output)





@router.post("/system/nginx/test", response_model=NginxTestResult)

async def nginx_test(

    settings: Settings = Depends(get_settings),

    _user: User = Depends(require_permission(Permission.READ)),

) -> NginxTestResult:

    ok, output = NginxOps(settings).test_config()

    return NginxTestResult(success=ok, output=output)





@router.post("/system/nginx/reload", response_model=MessageResponse)

async def nginx_reload(

    request: Request,

    db: Session = Depends(get_db),

    settings: Settings = Depends(get_settings),

    user: User = Depends(require_permission(Permission.EDIT)),

) -> MessageResponse:

    ok, output = NginxOps(settings).reload()

    if not ok:

        log_audit(

            db,

            username=user.username,

            action="nginx_reload",

            resource="nginx",

            client_ip=_client_ip(request),

            new_value={"success": False, "output": output},

        )

        NotificationService(settings, db).dispatch_nginx_failure("reload", output)

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=output)

    log_audit(

        db,

        username=user.username,

        action="nginx_reload",

        resource="nginx",

        client_ip=_client_ip(request),

        new_value={"success": True},

    )

    return MessageResponse(message="Nginx reloaded", detail=output)



@router.get("/audit", response_model=AuditLogListResponse)

async def list_audit_logs(

    db: Session = Depends(get_db),

    page: int = Query(1, ge=1),

    page_size: int = Query(50, ge=1, le=200),

    action: Optional[str] = None,

    resource: Optional[str] = None,

    _user: User = Depends(require_permission(Permission.READ)),

) -> AuditLogListResponse:

    query = filter_query_by_org(db.query(AuditLog), AuditLog, _user)

    if action:

        query = query.filter(AuditLog.action == action)

    if resource:

        query = query.filter(AuditLog.resource.contains(resource))

    total = query.count()

    entries = (

        query.order_by(AuditLog.created_at.desc())

        .offset((page - 1) * page_size)

        .limit(page_size)

        .all()

    )

    return AuditLogListResponse(

        items=[

            AuditLogResponse(

                id=entry.id,

                username=entry.username,

                action=entry.action,

                resource=entry.resource,

                old_value=entry.old_value,

                new_value=entry.new_value,

                client_ip=entry.client_ip,

                created_at=entry.created_at,

            )

            for entry in entries

        ],

        total=total,

        page=page,

        page_size=page_size,

    )



@router.get("/audit/export")
async def export_audit_logs(
    format: str = Query("json", pattern="^(csv|json)$"),
    from_dt: Optional[str] = Query(None, alias="from"),
    to_dt: Optional[str] = Query(None, alias="to"),
    action: Optional[str] = None,
    resource: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.READ)),
):
    from datetime import datetime

    from fastapi.responses import Response

    parsed_from = datetime.fromisoformat(from_dt) if from_dt else None
    parsed_to = datetime.fromisoformat(to_dt) if to_dt else None
    content, media_type, filename = AuditExportService(db).export(
        user,
        format=format,
        from_dt=parsed_from,
        to_dt=parsed_to,
        action=action,
        resource=resource,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



@router.get("/health")

async def health() -> dict:

    return {"status": "ok"}


