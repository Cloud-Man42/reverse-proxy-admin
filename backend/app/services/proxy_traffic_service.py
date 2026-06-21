import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.metrics import RequestEvent
from app.models.proxy_traffic import ProxyTrafficAggregate, ProxyTrafficLogState
from app.schemas import ProxyTrafficHistoryPoint, ProxyTrafficStatsResponse, ProxyTrafficSummary
from app.services.access_log_parser import parse_access_line
from app.services.error_log_parser import classify_failed_request
from app.services.log_reader import LogReader
from app.services.metrics_settings_service import MetricsSettingsService
from app.services.proxy_service import ProxyService


def _status_bucket(status: int) -> str:
    if 200 <= status < 300:
        return "status_2xx"
    if 300 <= status < 400:
        return "status_3xx"
    if 400 <= status < 500:
        return "status_4xx"
    if 500 <= status < 600:
        return "status_5xx"
    return "status_4xx"


def _merge_count_maps(existing_json: str, incoming: dict[str, int]) -> str:
    try:
        existing = json.loads(existing_json or "{}")
    except json.JSONDecodeError:
        existing = {}
    if not isinstance(existing, dict):
        existing = {}
    for key, count in incoming.items():
        existing[key] = int(existing.get(key, 0)) + count
    return json.dumps(existing)


def _merge_status_codes(existing_json: str, incoming: dict[str, int]) -> str:
    try:
        existing = json.loads(existing_json or "{}")
    except json.JSONDecodeError:
        existing = {}
    if not isinstance(existing, dict):
        existing = {}
    for key, count in incoming.items():
        existing[str(key)] = int(existing.get(str(key), 0)) + int(count)
    return json.dumps(existing)


def _new_bucket() -> dict:
    return {
        "requests": 0,
        "bytes_in": 0,
        "bytes_out": 0,
        "upstream_bytes_in": 0,
        "upstream_bytes_out": 0,
        "latency_sum_ms": 0.0,
        "latency_count": 0,
        "upstream_latency_sum_ms": 0.0,
        "upstream_latency_count": 0,
        "max_response_time_ms": 0.0,
        "status_2xx": 0,
        "status_3xx": 0,
        "status_4xx": 0,
        "status_5xx": 0,
        "status_codes": {},
        "top_clients": {},
        "top_paths": {},
    }


def _apply_parsed_line(totals: dict, parsed) -> None:
    totals["requests"] += 1
    totals["bytes_in"] += parsed.bytes_in or 0
    totals["bytes_out"] += parsed.bytes_sent or 0
    totals["upstream_bytes_in"] += parsed.upstream_bytes_in or 0
    totals["upstream_bytes_out"] += parsed.upstream_bytes_out or 0
    totals[_status_bucket(parsed.status)] += 1
    totals["status_codes"][str(parsed.status)] = totals["status_codes"].get(str(parsed.status), 0) + 1
    if parsed.request_time is not None:
        latency_ms = parsed.request_time * 1000
        totals["latency_sum_ms"] += latency_ms
        totals["latency_count"] += 1
        totals["max_response_time_ms"] = max(totals["max_response_time_ms"], latency_ms)
    if parsed.upstream_response_time is not None:
        totals["upstream_latency_sum_ms"] += parsed.upstream_response_time * 1000
        totals["upstream_latency_count"] += 1
    totals["top_clients"][parsed.client_ip] = totals["top_clients"].get(parsed.client_ip, 0) + 1
    totals["top_paths"][parsed.path] = totals["top_paths"].get(parsed.path, 0) + 1


def _weighted_avg_ms(existing_avg: float, existing_count: int, new_sum: float, new_count: int) -> float:
    total_count = existing_count + new_count
    if total_count <= 0:
        return 0.0
    existing_sum = existing_avg * existing_count
    return (existing_sum + new_sum) / total_count


