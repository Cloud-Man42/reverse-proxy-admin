from unittest.mock import patch
from uuid import uuid4

from app.services.catalog_service import CatalogService
from app.services.nginx_ops import NginxOps
from app.schemas.catalog import TemplateCreateProxyRequest


def test_legacy_templates_endpoint_shape(client, auth_session):
    response = client.get("/api/templates/legacy", cookies=auth_session["cookies"])
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 9
    first = data[0]
    assert "slug" in first
    assert "defaults" in first
    assert isinstance(first["defaults"], dict)


def test_legacy_slug_alias_resolves(client, auth_session):
    response = client.get("/api/templates/proxmox", cookies=auth_session["cookies"])
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "proxmox-ve"


def test_catalog_list_returns_paginated_shape(client, auth_session):
    response = client.get("/api/templates", cookies=auth_session["cookies"])
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 100


@patch("app.services.proxy_service.certificate_exists", return_value=True)
@patch.object(NginxOps, "reload", return_value=(True, "reloaded"))
@patch.object(NginxOps, "test_config", return_value=(True, "ok"))
@patch.object(NginxOps, "enable_site")
def test_create_proxy_from_template_success(_enable, _test, _reload, _cert, client, auth_session, temp_settings):
    catalog = CatalogService(temp_settings)
    template = catalog.get_template("grafana")
    assert template is not None
    proxy_name = f"grafana-{uuid4().hex[:8]}"
    payload = TemplateCreateProxyRequest(
        name=proxy_name,
        domain=f"{proxy_name}.example.com",
        upstream_host="127.0.0.1",
        upstream_port=3000,
        force_https=False,
    )
    response = client.post(
        f"/api/templates/{template.slug}/create-proxy",
        json=payload.model_dump(mode="json"),
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True, data.get("message", data)
    assert data["proxy"]["name"] == proxy_name


@patch("app.services.proxy_service.certificate_exists", return_value=True)
@patch.object(NginxOps, "reload", return_value=(True, "reloaded"))
@patch.object(NginxOps, "test_config", return_value=(False, "syntax error"))
@patch.object(NginxOps, "enable_site")
def test_create_proxy_from_template_rolls_back_on_nginx_test_failure(_enable, _test, _reload, _cert, client, auth_session, temp_settings):
    catalog = CatalogService(temp_settings)
    template = catalog.get_template("grafana")
    assert template is not None
    proxy_name = f"grafana-fail-{uuid4().hex[:8]}"
    payload = TemplateCreateProxyRequest(
        name=proxy_name,
        domain=f"{proxy_name}.example.com",
        upstream_host="127.0.0.1",
        upstream_port=3000,
        force_https=False,
    )
    response = client.post(
        f"/api/templates/{template.slug}/create-proxy",
        json=payload.model_dump(mode="json"),
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["failure_stage"]
