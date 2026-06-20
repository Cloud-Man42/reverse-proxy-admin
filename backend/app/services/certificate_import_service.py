import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.imported_certificate import ImportedCertificate
from app.schemas import CertificateResponse
from app.security.validators import validate_domain
from app.services.certificate_pem import (
    CertificatePemError,
    build_fullchain,
    certificate_metadata,
    domain_in_certificate,
    extract_domains,
    load_certificates,
    load_private_key,
    private_key_matches_certificate,
    validate_certificate_name,
)


class CertificateImportService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db

    @property
    def certs_root(self) -> Path:
        return self.settings.data_dir / "certs"

    def cert_dir(self, name: str) -> Path:
        return self.certs_root / name

    def paths_for(self, cert: ImportedCertificate) -> tuple[Path, Path]:
        directory = self.cert_dir(cert.name)
        return directory / "fullchain.pem", directory / "privkey.pem"

    def get_by_name(self, name: str) -> ImportedCertificate | None:
        return self.db.query(ImportedCertificate).filter(ImportedCertificate.name == name).first()

    def is_imported(self, name: str) -> bool:
        return self.get_by_name(name) is not None

    def find_for_domain(self, domain: str) -> ImportedCertificate | None:
        requested = domain.strip().lower()
        rows = self.db.query(ImportedCertificate).all()
        for row in rows:
            if row.primary_domain.lower() == requested:
                return row
            if any(entry.lower() == requested for entry in row.domains_list()):
                return row
        return None

    def _status_for_expiry(self, expiry: datetime) -> str:
        now = datetime.now(timezone.utc)
        days = (expiry - now).days
        if days < 0:
            return "expired"
        if days <= self.settings.certbot_expiring_days:
            return "expiring"
        return "valid"

    def _metadata_from_files(self, cert_path: Path) -> tuple[str, datetime]:
        certs = load_certificates(cert_path.read_text(encoding="utf-8"))
        return certificate_metadata(certs[0])

    def list_certificates(self) -> list[CertificateResponse]:
        rows = self.db.query(ImportedCertificate).order_by(ImportedCertificate.name.asc()).all()
        responses: list[CertificateResponse] = []
        for row in rows:
            cert_path, _ = self.paths_for(row)
            if not cert_path.is_file():
                continue
            try:
                issuer, expiry = self._metadata_from_files(cert_path)
            except (OSError, CertificatePemError):
                continue
            responses.append(
                CertificateResponse(
                    name=row.name,
                    domains=row.domains_list() or [row.primary_domain],
                    issuer=issuer,
                    expiry=expiry,
                    status=self._status_for_expiry(expiry),
                    source="imported",
                    renewable=False,
                )
            )
        return responses

    def import_certificate(
        self,
        *,
        name: str,
        domain: str,
        certificate_pem: str,
        private_key_pem: str,
        chain_pem: str | None = None,
    ) -> ImportedCertificate:
        cert_name = validate_certificate_name(name)
        primary_domain = validate_domain(domain)
        if self.get_by_name(cert_name):
            raise ValueError(f"Certificate name '{cert_name}' is already in use")

        leaf_certs = load_certificates(certificate_pem)
        leaf = leaf_certs[0]
        if len(leaf_certs) > 1:
            raise ValueError("Upload only the leaf certificate in the certificate field; add intermediates in the chain field")

        private_key = load_private_key(private_key_pem)
        if not private_key_matches_certificate(leaf, private_key):
            raise ValueError("Private key does not match the uploaded certificate")

        if not domain_in_certificate(leaf, primary_domain):
            raise ValueError(f"Certificate does not include domain {primary_domain}")

        chain_parts: list[str] = []
        if chain_pem and chain_pem.strip():
            chain_parts.append(chain_pem)
        fullchain = build_fullchain(leaf, chain_parts)
        domains = extract_domains(leaf) or [primary_domain]

        directory = self.cert_dir(cert_name)
        directory.mkdir(parents=True, exist_ok=True)
        cert_path = directory / "fullchain.pem"
        key_path = directory / "privkey.pem"
        cert_path.write_text(fullchain, encoding="utf-8")
        key_path.write_text(private_key_pem.strip() + "\n", encoding="utf-8")
        os.chmod(cert_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)

        row = ImportedCertificate(
            name=cert_name,
            primary_domain=primary_domain,
            domains_json=json.dumps(domains),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_certificate(self, name: str) -> None:
        row = self.get_by_name(name)
        if not row:
            raise ValueError(f"Imported certificate '{name}' was not found")

        directory = self.cert_dir(name)
        for path in (directory / "fullchain.pem", directory / "privkey.pem"):
            if path.exists():
                path.unlink()
        if directory.exists() and not any(directory.iterdir()):
            directory.rmdir()

        self.db.delete(row)
        self.db.commit()
