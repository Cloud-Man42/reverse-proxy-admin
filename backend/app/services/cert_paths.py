import re
import subprocess
from pathlib import Path

from app.config import Settings

DOMAIN_LINE_RE = re.compile(r"^\s*Domains:\s*(.+)$", re.IGNORECASE)
CERT_NAME_LINE_RE = re.compile(r"^\s*Certificate Name:\s*(.+)$", re.IGNORECASE)


def certificate_paths(settings: Settings, domain: str) -> tuple[Path, Path]:
    live_dir = settings.letsencrypt_live / domain
    return live_dir / "fullchain.pem", live_dir / "privkey.pem"


def build_certbot_cmd(settings: Settings, *args: str) -> list[str]:
    settings.ensure_certbot_dirs()
    cmd = [
        "/usr/bin/certbot",
        "--config-dir",
        str(settings.certbot_config_dir),
        "--work-dir",
        str(settings.certbot_work_dir),
        "--logs-dir",
        str(settings.certbot_logs_dir),
        *args,
    ]
    if settings.use_sudo:
        return ["sudo", *cmd]
    return cmd


def run_certbot_certificates(settings: Settings) -> tuple[int, str]:
    result = subprocess.run(
        build_certbot_cmd(settings, "certificates"),
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output


def domain_has_certificate_in_output(domain: str, output: str) -> bool:
    domain_lower = domain.lower()
    for line in output.splitlines():
        name_match = CERT_NAME_LINE_RE.match(line)
        if name_match and name_match.group(1).strip().lower() == domain_lower:
            return True
        domains_match = DOMAIN_LINE_RE.match(line)
        if domains_match:
            domains = domains_match.group(1).split()
            if any(entry.lower() == domain_lower for entry in domains):
                return True
    return False


def certificate_exists(settings: Settings, domain: str) -> bool:
    cert_path, key_path = certificate_paths(settings, domain)
    try:
        if cert_path.is_file() and key_path.is_file():
            return True
    except OSError:
        pass

    if not settings.use_sudo:
        return False

    returncode, output = run_certbot_certificates(settings)
    if returncode != 0:
        return False
    if "No certificates found" in output:
        return False
    return domain_has_certificate_in_output(domain, output)


def certificate_exists_message(settings: Settings, domain: str) -> tuple[bool, str]:
    cert_path, _ = certificate_paths(settings, domain)
    if certificate_exists(settings, domain):
        return True, f"Certificate found for {domain}"

    if settings.use_sudo:
        returncode, output = run_certbot_certificates(settings)
        detail = output.strip() or f"certbot certificates exited with code {returncode}"
        return False, f"No certificate for {domain} (expected at {cert_path}). Certbot: {detail[:500]}"

    return False, f"No certificate at {cert_path}. Issue cert before enabling force_https."
