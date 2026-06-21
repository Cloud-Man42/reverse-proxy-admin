from unittest.mock import patch

from app.services.catalog_service import CatalogService
from app.services.waf_service import WafService
from app.schemas.catalog import TemplatePreviewRequest


def test_preview_builds_config(db_session, temp_settings):
    catalog = CatalogService(temp_settings)
    template = catalog.get_template("grafana")
    assert template is not None
    request = TemplatePreviewRequest(
        domain="grafana.example.com",
        upstream_host="127.0.0.1",
        upstream_port=3000,
    )
    with patch("app.services.proxy_service.NginxOps") as nginx_ops:
        nginx_ops.return_value.status.return_value = (True, "ok")
        preview = catalog.preview(template, request, db_session)
    assert "proxy_pass" in preview.rendered_config
    assert "grafana.example.com" in preview.rendered_config
    assert preview.resolved_payload["routes"][0]["target_port"] == 3000
