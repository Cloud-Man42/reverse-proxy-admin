from app.services.template_service import TemplateService


def test_seeds_catalog_templates(db_session):
    service = TemplateService(db_session)
    templates = service.list_templates()
    assert len(templates) >= 100
    slugs = {template.slug for template in templates}
    assert "grafana" in slugs
    assert "custom" in slugs
    assert all(template.builtin for template in templates)


def test_get_template_by_slug(db_session):
    service = TemplateService(db_session)
    template = service.get_by_slug("grafana")
    assert template is not None
    assert template.slug == "grafana"
    assert template.defaults["routes"][0]["target_port"] == 3000
    assert template.websocket_support is True


def test_get_template_by_legacy_alias(db_session):
    service = TemplateService(db_session)
    template = service.get_by_slug("proxmox")
    assert template is not None
    assert template.slug == "proxmox-ve"


def test_get_unknown_template_returns_none(db_session):
    service = TemplateService(db_session)
    assert service.get_by_slug("missing-template") is None


def test_ensure_builtins_is_idempotent(db_session):
    from app.models.proxy_template import ProxyTemplate

    service = TemplateService(db_session)
    service.ensure_builtins()
    first_count = db_session.query(ProxyTemplate).count()
    service.ensure_builtins()
    assert db_session.query(ProxyTemplate).count() == first_count
