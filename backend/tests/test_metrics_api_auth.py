import pytest


@pytest.mark.api
def test_metrics_endpoints_require_auth(client):
    assert client.get("/api/metrics/dashboard").status_code == 401
    assert client.get("/api/live-requests").status_code == 401
    assert client.get("/api/failed-requests").status_code == 401
    assert client.get("/api/alerts").status_code == 401


@pytest.mark.api
def test_metrics_dashboard_readable_by_viewer(client, viewer_session, monkeypatch):
    monkeypatch.setattr("app.services.metrics_service.NginxOps.status", lambda self: (True, "active"))
    monkeypatch.setattr("app.services.metrics_service.CertificateService.list_certificates", lambda self: [])
    monkeypatch.setattr("app.services.metrics_service.ProxyService.list_proxies", lambda self: [])
    response = client.get("/api/metrics/dashboard", headers=viewer_session["headers"])
    assert response.status_code == 200
    data = response.json()
    assert "live_traffic" in data
    assert "system_health" in data


@pytest.mark.api
def test_alert_mutations_require_edit(client, viewer_session):
    response = client.post(
        "/api/alerts",
        headers=viewer_session["headers"],
        json={
            "name": "Test",
            "metric_type": "error_rate",
            "threshold": 0.1,
        },
    )
    assert response.status_code == 403


@pytest.mark.api
def test_live_requests_response_has_no_sensitive_fields(client, auth_session, db_session):
    from datetime import datetime

    from app.models.metrics import RequestEvent

    db_session.add(
        RequestEvent(
            timestamp=datetime.utcnow(),
            proxy_id="app-a",
            client_ip="203.0.113.10",
            host="example.com",
            method="GET",
            uri="/safe",
            status=200,
            bytes_sent=100,
            user_agent="curl/8.0",
        )
    )
    db_session.commit()

    response = client.get("/api/live-requests", headers=auth_session["headers"])
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert set(item.keys()) <= {
        "timestamp",
        "client_ip",
        "host",
        "uri",
        "method",
        "status",
        "backend_addr",
        "response_time_ms",
        "upstream_time_ms",
        "bytes_sent",
        "user_agent",
    }
    assert "authorization" not in item
    assert "cookie" not in item
