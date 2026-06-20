from datetime import datetime, timezone

import pytest

from app.services.analytics_service import AnalyticsService
from app.services.proxy_traffic_service import ProxyTrafficService


def _latency_log_line(
    client_ip: str = "203.0.113.10",
    status: int = 200,
    path: str = "/",
    request_time: str = "0.125",
    upstream_time: str = "0.050",
) -> str:
    stamp = datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")
    return (
        f"{client_ip}|{stamp}|example.com|GET {path} HTTP/1.1|{status}|512|256|128|384"
        f"|-|curl/8.0|{request_time}|{upstream_time}"
    )


def _write_proxy_config(temp_settings, proxy_id: str = "myapp") -> None:
    config_path = temp_settings.nginx_sites_available / f"{proxy_id}.conf"
    config_path.write_text(
        f"""
server {{
    listen 80;
    server_name example.com;
    location / {{
        proxy_pass http://10.0.0.10:8080;
    }}
}}
""",
        encoding="utf-8",
    )


def test_analytics_summary_and_proxy_detail(temp_settings, db_session):
    _write_proxy_config(temp_settings)
    log_path = temp_settings.nginx_access_log.parent / "proxy-myapp.log"
    log_path.write_text(
        "\n".join(
            [
                _latency_log_line(status=200, path="/", request_time="0.100", upstream_time="0.040"),
                _latency_log_line(
                    client_ip="203.0.113.11",
                    status=404,
                    path="/missing",
                    request_time="0.200",
                    upstream_time="0.080",
                ),
                _latency_log_line(client_ip="198.51.100.1", status=500, path="/api", request_time="0.300"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    traffic = ProxyTrafficService(temp_settings, db_session)
    assert traffic.collect_proxy("myapp") == 3

    analytics = AnalyticsService(temp_settings, db_session)
    summary = analytics.get_summary("24h")
    assert summary.range == "24h"
    assert len(summary.items) == 1
    item = summary.items[0]
    assert item.proxy_id == "myapp"
    assert item.requests == 3
    assert item.status_2xx == 1
    assert item.status_4xx == 1
    assert item.status_5xx == 1
    assert item.error_rate == pytest.approx(2 / 3)
    assert item.latency_avg_ms > 0

    detail = analytics.get_proxy_analytics("myapp", "24h")
    assert detail is not None
    assert detail.requests == 3
    assert "203.0.113.10" in detail.top_clients
    assert detail.top_clients["203.0.113.10"] == 1
    assert "/" in detail.top_paths
    assert detail.top_paths["/"] == 1


def test_analytics_missing_proxy(temp_settings, db_session):
    analytics = AnalyticsService(temp_settings, db_session)
    assert analytics.get_proxy_analytics("missing", "24h") is None
