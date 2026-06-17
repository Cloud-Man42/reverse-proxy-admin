import re
import subprocess
from collections import deque
from pathlib import Path

from app.config import Settings

SUBPROCESS_TIMEOUT_SECONDS = 15

DOMAIN_LINE_RE = re.compile(r"^\s*Domains:\s*(.+)$", re.IGNORECASE)
CERT_NAME_LINE_RE = re.compile(r"^\s*Certificate Name:\s*(.+)$", re.IGNORECASE)
CERT_PATH_LINE_RE = re.compile(r"^\s*Certificate Path:\s*\S+/([^/\s]+)/fullchain\.pem", re.IGNORECASE)


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


def _run_subprocess(cmd: list[str], timeout: int = SUBPROCESS_TIMEOUT_SECONDS) -> tuple[int, str]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, "Command timed out"
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output


def run_certbot_certificates(settings: Settings) -> tuple[int, str]:
    return _run_subprocess(build_certbot_cmd(settings, "certificates"))


def _sudo_path_is_file(settings: Settings, path: Path) -> bool:
    if not settings.use_sudo:
        try:
            return path.is_file()
        except OSError:
            return False
    returncode, _ = _run_subprocess(["sudo", "/usr/bin/test", "-f", str(path)], timeout=5)
    return returncode == 0


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
        path_match = CERT_PATH_LINE_RE.match(line)
        if path_match and path_match.group(1).strip().lower() == domain_lower:
            return True
        if "certificate path:" in line.lower() and domain_lower in line.lower():
            return True
    return False


def certificate_exists(settings: Settings, domain: str) -> bool:
    cert_path, key_path = certificate_paths(settings, domain)
    try:
        if cert_path.is_file() and key_path.is_file():
            return True
    except OSError:
        pass

    if _sudo_path_is_file(settings, cert_path) and _sudo_path_is_file(settings, key_path):
        return True

    if not settings.use_sudo:
        return False

    returncode, output = run_certbot_certificates(settings)
    if returncode == 124:
        return False
    if "No certificates found" in output:
        return False
    if domain_has_certificate_in_output(domain, output):
        return True

    returncode, minimal_output = _run_subprocess(
        ["sudo", "/usr/bin/certbot", "certificates", "--config-dir", str(settings.certbot_config_dir)]
    )
    if returncode == 124:
        return False
    return domain_has_certificate_in_output(domain, minimal_output)


def certificate_exists_message(settings: Settings, domain: str) -> tuple[bool, str]:
    cert_path, key_path = certificate_paths(settings, domain)
    if certificate_exists(settings, domain):
        return True, f"Certificate found for {domain}"

    if settings.use_sudo:
        readable = _sudo_path_is_file(settings, cert_path)
        key_readable = _sudo_path_is_file(settings, key_path)
        returncode, output = run_certbot_certificates(settings)
        if returncode == 124:
            detail = "certbot certificates timed out"
        else:
            detail = output.strip() or f"certbot certificates exited with code {returncode}"
        return (
            False,
            "No certificate for "
            f"{domain} (expected at {cert_path}, sudo readable={readable}/{key_readable}). "
            f"Certbot: {detail[:500]}",
        )

    return False, f"No certificate at {cert_path}. Issue cert before enabling force_https."
