import datetime

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.services.certificate_import_service import CertificateImportService
from app.services.certificate_pem import CertificatePemError, load_certificates, private_key_matches_certificate
from app.services.cert_paths import certificate_exists, resolve_certificate_paths


def generate_self_signed_pems(domain: str) -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(domain)]), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return cert_pem, key_pem


def test_private_key_matches_certificate():
    cert_pem, key_pem = generate_self_signed_pems("shop.example.com")
    cert = load_certificates(cert_pem)[0]
    from app.services.certificate_pem import load_private_key

    assert private_key_matches_certificate(cert, load_private_key(key_pem)) is True


def test_import_certificate_stores_files_and_metadata(db_session, temp_settings):
    cert_pem, key_pem = generate_self_signed_pems("shop.example.com")
    service = CertificateImportService(temp_settings, db_session)
    imported = service.import_certificate(
        name="shop.example.com",
        domain="shop.example.com",
        certificate_pem=cert_pem,
        private_key_pem=key_pem,
    )

    cert_path, key_path = service.paths_for(imported)
    assert cert_path.is_file()
    assert key_path.is_file()
    assert imported.primary_domain == "shop.example.com"
    listed = service.list_certificates()
    assert len(listed) == 1
    assert listed[0].source == "imported"
    assert listed[0].renewable is False


def test_import_rejects_mismatched_key(db_session, temp_settings):
    cert_pem, _ = generate_self_signed_pems("shop.example.com")
    _, other_key = generate_self_signed_pems("other.example.com")
    service = CertificateImportService(temp_settings, db_session)
    with pytest.raises(ValueError, match="does not match"):
        service.import_certificate(
            name="shop.example.com",
            domain="shop.example.com",
            certificate_pem=cert_pem,
            private_key_pem=other_key,
        )


def test_certificate_exists_finds_imported_cert(db_session, temp_settings):
    cert_pem, key_pem = generate_self_signed_pems("secure.example.com")
    CertificateImportService(temp_settings, db_session).import_certificate(
        name="secure.example.com",
        domain="secure.example.com",
        certificate_pem=cert_pem,
        private_key_pem=key_pem,
    )
    assert certificate_exists(temp_settings, "secure.example.com", db_session) is True
    cert_path, key_path = resolve_certificate_paths(temp_settings, "secure.example.com", db_session)
    assert "certs/secure.example.com/fullchain.pem" in cert_path.as_posix()
    assert key_path.name == "privkey.pem"


def test_delete_imported_certificate(db_session, temp_settings):
    cert_pem, key_pem = generate_self_signed_pems("delete.example.com")
    service = CertificateImportService(temp_settings, db_session)
    service.import_certificate(
        name="delete.example.com",
        domain="delete.example.com",
        certificate_pem=cert_pem,
        private_key_pem=key_pem,
    )
    service.delete_certificate("delete.example.com")
    assert service.get_by_name("delete.example.com") is None
    assert certificate_exists(temp_settings, "delete.example.com", db_session) is False


def test_validate_certificate_name_rejects_invalid():
    with pytest.raises(CertificatePemError):
        from app.services.certificate_pem import validate_certificate_name

        validate_certificate_name("../bad")
