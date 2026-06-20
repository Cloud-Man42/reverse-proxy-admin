import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

COMBINED_RE = re.compile(
    r'^(\S+) \S+ \S+ \[([^\]]+)\] "([^"]+)" (\d+) (\d+) "([^"]*)" "([^"]*)"'
)
PROXY_DEBUG_RE = re.compile(
    r"^([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|(\d+)\|(\d+)\|([^|]*)\|(.*?)$"
)
NGINX_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"


@dataclass
class ParsedAccessEntry:
    client_ip: str
    timestamp_raw: str
    host: str
    method: str
    path: str
    status: int
    bytes_sent: int
    bytes_in: int = 0
    upstream_bytes_in: int = 0
    upstream_bytes_out: int = 0
    forwarded_for: Optional[str] = None
    user_agent: Optional[str] = None
    request_time: Optional[float] = None
    upstream_response_time: Optional[float] = None

    @property
    def timestamp(self) -> Optional[datetime]:
        try:
            return datetime.strptime(self.timestamp_raw, NGINX_TIME_FORMAT)
        except ValueError:
            return None


def _split_request(request: str) -> tuple[str, str]:
    parts = request.split(" ", 1)
    if len(parts) == 1:
        return parts[0], "/"
    method, remainder = parts
    path = remainder.rsplit(" ", 1)[0] if remainder else "/"
    return method, path or "/"


def _parse_float(value: str) -> Optional[float]:
    if not value or value == "-":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_access_line(line: str) -> Optional[ParsedAccessEntry]:
    line = line.strip()
    if not line:
        return None

    parts = line.split("|")
    if len(parts) >= 11:
        (
            client_ip,
            timestamp_raw,
            host,
            request,
            status,
            bytes_sent,
            bytes_in,
            upstream_bytes_in,
            upstream_bytes_out,
            forwarded_for,
            user_agent,
        ) = parts[:11]
        request_time = None
        upstream_response_time = None
        if len(parts) >= 13:
            request_time = _parse_float(parts[11])
            upstream_response_time = _parse_float(parts[12])
        method, path = _split_request(request)
        return ParsedAccessEntry(
            client_ip=client_ip,
            timestamp_raw=timestamp_raw,
            host=host or "-",
            method=method,
            path=path,
            status=int(status),
            bytes_sent=int(bytes_sent),
            bytes_in=int(bytes_in or 0),
            upstream_bytes_in=int(upstream_bytes_in or 0),
            upstream_bytes_out=int(upstream_bytes_out or 0),
            forwarded_for=forwarded_for or None,
            user_agent=user_agent or None,
            request_time=request_time,
            upstream_response_time=upstream_response_time,
        )

    debug_match = PROXY_DEBUG_RE.match(line)
    if debug_match:
        client_ip, timestamp_raw, host, request, status, bytes_sent, forwarded_for, user_agent = debug_match.groups()
        method, path = _split_request(request)
        return ParsedAccessEntry(
            client_ip=client_ip,
            timestamp_raw=timestamp_raw,
            host=host or "-",
            method=method,
            path=path,
            status=int(status),
            bytes_sent=int(bytes_sent),
            forwarded_for=forwarded_for or None,
            user_agent=user_agent or None,
        )

    combined_match = COMBINED_RE.match(line)
    if combined_match:
        client_ip, timestamp_raw, request, status, bytes_sent, _referer, user_agent = combined_match.groups()
        method, path = _split_request(request)
        return ParsedAccessEntry(
            client_ip=client_ip,
            timestamp_raw=timestamp_raw,
            host="-",
            method=method,
            path=path,
            status=int(status),
            bytes_sent=int(bytes_sent),
            forwarded_for=None,
            user_agent=user_agent or None,
        )
    return None


def entry_matches_domains(entry: ParsedAccessEntry, domains: List[str]) -> bool:
    host = entry.host.lower()
    if host and host != "-":
        return any(host == domain.lower() or host.endswith(f".{domain.lower()}") for domain in domains)

    line_hint = f"{entry.path} {entry.user_agent or ''}".lower()
    return any(domain.lower() in line_hint for domain in domains)
