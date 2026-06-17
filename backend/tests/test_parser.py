import pytest
from pathlib import Path

from app.config import Settings
from app.services.nginx_parser import parse_config_file


WS_CONFIG = """
server {
    listen 443 ssl;
    server_name secure.example.com;
    ssl_certificate /etc/letsencrypt/live/secure.example.com/fullchain.pem;

    location / {
        proxy_pass https://10.0.0.2:8443;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        auth_basic "Restricted";
    }
}
"""


@pytest.fixture
def temp_settings(tmp_path: Path) -> Settings:
    sites_available = tmp_path / "sites-available"
    sites_enabled = tmp_path / "sites-enabled"
    sites_available.mkdir()
    sites_enabled.mkdir()
    return Settings(
        nginx_sites_available=sites_available,
        nginx_sites_enabled=sites_enabled,
        use_sudo=False,
    )


def test_parse_ssl_and_websocket(temp_settings: Settings):
    path = temp_settings.nginx_sites_available / "secure.conf"
    path.write_text(WS_CONFIG, encoding="utf-8")
    parsed = parse_config_file(path, temp_settings)
    assert parsed is not None
    assert parsed.https_enabled is True
    assert parsed.websocket_enabled is True
    assert parsed.basic_auth_enabled is True
    assert parsed.target_protocol == "https"
