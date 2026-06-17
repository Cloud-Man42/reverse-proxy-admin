import pytest
from pathlib import Path

from app.config import Settings
from app.schemas import ProxyAppCreate, TargetProtocol
from app.services.nginx_parser import parse_config_file
from app.services.nginx_writer import NginxWriter


SAMPLE_CONFIG = """
server {
    listen 80;
    server_name example.domain.com;

    location / {
        proxy_pass http://192.168.1.10:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
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
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backups",
        nginx_sites_available=sites_available,
        nginx_sites_enabled=sites_enabled,
        htpasswd_dir=tmp_path / "htpasswd",
        use_sudo=False,
        admin_password="test-password",
    )


def test_parse_simple_proxy(temp_settings: Settings, tmp_path: Path):
    config_path = temp_settings.nginx_sites_available / "example.conf"
    config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
    parsed = parse_config_file(config_path, temp_settings)
    assert parsed is not None
    assert parsed.domains == ["example.domain.com"]
    assert parsed.target_host == "192.168.1.10"
    assert parsed.target_port == 8080


def test_generate_config_contains_core_directives(temp_settings: Settings):
    writer = NginxWriter(temp_settings)
    app = ProxyAppCreate(
        name="myapp",
        domains=["example.domain.com"],
        target_protocol=TargetProtocol.HTTP,
        target_host="192.168.1.10",
        target_port=8080,
    )
    rendered = writer.render_config(app)
    assert "server_name example.domain.com" in rendered
    assert "proxy_pass http://192.168.1.10:8080" in rendered
    assert "Upgrade $http_upgrade" not in rendered


def test_generate_config_with_websocket(temp_settings: Settings):
    writer = NginxWriter(temp_settings)
    app = ProxyAppCreate(
        name="wsapp",
        domains=["ws.example.com"],
        target_protocol=TargetProtocol.HTTP,
        target_host="10.0.0.5",
        target_port=3000,
        websocket_enabled=True,
    )
    rendered = writer.render_config(app)
    assert 'proxy_set_header Upgrade $http_upgrade' in rendered
    assert 'proxy_set_header Connection "upgrade"' in rendered
