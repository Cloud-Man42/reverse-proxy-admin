import pytest

from app.schemas import ProxyAppCreate, ProxyRoute, TargetProtocol
from app.services.traffic_debug_service import TrafficDebugService


PROXY_DEBUG_LINE = (
    "203.0.113.10|17/Jun/2026:13:08:39 +0000|example.com|GET / HTTP/1.1|200|512|-|curl/8.0"
)


def test_read_proxy_traffic_from_dedicated_log(temp_settings):
    config_path = temp_settings.nginx_sites_available / "myapp.conf"
    config_path.write_text(
        """
server {
    listen 80;
    server_name example.com;
    location / {
        proxy_pass http://10.0.0.10:8080;
    }
}
""",
        encoding="utf-8",
    )
    log_path = temp_settings.nginx_access_log.parent / "proxy-myapp.log"
    log_path.write_text(PROXY_DEBUG_LINE + "\n", encoding="utf-8")

    result = TrafficDebugService(temp_settings).read_proxy_traffic("myapp", lines=10)
    assert result.dedicated_log is True
    assert len(result.entries) == 1
    assert result.entries[0].client_ip == "203.0.113.10"


def test_read_proxy_traffic_raises_for_unknown_proxy(temp_settings):
    with pytest.raises(ValueError, match="Proxy not found"):
        TrafficDebugService(temp_settings).read_proxy_traffic("missing", lines=10)


def test_read_proxy_traffic_skips_unparsed_lines(temp_settings):
    config_path = temp_settings.nginx_sites_available / "myapp.conf"
    config_path.write_text(
        """
server {
    listen 80;
    server_name example.com;
    location / {
        proxy_pass http://10.0.0.10:8080;
    }
}
""",
        encoding="utf-8",
    )
    log_path = temp_settings.nginx_access_log.parent / "proxy-myapp.log"
    log_path.write_text("garbage line\n" + PROXY_DEBUG_LINE + "\n", encoding="utf-8")

    result = TrafficDebugService(temp_settings).read_proxy_traffic("myapp", lines=10)
    assert len(result.entries) == 1
