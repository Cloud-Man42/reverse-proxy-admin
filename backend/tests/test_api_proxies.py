from unittest.mock import patch

import pytest

from app.services.nginx_ops import NginxOps
from tests.conftest import sample_proxy_payload


@pytest.mark.api
def test_list_proxies_requires_auth(client):
    response = client.get("/api/proxies")
    assert response.status_code == 401


@pytest.mark.api
@patch.object(NginxOps, "reload", return_value=(True, "ok"))
@patch.object(NginxOps, "test_config", return_value=(True, "ok"))
@patch.object(NginxOps, "enable_site")
def test_create_proxy_success(_enable, _test, _reload, client, auth_session):
    payload = sample_proxy_payload(name="apiapp").model_dump()
    response = client.post(
        "/api/proxies",
        json=payload,
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 200
    assert response.json()["name"] == "apiapp"


@pytest.mark.api
def test_create_proxy_invalid_payload(client, auth_session):
    payload = sample_proxy_payload(name="myapp").model_dump()
    payload["name"] = "Bad Name"
    response = client.post(
        "/api/proxies",
        json=payload,
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 422


@pytest.mark.api
def test_viewer_cannot_create_proxy(client, viewer_session):
    payload = sample_proxy_payload(name="viewerapp").model_dump()
    response = client.post(
        "/api/proxies",
        json=payload,
        cookies=viewer_session["cookies"],
        headers=viewer_session["headers"],
    )
    assert response.status_code == 403


@pytest.mark.api
def test_get_unknown_proxy_returns_404(client, auth_session):
    response = client.get("/api/proxies/does-not-exist", cookies=auth_session["cookies"])
    assert response.status_code == 404


@pytest.mark.api
@patch.object(NginxOps, "reload", return_value=(True, "ok"))
@patch.object(NginxOps, "test_config", return_value=(True, "ok"))
@patch.object(NginxOps, "enable_site")
def test_traffic_debug_unknown_proxy(_enable, _test, _reload, client, auth_session):
    response = client.get("/api/proxies/missing/traffic-debug", cookies=auth_session["cookies"])
    assert response.status_code == 404


@pytest.mark.api
def test_test_flow_draft(client, auth_session):
    payload = sample_proxy_payload(name="flowapp").model_dump()
    response = client.post(
        "/api/proxies/actions/test-flow",
        json=payload,
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 200
    assert "checks" in response.json()
