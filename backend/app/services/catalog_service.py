from __future__ import annotations

import logging
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.proxy_template import ProxyTemplate
from app.security.validators import validate_slug
from app.schemas import CustomHeader, ProxyAppCreate, ProxyRoute, TargetProtocol
from app.schemas.catalog import (
    ApplicationTemplate,
    ApplicationTemplateResponse,
    CatalogFilter,
    TemplateCreateProxyRequest,
    TemplateGroup,
    TemplateGroupResponse,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
)

logger = logging.getLogger(__name__)

CATALOG_DIR = Path(__file__).resolve().parent.parent.parent / "catalog"
GROUPS_FILE = CATALOG_DIR / "groups.yaml"
TEMPLATES_DIR = CATALOG_DIR / "templates"


@lru_cache(maxsize=1)
def _load_catalog() -> tuple[list[TemplateGroup], dict[str, ApplicationTemplate], dict[str, str]]:
    groups_data = yaml.safe_load(GROUPS_FILE.read_text(encoding="utf-8")) or []
    groups = [TemplateGroup.model_validate(item) for item in groups_data]

    templates: dict[str, ApplicationTemplate] = {}
    alias_map: dict[str, str] = {}

    for path in sorted(TEMPLATES_DIR.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for raw in payload.get("templates", []):
            try:
                template = ApplicationTemplate.model_validate(raw)
            except Exception as exc:
                logger.warning("Skipping invalid catalog template in %s: %s", path.name, exc)
                continue
            templates[template.slug] = template
            for alias in template.slug_aliases:
                alias_map[alias] = template.slug

    return groups, templates, alias_map


class CatalogService:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.groups, self.templates, self.alias_map = _load_catalog()

    def resolve_slug(self, slug: str) -> Optional[str]:
        if slug in self.templates:
            return slug
        return self.alias_map.get(slug)

    def get_template(self, slug: str) -> Optional[ApplicationTemplate]:
        resolved = self.resolve_slug(slug)
        if not resolved:
            return None
        return self.templates.get(resolved)

    def list_groups(self) -> list[TemplateGroupResponse]:
        counts: dict[str, int] = {}
        for template in self.templates.values():
            counts[template.group] = counts.get(template.group, 0) + 1
        return [
            TemplateGroupResponse(
                slug=group.slug,
                name=group.name,
                description=group.description,
                icon=group.icon,
                sort_order=group.sort_order,
                template_count=counts.get(group.slug, 0),
            )
            for group in sorted(self.groups, key=lambda item: item.sort_order)
        ]

    def list_templates(self, filters: CatalogFilter) -> tuple[list[ApplicationTemplate], int]:
        items = list(self.templates.values())
        if filters.group:
            items = [item for item in items if item.group == filters.group]
        if filters.tag:
            items = [item for item in items if filters.tag in item.tags]
        if filters.availability_level:
            items = [item for item in items if item.availability_level == filters.availability_level]
        if filters.optimized is not None:
            items = [item for item in items if item.optimized is filters.optimized]
        if filters.websocket is not None:
            items = [item for item in items if item.websocket_support is filters.websocket]
        if filters.large_upload is not None:
            items = [item for item in items if item.large_upload_support is filters.large_upload]
        if filters.https_upstream is not None:
            items = [item for item in items if item.https_upstream_supported is filters.https_upstream]
        if filters.q:
            query = filters.q.lower().strip()
            items = [
                item
                for item in items
                if query in item.name.lower()
                or query in item.slug.lower()
                or query in item.description.lower()
                or any(query in tag.lower() for tag in item.tags)
            ]
        items.sort(key=lambda item: (item.group, item.name))
        total = len(items)
        start = (filters.page - 1) * filters.page_size
        end = start + filters.page_size
        return items[start:end], total

    def to_response(self, template: ApplicationTemplate, *, template_id: int = 0, builtin: bool = True) -> ApplicationTemplateResponse:
        return ApplicationTemplateResponse(
            id=template_id,
            slug=template.slug,
            name=template.name,
            description=template.description,
            group=template.group,
            category=template.category,
            icon=template.icon,
            tags=template.tags,
            availability_level=template.availability_level,
            optimized=template.optimized,
            default_upstream_protocol=template.default_upstream_protocol,
            default_upstream_port=template.default_upstream_port,
            websocket_support=template.websocket_support,
            large_upload_support=template.large_upload_support,
            recommended_client_max_body_size=template.recommended_client_max_body_size,
            recommended_proxy_read_timeout=template.recommended_proxy_read_timeout,
            recommended_proxy_send_timeout=template.recommended_proxy_send_timeout,
            recommended_proxy_connect_timeout=template.recommended_proxy_connect_timeout,
            https_upstream_supported=template.https_upstream_supported,
            http_to_https_redirect_default=template.http_to_https_redirect_default,
            recommended_headers=template.recommended_headers,
            security_headers=template.security_headers,
            health_check_path=template.health_check_path,
            rate_limit_recommendation=template.rate_limit_recommendation,
            notes=template.notes,
            security_notes=template.security_notes,
            documentation_url=template.documentation_url,
            long_description=template.long_description,
            slug_aliases=template.slug_aliases,
            hsts_recommended=template.hsts_recommended,
            defaults=template.to_defaults_dict(),
            builtin=builtin,
        )

    def build_proxy_payload(self, template: ApplicationTemplate, request: TemplatePreviewRequest | TemplateCreateProxyRequest) -> ProxyAppCreate:
        protocol = request.upstream_protocol or template.default_upstream_protocol
        port = request.upstream_port or template.default_upstream_port
        websocket = (
            request.websocket_enabled
            if request.websocket_enabled is not None
            else template.websocket_support
        )
        force_https = (
            request.force_https
            if request.force_https is not None
            else template.http_to_https_redirect_default
        )
        max_body_size = request.max_body_size
        if max_body_size is None and request.large_upload_enabled is not False and template.large_upload_support:
            max_body_size = template.recommended_client_max_body_size
        if request.large_upload_enabled is False:
            max_body_size = None

        custom_headers: list[CustomHeader] = []
        if request.apply_recommended_headers:
            custom_headers.extend(
                CustomHeader(name=header.name, value=header.value) for header in template.recommended_headers
            )

        security_headers: list[CustomHeader] = []
        if request.apply_security_headers:
            security_headers.extend(
                CustomHeader(name=header.name, value=header.value) for header in template.security_headers
            )

        hsts_enabled = request.hsts_enabled if request.hsts_enabled is not None else template.hsts_recommended

        notes_parts = [part for part in [template.notes, template.security_notes] if part]
        proxy_name = getattr(request, "name", None)
        if not proxy_name:
            candidate = request.domain.split(".")[0].lower().replace("_", "-")
            try:
                proxy_name = validate_slug(candidate)
            except ValueError:
                proxy_name = validate_slug(template.slug)
        return ProxyAppCreate(
            name=proxy_name,
            domains=[request.domain],
            routes=[
                ProxyRoute(
                    path_prefix="/",
                    target_protocol=TargetProtocol(protocol),
                    target_host=request.upstream_host,
                    target_port=port,
                    websocket_enabled=websocket,
                )
            ],
            custom_headers=custom_headers,
            security_headers=security_headers,
            max_body_size=max_body_size,
            force_https=force_https,
            enabled=getattr(request, "enabled", True),
            notes=" | ".join(notes_parts) if notes_parts else None,
            proxy_read_timeout=request.proxy_read_timeout or template.recommended_proxy_read_timeout,
            proxy_send_timeout=request.proxy_send_timeout or template.recommended_proxy_send_timeout,
            proxy_connect_timeout=request.proxy_connect_timeout or template.recommended_proxy_connect_timeout,
            hsts_enabled=hsts_enabled,
        )

    def preview(self, template: ApplicationTemplate, request: TemplatePreviewRequest, db: Session) -> TemplatePreviewResponse:
        from app.services.proxy_service import ProxyService

        payload = self.build_proxy_payload(template, request)
        warnings: list[str] = []
        if template.rate_limit_recommendation:
            warnings.append(f"Rate limit recommendation: {template.rate_limit_recommendation}")
        if template.health_check_path:
            warnings.append(f"Suggested health check path: {template.health_check_path}")
        service = ProxyService(self.settings, db)
        rendered = service._render_config(payload, payload.name)
        return TemplatePreviewResponse(
            rendered_config=rendered,
            resolved_payload=payload.model_dump(mode="json"),
            warnings=warnings,
        )

    def sync_legacy_db(self, db: Session) -> None:
        existing = {row.slug: row for row in db.query(ProxyTemplate).filter(ProxyTemplate.builtin.is_(True)).all()}
        changed = False
        for template in self.templates.values():
            defaults_json = json.dumps(template.to_defaults_dict())
            row = existing.get(template.slug)
            if row is None:
                db.add(
                    ProxyTemplate(
                        slug=template.slug,
                        name=template.name,
                        description=template.description,
                        defaults_json=defaults_json,
                        builtin=True,
                    )
                )
                changed = True
            else:
                row.name = template.name
                row.description = template.description
                row.defaults_json = defaults_json
                changed = True
        if changed:
            db.commit()


def reload_catalog_cache() -> None:
    _load_catalog.cache_clear()
