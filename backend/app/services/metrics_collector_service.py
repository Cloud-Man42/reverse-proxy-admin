from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.metrics import BackendMetric, ConnectionMetric, RequestEvent
from app.models.proxy_traffic import ProxyTrafficAggregate
from app.services.backend_pool_service import BackendPoolService
from app.services.health_check_service import HealthCheckService
from app.services.metrics_settings_service import MetricsSettingsService
from app.services.nginx_stub_status import fetch_stub_status


class ConnectionMetricService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db
        self.metrics_settings = MetricsSettingsService(db)

    def collect(self) -> bool:
        config = self.metrics_settings.get_or_create()
        snapshot = fetch_stub_status(config.stub_status_url)
        if not snapshot:
            return False
        self.db.add(
            ConnectionMetric(
                timestamp=datetime.utcnow(),
                active=snapshot.active,
                reading=snapshot.reading,
                writing=snapshot.writing,
                waiting=snapshot.waiting,
                accepts=snapshot.accepts,
                handled=snapshot.handled,
                requests=snapshot.requests,
            )
        )
        self.db.commit()
        return True

    def latest(self) -> ConnectionMetric | None:
        return (
            self.db.query(ConnectionMetric)
            .order_by(ConnectionMetric.timestamp.desc())
            .first()
        )


class BackendMetricCollector:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db
        self.pools = BackendPoolService(settings, db)
        self.health = HealthCheckService(settings, db)

    def collect(self) -> int:
        count = 0
        dashboard = self.health.get_dashboard()
        status_by_id = {item.id: item for item in dashboard.servers}
        servers, _ = self.pools.list_servers(page_size=1000)
        now = datetime.utcnow()
        for server in servers:
            item = status_by_id.get(server.id)
            status = item.health_status.value if item else "unknown"
            self.db.add(
                BackendMetric(
                    backend_server_id=server.id,
                    timestamp=now,
                    status=status,
                    response_time_ms=item.response_ms if item and item.response_ms else 0.0,
                    requests=0,
                    errors=1 if status == "offline" else 0,
                    active_connections=0,
                )
            )
            count += 1
        self.db.commit()
        return count


class MetricsRetentionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = MetricsSettingsService(db)

    def cleanup(self) -> dict[str, int]:
        config = self.settings.get_or_create()
        now = datetime.utcnow()
        deleted = {
            "request_events": self.db.query(RequestEvent)
            .filter(RequestEvent.timestamp < now - timedelta(days=config.raw_retention_days))
            .delete(),
            "minute_metrics": self.db.query(ProxyTrafficAggregate)
            .filter(
                ProxyTrafficAggregate.period_type == "minute",
                ProxyTrafficAggregate.period_start
                < now - timedelta(days=config.minute_retention_days),
            )
            .delete(),
            "hour_metrics": self.db.query(ProxyTrafficAggregate)
            .filter(
                ProxyTrafficAggregate.period_type == "hour",
                ProxyTrafficAggregate.period_start
                < now - timedelta(days=config.hour_retention_days),
            )
            .delete(),
            "connection_metrics": self.db.query(ConnectionMetric)
            .filter(ConnectionMetric.timestamp < now - timedelta(days=config.hour_retention_days))
            .delete(),
            "backend_metrics": self.db.query(BackendMetric)
            .filter(BackendMetric.timestamp < now - timedelta(days=config.hour_retention_days))
            .delete(),
        }
        self.db.commit()
        return deleted
