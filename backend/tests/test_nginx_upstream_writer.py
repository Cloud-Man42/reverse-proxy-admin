from app.models.backend_pool import BackendPool
from app.models.backend_server import BackendServer
from app.schemas import LoadBalancingMethod, ProxyAppCreate, TargetProtocol
from app.services.nginx_writer import NginxWriter


def test_render_upstream_round_robin(temp_settings):
    pool = BackendPool(
        id=1,
        name="demo_pool",
        load_balancing_method=LoadBalancingMethod.ROUND_ROBIN.value,
        enabled=True,
    )
    pool.servers = [
        BackendServer(host="192.168.1.10", port=443, protocol="https", weight=10, role="primary", enabled=True, name="s1"),
        BackendServer(host="192.168.1.11", port=443, protocol="https", weight=5, role="backup", enabled=True, name="s2"),
    ]
    app = ProxyAppCreate(
        name="demo",
        domains=["demo.example.com"],
        routes=[{"path_prefix": "/", "target_protocol": "https", "target_host": "127.0.0.1", "target_port": 443}],
    )
    writer = NginxWriter(temp_settings)
    config = writer.render_config(app, {0: pool})
    assert "upstream demo_0_backend" in config
    assert "server 192.168.1.10:443 weight=10 max_fails=3 fail_timeout=30s;" in config
    assert "server 192.168.1.11:443 weight=5 backup max_fails=3 fail_timeout=30s;" in config
    assert "proxy_pass https://demo_0_backend;" in config


def test_render_upstream_least_conn(temp_settings):
    pool = BackendPool(
        id=1,
        name="demo_pool",
        load_balancing_method=LoadBalancingMethod.LEAST_CONN.value,
        enabled=True,
    )
    pool.servers = [
        BackendServer(host="10.0.0.1", port=8080, protocol="http", weight=1, role="primary", enabled=True, name="s1"),
    ]
    app = ProxyAppCreate(
        name="web",
        domains=["web.example.com"],
        routes=[{"path_prefix": "/", "target_protocol": "http", "target_host": "127.0.0.1", "target_port": 8080}],
    )
    config = NginxWriter(temp_settings).render_config(app, {0: pool})
    assert "least_conn;" in config
    assert "max_fails=3 fail_timeout=30s;" in config
    assert "proxy_pass http://web_0_backend;" in config


def test_render_upstream_excludes_offline_servers(temp_settings):
    pool = BackendPool(
        id=1,
        name="demo_pool",
        load_balancing_method=LoadBalancingMethod.ROUND_ROBIN.value,
        enabled=True,
    )
    pool.servers = [
        BackendServer(
            host="192.168.1.10",
            port=8080,
            protocol="http",
            weight=1,
            role="primary",
            enabled=True,
            name="healthy",
            health_status="healthy",
        ),
        BackendServer(
            host="192.168.1.11",
            port=8080,
            protocol="http",
            weight=1,
            role="primary",
            enabled=True,
            name="offline",
            health_status="offline",
        ),
    ]
    app = ProxyAppCreate(
        name="demo",
        domains=["demo.example.com"],
        routes=[{"path_prefix": "/", "target_protocol": "http", "target_host": "127.0.0.1", "target_port": 8080}],
    )
    config = NginxWriter(temp_settings).render_config(app, {0: pool})
    assert "server 192.168.1.10:8080 max_fails=3 fail_timeout=30s;" in config
    assert "192.168.1.11" not in config
