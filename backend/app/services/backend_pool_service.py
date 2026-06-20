from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.config import Settings
from app.models.backend_pool import BackendPool
from app.models.backend_server import BackendServer
from app.models.health_check import HealthCheckAggregate, HealthCheckResult
from app.models.user import User
from app.schemas import (
    BackendPoolCreate,
    BackendPoolResponse,
    BackendPoolUpdate,
    BackendRole,
    BackendServerCreate,
    BackendServerResponse,
    BackendServerUpdate,
    HealthCheckType,
    HealthStatus,
    LoadBalancerSummary,
    LoadBalancingMethod,
    TargetProtocol,
)
from app.security.tenant_context import filter_query_by_org, get_current_org
from app.services.load_balancer_service import LoadBalancerService


class BackendPoolService:
    def __init__(self, settings: Settings, db: Session, user: Optional[User] = None) -> None:
        self.settings = settings
        self.db = db
        self.user = user
        self.lb = LoadBalancerService(settings)

    def _pool_query(self):
        query = self.db.query(BackendPool).options(joinedload(BackendPool.servers))
        if self.user:
            query = filter_query_by_org(query, BackendPool, self.user)
        return query

    def _default_org_id(self) -> Optional[int]:
        if self.user:
            return get_current_org(self.user) or self.user.organization_id
        return None
    def list_pools(
        self,
        *,
        proxy_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[BackendPoolResponse], int]:
        query = self._pool_query()
        if proxy_id:
            query = query.filter(BackendPool.proxy_id == proxy_id)
        total = query.count()
        pools = query.order_by(BackendPool.name).offset((page - 1) * page_size).limit(page_size).all()
        return [self._to_response(pool) for pool in pools], total

    def get_pool(self, pool_id: int) -> Optional[BackendPoolResponse]:
        pool = self._pool_query().filter(BackendPool.id == pool_id).first()
        return self._to_response(pool) if pool else None

    def get_pool_by_name(self, name: str) -> Optional[BackendPool]:
        return self._pool_query().filter(BackendPool.name == name).first()

    def create_pool(self, payload: BackendPoolCreate) -> BackendPoolResponse:
        name_query = self.db.query(BackendPool).filter(BackendPool.name == payload.name)
        if self.user:
            name_query = filter_query_by_org(name_query, BackendPool, self.user)
        if name_query.first():
            raise ValueError(f"Pool name '{payload.name}' already exists")
        pool = BackendPool(
            name=payload.name,
            proxy_id=payload.proxy_id,
            route_path=payload.route_path,
            load_balancing_method=payload.load_balancing_method.value,
            enabled=payload.enabled,
            notes=payload.notes,
            organization_id=self._default_org_id(),
        )
        self.db.add(pool)
        self.db.flush()
        for server_data in payload.servers:
            self._validate_server_protocols(payload.servers, server_data.protocol.value)
            server = BackendServer(
                pool_id=pool.id,
                name=server_data.name,
                host=server_data.host,
                port=server_data.port,
                protocol=server_data.protocol.value,
                weight=server_data.weight,
                role=server_data.role.value,
                enabled=server_data.enabled,
                health_check_type=server_data.health_check_type.value,
                health_check_path=server_data.health_check_path,
                notes=server_data.notes,
            )
            self.db.add(server)
        self.db.commit()
        self.db.refresh(pool)
        return self._to_response(self._pool_query().filter(BackendPool.id == pool.id).first())

    def update_pool(self, pool_id: int, payload: BackendPoolUpdate) -> Optional[BackendPoolResponse]:
        pool = self._pool_query().filter(BackendPool.id == pool_id).first()
        if not pool:
            return None
        data = payload.model_dump(exclude_unset=True)
        if "load_balancing_method" in data and data["load_balancing_method"]:
            data["load_balancing_method"] = data["load_balancing_method"].value
        for key, value in data.items():
            setattr(pool, key, value)
        self.db.commit()
        return self.get_pool(pool_id)

    def delete_pool(self, pool_id: int) -> bool:
        pool = self._pool_query().filter(BackendPool.id == pool_id).first()
        if not pool:
            return False
        self.db.delete(pool)
        self.db.commit()
        return True

    def create_server(self, payload: BackendServerCreate) -> BackendServerResponse:
        pool = self._pool_query().filter(BackendPool.id == payload.pool_id).first()
        if not pool:
            raise ValueError("Pool not found")
        protocols = {s.protocol for s in pool.servers if s.enabled}
        protocols.add(payload.protocol.value)
        if len(protocols) > 1:
            raise ValueError("All servers in a pool must use the same protocol")
        server = BackendServer(
            pool_id=payload.pool_id,
            name=payload.name,
            host=payload.host,
            port=payload.port,
            protocol=payload.protocol.value,
            weight=payload.weight,
            role=payload.role.value,
            enabled=payload.enabled,
            health_check_type=payload.health_check_type.value,
            health_check_path=payload.health_check_path,
            notes=payload.notes,
        )
        self.db.add(server)
        self.db.commit()
        self.db.refresh(server)
        return self._server_response(server, pool.name)

    def update_server(self, server_id: int, payload: BackendServerUpdate) -> Optional[BackendServerResponse]:
        server_query = self.db.query(BackendServer).filter(BackendServer.id == server_id)
        if self.user and not self.user.is_super_admin():
            org_id = get_current_org(self.user) or self.user.organization_id
            if org_id is not None:
                server_query = server_query.join(BackendPool).filter(BackendPool.organization_id == org_id)
        server = server_query.first()
        if not server:
            return None
        data = payload.model_dump(exclude_unset=True)
        for enum_key in ("protocol", "role", "health_check_type"):
            if enum_key in data and data[enum_key] is not None:
                data[enum_key] = data[enum_key].value
        for key, value in data.items():
            setattr(server, key, value)
        self.db.commit()
        pool = self.db.query(BackendPool).filter(BackendPool.id == server.pool_id).first()
        return self._server_response(server, pool.name if pool else "")

    def delete_server(self, server_id: int) -> bool:
        server_query = self.db.query(BackendServer).filter(BackendServer.id == server_id)
        if self.user and not self.user.is_super_admin():
            org_id = get_current_org(self.user) or self.user.organization_id
            if org_id is not None:
                server_query = server_query.join(BackendPool).filter(BackendPool.organization_id == org_id)
        server = server_query.first()
        if not server:
            return False
        self.db.delete(server)
        self.db.commit()
        return True

    def list_servers(
        self,
        *,
        pool_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[BackendServerResponse], int]:
        query = self.db.query(BackendServer)
        if self.user and not self.user.is_super_admin():
            org_id = get_current_org(self.user) or self.user.organization_id
            if org_id is not None:
                query = query.join(BackendPool).filter(BackendPool.organization_id == org_id)
        if pool_id:
            query = query.filter(BackendServer.pool_id == pool_id)
        total = query.count()
        servers = query.order_by(BackendServer.name).offset((page - 1) * page_size).limit(page_size).all()
        pool_names = {p.id: p.name for p in self._pool_query().all()}
        return [self._server_response(s, pool_names.get(s.pool_id, "")) for s in servers], total

    def list_load_balancers(self) -> list[LoadBalancerSummary]:
        pools = self._pool_query().all()
        summaries: list[LoadBalancerSummary] = []
        for pool in pools:
            enabled_servers = [s for s in pool.servers if s.enabled]
            summaries.append(
                LoadBalancerSummary(
                    pool_id=pool.id,
                    pool_name=pool.name,
                    proxy_id=pool.proxy_id,
                    load_balancing_method=LoadBalancingMethod(pool.load_balancing_method),
                    server_count=len(enabled_servers),
                    primary_count=sum(1 for s in enabled_servers if s.role == BackendRole.PRIMARY.value),
                    backup_count=sum(1 for s in enabled_servers if s.role == BackendRole.BACKUP.value),
                    healthy_count=sum(1 for s in enabled_servers if s.health_status == HealthStatus.HEALTHY.value),
                    offline_count=sum(1 for s in enabled_servers if s.health_status == HealthStatus.OFFLINE.value),
                )
            )
        return summaries

    def get_pools_for_proxy(self, proxy_id: str) -> list[BackendPool]:
        return self._pool_query().filter(BackendPool.proxy_id == proxy_id).all()

    def get_pool_for_route(self, proxy_id: str, route_path: str, pool_id: Optional[int]) -> Optional[BackendPool]:
        if pool_id:
            return self._pool_query().filter(BackendPool.id == pool_id).first()
        return (
            self._pool_query()
            .filter(BackendPool.proxy_id == proxy_id, BackendPool.route_path == route_path)
            .first()
        )

    @staticmethod
    def _validate_server_protocols(servers, protocol: str) -> None:
        protocols = {s.protocol.value for s in servers if s.enabled}
        protocols.add(protocol)
        if len(protocols) > 1:
            raise ValueError("All servers in a pool must use the same protocol")

    def _server_response(self, server: BackendServer, pool_name: str) -> BackendServerResponse:
        last = (
            self.db.query(HealthCheckResult)
            .filter(HealthCheckResult.server_id == server.id)
            .order_by(HealthCheckResult.checked_at.desc())
            .first()
        )
        agg = (
            self.db.query(HealthCheckAggregate)
            .filter(HealthCheckAggregate.server_id == server.id, HealthCheckAggregate.period_type == "hour")
            .order_by(HealthCheckAggregate.period_start.desc())
            .first()
        )
        return BackendServerResponse(
            id=server.id,
            pool_id=server.pool_id,
            name=server.name,
            host=server.host,
            port=server.port,
            protocol=TargetProtocol(server.protocol),
            weight=server.weight,
            role=BackendRole(server.role),
            enabled=server.enabled,
            health_check_type=HealthCheckType(server.health_check_type),
            health_check_path=server.health_check_path,
            notes=server.notes,
            health_status=HealthStatus(server.health_status),
            last_check_at=last.checked_at if last else None,
            response_ms=last.response_ms if last else None,
            uptime_percent_24h=agg.uptime_percent if agg else None,
        )

    def _to_response(self, pool: BackendPool) -> BackendPoolResponse:
        enabled = [s for s in pool.servers if s.enabled]
        primaries = [s for s in enabled if s.role == BackendRole.PRIMARY.value]
        backups = [s for s in enabled if s.role == BackendRole.BACKUP.value]
        primary_healthy = any(s.health_status == HealthStatus.HEALTHY.value for s in primaries)
        failover_active = not primary_healthy and any(
            s.health_status == HealthStatus.HEALTHY.value for s in backups
        )
        return BackendPoolResponse(
            id=pool.id,
            name=pool.name,
            proxy_id=pool.proxy_id,
            route_path=pool.route_path,
            load_balancing_method=LoadBalancingMethod(pool.load_balancing_method),
            enabled=pool.enabled,
            notes=pool.notes,
            servers=[self._server_response(s, pool.name) for s in pool.servers],
            primary_count=len(primaries),
            backup_count=len(backups),
            failover_active=failover_active,
        )
