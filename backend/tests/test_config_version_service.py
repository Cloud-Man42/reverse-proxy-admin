from unittest.mock import patch

from app.schemas import ProxyAppCreate, ProxyRoute, TargetProtocol
from app.services.config_version_service import ConfigVersionService, RESOURCE_PROXY
from app.services.nginx_ops import NginxOps
from app.services.proxy_service import ProxyService


def test_record_and_list_versions(db_session, temp_settings):
    service = ConfigVersionService(temp_settings, db_session)

    first = service.record(
        resource_type=RESOURCE_PROXY,
        resource_id="app1",
        username="admin",
        summary="Created proxy",
        old_config=None,
        new_config="server { listen 80; }",
    )
    second = service.record(
        resource_type=RESOURCE_PROXY,
        resource_id="app1",
        username="admin",
        summary="Updated proxy",
        old_config="server { listen 80; }",
        new_config="server { listen 80; server_name example.com; }",
    )

    versions = service.list_versions(resource_type=RESOURCE_PROXY, resource_id="app1")
    assert len(versions) == 2
    assert versions[0].id == second.id
    assert versions[0].version == 2
    assert versions[1].id == first.id
    assert first.version == 1


def test_compare_versions(db_session, temp_settings):
    service = ConfigVersionService(temp_settings, db_session)
    left = service.record(
        resource_type=RESOURCE_PROXY,
        resource_id="app1",
        username="admin",
        summary="Created proxy",
        old_config=None,
        new_config="alpha\nbeta",
    )
    right = service.record(
        resource_type=RESOURCE_PROXY,
        resource_id="app1",
        username="admin",
        summary="Updated proxy",
        old_config="alpha\nbeta",
        new_config="alpha\ngamma",
    )

    result = service.compare(left.id, right.id)
    assert result is not None
    assert result.version1 == 1
    assert result.version2 == 2
    assert "-beta" in result.diff
    assert "+gamma" in result.diff


@patch.object(NginxOps, "reload", return_value=(True, "reloaded"))
@patch.object(NginxOps, "test_config", return_value=(True, "ok"))
@patch.object(NginxOps, "enable_site")
def test_rollback_restores_previous_config(_enable, _test, _reload, db_session, temp_settings):
    service = ConfigVersionService(temp_settings, db_session)
    path = temp_settings.nginx_sites_available / "app1.conf"
    original = "server { listen 80; }"
    updated = "server { listen 80; server_name example.com; }"
    path.write_text(updated, encoding="utf-8")

    version = service.record(
        resource_type=RESOURCE_PROXY,
        resource_id="app1",
        username="admin",
        summary="Updated proxy",
        old_config=original,
        new_config=updated,
    )

    ok, message, rollback_version = service.rollback(version.id, "admin")
    assert ok is True
    assert "reloaded" in message
    assert path.read_text(encoding="utf-8") == original
    assert rollback_version is not None
    assert rollback_version.version == 2


@patch.object(NginxOps, "disable_site")
@patch.object(NginxOps, "reload", return_value=(True, "reloaded"))
@patch.object(NginxOps, "test_config", return_value=(True, "ok"))
@patch.object(NginxOps, "enable_site")
def test_proxy_service_records_config_versions(_enable, _test, _reload, _disable, db_session, temp_settings):
    proxy_service = ProxyService(temp_settings, db_session)
    config_service = ConfigVersionService(temp_settings, db_session)
    payload = ProxyAppCreate(
        name="versioned",
        domains=["example.com"],
        routes=[
            ProxyRoute(
                path_prefix="/",
                target_protocol=TargetProtocol.HTTP,
                target_host="10.0.0.10",
                target_port=8080,
            )
        ],
    )

    ok, _, created, _ = proxy_service.create_proxy(payload, username="admin")
    assert ok and created is not None

    versions = config_service.list_versions(resource_type=RESOURCE_PROXY, resource_id="versioned")
    assert len(versions) == 1
    assert versions[0].summary == "Created proxy"
    assert versions[0].username == "admin"

    detail = config_service.get_detail(versions[0].id)
    assert detail is not None
    assert detail.new_config
    assert detail.old_config is None
