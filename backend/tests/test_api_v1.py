import pytest
from unittest.mock import patch

from app.schemas import ApiTokenCreate
from app.services.api_token_service import ApiTokenService
from app.services.nginx_ops import NginxOps


@pytest.fixture
def read_token(db_session):
    service = ApiTokenService(db_session)
    _, plain = service.create(
        ApiTokenCreate(
            name="v1-read",
            scopes=["proxies:read", "backend_pools:read", "certificates:read", "health:read", "analytics:read", "system:read", "audit:read"],
        )
    )
    return plain


@pytest.fixture
def write_token(db_session):
    service = ApiTokenService(db_session)
    _, plain = service.create(
        ApiTokenCreate(
            name="v1-write",
            scopes=["proxies:read", "proxies:write", "backend_pools:read", "backend_pools:write"],
        )
    )
    return plain


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.api
def test_v1_proxy_hosts_list(client, read_token):
    response = client.get("/api/v1/proxy-hosts", headers=bearer(read_token))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.api
@patch.object(NginxOps, "reload", return_value=(True, "ok"))
@patch.object(NginxOps, "test_config", return_value=(True, "ok"))
@patch.object(NginxOps, "enable_site")
def test_v1_proxy_hosts_create(_enable, _test, _reload, client, write_token, temp_settings):
    payload = {
        "name": "v1apiapp",
        "domains": ["v1api.example.com"],
        "routes": [
            {
                "path_prefix": "/",
                "target_protocol": "http",
                "target_host": "127.0.0.1",
                "target_port": 8080,
            }
        ],
        "enabled": True,
    }
    response = client.post("/api/v1/proxy-hosts", headers=bearer(write_token), json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "v1apiapp"

    get_resp = client.get(f"/api/v1/proxy-hosts/{data['id']}", headers=bearer(write_token))
    assert get_resp.status_code == 200

    delete_resp = client.delete(f"/api/v1/proxy-hosts/{data['id']}", headers=bearer(write_token))
    assert delete_resp.status_code == 200


@pytest.mark.api
def test_v1_backend_pools_list(client, read_token):
    response = client.get("/api/v1/backend-pools", headers=bearer(read_token))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.api
def test_v1_certificates_list(client, read_token):
    response = client.get("/api/v1/certificates", headers=bearer(read_token))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.api
def test_v1_health_dashboard(client, read_token):
    response = client.get("/api/v1/health/dashboard", headers=bearer(read_token))
    assert response.status_code == 200
    data = response.json()
    assert "healthy" in data
    assert "servers" in data


@pytest.mark.api
def test_v1_analytics_summary(client, read_token):
    response = client.get("/api/v1/analytics/summary", headers=bearer(read_token))
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "range" in data


@pytest.mark.api
@patch.object(NginxOps, "status", return_value=(True, "active"))
def test_v1_system_health(_status, client, read_token):
    response = client.get("/api/v1/system/health", headers=bearer(read_token))
    assert response.status_code == 200
    data = response.json()
    assert "nginx_active" in data
    assert "disk_percent" in data


@pytest.mark.api
def test_v1_audit_logs(client, read_token):
    response = client.get("/api/v1/audit", headers=bearer(read_token))
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.api
def test_v1_write_scope_required_for_create(client, read_token):
    payload = {
        "name": "deniedapp",
        "domains": ["denied.example.com"],
        "routes": [
            {
                "path_prefix": "/",
                "target_protocol": "http",
                "target_host": "127.0.0.1",
                "target_port": 8080,
            }
        ],
        "enabled": True,
    }
    response = client.post("/api/v1/proxy-hosts", headers=bearer(read_token), json=payload)
    assert response.status_code == 403
