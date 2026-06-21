from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.schemas import MessageResponse, ProxyAppResponse, ProxyTemplateResponse
from app.schemas.catalog import (
    ApplicationTemplateResponse,
    CatalogFilter,
    TemplateAvailabilityLevel,
    TemplateCreateProxyRequest,
    TemplateCreateProxyResponse,
    TemplateGroupResponse,
    TemplateListResponse,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
)
from app.security.ip_allowlist import _client_ip
from app.security.permissions import Permission, require_permission
from app.services.audit_service import log_audit
from app.services.catalog_service import CatalogService
from app.services.proxy_service import ProxyService
from app.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["templates"])


def get_service(db: Session = Depends(get_db)) -> TemplateService:
    return TemplateService(db)


@router.get("/groups", response_model=List[TemplateGroupResponse])
async def list_template_groups(
    service: TemplateService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> List[TemplateGroupResponse]:
    return service.list_groups()


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    q: Optional[str] = None,
    group: Optional[str] = None,
    tag: Optional[str] = None,
    availability_level: Optional[TemplateAvailabilityLevel] = None,
    optimized: Optional[bool] = None,
    websocket: Optional[bool] = None,
    large_upload: Optional[bool] = None,
    https_upstream: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    service: TemplateService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> TemplateListResponse:
    filters = CatalogFilter(
        q=q,
        group=group,
        tag=tag,
        availability_level=availability_level,
        optimized=optimized,
        websocket=websocket,
        large_upload=large_upload,
        https_upstream=https_upstream,
        page=page,
        page_size=page_size,
    )
    items, total = service.list_catalog(filters)
    db_rows = service._db_id_map()
    responses = [
        service.catalog_service().to_response(
            item,
            template_id=db_rows[item.slug].id if item.slug in db_rows else 0,
            builtin=True,
        )
        for item in items
    ]
    return TemplateListResponse(items=responses, total=total, page=page, page_size=page_size)


@router.get("/legacy", response_model=List[ProxyTemplateResponse])
async def list_templates_legacy(
    service: TemplateService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> List[ProxyTemplateResponse]:
    return service.list_templates()


@router.get("/{slug}", response_model=ApplicationTemplateResponse)
async def get_template(
    slug: str,
    service: TemplateService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> ApplicationTemplateResponse:
    template = service.get_catalog_template(slug)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    db_rows = service._db_id_map()
    row = db_rows.get(template.slug)
    return service.catalog_service().to_response(template, template_id=row.id if row else 0, builtin=True)


@router.post("/{slug}/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    slug: str,
    payload: TemplatePreviewRequest,
    db: Session = Depends(get_db),
    service: TemplateService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> TemplatePreviewResponse:
    template = service.get_catalog_template(slug)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    catalog = CatalogService()
    return catalog.preview(template, payload, db)


@router.post("/{slug}/create-proxy", response_model=TemplateCreateProxyResponse)
async def create_proxy_from_template(
    slug: str,
    payload: TemplateCreateProxyRequest,
    request: Request,
    db: Session = Depends(get_db),
    service: TemplateService = Depends(get_service),
    user: User = Depends(require_permission(Permission.CREATE)),
) -> TemplateCreateProxyResponse:
    template = service.get_catalog_template(slug)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    catalog = CatalogService()
    proxy_payload = catalog.build_proxy_payload(template, payload)
    proxy_service = ProxyService(catalog.settings, db)
    ok, message, proxy, failure_stage = proxy_service.create_proxy(proxy_payload, username=user.username)
    if not ok:
        return TemplateCreateProxyResponse(success=False, message=message, failure_stage=failure_stage)
    log_audit(
        db,
        username=user.username,
        action="create_proxy_from_template",
        resource=proxy_payload.name,
        client_ip=_client_ip(request),
        new_value={"template_slug": template.slug, "domain": payload.domain},
    )
    return TemplateCreateProxyResponse(
        success=True,
        message=message,
        proxy=proxy.model_dump(mode="json") if proxy else None,
    )
