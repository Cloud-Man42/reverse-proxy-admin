from unittest.mock import patch

import pytest

from app.services.certbot_ops import CertbotOps

def test_resolve_contact_email_rejects_placeholder(temp_settings):
    ops = CertbotOps(temp_settings)
    with pytest.raises(ValueError, match="valid CERTBOT_EMAIL"):
        ops.resolve_contact_email("admin@example.com")


def test_resolve_contact_email_accepts_real_address(temp_settings):
    ops = CertbotOps(temp_settings)
    assert ops.resolve_contact_email("admin@inacloud.se") == "admin@inacloud.se"


def test_certbot_cmd_includes_config_dirs(temp_settings):
    ops = CertbotOps(temp_settings)
    cmd = ops._certbot_cmd("certificates")
    assert str(temp_settings.certbot_config_dir) in cmd
    assert "--logs-dir" in cmd

