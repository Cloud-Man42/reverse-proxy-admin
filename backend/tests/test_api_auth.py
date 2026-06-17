import pytest


@pytest.mark.api
def test_login_success(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "test-password"})
    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert "csrf_token" in response.json()


@pytest.mark.api
def test_login_wrong_password(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


@pytest.mark.api
def test_me_requires_authentication(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.api
def test_logout_requires_csrf(client, auth_session):
    response = client.post("/api/auth/logout", cookies=auth_session["cookies"])
    assert response.status_code == 403


@pytest.mark.api
def test_logout_success(client, auth_session):
    response = client.post(
        "/api/auth/logout",
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 200
