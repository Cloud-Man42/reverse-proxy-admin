from datetime import datetime, timedelta

import pytest

from app.models.notification import NotificationLog
from app.models.system_alert import SystemAlertHistory


@pytest.mark.api
def test_dashboard_returns_extended_stats(client, auth_session, db_session, temp_settings, monkeypatch):
    from app.models.proxy_traffic import ProxyTrafficAggregate

    hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    db_session.add(
        ProxyTrafficAggregate(
            proxy_id="app-a",
            period_start=hour,
            period_end=hour + timedelta(hours=1),
            period_type="hour",
            requests=10,
            bytes_in=2048,
            bytes_out=4096,
            upstream_bytes_in=512,
            upstream_bytes_out=1024,
        )
    )
    db_session.add(
        NotificationLog(
            event_type="backend_offline",
            subject="Backend offline",
            recipient_email="admin@example.com",
            status="sent",
            detail="Server down",
        )
    )
    db_session.add(
        SystemAlertHistory(
            alert_type="system_threshold",
            metric="cpu",
            value=95.0,
            threshold=90.0,
            status="breached",
            message="CPU usage high",
        )
    )
    db_session.commit()

    monkeypatch.setattr("app.services.metrics_service.ProxyService.list_proxies", lambda self: [])
    monkeypatch.setattr(
        "app.services.metrics_service.HealthCheckService.get_dashboard",
        lambda self: type("Health", (), {"healthy": 2, "warning": 1, "offline": 0, "unknown": 0})(),
    )
    monkeypatch.setattr("app.services.metrics_service.NginxOps.status", lambda self: (True, "active"))
    monkeypatch.setattr("app.services.metrics_service.SmtpService.status_label", lambda self: "connected")
    monkeypatch.setattr("app.services.metrics_service.CertificateService.list_certificates", lambda self: [])
    monkeypatch.setattr("app.api.system.LogReader.read_error_log", lambda self, lines=10: [])

    response = client.get("/api/dashboard", headers=auth_session["headers"])
    assert response.status_code == 200
    data = response.json()

    assert data["active_proxies"] == 0
    assert data["healthy_backends"] == 2
    assert data["warning_backends"] == 1
    assert data["traffic_bytes_in_24h"] == 2048
    assert data["traffic_bytes_out_24h"] == 4096
    assert len(data["traffic_history"]) == 1
    assert data["traffic_history"][0]["bytes_out"] == 4096
    assert len(data["recent_alerts"]) >= 2
    sources = {alert["source"] for alert in data["recent_alerts"]}
    assert "notification" in sources
    assert "system" in sources


@pytest.mark.api
def test_dashboard_requires_auth(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 401
