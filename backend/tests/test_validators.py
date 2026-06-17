import pytest

from app.security.validators import (
    validate_certbot_email,
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


def test_validate_certbot_email_accepts_real_address():
    assert validate_certbot_email("Admin@Inacloud.se") == "admin@inacloud.se"


def test_validate_certbot_email_rejects_placeholder():
    with pytest.raises(ValueError, match="placeholder"):
        validate_certbot_email("admin@example.com")


def test_validate_path_prefix():
    from app.security.validators import validate_path_prefix

    assert validate_path_prefix("/") == "/"
    assert validate_path_prefix("/api/") == "/api"
    with pytest.raises(ValueError):
        validate_path_prefix("api")


def test_validate_header_name_rejects_injection():
    from app.security.validators import validate_header_name

    with pytest.raises(ValueError):
        validate_header_name("X-Injected; rm -rf /")
