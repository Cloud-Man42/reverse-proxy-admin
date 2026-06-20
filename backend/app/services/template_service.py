import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.proxy_template import ProxyTemplate
from app.schemas import ProxyTemplateResponse


def _route(
    *,
    path_prefix: str = "/",
    target_protocol: str = "http",
    target_host: str = "127.0.0.1",
    target_port: int = 8080,
    websocket_enabled: bool = False,
) -> dict[str, Any]:
    return {
        "path_prefix": path_prefix,
        "target_protocol": target_protocol,
        "target_host": target_host,
        "target_port": target_port,
        "websocket_enabled": websocket_enabled,
    }


BUILTIN_PRESETS: list[dict[str, Any]] = [
    {
        "slug": "wordpress",
        "name": "WordPress",
        "description": "Typical WordPress site with HTTPS redirect and large upload support.",
        "defaults": {
            "routes": [_route(target_port=8080)],
            "force_https": True,
            "max_body_size": "64m",
            "notes": "WordPress application proxy",
        },
    },
    {
        "slug": "nextcloud",
        "name": "Nextcloud",
        "description": "Nextcloud with WebSocket support and large file uploads.",
        "defaults": {
            "routes": [_route(target_port=8080, websocket_enabled=True)],
            "force_https": True,
            "max_body_size": "10G",
            "notes": "Nextcloud sync and share",
        },
    },
    {
        "slug": "grafana",
        "name": "Grafana",
        "description": "Grafana dashboards with live WebSocket updates.",
        "defaults": {
            "routes": [_route(target_port=3000, websocket_enabled=True)],
            "force_https": True,
            "notes": "Grafana monitoring UI",
        },
    },
    {
        "slug": "jellyfin",
        "name": "Jellyfin",
        "description": "Jellyfin media server with streaming-friendly settings.",
        "defaults": {
            "routes": [_route(target_port=8096, websocket_enabled=True)],
            "force_https": True,
            "max_body_size": "0",
            "notes": "Jellyfin media server",
        },
    },
    {
        "slug": "hestiacp",
        "name": "HestiaCP",
        "description": "Hestia Control Panel on the default port 8083.",
        "defaults": {
            "routes": [_route(target_port=8083)],
            "force_https": True,
            "notes": "HestiaCP admin panel",
        },
    },
    {
        "slug": "mailcow",
        "name": "Mailcow",
        "description": "Mailcow mail suite with HTTPS and WebSocket support.",
        "defaults": {
            "routes": [_route(target_port=8080, websocket_enabled=True)],
            "force_https": True,
            "max_body_size": "50m",
            "notes": "Mailcow mail stack",
        },
    },
    {
        "slug": "portainer",
        "name": "Portainer",
        "description": "Portainer container UI with WebSocket terminal access.",
        "defaults": {
            "routes": [_route(target_port=9000, websocket_enabled=True)],
            "force_https": True,
            "notes": "Portainer Docker UI",
        },
    },
    {
        "slug": "proxmox",
        "name": "Proxmox VE",
        "description": "Proxmox web UI on port 8006 with HTTPS upstream.",
        "defaults": {
            "routes": [_route(target_protocol="https", target_port=8006, websocket_enabled=True)],
            "force_https": True,
            "notes": "Proxmox virtualization console",
        },
    },
    {
        "slug": "custom",
        "name": "Custom",
        "description": "Blank starting point with a single HTTP route.",
        "defaults": {
            "routes": [_route()],
            "force_https": False,
            "notes": "",
        },
    },
]


class TemplateService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_builtins(self) -> None:
        existing = {row.slug for row in self.db.query(ProxyTemplate.slug).filter(ProxyTemplate.builtin.is_(True)).all()}
        added = False
        for preset in BUILTIN_PRESETS:
            if preset["slug"] in existing:
                continue
            self.db.add(
                ProxyTemplate(
                    slug=preset["slug"],
                    name=preset["name"],
                    description=preset.get("description"),
                    defaults_json=json.dumps(preset["defaults"]),
                    builtin=True,
                )
            )
            added = True
        if added:
            self.db.commit()

    @staticmethod
    def _to_response(row: ProxyTemplate) -> ProxyTemplateResponse:
        return ProxyTemplateResponse(
            id=row.id,
            slug=row.slug,
            name=row.name,
            description=row.description,
            defaults=json.loads(row.defaults_json or "{}"),
            builtin=row.builtin,
        )

    def list_templates(self) -> list[ProxyTemplateResponse]:
        self.ensure_builtins()
        rows = self.db.query(ProxyTemplate).order_by(ProxyTemplate.name).all()
        return [self._to_response(row) for row in rows]

    def get_by_slug(self, slug: str) -> Optional[ProxyTemplateResponse]:
        self.ensure_builtins()
        row = self.db.query(ProxyTemplate).filter(ProxyTemplate.slug == slug).first()
        return self._to_response(row) if row else None
