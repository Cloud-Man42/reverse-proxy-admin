from unittest.mock import patch

import pytest

from app.services.certificate_import_service import CertificateImportService
from tests.test_certificate_import_service import generate_self_signed_pems


@pytest.mark.api
def test_import_certificate_success(client, auth_session, db_session, temp_settings):
    cert_pem, key_pem = generate_self_signed_pems("api-import.example.com")
    response = client.post(
        "/api/certificates/import",
        data={
            "name": "api-import.example.com",
            "domain": "api-import.example.com",
        },
        files={
            "certificate": ("cert.pem", cert_pem, "application/x-pem-file"),
            "private_key": ("key.pem", key_pem, "application/x-pem-file"),
        },
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 201
    assert response.json()["message"] == "Certificate imported"

    listed = client.get("/api/certificates", cookies=auth_session["cookies"])
    assert listed.status_code == 200
    names = [entry["name"] for entry in listed.json()]
    assert "api-import.example.com" in names


@pytest.mark.api
def test_renew_imported_certificate_rejected(client, auth_session, db_session, temp_settings):
    cert_pem, key_pem = generate_self_signed_pems("no-renew.example.com")
    CertificateImportService(temp_settings, db_session).import_certificate(
        name="no-renew.example.com",
        domain="no-renew.example.com",
        certificate_pem=cert_pem,
        private_key_pem=key_pem,
    )
    response = client.post(
        "/api/certificates/no-renew.example.com/renew",
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 400
    assert "cannot be renewed automatically" in response.json()["detail"].lower()


@pytest.mark.api
def test_delete_imported_certificate(client, auth_session, db_session, temp_settings):
    cert_pem, key_pem = generate_self_signed_pems("delete-api.example.com")
    CertificateImportService(temp_settings, db_session).import_certificate(
        name="delete-api.example.com",
        domain="delete-api.example.com",
        certificate_pem=cert_pem,
        private_key_pem=key_pem,
    )
    response = client.delete(
        "/api/certificates/delete-api.example.com",
        cookies=auth_session["cookies"],
        headers=auth_session["headers"],
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Certificate deleted"
