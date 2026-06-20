from app.models.proxy_rate_limit import ProxyRateLimit
from app.schemas import ProxyAppCreate, TargetProtocol
from app.services.nginx_writer import NginxWriter


def test_render_rate_limit_client_ip(temp_settings):
    app = ProxyAppCreate(
        name="limited",
        domains=["limited.example.com"],
        routes=[
            {
                "path_prefix": "/",
                "target_protocol": TargetProtocol.HTTP,
                "target_host": "10.0.0.10",
                "target_port": 8080,
            }
        ],
    )
    rate_limit = ProxyRateLimit(
        proxy_id="limited",
        enabled=True,
        requests_per_minute=120,
        burst=30,
        nodelay=True,
        key_type="client_ip",
    )
    config = NginxWriter(temp_settings).render_config(app, rate_limit=rate_limit)
    assert "limit_req_zone $binary_remote_addr zone=limited_rl:10m rate=120r/m;" in config
    assert "limit_req zone=limited_rl burst=30 nodelay;" in config


def test_render_rate_limit_uri_key(temp_settings):
    app = ProxyAppCreate(
        name="uri-limit",
        domains=["uri.example.com"],
        routes=[
            {
                "path_prefix": "/api",
                "target_protocol": TargetProtocol.HTTP,
                "target_host": "10.0.0.10",
                "target_port": 8080,
            }
        ],
    )
    rate_limit = ProxyRateLimit(
        proxy_id="uri-limit",
        enabled=True,
        requests_per_minute=60,
        burst=10,
        nodelay=False,
        key_type="uri",
    )
    config = NginxWriter(temp_settings).render_config(app, rate_limit=rate_limit)
    assert "limit_req_zone $uri zone=uri-limit_rl:10m rate=60r/m;" in config
    assert "limit_req zone=uri-limit_rl burst=10;" in config
    assert "nodelay" not in config.split("limit_req zone=uri-limit_rl")[1].split("\n")[0]


def test_render_without_rate_limit(temp_settings):
    app = ProxyAppCreate(
        name="open",
        domains=["open.example.com"],
        routes=[
            {
                "path_prefix": "/",
                "target_protocol": TargetProtocol.HTTP,
                "target_host": "10.0.0.10",
                "target_port": 8080,
            }
        ],
    )
    config = NginxWriter(temp_settings).render_config(app)
    assert "limit_req_zone" not in config
    assert "limit_req zone=" not in config
