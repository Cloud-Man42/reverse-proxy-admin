from unittest.mock import patch

import pytest

from app.config import Settings
from app.services.cert_paths import (
    certificate_exists,
    domain_has_certificate_in_output,
)


def test_certificate_exists_when_files_readable(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        letsencrypt_live=tmp_path / "letsencrypt" / "live",
        certbot_config_dir=tmp_path / "letsencrypt",
        use_sudo=False,
    )
    domain = "example.com"
    cert_dir = settings.letsencrypt_live / domain
    cert_dir.mkdir(parents=True)
    (cert_dir / "fullchain.pem").write_text("cert", encoding="utf-8")
    (cert_dir / "privkey.pem").write_text("key", encoding="utf-8")
    assert certificate_exists(settings, domain) is True


def test_domain_has_certificate_in_output_matches_domains_line():
    output = """
Found the following certs:
  Certificate Name: sora.inacloud.net
    Domains: sora.inacloud.net
    Expiry Date: 2026-09-15 12:00:00+00:00 (VALID: 89 days)
"""
    assert domain_has_certificate_in_output("sora.inacloud.net", output) is True
    assert domain_has_certificate_in_output("missing.example.com", output) is False


def test_certificate_exists_uses_certbot_when_unreadable(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        letsencrypt_live=tmp_path / "letsencrypt" / "live",
        certbot_config_dir=tmp_path / "letsencrypt",
        certbot_work_dir=tmp_path / "data" / "certbot" / "work",
        certbot_logs_dir=tmp_path / "data" / "certbot" / "logs",
        use_sudo=True,
    )
    domain = "sora.inacloud.net"
    certbot_output = "Certificate Name: sora.inacloud.net\n  Domains: sora.inacloud.net\n"
    with patch("pathlib.Path.is_file", return_value=False):
        with patch("app.services.cert_paths.run_certbot_certificates", return_value=(0, certbot_output)):
            assert certificate_exists(settings, domain) is True


def test_certificate_exists_false_when_certbot_fails(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        letsencrypt_live=tmp_path / "letsencrypt" / "live",
        certbot_config_dir=tmp_path / "letsencrypt",
        use_sudo=True,
    )
    with patch("pathlib.Path.is_file", return_value=False):
        with patch("app.services.cert_paths.run_certbot_certificates", return_value=(1, "error")):
            assert certificate_exists(settings, "missing.example.com") is False


def test_certificate_exists_false_when_no_certificates_found(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        letsencrypt_live=tmp_path / "letsencrypt" / "live",
        certbot_config_dir=tmp_path / "letsencrypt",
        use_sudo=True,
    )
    with patch("pathlib.Path.is_file", return_value=False):
        with patch("app.services.cert_paths.run_certbot_certificates", return_value=(0, "No certificates found.")):
            assert certificate_exists(settings, "missing.example.com") is False
