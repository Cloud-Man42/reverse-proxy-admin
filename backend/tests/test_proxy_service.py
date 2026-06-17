from unittest.mock import patch

import pytest
from pathlib import Path

from app.config import Settings
from app.schemas import ProxyAppCreate, ProxyAppUpdate, TargetProtocol
from app.services.nginx_ops import NginxOps
from app.services.proxy_service import ProxyService


@pytest.fixture
def temp_settings(tmp_path: Path) -> Settings:
    sites_available = tmp_path / "sites-available"
    sites_enabled = tmp_path / "sites-enabled"
    sites_available.mkdir()
    sites_enabled.mkdir()
    return Settings(
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backups",
        nginx_sites_available=sites_available,
        nginx_sites_enabled=sites_enabled,
        htpasswd_dir=tmp_path / "htpasswd",
        use_sudo=False,
        admin_password="test-password",
    )


def _sample_create(name: str = "app1") -> ProxyAppCreate:
    return ProxyAppCreate(
        name=name,
        domains=["example.com"],
        target_protocol=TargetProtocol.HTTP,
        target_host="10.0.0.10",
        target_port=8080,
    )


def _sample_update(name: str = "app2") -> ProxyAppUpdate:
    return ProxyAppUpdate(
        name=name,
        domains=["example.com"],
        target_protocol=TargetProtocol.HTTP,
        target_host="10.0.0.10",
        target_port=8080,
    )


@patch.object(NginxOps, "disable_site")
@patch.object(NginxOps, "enable_site")
@patch.object(NginxOps, "is_enabled", return_value=True)
@patch.object(NginxOps, "reload", return_value=(True, "reloaded"))
@patch.object(NginxOps, "test_config", return_value=(True, "ok"))
def test_update_proxy_can_rename_app(
    _test_config,
    _reload,
    _is_enabled,
    enable_site,
    disable_site,
    temp_settings: Settings,
) -> None:
    service = ProxyService(temp_settings)
    ok, _, created = service.create_proxy(_sample_create("app1"))
    assert ok and created is not None

    ok, _, updated = service.update_proxy("app1", _sample_update("app2"))
    assert ok
    assert updated is not None
    assert updated.id == "app2"
    assert (temp_settings.nginx_sites_available / "app1.conf").exists() is False
    assert (temp_settings.nginx_sites_available / "app2.conf").exists() is True
    disable_site.assert_any_call("app1.conf")
    enable_site.assert_any_call("app2.conf")
