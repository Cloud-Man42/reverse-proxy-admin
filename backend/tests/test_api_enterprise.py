import pytest


@pytest.mark.api
def test_smtp_settings_hide_password(client, auth_session):
    response = client.get("/api/smtp", headers=auth_session["headers"])
    assert response.status_code == 200
    data = response.json()
    assert "password" not in data
    assert "password_set" in data


@pytest.mark.api
def test_smtp_settings_allow_empty_sender_email(client, auth_session):
    response = client.put(
        "/api/smtp",
        json={
            "host": "smtp.example.com",
            "port": 587,
            "username": "mailer@example.com",
            "sender_name": "Admin",
            "sender_email": "",
            "default_recipient_email": "alerts@example.com",
            "security_mode": "starttls",
        },
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 200
    assert response.json()["sender_email"] == ""
    assert response.json()["default_recipient_email"] == "alerts@example.com"


@pytest.mark.api
def test_backend_pools_require_auth(client):
    response = client.get("/api/backend-pools")
    assert response.status_code == 401
