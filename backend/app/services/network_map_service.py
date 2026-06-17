from datetime import datetime

from app.config import Settings
from app.schemas import NetworkMapEdge, NetworkMapNode, NetworkMapResponse
from app.services.firewall_service import FirewallService
from app.services.nginx_ops import NginxOps
from app.services.proxy_service import ProxyService


class NetworkMapService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.proxy_service = ProxyService(settings)
        self.firewall_service = FirewallService(settings)
        self.nginx_ops = NginxOps(settings)

    def _firewall_subtitle(self) -> str:
        status = self.firewall_service.get_status()
        if not status.rules:
            ports = ", ".join(str(p) for p in self.settings.network_exposed_ports)
            return f"UFW — ports {ports}"
        highlights: list[str] = []
        for rule in status.rules[:4]:
            highlights.append(f"{rule.port}/{rule.protocol} ← {rule.source}")
        suffix = f" (+{len(status.rules) - 4} more)" if len(status.rules) > 4 else ""
        prefix = "UFW active" if status.active else "UFW inactive"
        return f"{prefix}: " + "; ".join(highlights) + suffix

    def build(self) -> NetworkMapResponse:
        proxies = self.proxy_service.list_proxies()
        nginx_active, _ = self.nginx_ops.status()
        firewall = self.firewall_service.get_status()

        nodes: list[NetworkMapNode] = [
            NetworkMapNode(
                id="internet",
                type="internet",
                label="Internet",
                subtitle="Inbound traffic",
                status="active",
                metadata={},
            ),
            NetworkMapNode(
                id="firewall",
                type="firewall",
                label="Firewall (UFW)",
                subtitle=self._firewall_subtitle(),
                status="active" if firewall.active else "inactive",
                metadata={
                    "source": firewall.source,
                    "rules": [
                        {"port": r.port, "protocol": r.protocol, "source": r.source, "action": r.action}
                        for r in firewall.rules
                    ],
                },
            ),
            NetworkMapNode(
                id="nginx",
                type="reverse_proxy",
                label=f"Nginx @ {self.settings.server_public_ip}",
                subtitle=self.settings.server_hostname,
                status="active" if nginx_active else "inactive",
                metadata={
                    "hostname": self.settings.server_hostname,
                    "ip": self.settings.server_public_ip,
                    "ports": self.settings.network_exposed_ports,
                },
            ),
            NetworkMapNode(
                id="admin-ui",
                type="admin_ui",
                label="Admin UI",
                subtitle=f":{self.settings.admin_ui_port} → 127.0.0.1:8080",
                status="active" if nginx_active else "inactive",
                metadata={"port": self.settings.admin_ui_port},
            ),
        ]

        edges: list[NetworkMapEdge] = [
            NetworkMapEdge(id="e-internet-firewall", source="internet", target="firewall", label="ingress"),
            NetworkMapEdge(id="e-firewall-nginx", source="firewall", target="nginx", label="filtered"),
            NetworkMapEdge(
                id="e-nginx-admin",
                source="nginx",
                target="admin-ui",
                label=f":{self.settings.admin_ui_port}",
            ),
        ]

        for index, proxy in enumerate(proxies):
            app_id = f"app-{proxy.id}"
            upstream_id = f"upstream-{proxy.id}"
            domain_label = proxy.domains[0] if proxy.domains else proxy.name
            status = "inactive" if not proxy.enabled else ("active" if nginx_active else "warning")

            nodes.append(
                NetworkMapNode(
                    id=app_id,
                    type="proxy_app",
                    label=domain_label,
                    subtitle=", ".join(proxy.domains) if len(proxy.domains) > 1 else proxy.name,
                    status=status,
                    metadata={
                        "proxy_id": proxy.id,
                        "enabled": proxy.enabled,
                        "https_enabled": proxy.https_enabled,
                        "websocket_enabled": proxy.websocket_enabled,
                        "domains": proxy.domains,
                    },
                )
            )
            nodes.append(
                NetworkMapNode(
                    id=upstream_id,
                    type="upstream",
                    label=proxy.upstream,
                    subtitle=f"{proxy.target_protocol}://{proxy.target_host}:{proxy.target_port}",
                    status=status,
                    metadata={
                        "proxy_id": proxy.id,
                        "target_host": proxy.target_host,
                        "target_port": proxy.target_port,
                    },
                )
            )
            edges.append(
                NetworkMapEdge(
                    id=f"e-nginx-{app_id}",
                    source="nginx",
                    target=app_id,
                    label=domain_label,
                )
            )
            edges.append(
                NetworkMapEdge(
                    id=f"e-{app_id}-{upstream_id}",
                    source=app_id,
                    target=upstream_id,
                    label="proxy_pass",
                )
            )

        return NetworkMapResponse(nodes=nodes, edges=edges, generated_at=datetime.utcnow())
