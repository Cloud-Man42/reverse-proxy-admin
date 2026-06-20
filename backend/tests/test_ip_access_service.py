from app.models.ip_access_rule import IpAccessRule
from app.schemas import IpAccessRuleCreate, IpAccessRuleUpdate, IpAccessScope, IpAccessRuleType
from app.services.ip_access_service import IpAccessService


def test_ip_access_crud(db_session):
    service = IpAccessService(db_session)
    created = service.create(
        IpAccessRuleCreate(
            scope=IpAccessScope.GLOBAL,
            rule_type=IpAccessRuleType.DENY,
            cidr="192.0.2.0/24",
            enabled=True,
            notes="test block",
        )
    )
    assert created.id
    assert created.cidr == "192.0.2.0/24"

    listed = service.list_rules(scope="global")
    assert len(listed) == 1

    updated = service.update(created.id, IpAccessRuleUpdate(enabled=False))
    assert updated.enabled is False

    assert service.delete(created.id) is True
    assert service.get(created.id) is None


def test_ip_access_render_nginx_directives():
    rules = [
        IpAccessRule(id=1, scope="proxy", proxy_id="app", rule_type="allow", cidr="10.0.0.0/8", enabled=True),
        IpAccessRule(id=2, scope="proxy", proxy_id="app", rule_type="deny", cidr="192.0.2.1/32", enabled=True),
    ]
    rendered = IpAccessService.render_nginx_directives(rules)
    assert "allow 10.0.0.0/8;" in rendered
    assert "deny 192.0.2.1/32;" in rendered


def test_ip_access_render_global_include():
    rules = [
        IpAccessRule(id=1, scope="global", proxy_id=None, rule_type="deny", cidr="198.51.100.0/24", enabled=True),
    ]
    content = IpAccessService.render_global_include(rules)
    assert "deny 198.51.100.0/24;" in content
    assert "Global IP access rules" in content


def test_rules_for_proxy_combines_global_and_proxy(db_session):
    service = IpAccessService(db_session)
    service.create(
        IpAccessRuleCreate(
            scope=IpAccessScope.GLOBAL,
            rule_type=IpAccessRuleType.ALLOW,
            cidr="10.0.0.0/8",
        )
    )
    service.create(
        IpAccessRuleCreate(
            scope=IpAccessScope.PROXY,
            proxy_id="myapp",
            rule_type=IpAccessRuleType.DENY,
            cidr="203.0.113.5/32",
        )
    )
    rules = service.rules_for_proxy("myapp")
    assert len(rules) == 2
    scopes = {rule.scope for rule in rules}
    assert scopes == {"global", "proxy"}
