from typing import Optional

from sqlalchemy.orm import Session

from app.config import Settings
from app.schemas import AnalyticsProxyResponse, AnalyticsSummaryItem, AnalyticsSummaryResponse
from app.services.proxy_traffic_service import ProxyTrafficService


def _top_n(counts: dict[str, int], limit: int = 10) -> dict[str, int]:
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit])


class AnalyticsService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.traffic = ProxyTrafficService(settings, db)

    def get_summary(self, range_key: str = "24h") -> AnalyticsSummaryResponse:
        items = [
            AnalyticsSummaryItem(**item)
            for item in self.traffic.list_analytics_summary(range_key)
        ]
        return AnalyticsSummaryResponse(range=range_key, items=items)

    def get_proxy_analytics(self, proxy_id: str, range_key: str = "24h") -> Optional[AnalyticsProxyResponse]:
        data = self.traffic.get_proxy_analytics_data(proxy_id, range_key)
        if not data:
            return None
        return AnalyticsProxyResponse(
            proxy_id=data["proxy_id"],
            proxy_name=data["proxy_name"],
            domains=data["domains"],
            range=data["range"],
            requests=data["requests"],
            rps=data["rps"],
            latency_avg_ms=data["latency_avg_ms"],
            upstream_latency_avg_ms=data["upstream_latency_avg_ms"],
            error_rate=data["error_rate"],
            status_2xx=data["status_2xx"],
            status_3xx=data["status_3xx"],
            status_4xx=data["status_4xx"],
            status_5xx=data["status_5xx"],
            bytes_in=data["bytes_in"],
            bytes_out=data["bytes_out"],
            top_clients=_top_n(data["top_clients"]),
            top_paths=_top_n(data["top_paths"]),
            history=data["history"],
        )
