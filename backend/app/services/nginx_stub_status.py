from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen


STUB_STATUS_RE = re.compile(
    r"Active connections:\s*(?P<active>\d+)\s+"
    r"server accepts handled requests\s+"
    r"(?P<accepts>\d+)\s+(?P<handled>\d+)\s+(?P<requests>\d+)\s+"
    r"Reading:\s*(?P<reading>\d+)\s+Writing:\s*(?P<writing>\d+)\s+Waiting:\s*(?P<waiting>\d+)",
    re.MULTILINE,
)


@dataclass
class StubStatusSnapshot:
    active: int = 0
    reading: int = 0
    writing: int = 0
    waiting: int = 0
    accepts: int = 0
    handled: int = 0
    requests: int = 0


def parse_stub_status(body: str) -> Optional[StubStatusSnapshot]:
    match = STUB_STATUS_RE.search(body)
    if not match:
        return None
    data = match.groupdict()
    return StubStatusSnapshot(
        active=int(data["active"]),
        reading=int(data["reading"]),
        writing=int(data["writing"]),
        waiting=int(data["waiting"]),
        accepts=int(data["accepts"]),
        handled=int(data["handled"]),
        requests=int(data["requests"]),
    )


def fetch_stub_status(url: str, timeout: float = 3.0) -> Optional[StubStatusSnapshot]:
    if not url.startswith("http://127.0.0.1") and not url.startswith("http://localhost"):
        return None
    try:
        request = Request(url, headers={"User-Agent": "reverse-proxy-admin/1.0"})
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except (URLError, OSError, ValueError):
        return None
    return parse_stub_status(body)
