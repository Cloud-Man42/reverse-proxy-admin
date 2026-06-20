PROXY_DEBUG_EXTENDED = (
    "203.0.113.10|17/Jun/2026:13:08:39 +0000|example.com|GET / HTTP/1.1|200|512|256|128|384|-|curl/8.0"
)


def _extended_log_line() -> str:
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")
    return (
        f"203.0.113.10|{stamp}|example.com|GET / HTTP/1.1|200|512|256|128|384|-|curl/8.0"
    )


def test_collect_proxy_traffic_from_extended_log(temp_settings, db_session):
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
    log_path.write_text(_extended_log_line() + "\n", encoding="utf-8")

    from app.services.proxy_traffic_service import ProxyTrafficService

    service = ProxyTrafficService(temp_settings, db_session)
    parsed = service.collect_proxy("myapp")
    assert parsed == 1

    summary = service.list_summary("24h")
    assert summary[0].connections == 1
    assert summary[0].bytes_in == 256
    assert summary[0].bytes_out == 512

    stats = service.get_proxy_stats("myapp", "24h")
    assert stats is not None
    assert stats.connections == 1
    assert stats.upstream_bytes_in == 128
    assert stats.upstream_bytes_out == 384


def test_collect_proxy_traffic_handles_log_rotation(temp_settings, db_session):
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
    log_path.write_text(_extended_log_line() + "\n", encoding="utf-8")

    from app.models.proxy_traffic import ProxyTrafficLogState
    from app.services.proxy_traffic_service import ProxyTrafficService

    service = ProxyTrafficService(temp_settings, db_session)
    service.collect_proxy("myapp")
    state = db_session.get(ProxyTrafficLogState, "myapp")
    assert state is not None
    state.byte_offset = 999999
    db_session.commit()

    service.collect_proxy("myapp")
    db_session.refresh(state)
    assert state.byte_offset > 0


def test_aggregate_history_sums_all_proxies(temp_settings, db_session):
    from datetime import datetime, timedelta

    from app.models.proxy_traffic import ProxyTrafficAggregate
    from app.services.proxy_traffic_service import ProxyTrafficService

    hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    db_session.add(
        ProxyTrafficAggregate(
            proxy_id="myapp",
            period_start=hour,
            period_end=hour + timedelta(hours=1),
            period_type="hour",
            requests=5,
            bytes_in=100,
            bytes_out=200,
            upstream_bytes_in=0,
            upstream_bytes_out=0,
        )
    )
    db_session.add(
        ProxyTrafficAggregate(
            proxy_id="other",
            period_start=hour,
            period_end=hour + timedelta(hours=1),
            period_type="hour",
            requests=3,
            bytes_in=50,
            bytes_out=75,
            upstream_bytes_in=0,
            upstream_bytes_out=0,
        )
    )
    db_session.commit()

    service = ProxyTrafficService(temp_settings, db_session)
    assert service.total_bytes("24h") == (150, 275)
    history = service.aggregate_history("24h")
    assert len(history) == 1
    assert history[0].connections == 8
    assert history[0].bytes_in == 150
    assert history[0].bytes_out == 275
