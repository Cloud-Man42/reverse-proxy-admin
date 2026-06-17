import pytest

from app.config import Settings
from app.schemas import ProxyAppCreate, TargetProtocol
from app.services.nginx_parser import parse_config_file
from app.services.nginx_writer import NginxWriter


SAMPLE_CONFIG = """server {
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


def test_parse_simple_proxy(temp_settings):
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
    assert "access_log /var/log/nginx/proxy-myapp.log proxy_debug;" in rendered
    assert "Upgrade $http_upgrade" not in rendered


def test_generate_config_with_multiple_routes(temp_settings: Settings):
    writer = NginxWriter(temp_settings)
    app = ProxyAppCreate(
        name="multi",
        domains=["example.domain.com"],
        routes=[
            {
                "path_prefix": "/",
                "target_protocol": TargetProtocol.HTTP,
                "target_host": "192.168.1.10",
                "target_port": 3000,
            },
            {
                "path_prefix": "/api",
                "target_protocol": TargetProtocol.HTTP,
                "target_host": "192.168.1.10",
                "target_port": 5000,
            },
        ],
    )
    rendered = writer.render_config(app)
    assert "location /api/" in rendered
    assert "proxy_pass http://192.168.1.10:5000/;" in rendered
    assert "location / {" in rendered or "location /{" in rendered.replace(" ", "")
    assert "proxy_pass http://192.168.1.10:3000;" in rendered


def test_generate_config_with_websocket(temp_settings: Settings):
    writer = NginxWriter(temp_settings)
    app = ProxyAppCreate(
        name="wsapp",
        domains=["ws.example.com"],
        routes=[
            {
                "path_prefix": "/",
                "target_protocol": TargetProtocol.HTTP,
                "target_host": "10.0.0.5",
                "target_port": 3000,
                "websocket_enabled": True,
            }
        ],
    )
    rendered = writer.render_config(app)
    assert 'proxy_set_header Upgrade $http_upgrade' in rendered
    assert 'proxy_set_header Connection "upgrade"' in rendered
