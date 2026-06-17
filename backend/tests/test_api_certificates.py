from unittest.mock import patch

import pytest

from app.services.certbot_ops import CertbotOps


@pytest.mark.api
def test_certificate_settings(client, auth_session):
    response = client.get("/api/certificates/settings", cookies=auth_session["cookies"])
    assert response.status_code == 200
    assert "default_email" in response.json()


@pytest.mark.api
@patch.object(CertbotOps, "issue_certificate", return_value=(False, "certbot failed"))
def test_issue_certificate_failure(mock_issue, client, auth_session):
    response = client.post(
        "/api/certificates",
        json={"domain": "valid.example.com", "email": "admin@inacloud.se"},
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 400
    assert "certbot failed" in response.json()["detail"]
    mock_issue.assert_called_once()


@pytest.mark.api
def test_issue_certificate_rejects_placeholder_email(client, auth_session):
    response = client.post(
        "/api/certificates",
        json={"domain": "valid.example.com", "email": "admin@example.com"},
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 422
