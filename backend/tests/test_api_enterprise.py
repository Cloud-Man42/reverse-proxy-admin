import pytest


@pytest.mark.api
def test_smtp_settings_hide_password(client, auth_session):
    response = client.get("/api/smtp", headers=auth_session["headers"])
    assert response.status_code == 200
    data = response.json()
    assert "password" not in data
    assert "password_set" in data


@pytest.mark.api
def test_backend_pools_require_auth(client):
    response = client.get("/api/backend-pools")
    assert response.status_code == 401
