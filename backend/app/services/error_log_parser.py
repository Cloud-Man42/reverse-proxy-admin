from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional


ERROR_HINTS = {
    502: "Check if the backend is reachable from the reverse proxy.",
    503: "Check if the backend pool has healthy members.",
    504: "Check upstream timeout and backend response time.",
    500: "Inspect backend application logs for internal errors.",
    429: "Review rate limiting configuration and client traffic patterns.",
}


UPSTREAM_ERROR_RE = re.compile(
    r"upstream timed out|upstream prematurely closed|connect\(\) failed|no live upstreams",
    re.IGNORECASE,
)
SSL_ERROR_RE = re.compile(r"SSL_do_handshake|ssl handshake|certificate", re.IGNORECASE)


@dataclass
class ParsedErrorEntry:
    timestamp_raw: str
    level: str
    message: str
    client_ip: str = ""
    upstream: str = ""
    host: str = ""


def status_code_hint(status: int) -> str:
    return ERROR_HINTS.get(status, "Review access and error logs for this request.")


def classify_failed_request(status: int, message: str = "") -> tuple[bool, str]:
    if status in {500, 502, 503, 504, 429}:
        return True, status_code_hint(status)
    lowered = message.lower()
    if SSL_ERROR_RE.search(lowered):
        return True, "Check certificate, SNI, and upstream protocol."
    if "connection refused" in lowered:
        return True, "Check if the backend service is running and reachable."
    if "connection timed out" in lowered or "upstream timed out" in lowered:
        return True, status_code_hint(504)
    return False, ""


def parse_error_line(line: str) -> Optional[ParsedErrorEntry]:
    line = line.strip()
    if not line:
        return None
    match = re.match(r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (.+)$", line)
    if not match:
        return ParsedErrorEntry(timestamp_raw="", level="error", message=line)
    timestamp_raw, level, message = match.groups()
    client_ip = ""
    upstream = ""
    host = ""
    client_match = re.search(r"client: ([0-9a-fA-F:\.]+)", message)
    if client_match:
        client_ip = client_match.group(1)
    upstream_match = re.search(r"upstream: \"?([^\",]+)", message)
    if upstream_match:
        upstream = upstream_match.group(1)
    host_match = re.search(r"host: \"?([^\",]+)", message)
    if host_match:
        host = host_match.group(1)
    return ParsedErrorEntry(
        timestamp_raw=timestamp_raw,
        level=level,
        message=message,
        client_ip=client_ip,
        upstream=upstream,
        host=host,
    )


def parse_proxy_json_line(line: str) -> Optional[dict]:
    line = line.strip()
    if not line or not line.startswith("{"):
        return None
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload
