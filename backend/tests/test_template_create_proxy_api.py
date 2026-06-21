from unittest.mock import patch

from app.services.nginx_ops import NginxOps
from app.schemas.catalog import TemplatePreviewRequest


@patch.object(NginxOps, "status", return_value=(True, "ok"))
def test_preview_api_returns_rendered_config(_status, client, auth_session):
    payload = TemplatePreviewRequest(
        domain="grafana.example.com",
        upstream_host="127.0.0.1",
        upstream_port=3000,
    )
    response = client.post(
        "/api/templates/grafana/preview",
        json=payload.model_dump(mode="json"),
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert "proxy_pass" in data["rendered_config"]
    assert data["resolved_payload"]["routes"][0]["target_port"] == 3000


def test_preview_api_invalid_domain_returns_422(client, auth_session):
    response = client.post(
        "/api/templates/grafana/preview",
        json={"domain": "not a valid domain!!!", "upstream_host": "127.0.0.1"},
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 422
