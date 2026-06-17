from unittest.mock import patch

import pytest

from app.config import Settings
from app.schemas import ProxyAppResponse, TargetProtocol
from app.services.network_map_service import NetworkMapService


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        nginx_sites_available=tmp_path / "sites-available",
        nginx_sites_enabled=tmp_path / "sites-enabled",
        use_sudo=False,
        server_public_ip="203.0.113.1",
        server_hostname="test-proxy",
    )


def _sample_proxy(**overrides) -> ProxyAppResponse:
    route = {
        "path_prefix": "/",
        "target_protocol": TargetProtocol.HTTP,
        "target_host": "10.0.0.5",
        "target_port": 8080,
        "websocket_enabled": False,
    }
    data = {
        "id": "myapp",
        "name": "myapp",
        "config_file": "myapp.conf",
        "domains": ["example.com"],
        "routes": [route],
        "target_protocol": TargetProtocol.HTTP,
        "target_host": "10.0.0.5",
        "target_port": 8080,
        "websocket_enabled": False,
        "custom_headers": [],
        "max_body_size": None,
        "basic_auth_enabled": False,
        "basic_auth_username": None,
        "basic_auth_password": None,
        "force_https": False,
        "enabled": True,
        "https_enabled": False,
        "upstream": "http://10.0.0.5:8080",
        "managed": True,
    }
    data.update(overrides)
    return ProxyAppResponse(**data)


def test_network_map_structure(settings: Settings):
    proxies = [
        _sample_proxy(),
        _sample_proxy(id="disabled", name="disabled", domains=["off.local"], enabled=False),
    ]
    with patch.object(NetworkMapService, "__init__", lambda self, s: None):
        service = NetworkMapService(settings)
        service.settings = settings
        service.proxy_service = type("P", (), {"list_proxies": lambda self: proxies})()
        service.firewall_service = type(
            "F",
            (),
            {
                "get_status": lambda self: type(
                    "S",
                    (),
                    {"active": True, "rules": [], "source": "fallback"},
                )()
            },
        )()
        service.nginx_ops = type("N", (), {"status": lambda self: (True, "ok")})()

        result = service.build()

    node_ids = {node.id for node in result.nodes}
    assert "internet" in node_ids
    assert "firewall" in node_ids
    assert "nginx" in node_ids
    assert "admin-ui" in node_ids
    assert "app-myapp" in node_ids
    assert "upstream-myapp" in node_ids
    assert "app-disabled" in node_ids

    disabled = next(n for n in result.nodes if n.id == "app-disabled")
    assert disabled.status == "inactive"

    edge_pairs = {(edge.source, edge.target) for edge in result.edges}
    assert ("internet", "firewall") in edge_pairs
    assert ("firewall", "nginx") in edge_pairs
    assert ("nginx", "admin-ui") in edge_pairs
    assert ("nginx", "app-myapp") in edge_pairs
    assert ("app-myapp", "upstream-myapp") in edge_pairs


def test_firewall_fallback(settings: Settings):
    from app.services.firewall_service import FirewallService

    with patch("app.services.firewall_service.subprocess.run") as mock_run:
        mock_run.return_value = type("R", (), {"returncode": 1, "stdout": "", "stderr": "denied"})()
        status = FirewallService(settings).get_status()

    assert status.source == "fallback"
    assert status.active is True
    assert len(status.rules) > 0
