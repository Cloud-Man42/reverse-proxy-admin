import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from app.config import Settings
from app.schemas import ProxyRoute, TargetProtocol


SERVER_BLOCK_RE = re.compile(r"server\s*\{", re.IGNORECASE)
PROXY_PASS_RE = re.compile(r"proxy_pass\s+([^;]+);", re.IGNORECASE)
LOCATION_RE = re.compile(r"location\s+([^{]+)\{", re.IGNORECASE)
LISTEN_RE = re.compile(r"^\s*listen\s+([^;]+);", re.MULTILINE | re.IGNORECASE)
SERVER_NAME_RE = re.compile(r"^\s*server_name\s+([^;]+);", re.MULTILINE | re.IGNORECASE)
SSL_CERT_RE = re.compile(r"^\s*ssl_certificate\s+([^;]+);", re.MULTILINE | re.IGNORECASE)
MAX_BODY_RE = re.compile(r"^\s*client_max_body_size\s+([^;]+);", re.MULTILINE | re.IGNORECASE)
AUTH_BASIC_RE = re.compile(r"^\s*auth_basic\s+([^;]+);", re.MULTILINE | re.IGNORECASE)
RETURN_HTTPS_RE = re.compile(r"^\s*return\s+301\s+https://", re.MULTILINE | re.IGNORECASE)


@dataclass
class ParsedLocation:
    path_prefix: str
    proxy_pass: str
    websocket: bool = False


@dataclass
class ParsedServerBlock:
    server_names: List[str] = field(default_factory=list)
    listens: List[str] = field(default_factory=list)
    locations: List[ParsedLocation] = field(default_factory=list)
    ssl_certificate: Optional[str] = None
    client_max_body_size: Optional[str] = None
    auth_basic: bool = False
    force_https: bool = False


@dataclass
class ParsedProxyConfig:
    config_file: str
    slug: str
    domains: List[str]
    routes: List[ProxyRoute]
    upstream: str
    target_protocol: str
    target_host: str
    target_port: int
    enabled: bool
    https_enabled: bool
    websocket_enabled: bool
    max_body_size: Optional[str]
    basic_auth_enabled: bool
    force_https: bool


def _split_server_blocks(content: str) -> List[str]:
    blocks: List[str] = []
    index = 0
    while index < len(content):
        match = SERVER_BLOCK_RE.search(content, index)
        if not match:
            break
        start = match.start()
        depth = 0
        pos = match.start()
        while pos < len(content):
            char = content[pos]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(content[start : pos + 1])
                    index = pos + 1
                    break
            pos += 1
        else:
            break
    return blocks


def _location_to_prefix(location: str) -> str:
    value = location.strip().strip('"').strip("'")
    if value == "/":
        return "/"
    return value.rstrip("/")


def _parse_block(block: str) -> ParsedServerBlock:
    parsed = ParsedServerBlock()
    server_name_match = SERVER_NAME_RE.search(block)
    if server_name_match:
        parsed.server_names.extend(server_name_match.group(1).split())
    parsed.listens = [match.group(1).strip() for match in LISTEN_RE.finditer(block)]
    ssl_match = SSL_CERT_RE.search(block)
    if ssl_match:
        parsed.ssl_certificate = ssl_match.group(1).split()[0]
    max_body_match = MAX_BODY_RE.search(block)
    if max_body_match:
        parsed.client_max_body_size = max_body_match.group(1).split()[0]
    auth_match = AUTH_BASIC_RE.search(block)
    if auth_match:
        parsed.auth_basic = auth_match.group(1).strip().lower() != "off"
    parsed.force_https = RETURN_HTTPS_RE.search(block) is not None

    for location_match in LOCATION_RE.finditer(block):
        location_value = location_match.group(1)
        start = location_match.end() - 1
        depth = 0
        end = start
        while end < len(block):
            if block[end] == "{":
                depth += 1
            elif block[end] == "}":
                depth -= 1
                if depth == 0:
                    break
            end += 1
        location_block = block[start : end + 1]
        proxy_match = PROXY_PASS_RE.search(location_block)
        if not proxy_match:
            continue
        parsed.locations.append(
            ParsedLocation(
                path_prefix=_location_to_prefix(location_value),
                proxy_pass=proxy_match.group(1).strip().strip('"').strip("'"),
                websocket="Upgrade $http_upgrade" in location_block and 'Connection "upgrade"' in location_block,
            )
        )
    return parsed


def _parse_upstream(proxy_pass: str) -> tuple[str, str, int]:
    url = proxy_pass if "://" in proxy_pass else f"http://{proxy_pass}"
    parsed = urlparse(url)
    protocol = parsed.scheme or "http"
    host = parsed.hostname or ""
    port = parsed.port or (443 if protocol == "https" else 80)
    return protocol, host, port


def _is_enabled(config_name: str, settings: Settings) -> bool:
    enabled_path = settings.nginx_sites_enabled / config_name
    return enabled_path.is_symlink() or enabled_path.exists()


def parse_config_file(path: Path, settings: Settings) -> Optional[ParsedProxyConfig]:
    content = path.read_text(encoding="utf-8")
    blocks = _split_server_blocks(content)
    proxy_block: Optional[ParsedServerBlock] = None
    https_enabled = False
    force_https = False

    for block in blocks:
        parsed = _parse_block(block)
        if parsed.locations:
            proxy_block = parsed
        if parsed.ssl_certificate or any("443" in listen for listen in parsed.listens):
            https_enabled = True
        if parsed.force_https:
            force_https = True

    if not proxy_block or not proxy_block.server_names or not proxy_block.locations:
        return None

    routes: List[ProxyRoute] = []
    for location in sorted(proxy_block.locations, key=lambda item: item.path_prefix):
        protocol, host, port = _parse_upstream(location.proxy_pass)
        routes.append(
            ProxyRoute(
                path_prefix=location.path_prefix,
                target_protocol=TargetProtocol(protocol),
                target_host=host,
                target_port=port,
                websocket_enabled=location.websocket,
            )
        )

    primary = routes[0]
    slug = path.stem
    return ParsedProxyConfig(
        config_file=path.name,
        slug=slug,
        domains=proxy_block.server_names,
        routes=routes,
        upstream=f"{primary.target_protocol.value}://{primary.target_host}:{primary.target_port}",
        target_protocol=primary.target_protocol.value,
        target_host=primary.target_host,
        target_port=primary.target_port,
        enabled=_is_enabled(path.name, settings),
        https_enabled=https_enabled,
        websocket_enabled=primary.websocket_enabled,
        max_body_size=proxy_block.client_max_body_size,
        basic_auth_enabled=proxy_block.auth_basic,
        force_https=force_https,
    )


def list_proxy_configs(settings: Settings) -> List[ParsedProxyConfig]:
    configs: List[ParsedProxyConfig] = []
    if not settings.nginx_sites_available.exists():
        return configs

    for path in sorted(settings.nginx_sites_available.glob("*.conf")):
        if path.stem in settings.excluded_config_files:
            continue
        parsed = parse_config_file(path, settings)
        if parsed:
            configs.append(parsed)
    return configs
