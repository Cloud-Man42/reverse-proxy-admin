import pytest

from app.services.api_token_service import ApiTokenService, hash_token
from app.schemas import ApiTokenCreate


@pytest.fixture
def api_token(db_session):
    service = ApiTokenService(db_session)
    token, plain = service.create(
        ApiTokenCreate(name="test-token", scopes=["proxies:read", "analytics:read"])
    )
    return {"token": token, "plain": plain}


@pytest.mark.api
def test_api_token_requires_bearer(client):
    response = client.get("/api/v1/proxy-hosts")
    assert response.status_code == 401


@pytest.mark.api
def test_api_token_invalid_bearer(client):
    response = client.get(
        "/api/v1/proxy-hosts",
        headers={"Authorization": "Bearer rpa_invalidtoken"},
    )
    assert response.status_code == 401


@pytest.mark.api
def test_api_token_scope_denied(client, db_session):
    service = ApiTokenService(db_session)
    _, plain = service.create(ApiTokenCreate(name="read-only", scopes=["analytics:read"]))
    response = client.get(
        "/api/v1/proxy-hosts",
        headers={"Authorization": f"Bearer {plain}"},
    )
    assert response.status_code == 403
    assert "proxies:read" in response.json()["detail"]


@pytest.mark.api
def test_api_token_valid_access(client, api_token):
    response = client.get(
        "/api/v1/proxy-hosts",
        headers={"Authorization": f"Bearer {api_token['plain']}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.api
def test_api_token_admin_scope(client, db_session):
    service = ApiTokenService(db_session)
    _, plain = service.create(ApiTokenCreate(name="admin-token", scopes=["admin"]))
    response = client.get(
        "/api/v1/proxy-hosts",
        headers={"Authorization": f"Bearer {plain}"},
    )
    assert response.status_code == 200


@pytest.mark.api
def test_api_token_revoked(client, db_session, api_token):
    ApiTokenService(db_session).revoke(api_token["token"].id)
    response = client.get(
        "/api/v1/proxy-hosts",
        headers={"Authorization": f"Bearer {api_token['plain']}"},
    )
    assert response.status_code == 401


@pytest.mark.api
def test_api_token_hash_validation(db_session, api_token):
    service = ApiTokenService(db_session)
    assert service.validate_hash(api_token["plain"]) is not None
    assert service.validate_hash("rpa_notfound") is None


@pytest.mark.api
def test_api_token_last_used_updated(client, db_session, api_token):
    token = api_token["token"]
    assert token.last_used_at is None
    client.get(
        "/api/v1/proxy-hosts",
        headers={"Authorization": f"Bearer {api_token['plain']}"},
    )
    db_session.refresh(token)
    assert token.last_used_at is not None


@pytest.mark.api
def test_hash_token_deterministic():
    assert hash_token("rpa_test") == hash_token("rpa_test")
    assert hash_token("rpa_test") != hash_token("rpa_other")


@pytest.mark.api
def test_api_tokens_admin_crud(client, auth_session):
    create_resp = client.post(
        "/api/api-tokens",
        headers=auth_session["headers"],
        cookies=auth_session["cookies"],
        json={"name": "ci-token", "scopes": ["proxies:read"]},
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["token"].startswith("rpa_")
    assert data["token_prefix"] == data["token"][:12]
    token_id = data["id"]

    list_resp = client.get(
        "/api/api-tokens",
        headers=auth_session["headers"],
        cookies=auth_session["cookies"],
    )
    assert list_resp.status_code == 200
    assert any(item["id"] == token_id for item in list_resp.json())

    revoke_resp = client.delete(
        f"/api/api-tokens/{token_id}",
        headers=auth_session["headers"],
        cookies=auth_session["cookies"],
    )
    assert revoke_resp.status_code == 200


@pytest.mark.api
def test_api_tokens_require_admin(client, viewer_session):
    response = client.get(
        "/api/api-tokens",
        headers=viewer_session["headers"],
        cookies=viewer_session["cookies"],
    )
    assert response.status_code == 403
