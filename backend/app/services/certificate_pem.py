import re
from datetime import datetime, timezone
from typing import Iterable

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed25519, ed448, rsa

MAX_PEM_BYTES = 256_000
CERT_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,126}$")


class CertificatePemError(ValueError):
    pass


def validate_certificate_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned or not CERT_NAME_RE.match(cleaned):
        raise CertificatePemError(
            "Certificate name must be 1-127 characters and contain only letters, numbers, dots, underscores, or hyphens."
        )
    return cleaned


def _decode_pem(text: str, label: str) -> str:
    if not text or not text.strip():
        raise CertificatePemError(f"{label} is required")
    if len(text.encode("utf-8")) > MAX_PEM_BYTES:
        raise CertificatePemError(f"{label} exceeds the maximum allowed size")
    return text.strip()


def load_certificates(pem_data: str) -> list[x509.Certificate]:
    pem_data = _decode_pem(pem_data, "Certificate")
    try:
        certs = x509.load_pem_x509_certificates(pem_data.encode("utf-8"))
    except ValueError as exc:
        raise CertificatePemError("Certificate PEM is invalid") from exc
    if not certs:
        raise CertificatePemError("Certificate PEM does not contain a certificate")
    return certs


def load_private_key(pem_data: str) -> object:
    pem_data = _decode_pem(pem_data, "Private key")
    try:
        return serialization.load_pem_private_key(pem_data.encode("utf-8"), password=None)
    except (TypeError, ValueError) as exc:
        raise CertificatePemError("Private key PEM is invalid or password-protected keys are not supported") from exc


def private_key_matches_certificate(certificate: x509.Certificate, private_key: object) -> bool:
    cert_public_key = certificate.public_key()
    if isinstance(private_key, rsa.RSAPrivateKey):
        return cert_public_key.public_numbers() == private_key.public_key().public_numbers()
    if isinstance(private_key, ec.EllipticCurvePrivateKey):
        return cert_public_key.public_numbers() == private_key.public_key().public_numbers()
    if isinstance(private_key, (ed25519.Ed25519PrivateKey, ed448.Ed448PrivateKey)):
        return cert_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ) == private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    if isinstance(private_key, dsa.DSAPrivateKey):
        return cert_public_key.public_numbers() == private_key.public_key().public_numbers()
    return False


def extract_domains(certificate: x509.Certificate) -> list[str]:
    domains: list[str] = []
    try:
        san_ext = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        for entry in san_ext.value:
            if isinstance(entry, x509.DNSName):
                domains.append(entry.value)
    except x509.ExtensionNotFound:
        pass

    if not domains:
        for attribute in certificate.subject:
            if attribute.oid == x509.oid.NameOID.COMMON_NAME:
                domains.append(attribute.value)
                break

    seen: set[str] = set()
    unique: list[str] = []
    for domain in domains:
        normalized = domain.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(domain.strip())
    return unique


def domain_in_certificate(certificate: x509.Certificate, domain: str) -> bool:
    requested = domain.strip().lower()
    return any(entry.lower() == requested for entry in extract_domains(certificate))


def build_fullchain(leaf: x509.Certificate, chain_pems: Iterable[str]) -> str:
    parts = [leaf.public_bytes(serialization.Encoding.PEM).decode("utf-8")]
    for pem in chain_pems:
        cleaned = _decode_pem(pem, "Certificate chain")
        for cert in load_certificates(cleaned):
            parts.append(cert.public_bytes(serialization.Encoding.PEM).decode("utf-8"))
    return "".join(parts)


def certificate_metadata(certificate: x509.Certificate) -> tuple[str, datetime]:
    issuer_parts = []
    for attribute in certificate.issuer:
        issuer_parts.append(f"{attribute.oid._name}={attribute.value}")
    issuer = ", ".join(issuer_parts) if issuer_parts else "unknown"
    expiry = certificate.not_valid_after_utc
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return issuer, expiry
