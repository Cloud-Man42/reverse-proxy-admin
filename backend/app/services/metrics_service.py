from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.metrics import BackendMetric, ConnectionMetric, RequestEvent
from app.models.proxy_traffic import ProxyTrafficAggregate
from app.services.alert_rule_service import AlertRuleService
from app.services.backend_pool_service import BackendPoolService
from app.services.certificate_service import CertificateService
from app.services.health_check_service import HealthCheckService
from app.services.metrics.base import resolve_range
from app.services.metrics_collector_service import ConnectionMetricService
from app.services.metrics_settings_service import MetricsSettingsService
from app.services.nginx_ops import NginxOps
from app.services.notification_service import NotificationService
from app.services.proxy_service import ProxyService
from app.services.proxy_traffic_service import ProxyTrafficService
from app.services.security_event_service import SecurityEventService
from app.services.smtp_service import SmtpService


STATUS_HINTS = {
    "502": "Many 502 errors usually indicate backend connectivity problems.",
    "504": "Many 504 errors usually indicate timeout or slow backend.",
    "404": "Many 404 errors may indicate incorrect routing or missing resources.",
    "429": "Many 429 errors indicate rate limiting.",
}


class MetricsService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db
        self.proxies = ProxyService(settings, db)
        self.traffic = ProxyTrafficService(settings, db)
        self.health = HealthCheckService(settings, db)
        self.pools = BackendPoolService(settings, db)
        self.certs = CertificateService(settings, db)
        self.alerts = AlertRuleService(settings, db)

    def _aggregate_query(self, range_key: str, proxy_id: str | None = None):
        time_range = resolve_range(range_key)
        query = self.db.query(ProxyTrafficAggregate).filter(
            ProxyTrafficAggregate.period_start >= time_range.start
        )
        if proxy_id:
            query = query.filter(ProxyTrafficAggregate.proxy_id == proxy_id)
        return query

    def _sum_traffic(self, range_key: str, proxy_id: str | None = None) -> dict:
        query = self._aggregate_query(range_key, proxy_id)
        row = query.with_entities(
            func.coalesce(func.sum(ProxyTrafficAggregate.requests), 0),
            func.coalesce(func.sum(ProxyTrafficAggregate.bytes_in), 0),
            func.coalesce(func.sum(ProxyTrafficAggregate.bytes_out), 0),
            func.coalesce(func.sum(ProxyTrafficAggregate.status_2xx), 0),
            func.coalesce(func.sum(ProxyTrafficAggregate.status_3xx), 0),
            func.coalesce(func.sum(ProxyTrafficAggregate.status_4xx), 0),
            func.coalesce(func.sum(ProxyTrafficAggregate.status_5xx), 0),
            func.coalesce(func.max(ProxyTrafficAggregate.max_response_time_ms), 0.0),
            func.coalesce(
                func.sum(ProxyTrafficAggregate.latency_avg_ms * ProxyTrafficAggregate.requests),
                0.0,
            ),
        ).one()
        requests = int(row[0])
        errors = int(row[5]) + int(row[6])
        return {
            "requests": requests,
            "bytes_in": int(row[1]),
            "bytes_out": int(row[2]),
            "status_2xx": int(row[3]),
            "status_3xx": int(row[4]),
            "status_4xx": int(row[5]),
            "status_5xx": int(row[6]),
            "max_response_time_ms": float(row[7]),
            "avg_response_time_ms": float(row[8]) / requests if requests else 0.0,
            "error_rate": errors / requests if requests else 0.0,
            "rps": requests / resolve_range(range_key).seconds if requests else 0.0,
        }

    def _merge_status_codes(self, range_key: str, proxy_id: str | None = None) -> dict[str, int]:
        merged: dict[str, int] = {}
        for (raw,) in self._aggregate_query(range_key, proxy_id).with_entities(
            ProxyTrafficAggregate.status_codes_json
        ):
            try:
                data = json.loads(raw or "{}")
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            for key, value in data.items():
                merged[str(key)] = merged.get(str(key), 0) + int(value)
        return merged

    def dashboard(self) -> dict:
        time_range = resolve_range("24h")
        totals = self._sum_traffic("24h")
        proxy_list = self.proxies.list_proxies()
        health = self.health.get_dashboard()
        nginx_active, _ = NginxOps(self.settings).status()
        smtp_status = SmtpService(self.settings, self.db).status_label()
        try:
            cert_list = self.certs.list_certificates()
            total_certs = len(cert_list)
            expiring = sum(1 for cert in cert_list if cert.status == "expiring")
            expired = sum(1 for cert in cert_list if cert.status == "expired")
            valid = total_certs - expiring - expired
        except Exception:
            total_certs = expiring = expired = valid = 0
        latest_conn = ConnectionMetricService(self.settings, self.db).latest()
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage(str(self.settings.data_dir)).percent
        except Exception:
            cpu = ram = disk = None
        alerts = self.alerts.merge_dashboard_alerts([])
        recent_notifications, _ = NotificationService(self.settings, self.db).list_logs(page=1, page_size=5)
        for entry in recent_notifications:
            alerts.append(
                {
                    "source": "notification",
                    "title": entry.event_type.replace("_", " ").title(),
                    "message": entry.subject,
                    "status": entry.status,
                    "severity": "critical" if entry.status != "sent" else "info",
                    "created_at": entry.created_at.isoformat(),
                }
            )
        return {
            "system_health": {
                "nginx_status": "running" if nginx_active else "stopped",
                "health_check_service": "running",
                "smtp_status": smtp_status,
                "ssl_certbot_status": "ok",
                "background_worker_status": "running" if self.settings.scheduler_enabled else "disabled",
                "cpu_percent": cpu,
                "ram_percent": ram,
                "disk_percent": disk,
            },
            "proxy_overview": {
                "total": len(proxy_list),
                "active": sum(1 for item in proxy_list if item.enabled),
                "disabled": sum(1 for item in proxy_list if not item.enabled),
                "total_backends": health.healthy + health.warning + health.offline + getattr(health, "unknown", 0),
                "healthy_backends": health.healthy,
                "warning_backends": health.warning,
                "offline_backends": health.offline,
            },
            "live_traffic": {
                "requests_per_second": totals["rps"],
                "active_connections": latest_conn.active if latest_conn else 0,
                "bandwidth_in": totals["bytes_in"],
                "bandwidth_out": totals["bytes_out"],
                "avg_response_time_ms": totals["avg_response_time_ms"],
                "error_rate_percent": round(totals["error_rate"] * 100, 2),
            },
            "ssl_overview": {
                "total": total_certs,
                "valid": valid,
                "expiring": expiring,
                "expired": expired,
                "renewal_errors": 0,
            },
            "alerts": alerts[:20],
            "traffic_history": [
                {
                    "timestamp": point.timestamp.isoformat(),
                    "requests": point.connections,
                    "bytes_in": point.bytes_in,
                    "bytes_out": point.bytes_out,
                }
                for point in self.traffic.aggregate_history("24h")
            ],
            "range": time_range.key,
        }

    def traffic(self, range_key: str = "24h") -> dict:
        totals = self._sum_traffic(range_key)
        history = self.traffic.aggregate_history(range_key)
        peak_rps = max((point.connections for point in history), default=0)
        return {
            "range": range_key,
            "totals": totals,
            "peak_rps": peak_rps / 3600 if range_key.endswith("h") else peak_rps,
            "series": {
                "requests": [{"timestamp": p.timestamp.isoformat(), "value": p.connections} for p in history],
                "bandwidth_in": [{"timestamp": p.timestamp.isoformat(), "value": p.bytes_in} for p in history],
                "bandwidth_out": [{"timestamp": p.timestamp.isoformat(), "value": p.bytes_out} for p in history],
                "response_time_ms": [
                    {"timestamp": p.timestamp.isoformat(), "value": totals["avg_response_time_ms"]}
                    for p in history
                ],
                "error_rate": [
                    {"timestamp": p.timestamp.isoformat(), "value": totals["error_rate"]} for p in history
                ],
            },
        }

    def status_codes(self, range_key: str = "24h", proxy_id: str | None = None) -> dict:
        totals = self._sum_traffic(range_key, proxy_id)
        specific = self._merge_status_codes(range_key, proxy_id)
        hints = [
            {"code": code, "hint": hint}
            for code, hint in STATUS_HINTS.items()
            if int(specific.get(code, 0)) > 0
        ]
        return {
            "range": range_key,
            "groups": {
                "2xx": totals["status_2xx"],
                "3xx": totals["status_3xx"],
                "4xx": totals["status_4xx"],
                "5xx": totals["status_5xx"],
            },
            "specific": specific,
            "hints": hints,
            "top_errors": sorted(
                ((code, count) for code, count in specific.items() if code.startswith(("4", "5"))),
                key=lambda item: item[1],
                reverse=True,
            )[:10],
        }

    def proxy_hosts(self, range_key: str = "24h", sort_by: str = "requests") -> dict:
        health = self.health.get_dashboard()
        servers_by_pool = {}
        pools, _ = self.pools.list_pools(page_size=1000)
        for pool in pools:
            servers_by_pool[pool.id] = [s for s in health.servers if s.pool_id == pool.id]
        items = []
        for proxy in self.proxies.list_proxies():
            totals = self._sum_traffic(range_key, proxy.id)
            pool_status = "healthy"
            for pool in pools:
                if pool.proxy_id == proxy.id:
                    pool_servers = servers_by_pool.get(pool.id, [])
                    if any(s.health_status.value == "offline" for s in pool_servers):
                        pool_status = "offline"
                    elif any(s.health_status.value == "warning" for s in pool_servers):
                        pool_status = "warning"
            items.append(
                {
                    "proxy_id": proxy.id,
                    "domains": proxy.domains,
                    "requests": totals["requests"],
                    "bandwidth": totals["bytes_in"] + totals["bytes_out"],
                    "error_count": totals["status_4xx"] + totals["status_5xx"],
                    "error_rate": totals["error_rate"],
                    "avg_response_time_ms": totals["avg_response_time_ms"],
                    "active_connections": 0,
                    "backend_pool_status": pool_status,
                    "enabled": proxy.enabled,
                }
            )
        sort_key = {
            "errors": lambda item: item["error_count"],
            "error_rate": lambda item: item["error_rate"],
            "response_time": lambda item: item["avg_response_time_ms"],
            "bandwidth": lambda item: item["bandwidth"],
        }.get(sort_by, lambda item: item["requests"])
        items.sort(key=sort_key, reverse=True)
        return {"range": range_key, "items": items}

    def client_ips(self, range_key: str = "24h", limit: int = 50) -> dict:
        merged: dict[str, dict] = {}
        for proxy in self.proxies.list_proxies():
            for ip, count in self.traffic._merge_top_json(proxy.id, range_key, "top_clients_json").items():
                entry = merged.setdefault(ip, {"requests": 0, "bandwidth": 0, "errors": 0})
                entry["requests"] += count
        events = (
            self.db.query(RequestEvent)
            .filter(RequestEvent.timestamp >= resolve_range(range_key).start)
            .order_by(RequestEvent.timestamp.desc())
            .limit(5000)
            .all()
        )
        for event in events:
            entry = merged.setdefault(event.client_ip, {"requests": 0, "bandwidth": 0, "errors": 0})
            entry["bandwidth"] += event.bytes_sent
            if event.is_failed:
                entry["errors"] += 1
            entry["last_seen"] = event.timestamp.isoformat()
            entry["user_agent"] = event.user_agent[:120]
        items = [
            {"client_ip": ip, **data}
            for ip, data in sorted(merged.items(), key=lambda item: item[1]["requests"], reverse=True)[:limit]
        ]
        return {"range": range_key, "items": items}

    def backends(self, range_key: str = "24h") -> dict:
        dashboard = self.health.get_dashboard()
        history_rows = (
            self.db.query(BackendMetric)
            .filter(BackendMetric.timestamp >= resolve_range(range_key).start)
            .order_by(BackendMetric.timestamp.asc())
            .all()
        )
        history_by_server: dict[int, list] = {}
        for row in history_rows:
            history_by_server.setdefault(row.backend_server_id, []).append(
                {
                    "timestamp": row.timestamp.isoformat(),
                    "response_time_ms": row.response_time_ms,
                    "status": row.status,
                    "errors": row.errors,
                }
            )
        items = []
        for server in dashboard.servers:
            items.append(
                {
                    "backend_server_id": server.id,
                    "name": server.name,
                    "host": server.host,
                    "port": server.port,
                    "protocol": server.protocol,
                    "status": server.health_status.value,
                    "response_time_ms": server.response_ms or 0.0,
                    "uptime_percent_24h": server.uptime_percent_24h or 0.0,
                    "history": history_by_server.get(server.id, []),
                }
            )
        return {"range": range_key, "items": items}

    def connections(self, range_key: str = "24h") -> dict:
        rows = (
            self.db.query(ConnectionMetric)
            .filter(ConnectionMetric.timestamp >= resolve_range(range_key).start)
            .order_by(ConnectionMetric.timestamp.asc())
            .all()
        )
        latest = ConnectionMetricService(self.settings, self.db).latest()
        return {
            "range": range_key,
            "latest": {
                "active": latest.active if latest else 0,
                "reading": latest.reading if latest else 0,
                "writing": latest.writing if latest else 0,
                "waiting": latest.waiting if latest else 0,
                "accepts": latest.accepts if latest else 0,
                "handled": latest.handled if latest else 0,
                "requests": latest.requests if latest else 0,
            },
            "series": [
                {
                    "timestamp": row.timestamp.isoformat(),
                    "active": row.active,
                    "reading": row.reading,
                    "writing": row.writing,
                    "waiting": row.waiting,
                }
                for row in rows
            ],
        }

    def ssl_stats(self) -> dict:
        certs = self.certs.list_certificates()
        expiring_soon = [cert for cert in certs if cert.status == "expiring"]
        expired = [cert for cert in certs if cert.status == "expired"]
        return {
            "total": len(certs),
            "valid": len(certs) - len(expiring_soon) - len(expired),
            "expiring_soon": len(expiring_soon),
            "expired": len(expired),
            "items": [
                {
                    "domain": cert.domains[0] if cert.domains else cert.name,
                    "status": cert.status,
                    "days_remaining": max(
                        0,
                        int((cert.expiry.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds() // 86400),
                    ),
                    "issuer": cert.issuer,
                    "expires_at": cert.expiry.isoformat(),
                }
                for cert in certs
            ],
        }

    def security(self, range_key: str = "24h") -> dict:
        start = resolve_range(range_key).start
        events, _ = SecurityEventService(self.db).list_events(
            page=1, page_size=200, from_dt=start
        )
        filtered = events
        by_type: dict[str, int] = {}
        by_ip: dict[str, int] = {}
        for event in filtered:
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1
            if event.client_ip:
                by_ip[event.client_ip] = by_ip.get(event.client_ip, 0) + 1
        return {
            "range": range_key,
            "total_events": len(filtered),
            "failed_logins": by_type.get("login_failed", 0),
            "rate_limited": by_type.get("rate_limited", 0),
            "blocked_ips": by_type.get("ip_blocked", 0),
            "top_blocked_ips": sorted(by_ip.items(), key=lambda item: item[1], reverse=True)[:10],
            "recent_events": [event.model_dump() for event in filtered[:20]],
        }

    def live_requests(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        domain: str | None = None,
        status: int | None = None,
        client_ip: str | None = None,
        search: str | None = None,
        errors_only: bool = False,
    ) -> dict:
        query = self.db.query(RequestEvent)
        if domain:
            query = query.filter(RequestEvent.host.contains(domain))
        if status is not None:
            query = query.filter(RequestEvent.status == status)
        if client_ip:
            query = query.filter(RequestEvent.client_ip == client_ip)
        if search:
            query = query.filter(RequestEvent.uri.contains(search))
        if errors_only:
            query = query.filter(RequestEvent.is_failed.is_(True))
        total = query.count()
        rows = (
            query.order_by(RequestEvent.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "timestamp": row.timestamp.isoformat(),
                    "client_ip": row.client_ip,
                    "host": row.host,
                    "uri": row.uri,
                    "method": row.method,
                    "status": row.status,
                    "backend_addr": row.backend_addr,
                    "response_time_ms": row.response_time_ms,
                    "upstream_time_ms": row.upstream_time_ms,
                    "bytes_sent": row.bytes_sent,
                    "user_agent": row.user_agent,
                }
                for row in rows
            ],
        }

    def failed_requests(self, *, page: int = 1, page_size: int = 100) -> dict:
        return self.live_requests(page=page, page_size=page_size, errors_only=True)
