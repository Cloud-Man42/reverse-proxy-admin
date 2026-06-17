import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.config import Settings
from app.schemas import CertificateResponse
from app.security.validators import validate_domain


class CertbotOps:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _cmd(self, *args: str) -> list[str]:
        if self.settings.use_sudo:
            return ["sudo", *args]
        return list(args)

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

    def list_certificates(self) -> List[CertificateResponse]:
        certs: List[CertificateResponse] = []
        live_dir = self.settings.letsencrypt_live
        if not live_dir.exists():
            return certs

        for entry in sorted(live_dir.iterdir()):
            if not entry.is_dir():
                continue
            cert_path = self._cert_path(entry.name)
            if not cert_path.exists():
                continue
            try:
                expiry = self._parse_expiry(cert_path)
                issuer = self._parse_issuer(cert_path)
            except RuntimeError:
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

    def issue_certificate(self, domain: str, email: str | None = None) -> tuple[bool, str]:
        domain = validate_domain(domain)
        email = email or self.settings.certbot_email
        result = subprocess.run(
            self._cmd(
                "certbot",
                "--nginx",
                "-d",
                domain,
                "--non-interactive",
                "--agree-tos",
                "-m",
                email,
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
            self._cmd("certbot", "renew", "--cert-name", cert_name),
            capture_output=True,
            text=True,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()

    def dry_run_renew(self) -> tuple[bool, str]:
        result = subprocess.run(
            self._cmd("certbot", "renew", "--dry-run"),
            capture_output=True,
            text=True,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()
