import subprocess
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.certificate_renewal import CertificateRenewalLog
from app.schemas import CertificateRenewalLogResponse, CertificateResponse
from app.security.validators import validate_certbot_email, validate_domain
from app.services.cert_paths import SUBPROCESS_TIMEOUT_SECONDS, run_certbot_certificates


class CertbotOps:
    CERTBOT_BIN = "/usr/bin/certbot"

    def __init__(self, settings: Settings, db: Optional[Session] = None) -> None:
        self.settings = settings
        self.db = db

    def _certbot_cmd(self, *args: str) -> list[str]:
        from app.services.cert_paths import build_certbot_cmd

        return build_certbot_cmd(self.settings, *args)

    def _cert_path(self, name: str) -> Path:
        return self.settings.letsencrypt_live / name / "fullchain.pem"

    def _run(self, cmd: list[str], timeout: int = SUBPROCESS_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )

    def _parse_expiry(self, cert_path: Path) -> datetime:
        result = self._run(["/usr/bin/openssl", "x509", "-enddate", "-noout", "-in", str(cert_path)], timeout=5)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "Unable to read certificate expiry")
        value = result.stdout.strip().replace("notAfter=", "")
        return datetime.strptime(value, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)

    def _parse_issuer(self, cert_path: Path) -> str:
        result = self._run(["/usr/bin/openssl", "x509", "-issuer", "-noout", "-in", str(cert_path)], timeout=5)
        return result.stdout.strip().replace("issuer=", "") if result.returncode == 0 else "unknown"

    def _status_for_expiry(self, expiry: datetime) -> str:
        now = datetime.now(timezone.utc)
        days = (expiry - now).days
        if days < 0:
            return "expired"
        if days <= self.settings.certbot_expiring_days:
            return "expiring"
        return "valid"

    def _parse_expiry_from_certbot_line(self, line: str) -> datetime | None:
        if "Expiry Date:" not in line:
            return None
        value = line.split("Expiry Date:", 1)[1].strip().split(" (", 1)[0]
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S%z")
        except ValueError:
            return None

    def _parse_certificates_from_certbot_output(self, output: str) -> List[CertificateResponse]:
        certs: List[CertificateResponse] = []
        current_name: str | None = None
        current_domains: list[str] = []
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("Certificate Name:"):
                current_name = stripped.split(":", 1)[1].strip()
                current_domains = []
                continue
            if stripped.startswith("Domains:") and current_name:
                current_domains = stripped.split(":", 1)[1].split()
                continue
            if stripped.startswith("Expiry Date:") and current_name:
                current_expiry = self._parse_expiry_from_certbot_line(stripped)
                if current_expiry is None:
                    continue
                certs.append(
                    CertificateResponse(
                        name=current_name,
                        domains=current_domains or [current_name],
                        issuer="Let's Encrypt",
                        expiry=current_expiry,
                        status=self._status_for_expiry(current_expiry),
                    )
                )
                current_name = None
        return certs

    def _list_from_live_dir(self) -> List[CertificateResponse]:
        certs: List[CertificateResponse] = []
        live_dir = self.settings.letsencrypt_live
        if not live_dir.exists():
            return certs

        try:
            entries = sorted(live_dir.iterdir())
        except OSError:
            return certs

        for entry in entries:
            if not entry.is_dir():
                continue
            cert_path = self._cert_path(entry.name)
            try:
                if not cert_path.is_file():
                    continue
                expiry = self._parse_expiry(cert_path)
                issuer = self._parse_issuer(cert_path)
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                continue
            certs.append(
                CertificateResponse(
                    name=entry.name,
                    domains=[entry.name],
                    issuer=issuer,
                    expiry=expiry,
                    status=self._status_for_expiry(expiry),
                )
            )
        return certs

    def list_certificates(self) -> List[CertificateResponse]:
        if self.settings.use_sudo:
            returncode, output = run_certbot_certificates(self.settings)
            if returncode == 124:
                return []
            if returncode != 0 or "No certificates found" in output:
                return []
            return self._parse_certificates_from_certbot_output(output)
        return self._list_from_live_dir()

    def resolve_contact_email(self, email: str | None = None) -> str:
        try:
            return validate_certbot_email(email or self.settings.certbot_email)
        except ValueError as exc:
            raise ValueError(
                "Set a valid CERTBOT_EMAIL in /etc/nginx-admin/env or provide an email when issuing the certificate."
            ) from exc

    def get_settings_info(self) -> tuple[str, bool]:
        email = self.settings.certbot_email.strip()
        try:
            validated = validate_certbot_email(email)
            return validated, True
        except ValueError:
            return email, False

    def log_renewal(
        self,
        certificate_name: str,
        domain: str,
        action: str,
        status: str,
        detail: str | None = None,
    ) -> None:
        if not self.db:
            return
        entry = CertificateRenewalLog(
            certificate_name=certificate_name,
            domain=domain,
            action=action,
            status=status,
            detail=detail,
        )
        self.db.add(entry)
        self.db.commit()

    def list_renewal_history(
        self,
        *,
        certificate_name: str | None = None,
        limit: int = 100,
    ) -> list[CertificateRenewalLogResponse]:
        if not self.db:
            return []
        query = self.db.query(CertificateRenewalLog)
        if certificate_name:
            query = query.filter(CertificateRenewalLog.certificate_name == certificate_name)
        rows = (
            query.order_by(CertificateRenewalLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            CertificateRenewalLogResponse(
                id=row.id,
                certificate_name=row.certificate_name,
                domain=row.domain,
                action=row.action,
                status=row.status,
                detail=row.detail,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def issue_certificate(self, domain: str, email: str | None = None) -> tuple[bool, str]:
        domain = validate_domain(domain)
        try:
            contact_email = self.resolve_contact_email(email)
        except ValueError as exc:
            return False, str(exc)
        try:
            result = self._run(
                self._certbot_cmd(
                    "--nginx",
                    "-d",
                    domain,
                    "--non-interactive",
                    "--agree-tos",
                    "-m",
                    contact_email,
                ),
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            output = "Certbot timed out while issuing certificate"
            self.log_renewal(domain, domain, "issue", "failed", output)
            return False, output
        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip()
        status = "success" if result.returncode == 0 else "failed"
        self.log_renewal(domain, domain, "issue", status, output)
        return result.returncode == 0, output

    def renew_certificate(self, cert_name: str) -> tuple[bool, str]:
        if not cert_name.replace("-", "").replace(".", "").isalnum():
            raise ValueError("Invalid certificate name")
        try:
            result = self._run(self._certbot_cmd("renew", "--cert-name", cert_name), timeout=300)
        except subprocess.TimeoutExpired:
            output = "Certbot timed out while renewing certificate"
            self.log_renewal(cert_name, cert_name, "renew", "failed", output)
            return False, output
        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip()
        status = "success" if result.returncode == 0 else "failed"
        self.log_renewal(cert_name, cert_name, "renew", status, output)
        return result.returncode == 0, output

    def dry_run_renew(self) -> tuple[bool, str]:
        try:
            result = self._run(self._certbot_cmd("renew", "--dry-run"), timeout=300)
        except subprocess.TimeoutExpired:
            output = "Certbot dry run timed out"
            self.log_renewal("all", "all", "dry_run", "failed", output)
            return False, output
        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip()
        status = "success" if result.returncode == 0 else "failed"
        self.log_renewal("all", "all", "dry_run", status, output)
        return result.returncode == 0, output
