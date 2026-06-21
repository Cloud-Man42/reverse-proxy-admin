import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.proxy_template import ProxyTemplate
from app.schemas import ProxyTemplateResponse
from app.schemas.catalog import CatalogFilter
from app.services.catalog_service import CatalogService


class TemplateService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.catalog = CatalogService()

    def ensure_builtins(self) -> None:
        self.catalog.sync_legacy_db(self.db)

    def _db_id_map(self) -> dict[str, ProxyTemplate]:
        self.ensure_builtins()
        return {row.slug: row for row in self.db.query(ProxyTemplate).filter(ProxyTemplate.builtin.is_(True)).all()}

    def list_templates(self, filters: Optional[CatalogFilter] = None) -> list[ProxyTemplateResponse]:
        catalog_filter = filters or CatalogFilter(page_size=500)
        items, _ = self.catalog.list_templates(catalog_filter)
        db_rows = self._db_id_map()
        responses: list[ProxyTemplateResponse] = []
        for template in items:
            row = db_rows.get(template.slug)
            response = self.catalog.to_response(
                template,
                template_id=row.id if row else 0,
                builtin=True,
            )
            responses.append(self._to_legacy_response(response))
        return responses

    def get_by_slug(self, slug: str) -> Optional[ProxyTemplateResponse]:
        template = self.catalog.get_template(slug)
        if template is None:
            return None
        self.ensure_builtins()
        row = self.db.query(ProxyTemplate).filter(ProxyTemplate.slug == template.slug).first()
        response = self.catalog.to_response(template, template_id=row.id if row else 0, builtin=True)
        return self._to_legacy_response(response)

    @staticmethod
    def _to_legacy_response(response) -> ProxyTemplateResponse:
        return ProxyTemplateResponse(
            id=response.id,
            slug=response.slug,
            name=response.name,
            description=response.description,
            defaults=response.defaults,
            builtin=response.builtin,
            group=response.group,
            category=response.category,
            icon=response.icon,
            tags=response.tags,
            availability_level=response.availability_level.value,
            optimized=response.optimized,
            default_upstream_protocol=response.default_upstream_protocol,
            default_upstream_port=response.default_upstream_port,
            websocket_support=response.websocket_support,
            large_upload_support=response.large_upload_support,
            https_upstream_supported=response.https_upstream_supported,
            documentation_url=response.documentation_url,
        )

    def list_catalog(self, filters: CatalogFilter):
        return self.catalog.list_templates(filters)

    def list_groups(self):
        return self.catalog.list_groups()

    def get_catalog_template(self, slug: str):
        return self.catalog.get_template(slug)

    def catalog_service(self) -> CatalogService:
        return self.catalog
