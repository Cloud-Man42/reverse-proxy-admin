from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.schemas import (
    GeoRuleCreate,
    GeoRuleResponse,
    GeoRuleUpdate,
    IpAccessRuleCreate,
    IpAccessRuleResponse,
    IpAccessRuleUpdate,
    MessageResponse,
    ProxyWafSettingsResponse,
    ProxyWafSettingsUpdate,
    SecurityEventListResponse,
    ThreatFeedCreate,
    ThreatFeedResponse,
    ThreatFeedUpdate,
)
from app.security.ip_allowlist import _client_ip
from app.security.permissions import Permission, require_permission
from app.services.audit_service import log_audit
from app.services.geoip_service import GeoIpService
from app.services.ip_access_service import IpAccessService
from app.services.nginx_parser import list_proxy_configs
from app.services.proxy_service import ProxyService
from app.services.security_event_service import AuditExportService, SecurityEventService
from app.services.threat_feed_service import ThreatFeedService
from app.services.waf_service import WafService

router = APIRouter(prefix="/security", tags=["security"])


def _regen_proxies(settings: Settings, db: Session, proxy_ids: Optional[List[str]] = None) -> None:
    service = ProxyService(settings, db)
    targets = proxy_ids or [item.slug for item in list_proxy_configs(settings)]
    for proxy_id in targets:
        proxy = service.get_proxy(proxy_id)
        if not proxy:
            continue
        path = service.writer.config_path_for(proxy_id)
        if not path.exists():
            continue
        from app.schemas import ProxyAppCreate

        payload = ProxyAppCreate(
            name=proxy.name,
            domains=proxy.domains,
            routes=proxy.routes,
            custom_headers=proxy.custom_headers,
            max_body_size=proxy.max_body_size,
            basic_auth_enabled=proxy.basic_auth_enabled,
            force_https=proxy.force_https,
            enabled=proxy.enabled,
            notes=proxy.notes,
        )
        service._write_proxy_state(path, payload, proxy_id)


