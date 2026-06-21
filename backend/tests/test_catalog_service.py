from app.schemas.catalog import ApplicationTemplate, CatalogFilter, TemplateAvailabilityLevel, TemplateHeader
from app.services.catalog_service import CatalogService


def test_catalog_loads_groups_and_templates():
    catalog = CatalogService()
    groups = catalog.list_groups()
    assert len(groups) >= 17
    assert any(group.slug == "monitoring-observability" for group in groups)
    assert len(catalog.templates) >= 100


def test_catalog_resolves_slug_alias():
    catalog = CatalogService()
    assert catalog.resolve_slug("proxmox") == "proxmox-ve"
    template = catalog.get_template("proxmox")
    assert template is not None
    assert template.slug == "proxmox-ve"


def test_catalog_filters_optimized_and_availability():
    catalog = CatalogService()
    items, total = catalog.list_templates(CatalogFilter(optimized=True, page_size=200))
    assert total >= 10
    assert all(item.optimized for item in items)
    free_items, free_total = catalog.list_templates(
        CatalogFilter(availability_level=TemplateAvailabilityLevel.FREE, page_size=200)
    )
    assert free_total >= 15
    assert all(item.availability_level.value == "free" for item in free_items)


def test_catalog_search_by_name():
    catalog = CatalogService()
    items, total = catalog.list_templates(CatalogFilter(q="grafana", page_size=20))
    assert total >= 1
    assert any(item.slug == "grafana" for item in items)


def test_template_header_validation_rejects_unsafe_values():
    template = ApplicationTemplate(
        slug="demo",
        name="Demo",
        description="Demo",
        group="general",
        category="General",
        recommended_headers=[TemplateHeader(name="X-Test", value="safe")],
    )
    assert template.recommended_headers[0].name == "X-Test"

    try:
        TemplateHeader(name="Bad;Header", value="x")
        assert False, "expected validation error"
    except Exception:
        pass


def test_template_defaults_include_proxy_fields():
    catalog = CatalogService()
    template = catalog.get_template("nextcloud")
    assert template is not None
    defaults = template.to_defaults_dict()
    assert defaults["routes"][0]["websocket_enabled"] is True
    assert defaults["max_body_size"]
    assert defaults["proxy_read_timeout"]
