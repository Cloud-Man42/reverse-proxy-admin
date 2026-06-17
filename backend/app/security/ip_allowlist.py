import ipaddress
from typing import List

from fastapi import HTTPException, Request, status

from app.config import Settings


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


def is_ip_allowed(client_ip: str, allowed: List[str]) -> bool:
    if not allowed:
        return True
    try:
        ip = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for entry in allowed:
        entry = entry.strip()
        if not entry:
            continue
        try:
            if "/" in entry:
                if ip in ipaddress.ip_network(entry, strict=False):
                    return True
            elif ip == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue
    return False


async def ip_allowlist_middleware(request: Request, settings: Settings) -> None:
    if request.url.path.startswith("/api/health"):
        return
    client_ip = _client_ip(request)
    if not is_ip_allowed(client_ip, settings.allowed_ips):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied from IP {client_ip}",
        )
