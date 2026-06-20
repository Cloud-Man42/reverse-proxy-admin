from typing import Optional

from app.config import Settings
from app.models.backend_pool import BackendPool
from app.models.backend_server import BackendServer
from app.schemas import LoadBalancingMethod


class LoadBalancerService:
    LB_DIRECTIVES = {
        LoadBalancingMethod.LEAST_CONN: "least_conn",
        LoadBalancingMethod.IP_HASH: "ip_hash",
        LoadBalancingMethod.RANDOM: "random",
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def upstream_name(proxy_slug: str, route_index: int) -> str:
        return f"{proxy_slug}_{route_index}_backend"

    def render_upstream_block(self, pool: BackendPool, upstream_name: str) -> str:
        lines = [f"upstream {upstream_name} {{"]
        method = LoadBalancingMethod(pool.load_balancing_method)
        directive = self.LB_DIRECTIVES.get(method)
        if directive:
            lines.append(f"    {directive};")
        enabled_servers = [s for s in pool.servers if s.enabled]
        if not enabled_servers:
            lines.append("    # no enabled servers")
        for server in enabled_servers:
            parts = [f"server {server.host}:{server.port}"]
            if method == LoadBalancingMethod.WEIGHTED or server.weight != 1:
                parts.append(f"weight={server.weight}")
            if server.role == "backup":
                parts.append("backup")
            lines.append("    " + " ".join(parts) + ";")
        lines.append("}")
        return "\n".join(lines)

    def render_upstream_blocks_for_proxy(
        self,
        proxy_slug: str,
        route_pool_map: list[tuple[int, Optional[BackendPool]]],
    ) -> str:
        blocks: list[str] = []
        for route_index, pool in route_pool_map:
            if pool and pool.enabled:
                name = self.upstream_name(proxy_slug, route_index)
                blocks.append(self.render_upstream_block(pool, name))
        return "\n\n".join(blocks)

    @staticmethod
    def pool_protocol(pool: BackendPool) -> str:
        enabled = [s for s in pool.servers if s.enabled]
        if not enabled:
            return "http"
        return enabled[0].protocol

    def validate_pool(self, pool: BackendPool) -> None:
        enabled = [s for s in pool.servers if s.enabled]
        if not enabled:
            raise ValueError(f"Pool '{pool.name}' has no enabled servers")
        protocols = {s.protocol for s in enabled}
        if len(protocols) > 1:
            raise ValueError(f"Pool '{pool.name}' servers must share the same protocol")
