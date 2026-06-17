import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.config import Settings
from app.schemas import CertificateResponse
from app.security.validators import validate_certbot_email, validate_domain


class CertbotOps:
    CERTBOT_BIN = "/usr/bin/certbot"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _certbot_cmd(self, *args: str) -> list[str]:
        from app.services.cert_paths import build_certbot_cmd

        return build_certbot_cmd(self.settings, *args)

    def _cert_path(self, name: str) -> Path:
        return self.settings.letsencrypt_live / name / "fullchain.pem"

    def _parse_expiry(self, cert_path: Path) -> datetime:
        result = subprocess.run(
            ["openssl", "x509", "-enddate", "-noout", "-in", str(cert_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "Unable to read certificate expiry")
        value = result.stdout.strip().replace("notAfter=", "")
        return datetime.strptime(value, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)

    def _parse_issuer(self, cert_path: Path) -> str:
        result = subprocess.run(
            ["openssl", "x509", "-issuer", "-noout", "-in", str(cert_path)],
            capture_output=True,
            text=True,
            check=False,
        )
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

    def list_certificates(self) -> List[CertificateResponse]:
        from app.services.cert_paths import run_certbot_certificates

        certs: List[CertificateResponse] = []
        live_dir = self.settings.letsencrypt_live
        if live_dir.exists():
            try:
                entries = sorted(live_dir.iterdir())
            except OSError:
                entries = []
            for entry in entries:
                if not entry.is_dir():
                    continue
                cert_path = self._cert_path(entry.name)
                try:
                    if not cert_path.is_file():
                        continue
                    expiry = self._parse_expiry(cert_path)
                    issuer = self._parse_issuer(cert_path)
                except (OSError, RuntimeError):
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
            if certs:
                return certs

        if not self.settings.use_sudo:
            return certs

        returncode, output = run_certbot_certificates(self.settings)
        if returncode != 0 or "No certificates found" in output:
            return certs

        current_name: str | None = None
        current_domains: list[str] = []
        current_expiry: datetime | None = None
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("Certificate Name:"):
                current_name = stripped.split(":", 1)[1].strip()
                current_domains = []
                current_expiry = None
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

    def issue_certificate(self, domain: str, email: str | None = None) -> tuple[bool, str]:
        domain = validate_domain(domain)
        try:
            contact_email = self.resolve_contact_email(email)
        except ValueError as exc:
            return False, str(exc)
        result = subprocess.run(
            self._certbot_cmd(
                "--nginx",
                "-d",
                domain,
                "--non-interactive",
                "--agree-tos",
                "-m",
                contact_email,
            ),
            capture_output=True,
            text=True,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()

    def renew_certificate(self, cert_name: str) -> tuple[bool, str]:
        if not cert_name.replace("-", "").replace(".", "").isalnum():
            raise ValueError("Invalid certificate name")
        result = subprocess.run(
            self._certbot_cmd("renew", "--cert-name", cert_name),
            capture_output=True,
            text=True,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()

    def dry_run_renew(self) -> tuple[bool, str]:
        result = subprocess.run(
            self._certbot_cmd("renew", "--dry-run"),
            capture_output=True,
            text=True,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()
