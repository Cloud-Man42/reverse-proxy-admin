from app.models.proxy_template import ProxyTemplate
from app.services.template_service import BUILTIN_PRESETS, TemplateService


def test_seeds_builtin_templates(db_session):
    service = TemplateService(db_session)
    templates = service.list_templates()

    assert len(templates) == len(BUILTIN_PRESETS)
    slugs = {template.slug for template in templates}
    assert slugs == {preset["slug"] for preset in BUILTIN_PRESETS}
    assert all(template.builtin for template in templates)


def test_get_template_by_slug(db_session):
    service = TemplateService(db_session)
    template = service.get_by_slug("grafana")

    assert template is not None
    assert template.slug == "grafana"
    assert template.name == "Grafana"
    assert template.defaults["routes"][0]["target_port"] == 3000
    assert template.defaults["routes"][0]["websocket_enabled"] is True


def test_get_unknown_template_returns_none(db_session):
    service = TemplateService(db_session)
    assert service.get_by_slug("missing-template") is None


def test_ensure_builtins_is_idempotent(db_session):
    service = TemplateService(db_session)
    service.ensure_builtins()
    first_count = db_session.query(ProxyTemplate).count()
    service.ensure_builtins()
    assert db_session.query(ProxyTemplate).count() == first_count