class ProxyTrafficService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db
        self.reader = LogReader(settings)
        self.proxies = ProxyService(settings, db)

    def proxy_log_path(self, proxy_id: str) -> Path:
        return self.settings.nginx_access_log.parent / f"proxy-{proxy_id}.log"

    def collect_all(self) -> int:
        processed = 0
        for proxy in self.proxies.list_proxies():
            processed += self.collect_proxy(proxy.id)
        self.db.commit()
        return processed

    def collect_proxy(self, proxy_id: str) -> int:
        log_path = self.proxy_log_path(proxy_id)
        if not log_path.exists():
            return 0

        state = self.db.get(ProxyTrafficLogState, proxy_id)
        if state is None:
            state = ProxyTrafficLogState(proxy_id=proxy_id, byte_offset=0)
            self.db.add(state)

        file_size = log_path.stat().st_size
        if state.byte_offset > file_size:
            state.byte_offset = 0

        lines, new_offset = self.reader.read_from_offset(log_path, state.byte_offset)
        if not lines:
            state.updated_at = datetime.utcnow()
            return 0

        bucket_totals: dict[tuple[str, datetime], dict] = {}
        metrics_settings = MetricsSettingsService(self.db).get_or_create()
        sample_mod = max(metrics_settings.request_event_sample_rate, 1)
        parsed_count = 0
        for line in lines:
            parsed = parse_access_line(line)
            if not parsed:
                continue
            parsed_count += 1
            ts = parsed.timestamp or datetime.utcnow()
            if ts.tzinfo is not None:
                ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
            hour_start = ts.replace(minute=0, second=0, microsecond=0)
            minute_start = ts.replace(second=0, microsecond=0)
            for period_type, period_start in (("hour", hour_start), ("minute", minute_start)):
                totals = bucket_totals.setdefault((period_type, period_start), _new_bucket())
                _apply_parsed_line(totals, parsed)
            if parsed_count % sample_mod == 0:
                failed, hint = classify_failed_request(parsed.status)
                self.db.add(
                    RequestEvent(
                        timestamp=ts,
                        proxy_id=proxy_id,
                        client_ip=parsed.client_ip,
                        host=parsed.host,
                        method=parsed.method,
                        uri=parsed.path,
                        status=parsed.status,
                        backend_addr=parsed.upstream_addr or "",
                        response_time_ms=(parsed.request_time or 0) * 1000,
                        upstream_time_ms=(parsed.upstream_response_time or 0) * 1000,
                        bytes_sent=parsed.bytes_sent,
                        user_agent=(parsed.user_agent or "")[:512],
                        is_failed=failed,
                        error_hint=hint or None,
                    )
                )

        for (period_type, period_start), totals in bucket_totals.items():
            self._upsert_aggregate(proxy_id, period_start, totals, period_type=period_type)

        state.byte_offset = new_offset
        state.updated_at = datetime.utcnow()
        self.db.commit()
        return parsed_count

    def _upsert_aggregate(
        self, proxy_id: str, period_start: datetime, totals: dict, *, period_type: str = "hour"
    ) -> None:
        delta = timedelta(hours=1) if period_type == "hour" else timedelta(minutes=1)
        period_end = period_start + delta
        existing = (
            self.db.query(ProxyTrafficAggregate)
            .filter(
                ProxyTrafficAggregate.proxy_id == proxy_id,
                ProxyTrafficAggregate.period_start == period_start,
                ProxyTrafficAggregate.period_type == period_type,
            )
            .first()
        )
        incoming_latency_avg = (
            totals["latency_sum_ms"] / totals["latency_count"] if totals["latency_count"] else 0.0
        )
        incoming_upstream_latency_avg = (
            totals["upstream_latency_sum_ms"] / totals["upstream_latency_count"]
            if totals["upstream_latency_count"]
            else 0.0
        )
        if existing:
            prev_requests = existing.requests
            existing.requests += totals["requests"]
            existing.bytes_in += totals["bytes_in"]
            existing.bytes_out += totals["bytes_out"]
            existing.upstream_bytes_in += totals["upstream_bytes_in"]
            existing.upstream_bytes_out += totals["upstream_bytes_out"]
            existing.status_2xx += totals["status_2xx"]
            existing.status_3xx += totals["status_3xx"]
            existing.status_4xx += totals["status_4xx"]
            existing.status_5xx += totals["status_5xx"]
            existing.max_response_time_ms = max(
                existing.max_response_time_ms, totals.get("max_response_time_ms", 0.0)
            )
            existing.status_codes_json = _merge_status_codes(
                existing.status_codes_json, totals.get("status_codes", {})
            )
            existing.latency_avg_ms = _weighted_avg_ms(
                existing.latency_avg_ms,
                prev_requests,
                totals["latency_sum_ms"],
                totals["latency_count"],
            )
            existing.upstream_latency_avg_ms = _weighted_avg_ms(
                existing.upstream_latency_avg_ms,
                prev_requests,
                totals["upstream_latency_sum_ms"],
                totals["upstream_latency_count"],
            )
            existing.top_clients_json = _merge_count_maps(existing.top_clients_json, totals["top_clients"])
            existing.top_paths_json = _merge_count_maps(existing.top_paths_json, totals["top_paths"])
            existing.period_end = period_end
            return

        self.db.add(
            ProxyTrafficAggregate(
                proxy_id=proxy_id,
                period_start=period_start,
                period_end=period_end,
                period_type=period_type,
                requests=totals["requests"],
                bytes_in=totals["bytes_in"],
                bytes_out=totals["bytes_out"],
                upstream_bytes_in=totals["upstream_bytes_in"],
                upstream_bytes_out=totals["upstream_bytes_out"],
                latency_avg_ms=incoming_latency_avg,
                upstream_latency_avg_ms=incoming_upstream_latency_avg,
                max_response_time_ms=totals.get("max_response_time_ms", 0.0),
                status_2xx=totals["status_2xx"],
                status_3xx=totals["status_3xx"],
                status_4xx=totals["status_4xx"],
                status_5xx=totals["status_5xx"],
                status_codes_json=json.dumps(totals.get("status_codes", {})),
                top_clients_json=json.dumps(totals["top_clients"]),
                top_paths_json=json.dumps(totals["top_paths"]),
            )
        )

    def _range_start(self, range_key: str) -> datetime:
        now = datetime.utcnow()
        if range_key == "15m":
            return now - timedelta(minutes=15)
        if range_key == "1h":
            return now - timedelta(hours=1)
        if range_key == "7d":
            return now - timedelta(days=7)
        if range_key == "30d":
            return now - timedelta(days=30)
        return now - timedelta(hours=24)

    def _aggregate_period_type(self, range_key: str) -> str:
        if range_key in ("15m", "1h"):
            return "minute"
        return "hour"

    def _range_seconds(self, range_key: str) -> float:
        if range_key == "15m":
            return 15 * 60
        if range_key == "1h":
            return 3600
        if range_key == "7d":
            return 7 * 86400
        if range_key == "30d":
            return 30 * 86400
        return 86400

    def _sum_aggregates(self, proxy_id: str, range_key: str) -> dict:
        start = self._range_start(range_key)
        period_type = self._aggregate_period_type(range_key)
        row = (
            self.db.query(
                func.coalesce(func.sum(ProxyTrafficAggregate.requests), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.bytes_in), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.bytes_out), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.upstream_bytes_in), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.upstream_bytes_out), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.status_2xx), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.status_3xx), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.status_4xx), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.status_5xx), 0),
            )
            .filter(
                ProxyTrafficAggregate.proxy_id == proxy_id,
                ProxyTrafficAggregate.period_start >= start,
                ProxyTrafficAggregate.period_type == period_type,
            )
            .one()
        )
        latency_row = (
            self.db.query(
                func.coalesce(
                    func.sum(ProxyTrafficAggregate.latency_avg_ms * ProxyTrafficAggregate.requests),
                    0.0,
                ),
                func.coalesce(
                    func.sum(ProxyTrafficAggregate.upstream_latency_avg_ms * ProxyTrafficAggregate.requests),
                    0.0,
                ),
                func.coalesce(func.sum(ProxyTrafficAggregate.requests), 0),
            )
            .filter(
                ProxyTrafficAggregate.proxy_id == proxy_id,
                ProxyTrafficAggregate.period_start >= start,
                ProxyTrafficAggregate.period_type == period_type,
            )
            .one()
        )
        total_requests = int(latency_row[2])
        return {
            "connections": int(row[0]),
            "bytes_in": int(row[1]),
            "bytes_out": int(row[2]),
            "upstream_bytes_in": int(row[3]),
            "upstream_bytes_out": int(row[4]),
            "status_2xx": int(row[5]),
            "status_3xx": int(row[6]),
            "status_4xx": int(row[7]),
            "status_5xx": int(row[8]),
            "latency_avg_ms": float(latency_row[0]) / total_requests if total_requests else 0.0,
            "upstream_latency_avg_ms": float(latency_row[1]) / total_requests if total_requests else 0.0,
        }

    def _merge_top_json(self, proxy_id: str, range_key: str, field: str) -> dict[str, int]:
        start = self._range_start(range_key)
        period_type = self._aggregate_period_type(range_key)
        rows = (
            self.db.query(getattr(ProxyTrafficAggregate, field))
            .filter(
                ProxyTrafficAggregate.proxy_id == proxy_id,
                ProxyTrafficAggregate.period_start >= start,
                ProxyTrafficAggregate.period_type == period_type,
            )
            .all()
        )
        merged: dict[str, int] = {}
        for (raw,) in rows:
            try:
                data = json.loads(raw or "{}")
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            for key, count in data.items():
                merged[str(key)] = merged.get(str(key), 0) + int(count)
        return merged

    def get_proxy_stats(self, proxy_id: str, range_key: str = "24h") -> Optional[ProxyTrafficStatsResponse]:
        proxy = self.proxies.get_proxy(proxy_id)
        if not proxy:
            return None
        totals = self._sum_aggregates(proxy_id, range_key)
        history = self._history_points(proxy_id, range_key)
        return ProxyTrafficStatsResponse(
            proxy_id=proxy.id,
            proxy_name=proxy.name,
            domains=proxy.domains,
            range=range_key,
            connections=totals["connections"],
            bytes_in=totals["bytes_in"],
            bytes_out=totals["bytes_out"],
            upstream_bytes_in=totals["upstream_bytes_in"],
            upstream_bytes_out=totals["upstream_bytes_out"],
            history=history,
        )

    def get_proxy_analytics_data(self, proxy_id: str, range_key: str = "24h") -> Optional[dict]:
        proxy = self.proxies.get_proxy(proxy_id)
        if not proxy:
            return None
        totals = self._sum_aggregates(proxy_id, range_key)
        requests = totals["connections"]
        errors = totals["status_4xx"] + totals["status_5xx"]
        return {
            "proxy_id": proxy.id,
            "proxy_name": proxy.name,
            "domains": proxy.domains,
            "range": range_key,
            "requests": requests,
            "rps": requests / self._range_seconds(range_key) if requests else 0.0,
            "latency_avg_ms": totals["latency_avg_ms"],
            "upstream_latency_avg_ms": totals["upstream_latency_avg_ms"],
            "error_rate": errors / requests if requests else 0.0,
            "status_2xx": totals["status_2xx"],
            "status_3xx": totals["status_3xx"],
            "status_4xx": totals["status_4xx"],
            "status_5xx": totals["status_5xx"],
            "bytes_in": totals["bytes_in"],
            "bytes_out": totals["bytes_out"],
            "top_clients": self._merge_top_json(proxy_id, range_key, "top_clients_json"),
            "top_paths": self._merge_top_json(proxy_id, range_key, "top_paths_json"),
            "history": self._history_points(proxy_id, range_key),
        }

    def _history_points(self, proxy_id: str, range_key: str) -> list[ProxyTrafficHistoryPoint]:
        start = self._range_start(range_key)
        period_type = self._aggregate_period_type(range_key)
        rows = (
            self.db.query(ProxyTrafficAggregate)
            .filter(
                ProxyTrafficAggregate.proxy_id == proxy_id,
                ProxyTrafficAggregate.period_start >= start,
                ProxyTrafficAggregate.period_type == period_type,
            )
            .order_by(ProxyTrafficAggregate.period_start.asc())
            .all()
        )
        return [
            ProxyTrafficHistoryPoint(
                timestamp=row.period_start,
                connections=row.requests,
                bytes_in=row.bytes_in,
                bytes_out=row.bytes_out,
            )
            for row in rows
        ]

    def total_bytes(self, range_key: str = "24h") -> tuple[int, int]:
        start = self._range_start(range_key)
        period_type = self._aggregate_period_type(range_key)
        row = (
            self.db.query(
                func.coalesce(func.sum(ProxyTrafficAggregate.bytes_in), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.bytes_out), 0),
            )
            .filter(
                ProxyTrafficAggregate.period_start >= start,
                ProxyTrafficAggregate.period_type == period_type,
            )
            .one()
        )
        return int(row[0]), int(row[1])

    def aggregate_history(self, range_key: str = "24h") -> list[ProxyTrafficHistoryPoint]:
        start = self._range_start(range_key)
        rows = (
            self.db.query(
                ProxyTrafficAggregate.period_start,
                func.coalesce(func.sum(ProxyTrafficAggregate.requests), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.bytes_in), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.bytes_out), 0),
            )
            .filter(
                ProxyTrafficAggregate.period_start >= start,
                ProxyTrafficAggregate.period_type == "hour",
            )
            .group_by(ProxyTrafficAggregate.period_start)
            .order_by(ProxyTrafficAggregate.period_start.asc())
            .all()
        )
        return [
            ProxyTrafficHistoryPoint(
                timestamp=row[0],
                connections=int(row[1]),
                bytes_in=int(row[2]),
                bytes_out=int(row[3]),
            )
            for row in rows
        ]

    def list_summary(self, range_key: str = "24h") -> list[ProxyTrafficSummary]:
        start = self._range_start(range_key)
        period_type = self._aggregate_period_type(range_key)
        rows = (
            self.db.query(
                ProxyTrafficAggregate.proxy_id,
                func.coalesce(func.sum(ProxyTrafficAggregate.requests), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.bytes_in), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.bytes_out), 0),
            )
            .filter(
                ProxyTrafficAggregate.period_start >= start,
                ProxyTrafficAggregate.period_type == period_type,
            )
            .group_by(ProxyTrafficAggregate.proxy_id)
            .all()
        )
        totals_by_id = {row[0]: row for row in rows}
        summaries: list[ProxyTrafficSummary] = []
        for proxy in self.proxies.list_proxies():
            row = totals_by_id.get(proxy.id)
            summaries.append(
                ProxyTrafficSummary(
                    proxy_id=proxy.id,
                    proxy_name=proxy.name,
                    domains=proxy.domains,
                    enabled=proxy.enabled,
                    connections=int(row[1]) if row else 0,
                    bytes_in=int(row[2]) if row else 0,
                    bytes_out=int(row[3]) if row else 0,
                )
            )
        return summaries

    def list_analytics_summary(self, range_key: str = "24h") -> list[dict]:
        start = self._range_start(range_key)
        period_type = self._aggregate_period_type(range_key)
        rows = (
            self.db.query(
                ProxyTrafficAggregate.proxy_id,
                func.coalesce(func.sum(ProxyTrafficAggregate.requests), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.bytes_in), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.bytes_out), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.status_2xx), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.status_3xx), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.status_4xx), 0),
                func.coalesce(func.sum(ProxyTrafficAggregate.status_5xx), 0),
                func.coalesce(
                    func.sum(ProxyTrafficAggregate.latency_avg_ms * ProxyTrafficAggregate.requests),
                    0.0,
                ),
                func.coalesce(
                    func.sum(ProxyTrafficAggregate.upstream_latency_avg_ms * ProxyTrafficAggregate.requests),
                    0.0,
                ),
            )
            .filter(
                ProxyTrafficAggregate.period_start >= start,
                ProxyTrafficAggregate.period_type == period_type,
            )
            .group_by(ProxyTrafficAggregate.proxy_id)
            .all()
        )
        totals_by_id = {row[0]: row for row in rows}
        range_seconds = self._range_seconds(range_key)
        items: list[dict] = []
        for proxy in self.proxies.list_proxies():
            row = totals_by_id.get(proxy.id)
            requests = int(row[1]) if row else 0
            errors = int(row[6]) + int(row[7]) if row else 0
            items.append(
                {
                    "proxy_id": proxy.id,
                    "proxy_name": proxy.name,
                    "domains": proxy.domains,
                    "enabled": proxy.enabled,
                    "requests": requests,
                    "rps": requests / range_seconds if requests else 0.0,
                    "bytes_in": int(row[2]) if row else 0,
                    "bytes_out": int(row[3]) if row else 0,
                    "status_2xx": int(row[4]) if row else 0,
                    "status_3xx": int(row[5]) if row else 0,
                    "status_4xx": int(row[6]) if row else 0,
                    "status_5xx": int(row[7]) if row else 0,
                    "latency_avg_ms": float(row[8]) / requests if row and requests else 0.0,
                    "upstream_latency_avg_ms": float(row[9]) / requests if row and requests else 0.0,
                    "error_rate": errors / requests if requests else 0.0,
                }
            )
        return items

    def rollup_daily(self) -> None:
        now = datetime.utcnow()
        day_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        proxy_ids = [row[0] for row in self.db.query(ProxyTrafficAggregate.proxy_id).distinct().all()]
        for proxy_id in proxy_ids:
            rows = (
                self.db.query(ProxyTrafficAggregate)
                .filter(
                    ProxyTrafficAggregate.proxy_id == proxy_id,
                    ProxyTrafficAggregate.period_type == "hour",
                    ProxyTrafficAggregate.period_start >= day_start,
                    ProxyTrafficAggregate.period_start < day_end,
                )
                .all()
            )
            if not rows:
                continue
            total_requests = sum(row.requests for row in rows)
            self.db.add(
                ProxyTrafficAggregate(
                    proxy_id=proxy_id,
                    period_start=day_start,
                    period_end=day_end,
                    period_type="day",
                    requests=total_requests,
                    bytes_in=sum(row.bytes_in for row in rows),
                    bytes_out=sum(row.bytes_out for row in rows),
                    upstream_bytes_in=sum(row.upstream_bytes_in for row in rows),
                    upstream_bytes_out=sum(row.upstream_bytes_out for row in rows),
                    latency_avg_ms=_weighted_avg_ms(
                        0.0,
                        0,
                        sum(row.latency_avg_ms * row.requests for row in rows),
                        total_requests,
                    ),
                    upstream_latency_avg_ms=_weighted_avg_ms(
                        0.0,
                        0,
                        sum(row.upstream_latency_avg_ms * row.requests for row in rows),
                        total_requests,
                    ),
                    status_2xx=sum(row.status_2xx for row in rows),
                    status_3xx=sum(row.status_3xx for row in rows),
                    status_4xx=sum(row.status_4xx for row in rows),
                    status_5xx=sum(row.status_5xx for row in rows),
                    top_clients_json=_merge_count_maps(
                        "{}",
                        {
                            key: value
                            for row in rows
                            for key, value in json.loads(row.top_clients_json or "{}").items()
                        },
                    ),
                    top_paths_json=_merge_count_maps(
                        "{}",
                        {
                            key: value
                            for row in rows
                            for key, value in json.loads(row.top_paths_json or "{}").items()
                        },
                    ),
                )
            )
        self.db.commit()