@router.get("/ip-rules", response_model=List[IpAccessRuleResponse])
async def list_ip_rules(
    scope: Optional[str] = None,
    proxy_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> List[IpAccessRuleResponse]:
    return IpAccessService(db).list_rules(scope=scope, proxy_id=proxy_id)


@router.post("/ip-rules", response_model=IpAccessRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_ip_rule(
    payload: IpAccessRuleCreate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> IpAccessRuleResponse:
    rule = IpAccessService(db).create(payload)
    _regen_proxies(settings, db, [payload.proxy_id] if payload.proxy_id else None)
    log_audit(
        db,
        username=user.username,
        action="create_ip_rule",
        resource=str(rule.id),
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    return rule


@router.put("/ip-rules/{rule_id}", response_model=IpAccessRuleResponse)
async def update_ip_rule(
    rule_id: int,
    payload: IpAccessRuleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> IpAccessRuleResponse:
    service = IpAccessService(db)
    existing = service.get(rule_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    updated = service.update(rule_id, payload)
    proxy_ids = []
    if existing.proxy_id:
        proxy_ids.append(existing.proxy_id)
    if updated and updated.proxy_id and updated.proxy_id not in proxy_ids:
        proxy_ids.append(updated.proxy_id)
    _regen_proxies(settings, db, proxy_ids or None)
    log_audit(
        db,
        username=user.username,
        action="update_ip_rule",
        resource=str(rule_id),
        client_ip=_client_ip(request),
        new_value=payload.model_dump(exclude_unset=True),
    )
    return updated


@router.delete("/ip-rules/{rule_id}", response_model=MessageResponse)
async def delete_ip_rule(
    rule_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> MessageResponse:
    service = IpAccessService(db)
    existing = service.get(rule_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    service.delete(rule_id)
    _regen_proxies(settings, db, [existing.proxy_id] if existing.proxy_id else None)
    log_audit(
        db,
        username=user.username,
        action="delete_ip_rule",
        resource=str(rule_id),
        client_ip=_client_ip(request),
    )
    return MessageResponse(message="IP rule deleted")


@router.get("/geo-rules", response_model=List[GeoRuleResponse])
async def list_geo_rules(
    proxy_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> List[GeoRuleResponse]:
    return GeoIpService(get_settings(), db).list_rules(proxy_id=proxy_id)


@router.post("/geo-rules", response_model=GeoRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_geo_rule(
    payload: GeoRuleCreate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> GeoRuleResponse:
    service = GeoIpService(settings, db)
    rule = service.create(payload)
    from app.models.geo_rule import GeoRule

    geo_model = db.get(GeoRule, rule.id)
    service.write_include(payload.proxy_id, geo_model)
    _regen_proxies(settings, db, [payload.proxy_id])
    log_audit(
        db,
        username=user.username,
        action="create_geo_rule",
        resource=str(rule.id),
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    return rule


@router.put("/geo-rules/{rule_id}", response_model=GeoRuleResponse)
async def update_geo_rule(
    rule_id: int,
    payload: GeoRuleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> GeoRuleResponse:
    service = GeoIpService(settings, db)
    existing = service.get(rule_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    updated = service.update(rule_id, payload)
    proxy_id = updated.proxy_id if updated else existing.proxy_id
    geo_model = service.get_for_proxy(proxy_id)
    service.write_include(proxy_id, geo_model)
    _regen_proxies(settings, db, [proxy_id])
    log_audit(
        db,
        username=user.username,
        action="update_geo_rule",
        resource=str(rule_id),
        client_ip=_client_ip(request),
        new_value=payload.model_dump(exclude_unset=True),
    )
    return updated


@router.delete("/geo-rules/{rule_id}", response_model=MessageResponse)
async def delete_geo_rule(
    rule_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> MessageResponse:
    service = GeoIpService(settings, db)
    existing = service.get(rule_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    service.delete(rule_id)
    service.write_include(existing.proxy_id, None)
    _regen_proxies(settings, db, [existing.proxy_id])
    log_audit(
        db,
        username=user.username,
        action="delete_geo_rule",
        resource=str(rule_id),
        client_ip=_client_ip(request),
    )
    return MessageResponse(message="Geo rule deleted")


@router.get("/threat-feeds", response_model=List[ThreatFeedResponse])
async def list_threat_feeds(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> List[ThreatFeedResponse]:
    return ThreatFeedService(settings, db).list_feeds()


@router.post("/threat-feeds", response_model=ThreatFeedResponse, status_code=status.HTTP_201_CREATED)
async def create_threat_feed(
    payload: ThreatFeedCreate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> ThreatFeedResponse:
    feed = ThreatFeedService(settings, db).create(payload)
    log_audit(
        db,
        username=user.username,
        action="create_threat_feed",
        resource=str(feed.id),
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    return feed


@router.put("/threat-feeds/{feed_id}", response_model=ThreatFeedResponse)
async def update_threat_feed(
    feed_id: int,
    payload: ThreatFeedUpdate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> ThreatFeedResponse:
    service = ThreatFeedService(settings, db)
    updated = service.update(feed_id, payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")
    log_audit(
        db,
        username=user.username,
        action="update_threat_feed",
        resource=str(feed_id),
        client_ip=_client_ip(request),
        new_value=payload.model_dump(exclude_unset=True),
    )
    return updated


@router.delete("/threat-feeds/{feed_id}", response_model=MessageResponse)
async def delete_threat_feed(
    feed_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> MessageResponse:
    if not ThreatFeedService(settings, db).delete(feed_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")
    log_audit(
        db,
        username=user.username,
        action="delete_threat_feed",
        resource=str(feed_id),
        client_ip=_client_ip(request),
    )
    return MessageResponse(message="Threat feed deleted")


@router.post("/threat-feeds/{feed_id}/sync", response_model=ThreatFeedResponse)
async def sync_threat_feed(
    feed_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> ThreatFeedResponse:
    service = ThreatFeedService(settings, db)
    try:
        feed = service.sync_feed(feed_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    service._write_combined_deny_file()
    _regen_proxies(settings, db)
    SecurityEventService(db).log(
        event_type="threat_feed_sync",
        source="threat_feed",
        message=f"Synced threat feed {feed.name} ({feed.ip_count} IPs)",
    )
    log_audit(
        db,
        username=user.username,
        action="sync_threat_feed",
        resource=str(feed_id),
        client_ip=_client_ip(request),
        new_value={"ip_count": feed.ip_count},
    )
    return feed


@router.get("/waf/{proxy_id}", response_model=ProxyWafSettingsResponse)
async def get_waf_settings(
    proxy_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> ProxyWafSettingsResponse:
    return WafService(settings, db).get(proxy_id)


@router.put("/waf/{proxy_id}", response_model=ProxyWafSettingsResponse)
async def update_waf_settings(
    proxy_id: str,
    payload: ProxyWafSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission(Permission.EDIT)),
) -> ProxyWafSettingsResponse:
    result = WafService(settings, db).upsert(proxy_id, payload)
    _regen_proxies(settings, db, [proxy_id])
    SecurityEventService(db).log(
        event_type="waf_updated",
        source="waf",
        proxy_id=proxy_id,
        message=f"WAF settings updated for {proxy_id}",
    )
    log_audit(
        db,
        username=user.username,
        action="update_waf_settings",
        resource=proxy_id,
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
    )
    return result


@router.get("/events", response_model=SecurityEventListResponse)
async def list_security_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    proxy_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> SecurityEventListResponse:
    items, total = SecurityEventService(db).list_events(
        page=page,
        page_size=page_size,
        event_type=event_type,
        source=source,
        proxy_id=proxy_id,
    )
    return SecurityEventListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/events/export")
async def export_security_events(
    format: str = Query("json", pattern="^(csv|json)$"),
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    from_dt: Optional[str] = Query(None, alias="from"),
    to_dt: Optional[str] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> Response:
    from datetime import datetime

    parsed_from = datetime.fromisoformat(from_dt) if from_dt else None
    parsed_to = datetime.fromisoformat(to_dt) if to_dt else None
    content, media_type, filename = SecurityEventService(db).export_events(
        format=format,
        event_type=event_type,
        source=source,
        from_dt=parsed_from,
        to_dt=parsed_to,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
