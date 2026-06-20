import socket
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import Settings
from app.models.backend_server import BackendServer
from app.models.health_check import HealthCheckAggregate, HealthCheckResult
from app.schemas import (
    BackendServerResponse,
    HealthCheckDashboard,
    HealthCheckResultResponse,
    HealthHistoryPoint,
    HealthStatus,
)
from app.services.backend_pool_service import BackendPoolService


class HealthCheckService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db
        self.pool_service = BackendPoolService(settings, db)
        self._previous_status: dict[int, str] = {}

    def run_all(self) -> int:
        servers = (
            self.db.query(BackendServer)
            .filter(BackendServer.enabled.is_(True))
            .all()
        )
        count = 0
        for server in servers:
            self.check_server(server)
            count += 1
        self.db.commit()
        return count

    def check_server(self, server: BackendServer) -> HealthCheckResult:
        status, response_ms, http_status, error = self._perform_check(server)
        previous = server.health_status
        server.health_status = status.value
        result = HealthCheckResult(
            server_id=server.id,
            status=status.value,
            response_ms=response_ms,
            http_status=http_status,
            error=error,
            checked_at=datetime.utcnow(),
        )
        self.db.add(result)
        self._maybe_notify(server, previous, status.value)
        return result

    def run_server(self, server_id: int) -> Optional[HealthCheckResultResponse]:
        server = (
            self.db.query(BackendServer)
            .options(joinedload(BackendServer.pool))
            .filter(BackendServer.id == server_id)
            .first()
        )
        if not server:
            return None
        result = self.check_server(server)
        self.db.commit()
        self.db.refresh(result)
        return HealthCheckResultResponse(
            id=result.id,
            server_id=result.server_id,
            server_name=server.name,
            pool_name=server.pool.name if server.pool else "",
            status=HealthStatus(result.status),
            response_ms=result.response_ms,
            http_status=result.http_status,
            error=result.error,
            checked_at=result.checked_at,
        )

    def _perform_check(
        self, server: BackendServer
    ) -> tuple[HealthStatus, Optional[float], Optional[int], Optional[str]]:
        start = time.perf_counter()
        check_type = server.health_check_type
        try:
            if check_type == "tcp":
                with socket.create_connection((server.host, server.port), timeout=5):
                    elapsed = (time.perf_counter() - start) * 1000
                    status = (
                        HealthStatus.WARNING
                        if elapsed > self.settings.health_warning_ms
                        else HealthStatus.HEALTHY
                    )
                    return status, round(elapsed, 2), None, None
            scheme = "https" if check_type in ("https", "custom") else "http"
            path = server.health_check_path if check_type in ("custom", "http", "https") else "/"
            url = f"{scheme}://{server.host}:{server.port}{path}"
            with httpx.Client(verify=False, timeout=5.0) as client:
                response = client.get(url)
                elapsed = (time.perf_counter() - start) * 1000
                if response.status_code >= 500:
                    return HealthStatus.OFFLINE, round(elapsed, 2), response.status_code, f"HTTP {response.status_code}"
                status = (
                    HealthStatus.WARNING
                    if elapsed > self.settings.health_warning_ms
                    else HealthStatus.HEALTHY
                )
                return status, round(elapsed, 2), response.status_code, None
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return HealthStatus.OFFLINE, round(elapsed, 2), None, str(exc)

    def _maybe_notify(self, server: BackendServer, previous: str, current: str) -> None:
        if previous == current:
            return
        offline_transition = (
            current == HealthStatus.OFFLINE.value and previous != HealthStatus.OFFLINE.value
        ) or (
            previous == HealthStatus.OFFLINE.value and current != HealthStatus.OFFLINE.value
        )
        if offline_transition:
            from app.services.nginx_regen_service import NginxRegenService

            NginxRegenService.queue_for_server(server)
        if current == HealthStatus.OFFLINE.value and previous != HealthStatus.OFFLINE.value:
            from app.services.notification_service import NotificationService

            NotificationService(self.settings, self.db).dispatch_backend_offline(server)
        elif previous == HealthStatus.OFFLINE.value and current == HealthStatus.HEALTHY.value:
            from app.services.notification_service import NotificationService

            NotificationService(self.settings, self.db).dispatch_backend_restored(server)

    def get_dashboard(self) -> HealthCheckDashboard:
        servers, _ = self.pool_service.list_servers(page_size=1000)
        healthy = sum(1 for s in servers if s.health_status == HealthStatus.HEALTHY)
        warning = sum(1 for s in servers if s.health_status == HealthStatus.WARNING)
        offline = sum(1 for s in servers if s.health_status == HealthStatus.OFFLINE)
        unknown = sum(1 for s in servers if s.health_status == HealthStatus.UNKNOWN)
        return HealthCheckDashboard(
            healthy=healthy,
            warning=warning,
            offline=offline,
            unknown=unknown,
            servers=servers,
        )

    def list_results(
        self,
        *,
        server_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[HealthCheckResultResponse], int]:
        query = self.db.query(HealthCheckResult)
        if server_id:
            query = query.filter(HealthCheckResult.server_id == server_id)
        if status:
            query = query.filter(HealthCheckResult.status == status)
        total = query.count()
        results = (
            query.order_by(HealthCheckResult.checked_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        server_map = {
            s.id: s
            for s in self.db.query(BackendServer).options(joinedload(BackendServer.pool)).all()
        }
        items: list[HealthCheckResultResponse] = []
        for result in results:
            server = server_map.get(result.server_id)
            items.append(
                HealthCheckResultResponse(
                    id=result.id,
                    server_id=result.server_id,
                    server_name=server.name if server else "",
                    pool_name=server.pool.name if server and server.pool else "",
                    status=HealthStatus(result.status),
                    response_ms=result.response_ms,
                    http_status=result.http_status,
                    error=result.error,
                    checked_at=result.checked_at,
                )
            )
        return items, total

    def get_history(self, server_id: int, range_key: str = "24h") -> list[HealthHistoryPoint]:
        now = datetime.utcnow()
        if range_key == "7d":
            start = now - timedelta(days=7)
            period_type = "hour"
        elif range_key == "30d":
            start = now - timedelta(days=30)
            period_type = "day"
        else:
            start = now - timedelta(hours=24)
            period_type = "hour"
        aggregates = (
            self.db.query(HealthCheckAggregate)
            .filter(
                HealthCheckAggregate.server_id == server_id,
                HealthCheckAggregate.period_type == period_type,
                HealthCheckAggregate.period_start >= start,
            )
            .order_by(HealthCheckAggregate.period_start.asc())
            .all()
        )
        if aggregates:
            return [
                HealthHistoryPoint(
                    timestamp=agg.period_start,
                    uptime_percent=agg.uptime_percent,
                    avg_response_ms=None,
                )
                for agg in aggregates
            ]
        results = (
            self.db.query(HealthCheckResult)
            .filter(HealthCheckResult.server_id == server_id, HealthCheckResult.checked_at >= start)
            .order_by(HealthCheckResult.checked_at.asc())
            .all()
        )
        if not results:
            return []
        bucket: dict[str, list[HealthCheckResult]] = {}
        for result in results:
            key = result.checked_at.strftime("%Y-%m-%d %H:00")
            bucket.setdefault(key, []).append(result)
        points: list[HealthHistoryPoint] = []
        for key in sorted(bucket.keys()):
            items = bucket[key]
            healthy = sum(1 for item in items if item.status == HealthStatus.HEALTHY.value)
            uptime = (healthy / len(items)) * 100 if items else 0
            avg_ms = sum(item.response_ms or 0 for item in items) / len(items)
            points.append(
                HealthHistoryPoint(
                    timestamp=items[0].checked_at,
                    uptime_percent=round(uptime, 2),
                    avg_response_ms=round(avg_ms, 2),
                )
            )
        return points

    def rollup_aggregates(self) -> None:
        now = datetime.utcnow()
        hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        hour_end = hour_start + timedelta(hours=1)
        servers = self.db.query(BackendServer.id).all()
        for (server_id,) in servers:
            results = (
                self.db.query(HealthCheckResult)
                .filter(
                    HealthCheckResult.server_id == server_id,
                    HealthCheckResult.checked_at >= hour_start,
                    HealthCheckResult.checked_at < hour_end,
                )
                .all()
            )
            if not results:
                continue
            healthy = sum(1 for r in results if r.status == HealthStatus.HEALTHY.value)
            agg = HealthCheckAggregate(
                server_id=server_id,
                period_start=hour_start,
                period_end=hour_end,
                period_type="hour",
                total_checks=len(results),
                healthy_checks=healthy,
                uptime_percent=round((healthy / len(results)) * 100, 2),
            )
            self.db.add(agg)
        self.db.commit()
