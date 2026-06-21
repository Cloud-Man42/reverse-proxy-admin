import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from app.services.error_log_parser import parse_proxy_json_line

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
    upstream_addr: Optional[str] = None

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


def _parse_int(value: str, default: int = 0) -> int:
    if not value or value == "-":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def parse_access_line(line: str) -> Optional[ParsedAccessEntry]:
    line = line.strip()
    if not line:
        return None

    if line.startswith("{"):
        payload = parse_proxy_json_line(line)
        if payload:
            method, path = _split_request(str(payload.get("request_method", "GET")) + " " + str(payload.get("request_uri", "/")))
            request_time = _parse_float(str(payload.get("request_time", "")))
            upstream_response_time = _parse_float(str(payload.get("upstream_response_time", "")))
            return ParsedAccessEntry(
                client_ip=str(payload.get("remote_addr", "")),
                timestamp_raw=str(payload.get("time", "")),
                host=str(payload.get("host", "-")),
                method=method,
                path=path,
                status=int(payload.get("status", 0) or 0),
                bytes_sent=int(payload.get("body_bytes_sent", 0) or 0),
                request_time=request_time,
                upstream_response_time=upstream_response_time,
                upstream_addr=str(payload.get("upstream_addr", "") or "") or None,
                user_agent=str(payload.get("http_user_agent", "") or "") or None,
            )

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
                status=_parse_int(status),
                bytes_sent=_parse_int(bytes_sent),
                bytes_in=_parse_int(bytes_in),
                upstream_bytes_in=_parse_int(upstream_bytes_in),
                upstream_bytes_out=_parse_int(upstream_bytes_out),
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
