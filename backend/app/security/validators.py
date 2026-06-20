import ipaddress
import re
from typing import Annotated

from pydantic import AfterValidator, Field

DOMAIN_REGEX = re.compile(
    r"^(?:\*\.)?(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)
SLUG_REGEX = re.compile(r"^[a-z0-9-]+$")
PATH_PREFIX_REGEX = re.compile(r"^/[a-zA-Z0-9/_-]*$")
HEADER_NAME_REGEX = re.compile(r"^[A-Za-z0-9-]+$")
INJECTION_PATTERNS = re.compile(r"[;\`\$\(\)\r\n<>]")
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BLOCKED_EMAIL_DOMAINS = {"example.com", "example.org", "example.net", "localhost", "invalid", "test"}


def reject_injection(value: str) -> str:
    if INJECTION_PATTERNS.search(value):
        raise ValueError("Invalid characters detected in input")
    return value.strip()


def validate_domain(value: str, allow_wildcard: bool = True) -> str:
    value = reject_injection(value).lower()
    if allow_wildcard and value.startswith("*."):
        candidate = value[2:]
        if DOMAIN_REGEX.match(f"x.{candidate}"):
            return value
    if not DOMAIN_REGEX.match(value):
        raise ValueError(f"Invalid domain: {value}")
    return value


def validate_ip(value: str) -> str:
    value = reject_injection(value)
    try:
        ipaddress.ip_address(value)
    except ValueError as exc:
        raise ValueError(f"Invalid IP address: {value}") from exc
    return value


def validate_port(value: int) -> int:
    if value < 1 or value > 65535:
        raise ValueError("Port must be between 1 and 65535")
    return value


def validate_slug(value: str) -> str:
    value = reject_injection(value).lower()
    if not SLUG_REGEX.match(value):
        raise ValueError("Slug may only contain lowercase letters, numbers, and hyphens")
    return value


def validate_path_prefix(value: str) -> str:
    value = reject_injection(value.strip())
    if not value.startswith("/"):
        raise ValueError("Path prefix must start with /")
    if value != "/" and value.endswith("/"):
        value = value.rstrip("/")
    if not PATH_PREFIX_REGEX.match(value):
        raise ValueError("Path prefix contains invalid characters")
    return value


def validate_header_name(value: str) -> str:
    value = reject_injection(value)
    if not HEADER_NAME_REGEX.match(value):
        raise ValueError(f"Invalid header name: {value}")
    return value


def validate_header_value(value: str) -> str:
    value = reject_injection(value)
    if len(value) > 1024:
        raise ValueError("Header value too long")
    return value


def validate_certbot_email(value: str) -> str:
    value = reject_injection(value).lower()
    if not EMAIL_REGEX.match(value):
        raise ValueError("Invalid email address")
    domain = value.split("@", 1)[1]
    if domain in BLOCKED_EMAIL_DOMAINS or domain.endswith(".example"):
        raise ValueError("Certbot requires a real contact email address, not a placeholder")
    return value


def validate_smtp_sender_email(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    value = reject_injection(value).lower()
    if not EMAIL_REGEX.match(value):
        raise ValueError("Invalid email address")
    return value


CertbotEmailStr = Annotated[str, AfterValidator(validate_certbot_email)]
SmtpSenderEmailStr = Annotated[str, AfterValidator(validate_smtp_sender_email)]
DomainStr = Annotated[str, AfterValidator(lambda v: validate_domain(v))]
SlugStr = Annotated[str, AfterValidator(validate_slug)]
PathPrefixStr = Annotated[str, AfterValidator(validate_path_prefix)]
IpStr = Annotated[str, AfterValidator(validate_ip)]
PortInt = Annotated[int, Field(ge=1, le=65535)]
