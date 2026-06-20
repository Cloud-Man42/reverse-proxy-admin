from unittest.mock import patch

import pytest

from app.schemas import ProxyAppCreate, ProxyRoute, TargetProtocol
from app.services.nginx_ops import NginxOps
from app.services.proxy_service import ProxyService


@patch.object(NginxOps, "disable_site")
@patch.object(NginxOps, "enable_site")
@patch.object(NginxOps, "is_enabled", return_value=True)
@patch.object(NginxOps, "reload", return_value=(True, "reloaded"))
@patch.object(NginxOps, "test_config", return_value=(True, "ok"))
def test_update_proxy_can_rename_app(_test, _reload, _enabled, enable_site, disable_site, temp_settings):
    service = ProxyService(temp_settings)
    create_payload = ProxyAppCreate(
        name="app1",
        domains=["example.com"],
        routes=[ProxyRoute(path_prefix="/", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.10", target_port=8080)],
    )
    ok, _, created, _ = service.create_proxy(create_payload)
    assert ok and created is not None

    update_payload = ProxyAppCreate(
        name="app2",
        domains=["example.com"],
        routes=[ProxyRoute(path_prefix="/", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.10", target_port=8080)],
    )
    ok, _, updated, _ = service.update_proxy("app1", update_payload)
    assert ok
    assert updated is not None
    assert updated.id == "app2"


@patch.object(NginxOps, "enable_site")
@patch.object(NginxOps, "reload", return_value=(True, "reloaded"))
@patch.object(NginxOps, "test_config", return_value=(True, "ok"))
def test_force_https_rejected_without_certificate(_test, _reload, _enable, temp_settings):
    service = ProxyService(temp_settings)
    payload = ProxyAppCreate(
        name="secure",
        domains=["secure.example.com"],
        force_https=True,
        routes=[ProxyRoute(path_prefix="/", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.10", target_port=8080)],
    )
    with patch("app.services.proxy_service.certificate_exists", return_value=False):
        ok, message, _, _ = service.create_proxy(payload)
    assert ok is False
    assert "Force HTTPS" in message


@patch.object(NginxOps, "enable_site")
@patch.object(NginxOps, "reload", return_value=(True, "reloaded"))
@patch.object(NginxOps, "test_config", return_value=(True, "ok"))
def test_create_proxy_persists_notes(_test, _reload, _enable, temp_settings):
    service = ProxyService(temp_settings)
    payload = ProxyAppCreate(
        name="noted",
        domains=["example.com"],
        notes="Production traffic only",
        routes=[ProxyRoute(path_prefix="/", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.10", target_port=8080)],
    )
    ok, _, created, _ = service.create_proxy(payload)
    assert ok and created is not None
    assert created.notes == "Production traffic only"

    fetched = service.get_proxy("noted")
    assert fetched is not None
    assert fetched.notes == "Production traffic only"


@patch.object(NginxOps, "enable_site")
@patch.object(NginxOps, "reload", return_value=(True, "reloaded"))
@patch.object(NginxOps, "test_config", return_value=(False, "nginx -t failed"))
def test_create_proxy_rolls_back_on_nginx_test_failure(_test, _reload, _enable, temp_settings):
    service = ProxyService(temp_settings)
    payload = ProxyAppCreate(
        name="broken",
        domains=["example.com"],
        routes=[ProxyRoute(path_prefix="/", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.10", target_port=8080)],
    )
    ok, message, created, failure = service.create_proxy(payload)
    assert ok is False
    assert failure == "validation"
    assert "nginx -t failed" in message
    assert created is None
    assert not (temp_settings.nginx_sites_available / "broken.conf").exists()
