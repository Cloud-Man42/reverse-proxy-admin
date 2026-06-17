import pytest

from app.security.validators import (
    validate_domain,
    validate_ip,
    validate_port,
    validate_slug,
)


def test_validate_domain_accepts_fqdn():
    assert validate_domain("example.com") == "example.com"


def test_validate_domain_rejects_injection():
    with pytest.raises(ValueError):
        validate_domain("example.com; rm -rf /")


def test_validate_ip_accepts_private():
    assert validate_ip("192.168.1.10") == "192.168.1.10"


def test_validate_ip_rejects_invalid():
    with pytest.raises(ValueError):
        validate_ip("999.999.999.999")


def test_validate_port_range():
    assert validate_port(8080) == 8080
    with pytest.raises(ValueError):
        validate_port(70000)


def test_validate_slug():
    assert validate_slug("my-app-1") == "my-app-1"
    with pytest.raises(ValueError):
        validate_slug("Bad Name")
